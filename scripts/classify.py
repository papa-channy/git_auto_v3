import json
from pathlib import Path
from datetime import datetime

def classify_main(timestamp: str):
    log_dir = Path(f"logs/{timestamp}")
    result = {
        "commit": {},
        "notify": {
            "summary": "",
            "commits": [],
            "cost": "",
            "review_files": []
        },
        "record": {}
    }

    # ✅ 커밋 메시지
    for file in log_dir.glob("commit_out_*.txt"):
        varname = file.stem
        filename = varname.replace("commit_out_", "")
        result["commit"][filename] = file.read_text()

    # ✅ 기록 메시지
    for file in log_dir.glob("fx_out_*.txt"):
        varname = file.stem
        filename = varname.replace("fx_out_", "")
        result["record"][filename] = file.read_text()

    # ✅ 알림용 메시지 구성
    result["notify"]["commits"] = list(result["commit"].values())

    try:
        prompt_df = json.loads(Path("results/prompt_df.json").read_text(encoding="utf-8"))
        total_krw = sum(row["비용(krw)"] for row in prompt_df if isinstance(row["비용(krw)"], (int, float)))
        result["notify"]["cost"] = f"💸 전체 LLM 사용 비용: {total_krw:,}원"
    except Exception:
        result["notify"]["cost"] = "⚠️ 비용 정보 로딩 실패"

    review_file = Path("results/manual_review.json")
    if review_file.exists():
        try:
            review_list = json.loads(review_file.read_text(encoding="utf-8"))
            result["notify"]["review_files"] = review_list
        except Exception:
            result["notify"]["review_files"] = []

    result["notify"]["summary"] = (
        f"✅ 총 {len(result['commit'])}개 FILE 커밋 완료, "
        f"기록용 메시지 {len(result['record'])}개 생성됨."
    )

    # 저장
    out_path = log_dir / "classified_result.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ classify 결과 저장 완료 → {out_path}")

    return result
