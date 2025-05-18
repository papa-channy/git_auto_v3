import json
from pathlib import Path
import pandas as pd
from scripts.dataframe import load_df, save_df
from utils.cfg import cfg

def classify_file_strategy(row: pd.Series) -> str:
    file_tok = row.get("file token", 0) or 0
    diff_tok = row.get("diff token", 0) or 0

    if file_tok <= 300 and diff_tok <= 200:
        return "full_pass"
    elif file_tok <= 800:
        return "mid_focus"
    return "keyword_only"

def fst_mapper_main():
    timestamp = cfg.get_timestamp()
    paths = cfg.get_results_path(timestamp)
    log_file = cfg.init_log_file(timestamp)

    df = load_df(paths["strategy"])
    if df is None or df.empty:
        cfg.log("⚠️ strategy_df 불러오기 실패 또는 빈 상태", log_file)
        return

    # 📊 전략 기준 로그
    cfg.log("📊 분류 기준: full_pass ≤ 300/200, mid_focus ≤ 800", log_file)

    # ✅ 파일 전략 분류
    df["File strategy"] = df.apply(classify_file_strategy, axis=1)
    cfg.log("✅ File strategy 분류 완료", log_file)

    # 📈 전략 분포 로그 출력
    strategy_stats = df["File strategy"].value_counts().to_string()
    cfg.log(f"📊 전략 분포:\n{strategy_stats}", log_file)

    # ⚠️ 중요도 9 이상 수집
    review_files = df[df["Importance"].fillna(0) >= 9]["File"].tolist()
    review_path = paths["strategy"].parent / "manual_review.json"
    with open(review_path, "w", encoding="utf-8") as f:
        json.dump(review_files, f, ensure_ascii=False, indent=2)
    cfg.log(f"⚠️ 중요도 9 이상 파일 {len(review_files)}개 기록 완료 → {review_path}", log_file)

    # 💾 결과 저장
    save_df(df, paths["strategy"])
    cfg.log("✅ strategy_df 저장 완료", log_file)
