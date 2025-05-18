import json
from pathlib import Path
from collections import OrderedDict, defaultdict
import pandas as pd
from utils.cfg import cfg

def classify_main() -> dict:
    timestamp = cfg.get_timestamp()
    log_file = cfg.init_log_file(timestamp)
    log_dir = cfg.LOGS_DIR / timestamp

    result = {
        "commit": OrderedDict(),
        "fx_summary": OrderedDict(),
        "notify": {
            "summary": "",
            "commits": [],
            "cost_total": "",
            "cost_breakdown": {},
            "review_files": []
        }
    }

    # ✅ 커밋 메시지 수집
    for file in sorted(log_dir.glob("commit_out_*.txt")):
        filename = file.stem.replace("commit_out_", "")
        result["commit"][filename] = file.read_text(encoding="utf-8")

    # ✅ 기능 요약 수집
    for file in sorted(log_dir.glob("fx_out_*.txt")):
        filename = file.stem.replace("fx_out_", "")
        result["fx_summary"][filename] = file.read_text(encoding="utf-8")

    # ✅ 정렬된 커밋 순서 유지
    result["notify"]["commits"] = list(result["commit"].values())

    # ✅ 비용 계산
    try:
        paths = cfg.get_results_path(timestamp)
        cost_total = 0.0
        cost_breakdown = defaultdict(float)

        for path in [paths["in"], paths["out"]]:
            if not path.exists():
                continue
            df = pd.read_pickle(path)
            if df.empty or "cost(krw)" not in df.columns:
                continue

            df["cost(krw)"] = pd.to_numeric(df["cost(krw)"], errors="coerce").fillna(0)

            for meta in df["meta data"].dropna().unique():
                stage = str(meta).split(":")[0]
                stage_df = df[df["meta data"] == meta]
                stage_cost = stage_df["cost(krw)"].sum()
                cost_breakdown[stage] += stage_cost
                cost_total += stage_cost

        result["notify"]["cost_total"] = f"💸 전체 LLM 사용 비용: {cost_total:,.0f}원"
        result["notify"]["cost_breakdown"] = {
            k: f"{v:,.0f}원" for k, v in cost_breakdown.items()
        }

    except Exception as e:
        result["notify"]["cost_total"] = f"⚠️ 비용 정보 로딩 실패: {e}"

    # ✅ 중요도 높은 수동 검토 대상
    review_file = cfg.RESULTS_DIR / timestamp / "manual_review.json"
    try:
        if review_file.exists():
            result["notify"]["review_files"] = json.loads(review_file.read_text(encoding="utf-8"))
    except Exception:
        result["notify"]["review_files"] = []

    result["notify"]["summary"] = (
        f"✅ 총 {len(result['commit'])}개 파일 커밋 메시지 생성 완료, "
        f"기능 요약 {len(result['fx_summary'])}건 포함됨."
    )

    # ✅ 저장
    out_path = log_dir / "classified_result.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    cfg.log(f"✅ classify 결과 저장 완료 → {out_path}", log_file)

    return result
