from datetime import datetime
import os
import json
import pandas as pd
import tiktoken
from scripts.dataframe import (
    load_df, save_df,
    REPO_PATH, INFO_PATH, STRATEGY_PATH, PROMPT_PATH,
    init_prompt_df
)
from scripts.llm_router import call_llm


def split_chunks(lst, n):
    avg = len(lst) / float(n)
    out = []
    last = 0.0
    while last < len(lst):
        out.append(lst[int(last):int(last + avg)])
        last += avg
    return out


def log(message: str, log_file: str):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")


def build_strategy_pp(repo_df, info_df, strategy_df, file_chunk):
    files_info = info_df[info_df["FILE"].isin(file_chunk)].to_dict(orient="records")
    readme_map = {row["FILE"]: row["readme strategy"] for _, row in strategy_df.iterrows()}
    readme_summary = {f["FILE"]: readme_map[f["FILE"]] for f in file_chunk}
    recent_commits = info_df[info_df["FILE"].isin(file_chunk)]["5 LATEST COMMIT"].to_dict()

    prompt = f"""
Objective:
For each modified file, predict the following information in JSON format:
- Required Commit Detail (int, 1~5)
- Component Type
- Importance (int, 0~10)
- Most Related Files (list[str], up to 3)

JSON Example:
[
  {{
    "file": "ext_info.py",
    "Required Commit Detail": 4,
    "Component Type": "support",
    "Importance": 9,
    "Most Related Files": ["dataframe.py", "llm_router.py", "gen_msg.py"]
  }},
  ...
]

Output Format (follow strictly):
[
  {{
    "file": str,
    "Required Commit Detail": int,
    "Component Type": str,
    "Importance": int,
    "Most Related Files": list[str]
  }},
  ...
]

Reference for Required Commit Detail:
- Main branch: {repo_df["Main branch"].iloc[0]}
- Current branch: {repo_df["Current branch"].iloc[0]}
- Branch list: {repo_df["Branch list"].iloc[0]}
- Change Overview: {repo_df["Change Overview"].iloc[0]}

Structure:
{repo_df["Root path"].iloc[0]}

README summary:
{json.dumps(readme_summary, ensure_ascii=False)}

Last 5 commit:
{json.dumps(recent_commits, ensure_ascii=False)}

File meta:
{json.dumps(files_info, ensure_ascii=False)}
"""

    return prompt

# 🎯 전체 실행 함수
def mm_gen_main():
    repo_df = load_df(REPO_PATH)
    info_df = load_df(INFO_PATH)
    strategy_df = load_df(STRATEGY_PATH)
    prompt_df = init_prompt_df()

    file_list = strategy_df["FILE"].tolist()
    n = len(file_list)

    if n > 60:
        raise SystemExit("⚠️ 변경 FILE 수가 60개 초과 → 작업 종료")

    chunks = (
        split_chunks(file_list, 3) if n > 50 else
        split_chunks(file_list, 2) if n > 20 else
        [file_list]
    )

    all_results = []
    enc = tiktoken.encoding_for_model("gpt-4")

    timestamp = datetime.now().strftime("%y%m%d_%H%M")
    log_dir = f"logs/{timestamp}"
    os.makedirs(log_dir, exist_ok=True)
    log_file = f"{log_dir}/trigger.log"

    for chunk in chunks:
        st_pp_in = build_strategy_pp(repo_df, info_df, strategy_df, chunk)

        in_path = f"{log_dir}/st_pp_in.txt"
        with open(in_path, "w", encoding="utf-8") as f:
            f.write(st_pp_in)
        log(f"✅ 프롬프트 생성 완료: {in_path}", log_file)

        token_in = len(enc.encode(st_pp_in))
        prompt_df.loc[len(prompt_df)] = {
            "IN/OUT": "입력",
            "VAR NAME": "st_pp_in",
            "MODEL NAME": "gpt-4o",
            "meta(in)or purpose(out)": "폴더 구조, README STRATEGY, 변경 FILE 목록, 5 LATEST COMMIT, 브랜치 정보, 변경 요약 통계, FILE 유형, FILE 위치",
            "SAVE PATH": in_path,
            "I": False,
            "upload platform": "",
            "token값": token_in,
            "비용($)": None,
            "비용(krw)": None
        }

        response = call_llm(prompt=st_pp_in, model="gpt-4o")
        out_path = f"{log_dir}/st_pp_out.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(response)
        log(f"✅ GPT-4o 응답 저장 완료: {out_path}", log_file)

        token_out = len(enc.encode(response))
        prompt_df.loc[len(prompt_df)] = {
            "IN/OUT": "출력",
            "VAR NAME": "st_pp_out",
            "사용 MODEL NAME": "gpt-4o",
            "meta(in)or purpose(out)": "strategy_df_value",
            "SAVE PATH": out_path,
            "업로드 여부": False,
            "upload platform": "",
            "token값": token_out,
            "비용($)": None,
            "비용(krw)": None
        }

        parsed = json.loads(response)
        log("✅ 파싱 성공 및 strategy_df 반영 중...", log_file)
        all_results.extend(parsed)

    for row in all_results:
        idx = strategy_df[strategy_df["FILE"] == row["FILE"]].index[0]
        strategy_df.at[idx, "작성 디테일 등급"] = row["작성 디테일 등급"]
        strategy_df.at[idx, "기능 유형"] = row["기능 유형"]
        strategy_df.at[idx, "IMPORTANCE"] = row["IMPORTANCE"]
        strategy_df.at[idx, "연관도 높은 FILE 리스트"] = row["연관도 높은 FILE 리스트"]

    save_df(strategy_df, STRATEGY_PATH)
    save_df(prompt_df, PROMPT_PATH)
    log("✅ 전략 결과 및 프롬프트 추적 저장 완료", log_file)