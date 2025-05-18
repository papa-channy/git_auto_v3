from pathlib import Path
import pandas as pd
import functools
import time
import tiktoken
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.cfg import cfg
from scripts.llm_router import call_llm
from scripts.dataframe import save_df


class LLMManager:
    def __init__(self, stage: str, repo_df: pd.DataFrame, df_for_call: pd.DataFrame | None = None):
        self.stage = stage
        self.repo_df = repo_df
        self.call_count = 0
        self.config = cfg.get_llm_config(stage)
        self.model = self.config["model"][0]
        self.provider = self.config["provider"][0]
        self.params = {k: self.config[k] for k in ["temperature", "top_p", "top_k", "max_tokens"]}
        self.exchange_rate = cfg.get_usd_exchange_rate()
        self.timestamp = cfg.get_timestamp()
        self.paths = cfg.get_results_path(self.timestamp)
        self.log_file = cfg.init_log_file(self.timestamp)
        self.df_for_call = df_for_call
        self.n_files = len(df_for_call) if df_for_call is not None else len(repo_df["Diff list"].iloc[0])
        self.in_df = pd.DataFrame(columns=["prompt", "llm", "meta data", "token", "cost($)", "cost(krw)",
                                           "name4save", "save_path"])
        self.out_df = pd.DataFrame(columns=["prompt", "llm", "purpose", "Is upload", "upload pf",
                                            "token", "cost($)", "cost(krw)", "name4save", "save_path"])

    def __enter__(self):
        self._start_time = time.perf_counter()
        cfg.log(f"[{self.stage}] LLMManager 시작", self.log_file)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = round(time.perf_counter() - self._start_time, 3)
        msg = f"[{self.stage}] LLMManager 종료 (총 {elapsed}s)"
        if exc_type:
            msg += f" ❌ 예외 발생: {exc_val}"
        cfg.log(msg, self.log_file)

    def call(self, prompt: str, tag: str = "llm_call") -> str:
        enc = tiktoken.encoding_for_model("gpt-4")
        token_in = len(enc.encode(prompt))

        in_path = self._get_unique_file_path(self.paths[f"{self.stage}_in"], f"in_{tag}")
        out_path = self._get_unique_file_path(self.paths[f"{self.stage}_out"], f"out_{tag}")
        name4save = None
        save_path = None
        meta_data = f"{self.stage}:{tag}"
        purpose = f"{self.stage}_result"

        if self.df_for_call is not None and "id" in self.df_for_call.columns:
            matched = self.df_for_call[self.df_for_call["id"] == tag]
            if not matched.empty:
                row = matched.iloc[0]
                try:
                    save_path_list = row.get("save_path", [])
                    if isinstance(save_path_list, list) and len(save_path_list) >= 2:
                        in_path = Path(save_path_list[0])
                        out_path = Path(save_path_list[1])
                        save_path = save_path_list
                    name4save = row.get("name4save")
                    meta_data = row.get("meta data", meta_data)
                    purpose = row.get("purpose", purpose)
                except Exception as e:
                    cfg.log(f"[{self.stage}] {tag} 메타정보 파싱 실패: {e}", self.log_file)

        try:
            prompt_text = in_path.read_text(encoding="utf-8")
        except Exception as e:
            cfg.log(f"[{self.stage}] {tag} 입력 프롬프트 로딩 실패: {e}", self.log_file)
            return f"[ERROR] input prompt missing"

        t0 = time.perf_counter()
        try:
            response = call_llm(prompt_text, self.config, log=lambda m: cfg.log(m, self.log_file))
        except Exception as e:
            cfg.log(f"[{self.stage}] [{tag}] 호출 실패: {e}", self.log_file)
            return f"[ERROR] {e}"
        t1 = time.perf_counter()

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(response, encoding="utf-8")

        token_out = len(enc.encode(response))
        cost_in = cfg.calc_cost(self.model, token_in, "input")
        cost_out = cfg.calc_cost(self.model, token_out, "output")
        cost_in_krw = round(cost_in * self.exchange_rate, 4)
        cost_out_krw = round(cost_out * self.exchange_rate, 4)

        self.in_df.loc[len(self.in_df)] = {
            "prompt": tag, "llm": self.model, "meta data": meta_data,
            "token": token_in, "cost($)": cost_in, "cost(krw)": cost_in_krw,
            "name4save": name4save, "save_path": save_path
        }
        self.out_df.loc[len(self.out_df)] = {
            "prompt": tag, "llm": self.model, "purpose": purpose,
            "Is upload": False, "upload pf": "", "token": token_out,
            "cost($)": cost_out, "cost(krw)": cost_out_krw,
            "name4save": name4save, "save_path": save_path
        }

        return response

    def call_all(self, prompts: list[str], tags: list[str]) -> list[str]:
        results = [None] * len(prompts)

        if self.provider == "fireworks":
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(self.call, p, tag=t): i
                    for i, (p, t) in enumerate(zip(prompts, tags))
                }
                for future in as_completed(futures):
                    i = futures[future]
                    try:
                        results[i] = future.result()
                    except Exception as e:
                        results[i] = f"[ERROR] {e}"
        else:
            for i, (p, t) in enumerate(zip(prompts, tags)):
                results[i] = self.call(p, tag=t)
                time.sleep(2)

        return results

    def _get_unique_file_path(self, folder: Path, base_name: str) -> Path:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{base_name}.txt"
        counter = 1
        while path.exists():
            path = folder / f"{base_name}_{counter}.txt"
            counter += 1
        return path

    def save_all(self):
        save_df(self.in_df, self.paths["in"])
        save_df(self.out_df, self.paths["out"])
        cfg.log(f"[{self.stage}] in/out DataFrame 저장 완료", self.log_file)

