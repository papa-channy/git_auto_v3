import os
import json
import time
import pandas as pd
import tiktoken
from datetime import datetime
from pathlib import Path
from dataframe import load_df, save_df, REPO_PATH, INFO_PATH, STRATEGY_PATH, PROMPT_PATH, init_prompt_df
from llm_router import call_llm

# 🔧 로깅 함수
def log(message: str, log_file: Path):
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")

# 🗃️ 폴더 구조 트리 문자열 생성 (숨김 파일 제외)
def generate_tree_structure(base_path):
    tree_str = ""
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        files = [f for f in files if not f.startswith('.')]
        depth = root[len(str(base_path)):].count(os.sep)
        indent = '│   ' * depth + '├── '
        tree_str += f"{indent}{Path(root).name}/\n"
        subindent = '│   ' * (depth + 1) + '├── '
        for f in files:
            tree_str += f"{subindent}{f}\n"
    return tree_str

# 📘 README 추출 함수 (H1~H2 + 첫 문단)
def extract_readme_summary(readme_path):
    with open(readme_path, encoding="utf-8") as file:
        content = file.read()
    lines = content.split("\n")
    summary = []
    capture = False
    for line in lines:
        if line.startswith("# "):
            capture = True
        elif line.startswith("## ") and capture:
            break
        if capture:
            summary.append(line)
    if len(summary) <= 1:  # H1 없으면 첫 단락
        summary = content.split("\n\n")[0]
    return "\n".join(summary).strip()

# 🔑 키워드 기반 코드 줄 추출
def extract_keywords_code(filepath):
    keywords = ("def ", "return ", "class ", "self", "@", "from ", "logger")
    with open(filepath, encoding="utf-8") as file:
        lines = file.readlines()
    return ''.join([line for line in lines if any(kw in line for kw in keywords)])

# ⚙️ main 실행 함수
def fx_elab_main():
    repo_df = load_df(REPO_PATH)
    info_df = load_df(INFO_PATH)
    strategy_df = load_df(STRATEGY_PATH)
    prompt_df = init_prompt_df()

    timestamp = datetime.now().strftime("%y%m%d_%H%M")
    log_dir = Path(f"logs/{timestamp}")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "trigger.log"
    
    root_path = Path(repo_df["루트 path"].iloc[0])
    tree_structure = generate_tree_structure(root_path)

    enc = tiktoken.encoding_for_model("llama4-maverick-instruct-basic")

    for idx, row in strategy_df.iterrows():
        file_name = row["파일"]
        strategy = row["분석 전략"]
        file_path = root_path / '/'.join(info_df.loc[info_df["파일"] == file_name, "파일 위치"].iloc[0])
        
        # 메인 스크립트 분석 전략 적용
        if strategy == "full_pass":
            with file_path.open("r", encoding="utf-8") as file:
                main_content = file.read()
        elif strategy == "mid_focus":
            main_content = extract_keywords_code(file_path)  # 간략화된 방식 (함수 중심 추출 가능)
        else:
            main_content = extract_keywords_code(file_path)
        
        # 연관 스크립트 요약
        related_files_info = []
        for related_file in row["연관도 높은 파일 리스트"]:
            related_path = root_path / '/'.join(info_df.loc[info_df["파일"] == related_file, "파일 위치"].iloc[0])
            related_code = extract_keywords_code(related_path)
            recent_commit = info_df.loc[info_df["파일"] == related_file, "최근 커밋 메시지 5개"].iloc[0][0]
            related_files_info.append(f"{related_file}:\n{related_code}\n최근 커밋: {recent_commit}\n")

        # 최근 커밋 메시지 (메인 파일)
        recent_commits_main = info_df.loc[info_df["파일"] == file_name, "최근 커밋 메시지 5개"].iloc[0][:row["추출할 커밋 메시지 개수"]]
        
        # README 처리
        readme_strategy = row["readme 전략"]
        readme_content = ""
        readme_path = root_path / "README.md"
        if readme_strategy[0]:
            readme_content = extract_readme_summary(readme_path) if readme_strategy[1] == "summary" else readme_path.read_text(encoding="utf-8")

        # 프롬프트 생성
        fx_in = f"""
📌 요청 목적:
아래 스크립트의 주요 기능과 로직을 300 tokens 내외로 요약해주세요.
레포 전체 구조에서의 역할과 연계성을 포함해주세요.

📌 분석 파일: {file_name}
📎 기능 유형: {row["기능 유형"]}
📎 중요도 점수: {row["중요도 점수"]}

📎 메인 스크립트 내용:
{main_content}

📎 최근 커밋 메시지 (메인 파일):
{recent_commits_main}

📎 관련 스크립트 요약:
{"".join(related_files_info)}

📎 폴더 구조:
{tree_structure}

📎 README 요약:
{readme_content}
"""

        fx_in_path = log_dir / f"fx_in_{file_name}.txt"
        fx_in_path.write_text(fx_in, encoding="utf-8")

        token_in = len(enc.encode(fx_in))
        prompt_df.loc[len(prompt_df)] = {
            "입력/출력": "입력", "변수명": f"fx_in_{file_name}", "사용 모델": "llama4-maverick-instruct-basic",
            "사용한 정보(입력)or목적(출력)": "파일 내용, 관련 파일, 커밋 메시지, 폴더 구조, README",
            "저장 위치": str(fx_in_path), "업로드 여부": False, "upload platform": "",
            "token값": token_in, "비용($)": None, "비용(krw)": None
        }
        log(f"✅ 프롬프트 생성 완료: {fx_in_path}", log_file)

        # LLM 호출
        fx_out = call_llm(prompt=fx_in, model="llama4-maverick-instruct-basic")#config불러오도록 수정

        fx_out_path = log_dir / f"fx_out_{file_name}.txt"
        fx_out_path.write_text(fx_out, encoding="utf-8")

        token_out = len(enc.encode(fx_out))
        prompt_df.loc[len(prompt_df)] = {
            "입력/출력": "출력", "변수명": f"fx_out_{file_name}", "사용 모델": "llama4-maverick-instruct-basic",
            "사용한 정보(입력)or목적(출력)": "commit msg 작성 빽그라운드 제작",
            "저장 위치": str(fx_out_path), "업로드 여부": True, "upload platform": ["notify", "record"],
            "token값": token_out, "비용($)": None, "비용(krw)": None
        }
        log(f"✅ LLM 응답 저장 완료: {fx_out_path}", log_file)

        save_df(prompt_df, PROMPT_PATH)
        log("✅ prompt_df 저장 완료", log_file)

        time.sleep(5)

fx_elab_main()
