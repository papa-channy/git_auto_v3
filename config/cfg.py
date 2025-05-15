import yaml
import pytz
from pathlib import Path
from datetime import datetime, timedelta
from config import LLM_PARAM

USER_CONFIG_PATH = Path("config/user_config.yml")  # 스타일, LLM, 알림 등

BASE_DIR = Path(".").resolve()
RESULTS_DIR = BASE_DIR / "results"
LOGS_DIR = BASE_DIR / "logs"
PROMPT_DIR = BASE_DIR / "prompt"

REPO_PATH = RESULTS_DIR / "repo_df.pkl"
INFO_PATH = RESULTS_DIR / "info_df.pkl"
STRATEGY_PATH = RESULTS_DIR / "strategy_df.pkl"
PROMPT_PATH = RESULTS_DIR / "prompt_df.pkl"

TIMESTAMP_FORMAT = "%y%m%d_%H%M"

def get_now(source: str = "commit") -> datetime:
    with open(USER_CONFIG_PATH, encoding="utf-8") as f:
        user_cfg = yaml.safe_load(f)
    tz_str = user_cfg.get("timezone", {}).get(source, "UTC")
    tz = pytz.timezone(tz_str)
    return datetime.now(tz)

def get_timestamp():
    return datetime.now().strftime(TIMESTAMP_FORMAT)

def init_log_file(timestamp: str) -> Path:
    log_dir = LOGS_DIR / timestamp
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "for_debug.log"
    return log_file

def log(message: str, log_file: Path):
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")

def build_llm_file_structure(
    base_path: Path,
    valid_ext={".py", ".sh", ".js", ".ts", ".html", ".css"}
) -> tuple[list[str], list[str]]:
    folder_set = set()
    file_list = []

    for file in base_path.rglob("*"):
        if not file.is_file():
            continue
        if file.name.startswith(".") or file.name.startswith("__"):
            continue
        if "__pycache__" in file.parts or file.name.endswith(".pyc"):
            continue
        if file.suffix not in valid_ext:
            continue

        rel_path = file.relative_to(base_path)
        folder = rel_path.parent.as_posix()
        folder_set.add(folder)
        file_list.append((folder, file.name))

    folder_list = sorted(folder_set)
    folder_index = {folder: idx for idx, folder in enumerate(folder_list)}

    folder_lines = [
        f"{idx}={folder} ({folder.count('/') + 1 if folder else 1})"
        for idx, folder in enumerate(folder_list)
    ]

    file_lines = [
        f"[{folder_index[f]}]/{name}" for f, name in sorted(file_list)
    ]

    return folder_lines, file_lines

LLM_PARAM = {
    "strategy": {
        "temperature": 0.5,
        "top_p": 0.8,
        "top_k": 40,
        "max_tokens": 8000
    },
    "explain": {
        "temperature": 0.8,
        "top_p": 0.9,
        "top_k": 80,
        "max_tokens": 8000
    },
    "mk_msg": {
        "temperature": 0.8,
        "top_p": 0.8,
        "top_k": 60,
        "max_tokens": 4096
    }
}

def get_llm_config(stage: str) -> dict:
    """
    사용자 설정 FILE에서 provider/model을 불러오고
    config.py의 고정값과 병합하여 LLM 호출 config 생성
    """
    with open(USER_CONFIG_PATH, encoding="utf-8") as f:
        user_conf = yaml.safe_load(f)
    user_llm = user_conf["llm"][stage]  # "strategy", "explain", "mk_msg"
    return {
        **LLM_PARAM[stage],
        "provider": user_llm["provider"],
        "model": user_llm["model"]
    }

EXCHANGE_RATE_CACHE = BASE_DIR / "utils" / "ex_rate.txt"
EXCHANGE_RATE_FALLBACK = 1400.0  # 원화 기준 환율 (기본값)

maverick_input = 0.00022
maverick_output = 0.00088
gpt_4o_input = 0.0025
gpt_4o_output = 0.01
