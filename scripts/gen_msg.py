from datetime import datetime
import os
import json
import time
import tiktoken
from pathlib import Path
from scripts.dataframe import load_df, save_df, REPO_PATH, INFO_PATH, STRATEGY_PATH, PROMPT_PATH, init_prompt_df
from scripts.llm_router import call_llm

def log(message: str, log_file: Path):
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")

def gen_msg_main():
    repo_df = load_df(REPO_PATH)
    info_df = load_df(INFO_PATH)
    strategy_df = load_df(STRATEGY_PATH)
    prompt_df = init_prompt_df()

    # 설정 로딩
    style = json.loads(Path("config/style.json").read_text(encoding="utf-8"))
    llm_cfgs = json.loads(Path("config/llm.json").read_text(encoding="utf-8"))
    commit_style = style["style"]["commit_final"]
    commit_lang = style["language"]["commit"]
    llm_cfg = llm_cfgs["llm"]["commit_final"]

    # 로그 설정
    timestamp = datetime.now().strftime("%y%m%d_%H%M")
    log_dir = Path(f"logs/{timestamp}")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "trigger.log"
    root_path = Path(repo_df["root path"].iloc[0])
    enc = tiktoken.encoding_for_model(llm_cfg["model"][0])

    # 프롬프트 템플릿 미리 로딩
    prompt_template = Path(f"prompt/{commit_lang}/{commit_style}.txt").read_text(encoding="utf-8")

    for row in strategy_df.itertuples():
        filename = row.FILE
        file_path = root_path / "/".join(info_df[info_df["FILE"] == filename]["FILE 위치"].iloc[0])
        if not file_path.exists():
            log(f"❌ FILE 없음: {file_path}", log_file)
            continue

        # 📄 스크립트 텍스트 추출
        if row.분석_전략 == "full_pass":
            script_txt = file_path.read_text(encoding="utf-8")
        else:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            keywords = ["def ", "return ", "class ", "self", "@", "from ", "logger"]
            script_txt = "\n".join([line for line in lines if any(k in line for k in keywords)])

        # 🧠 기능 요약 텍스트 불러오기
        fx_path = log_dir / f"fx_out_{filename}.txt"
        if not fx_path.exists():
            log(f"⚠️ fx_out FILE 없음: {fx_path}", log_file)
            continue
        fx_summary = fx_path.read_text(encoding="utf-8")

        # 🧾 diff 텍스트 불러오기
        diff_var = info_df[info_df["FILE"] == filename]["diff var name"].iloc[0]
        diff_path = Path(f"results/diff_final/{diff_var}.txt")
        if not diff_path.exists():
            log(f"⚠️ diff 텍스트 없음: {diff_path}", log_file)
            continue
        diff_txt = diff_path.read_text(encoding="utf-8")

        # 📌 최근 커밋 메시지
        commit_msgs = info_df[info_df["FILE"] == filename]["5 LATEST COMMIT"].iloc[0]
        recent_commit = "\n".join(commit_msgs[:row.추출할_커밋_메시지_개수])

        # 🗂️ 폴더 구조
        tree_txt_path = Path("results/context/tree.txt")
        tree_txt = tree_txt_path.read_text(encoding="utf-8") if tree_txt_path.exists() else ""

        # 🧾 프롬프트 생성
        full_prompt = prompt_template.replace("{change}", f"""
📘 기능 요약:
{fx_summary}

📂 폴더 구조:
{tree_txt}

📄 변경된 스크립트 주요 내용:
{script_txt}

📌 최근 커밋 메시지:
{recent_commit}

🧾 변경 사항(diff):
{diff_txt}
""").strip()

        # 🔐 프롬프트 저장 및 추적
        prompt_file = log_dir / f"commit_in_{filename}.txt"
        prompt_file.write_text(full_prompt, encoding="utf-8")
        token_in = len(enc.encode(full_prompt))
        prompt_df.loc[len(prompt_df)] = {
            "IN/OUT": "입력", "VAR NAME": f"commit_in_{filename}",
            "사용 MODEL NAME": llm_cfg["model"][0],
            "meta(in)or purpose(out)": "기능 요약, 폴더 구조, 최근 커밋 메시지, 변경 스크립트, diff",
            "SAVE PATH": str(prompt_file), "업로드 여부": False,
            "upload platform": "", "token값": token_in,
            "비용($)": None, "비용(krw)": None
        }
        log(f"✅ 커밋 프롬프트 생성 완료: {prompt_file}", log_file)

        # LLM 호출
        response = call_llm(prompt=full_prompt, llm_cfg=llm_cfg, log=lambda m: log(m, log_file))
        result_file = log_dir / f"commit_out_{filename}.txt"
        result_file.write_text(response, encoding="utf-8")
        token_out = len(enc.encode(response))

        prompt_df.loc[len(prompt_df)] = {
            "IN/OUT": "출력", "VAR NAME": f"commit_out_{filename}",
            "사용 MODEL NAME": llm_cfg["model"][0],
            "meta(in)or purpose(out)": "최종 커밋 메시지 생성",
            "SAVE PATH": str(result_file), "업로드 여부": True,
            "upload platform": ["notify", "record"],
            "token값": token_out, "비용($)": None, "비용(krw)": None
        }
        log(f"✅ 커밋 메시지 생성 완료: {result_file}", log_file)

        save_df(prompt_df, PROMPT_PATH)
        time.sleep(5)

gen_msg_main()
