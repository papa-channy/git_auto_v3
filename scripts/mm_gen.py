import json
import uuid
import pandas as pd
from scripts.dataframe import load_df, save_df
from utils.cfg import cfg
from scripts.llm_mng import LLMManager
from pathlib import Path

CHUNK_THRESHOLDS = [(50, 3), (20, 2)]


def split_chunks(lst, n):
    avg = len(lst) / float(n)
    out, last = [], 0.0
    while last < len(lst):
        out.append(lst[int(last):int(last + avg)])
        last += avg
    return out


def clean_llm_response(response: str) -> str:
    lines = response.strip().splitlines()
    lines = [line for line in lines if not line.strip().startswith(("```", "'''"))]
    return "\n".join(lines).strip()


def build_strategy_prompt(repo_df, info_df, strategy_df, file_chunk, id_map):
    files_info = []
    for file in file_chunk:
        info_row = info_df[info_df["file"] == file].iloc[0]
        strategy_row = strategy_df[strategy_df["File"] == file].iloc[0]
        files_info.append({
            "file": file,
            "id": id_map[file],
            "file token": info_row["file token"],
            "diff token": info_row["diff token"],
            "Readme strategy": strategy_row["Readme strategy"],
            "5 latest commit": info_row["5 latest commit"]
        })

    prompt = f"""📌 Objective:
For each modified file, predict the following information in **valid JSON array format**:

Each result must correspond to a file from the list below:
{file_chunk}

Each item must include:
- "id": what I give you
- "File": exact filename from the list above
- "Required Commit Detail" (int, 1~5)
- "Component Type" (str)
- "Importance" (int, 0~10)
- "Most Related Files": up to 3 other files from the list (not including itself)

✅ Output Format (required):
List[Dict], e.g.
[
  {{
    "id": "uuid-string",
    "File": "ext_info.py",
    "Required Commit Detail": 4,
    "Component Type": "support",
    "Importance": 9,
    "Most Related Files": ["dataframe.py", "llm_router.py", "gen_msg.py"]
  }}
]

📚 Meta data per file:
{json.dumps(files_info, ensure_ascii=False)}

📂 Repository Info:
- Root: {repo_df["Root path"].iloc[0]}
- Branch: {repo_df["Current branch"].iloc[0]}
- Main: {repo_df["Main branch"].iloc[0]}
- All branches: {repo_df["Branch list"].iloc[0]}

📊 Git Change Summary:
{repo_df["Diff stat"].iloc[0]}

Return ONLY a JSON array (no explanation or comments).
"""
    return prompt


def mm_gen_main():
    timestamp = cfg.get_timestamp()
    paths = cfg.get_results_path(timestamp)
    log_file = cfg.init_log_file(timestamp)

    repo_df = load_df(paths["repo"])
    info_df = load_df(paths["info"])
    strategy_df = load_df(paths["strategy"])

    file_list = strategy_df["File"].tolist()
    if len(file_list) > 60:
        raise SystemExit("⚠️ 변경 파일 수가 60개 초과 → 작업 종료")

    # 1️⃣ UUID 미리 지정
    id_map = {file: str(uuid.uuid4()) for file in file_list}
    for file in file_list:
        idx = strategy_df[strategy_df["File"] == file].index[0]
        strategy_df.at[idx, "id"] = id_map[file]

    # 2️⃣ Chunk 분할
    for threshold, chunk_count in CHUNK_THRESHOLDS:
        if len(file_list) > threshold:
            chunks = split_chunks(file_list, chunk_count)
            cfg.log(f"📦 {len(file_list)}개 파일 → {chunk_count} 청크 분할", log_file)
            break
    else:
        chunks = [file_list]

    required_keys = {"id", "File", "Required Commit Detail", "Component Type", "Importance", "Most Related Files"}

    with LLMManager("strategy", repo_df, df_for_call=strategy_df) as llm:
        for i, chunk in enumerate(chunks):
            prompt_in = build_strategy_prompt(repo_df, info_df, strategy_df, chunk, id_map)

            name4save = f"chunk_{i+1}"
            in_path = paths["strategy_in"] / f"in_{i+1}.txt"
            out_path = paths["strategy_out"] / f"out_{i+1}.txt"
            in_path.write_text(prompt_in, encoding="utf-8")

            # 👉 임시 메타 데이터 구성
            chunk_df = pd.DataFrame([{
                "id": name4save,
                "name4save": name4save,
                "save_path": [str(in_path), str(out_path)]
            }])

            # 👉 단건이라도 DataFrame으로 넘김 (id 매칭 기반)
            llm.df_for_call = chunk_df

            try:
                response = llm.call_all([prompt_in], [name4save])[0]
                out_path.write_text(response, encoding="utf-8")  # ← 백업용 저장도 유지
                parsed = json.loads(clean_llm_response(response))

                for row in parsed:
                    if not required_keys.issubset(row):
                        cfg.log(f"⚠️ 필드 누락 → 무시됨: {row}", log_file)
                        continue

                    idx = strategy_df[strategy_df["id"] == row["id"]].index
                    if len(idx) == 0:
                        cfg.log(f"⚠️ 일치하는 ID 없음: {row['id']}", log_file)
                        continue

                    i = idx[0]
                    strategy_df.at[i, "Required Commit Detail"] = row["Required Commit Detail"]
                    strategy_df.at[i, "Component Type"] = row["Component Type"]
                    strategy_df.at[i, "Importance"] = row["Importance"]
                    strategy_df.at[i, "Most Related Files"] = row["Most Related Files"]

            except json.JSONDecodeError as e:
                cfg.log(f"❌ JSON 파싱 실패: {e}", log_file)
                cfg.log(f"응답 내용:\n{response}", log_file)
                raise SystemExit("🚫 LLM 응답 파싱 실패 → JSON 헤더 제거 여부 확인 필요")
            except Exception as e:
                cfg.log(f"❌ LLM 호출 실패: {e}", log_file)
                raise SystemExit("🚫 LLM 호출 실패 → 파이프라인 중단")

    save_df(strategy_df, paths["strategy"])
    cfg.log("✅ 전략 결과 및 프롬프트 저장 완료", log_file)
