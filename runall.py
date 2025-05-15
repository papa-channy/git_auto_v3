from datetime import datetime
from pathlib import Path

from scripts.ext_info import extract_all_info
from scripts.mm_gen import mm_gen_main
from scripts.fx_elab import fx_elab_main
from scripts.gen_msg import gen_msg_main
from scripts.cost_calc import calculate_llm_costs_from_df
from scripts.classify import classify_main
from scripts.upload import upload_main
# 로그 기록 함수
def log(msg, log_file):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")

def run_all():
    timestamp = datetime.now().strftime("%y%m%d_%H%M")
    log_dir = Path(f"logs/{timestamp}")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "trigger.log"

    try:
        log("📁 1. 변경 FILE 및 메타데이터 추출 시작", log_file)
        extract_all_info()
        log("✅ 1. ext_info 완료", log_file)
    except Exception as e:
        log(f"❌ ext_info 실패: {e}", log_file)

    try:
        log("🧠 2. 기능 예측 및 전략 매핑 시작", log_file)
        mm_gen_main()
        log("✅ 2. mm_gen 완료", log_file)
    except Exception as e:
        log(f"❌ mm_gen 실패: {e}", log_file)

    try:
        log("📘 3. 기능 설명 요약 시작", log_file)
        fx_elab_main()
        log("✅ 3. fx_elab 완료", log_file)
    except Exception as e:
        log(f"❌ fx_elab 실패: {e}", log_file)

    try:
        log("📝 4. 커밋 메시지 생성 시작", log_file)
        gen_msg_main()
        log("✅ 4. gen_msg 완료", log_file)
    except Exception as e:
        log(f"❌ gen_msg 실패: {e}", log_file)

    try:
        log("💸 5. 비용 계산 시작", log_file)
        calculate_llm_costs_from_df(timestamp, lambda m: log(m, log_file))
        log("✅ 5. 비용 계산 완료", log_file)
    except Exception as e:
        log(f"❌ 비용 계산 실패: {e}", log_file)

    try:
        log("📦 6. 결과 분류 시작", log_file)
        classify_main(timestamp)
        log("✅ 6. classify 완료", log_file)
    except Exception as e:
        log(f"❌ classify 실패: {e}", log_file)

    try:
        log("📤 7. 결과 업로드 시작", log_file)
        upload_main(timestamp)
        log("✅ 7. upload 완료", log_file)
    except Exception as e:
        log(f"❌ upload 실패: {e}", log_file)

    log("🏁 전체 자동화 완료", log_file)

run_all()
