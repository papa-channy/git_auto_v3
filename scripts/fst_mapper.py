import json
from datetime import datetime
from pathlib import Path
from scripts.dataframe import load_df, save_df, STRATEGY_PATH


def classify_strategy(row):
    file_tok = row["file token"]
    diff_tok = row["diff token"]

    if file_tok <= 300 and diff_tok <= 200:
        return "full_pass"
    elif file_tok <= 800:
        return "mid_focus"
    else:
        return "keyword_only"


def log(message: str, log_file: str):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")


def fst_mapper_main():
    df = load_df(STRATEGY_PATH)

    timestamp = datetime.now().strftime("%y%m%d_%H%M")
    log_dir = Path(f"logs/{timestamp}")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "trigger.log"

    df["FILE STRATEGY"] = df.apply(classify_strategy, axis=1)
    log("✅ FILE STRATEGY 분류 완료", log_file)

    review_files = df[df["IMPORTANCE"] >= 9]["FILE"].tolist()
    review_path = Path(STRATEGY_PATH).parent / "manual_review.json"
    with open(review_path, "w", encoding="utf-8") as f:
        json.dump(review_files, f, ensure_ascii=False, indent=2)
    log(f"⚠️ 중요도 9 이상 FILE {len(review_files)}개 기록 완료 → {review_path}", log_file)

    save_df(df, STRATEGY_PATH)
    log("✅ strategy_df 저장 완료", log_file)
