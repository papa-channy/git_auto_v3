from datetime import datetime
import os
import json
import pandas as pd
import tiktoken
from dataframe import (
    load_df, save_df,
    REPO_PATH, INFO_PATH, STRATEGY_PATH, PROMPT_PATH,
    init_prompt_df
)
from llm_router import call_llm


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
    files_info = info_df[info_df["파일"].isin(file_chunk)].to_dict(orient="records")
    readme_map = {row["파일"]: row["readme 전략"] for _, row in strategy_df.iterrows()}
    readme_summary = {f["파일"]: readme_map[f["파일"]] for f in file_chunk}
    recent_commits = info_df[info_df["파일"].isin(file_chunk)]["최근 커밋 메시지 5개"].to_dict()

    prompt = f"""
📌 요청 목적:
각 변경 파일에 대해 다음 정보를 JSON 형식으로 예측해주세요:
- 작성 디테일 등급 (int, 1~5)
- 기능 유형 (str)
- 중요도 점수 (int, 0~10)
- 연관도 높은 파일 리스트 (list[str], 최대 3개)

📌 출력 JSON 예시:
[
  {{
    "파일": "ext_info.py",
    "작성 디테일 등급": 4,
    "기능 유형": "Git 메타 수집",
    "중요도 점수": 9,
    "연관도 높은 파일 리스트": ["dataframe.py", "llm_router.py", "gen_msg.py"]
  }},
  ...
]

📌 출력 형식 (형식 엄수):
[
  {{
    "파일": str,
    "작성 디테일 등급": int,
    "기능 유형": str,
    "중요도 점수": int,
    "연관도 높은 파일 리스트": list[str]
  }},
  ...
]

📎 작성 디테일 등급 참고 정보:
- 주 브랜치: {repo_df["주 브랜치"].iloc[0]}
- 현재 브랜치: {repo_df["현재 브랜치"].iloc[0]}
- 브랜치 목록: {repo_df["브랜치 list"].iloc[0]}
- 변경 요약 통계: {repo_df["변경 요약 통계"].iloc[0]}

📎 레포 전체 폴더 구조:
{repo_df["루트 path"].iloc[0]}

📎 README 내용 요약 (파일별):
{json.dumps(readme_summary, ensure_ascii=False)}

📎 최근 커밋 메시지 5개 (파일별):
{json.dumps(recent_commits, ensure_ascii=False)}

📎 각 파일 정보:
{json.dumps(files_info, ensure_ascii=False)}
"""

    return prompt

# 🎯 전체 실행 함수
def mm_gen_main():
    repo_df = load_df(REPO_PATH)
    info_df = load_df(INFO_PATH)
    strategy_df = load_df(STRATEGY_PATH)
    prompt_df = init_prompt_df()

    file_list = strategy_df["파일"].tolist()
    n = len(file_list)

    if n > 60:
        raise SystemExit("⚠️ 변경 파일 수가 60개 초과 → 작업 종료")

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
            "입력/출력": "입력",
            "변수명": "st_pp_in",
            "사용 모델": "gpt-4o",
            "사용한 정보(입력)or목적(출력)": "폴더 구조, README 전략, 변경 파일 목록, 최근 커밋 메시지 5개, 브랜치 정보, 변경 요약 통계, 파일 유형, 파일 위치",
            "저장 위치": in_path,
            "업로드 여부": False,
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
            "입력/출력": "출력",
            "변수명": "st_pp_out",
            "사용 모델": "gpt-4o",
            "사용한 정보(입력)or목적(출력)": "strategy_df_value",
            "저장 위치": out_path,
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
        idx = strategy_df[strategy_df["파일"] == row["파일"]].index[0]
        strategy_df.at[idx, "작성 디테일 등급"] = row["작성 디테일 등급"]
        strategy_df.at[idx, "기능 유형"] = row["기능 유형"]
        strategy_df.at[idx, "중요도 점수"] = row["중요도 점수"]
        strategy_df.at[idx, "연관도 높은 파일 리스트"] = row["연관도 높은 파일 리스트"]

    save_df(strategy_df, STRATEGY_PATH)
    save_df(prompt_df, PROMPT_PATH)
    log("✅ 전략 결과 및 프롬프트 추적 저장 완료", log_file)