from utils.cfg import cfg
from utils.path import get_results_path
from utils.llm import get_llm_config
from utils.cfg import cfg

now = cfg.get_now("commit")           # 한국 시간 기반
ts = cfg.get_timestamp()              # 250518_1034 같은 포맷
log_file = cfg.init_log_file(ts)
cfg.log("✅ 로그 테스트", log_file)
conf = get_llm_config("strategy")
print(conf)
print(get_results_path("250518_1001")["prompt"])
# 타임스탬프 기반 로그 파일 생성
timestamp = cfg.get_timestamp()
log_file = cfg.init_log_file(timestamp)

# 메시지 기록
cfg.log("✅ [TEST] 로그 초기화 및 첫 줄 기록 성공", log_file)

# 로그 경로 출력 (확인용)
print(f"📄 로그 파일 경로: {log_file}")
