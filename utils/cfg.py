from pathlib import Path
from datetime import datetime, timedelta
import pytz
import yaml
import requests
from bs4 import BeautifulSoup

class cfg:
    # 📁 기본 경로
    BASE_DIR = Path(".").resolve()
    RESULTS_DIR = BASE_DIR / "results"
    LOGS_DIR = BASE_DIR / "logs"
    PROMPT_DIR = BASE_DIR / "prompt"
    USER_CONFIG_PATH = BASE_DIR / "config/user_config.yml"
    EXCHANGE_RATE_CACHE = BASE_DIR / "utils/ex_rate.txt"
    EXCHANGE_RATE_FALLBACK = 1400.0

    _user_config_cache = None  # ✅ 캐시 추가

    # ✅ 사용자 config 캐싱 로딩
    @staticmethod
    def get_user_config() -> dict:
        if cfg._user_config_cache is None:
            with cfg.USER_CONFIG_PATH.open(encoding="utf-8") as f:
                cfg._user_config_cache = yaml.safe_load(f)
        return cfg._user_config_cache

    # ✅ 변경 감지 확장자 로딩
    @staticmethod
    def get_allowed_extensions(log_func=None) -> list[str]:
        log_func = log_func or cfg.log
        try:
            user_cfg = cfg.get_user_config()
            exts = user_cfg.get("change detection", {}).get("provider")
            if isinstance(exts, list) and all(isinstance(ext, str) for ext in exts):
                return exts
            log_func("⚠️ 'change detection → provider' 값이 유효하지 않음 → 빈 리스트 반환")
            return []
        except Exception as e:
            log_func(f"⚠️ 확장자 설정 로딩 실패: {e}")
            return []

    # ✅ LLM 설정
    @staticmethod
    def get_llm_config(stage: str) -> dict:
        LLM_PARAM = {
            "strategy": {"temperature": 0.5, "top_p": 0.8, "top_k": 40, "max_tokens": 8000},
            "explain": {"temperature": 0.8, "top_p": 0.9, "top_k": 80, "max_tokens": 8000},
            "mk_msg": {"temperature": 0.8, "top_p": 0.8, "top_k": 60, "max_tokens": 4096},
        }
        user_conf = cfg.get_user_config()
        user_llm = user_conf["llm"][stage]
        return {
            **LLM_PARAM[stage],
            "provider": user_llm["provider"],
            "model": user_llm["model"]
        }

    @staticmethod
    def calc_cost(llm_name: str, tokens: int, direction: str) -> float:
        rate_map = {
            "gpt-4o": {"input": 0.0025, "output": 0.01},
            "llama4-maverick-instruct-basic": {"input": 0.00022, "output": 0.00088},
            "llama4-scout-instruct-basic": {"input": 0.00015, "output": 0.0006},
        }
        if llm_name not in rate_map:
            return 0.0
        rate = rate_map[llm_name][direction]
        return round(tokens * rate / 1000, 6)

    # ✅ 타임존 기반 현재 시간
    @staticmethod
    def get_now(source: str = "commit") -> datetime:
        user_conf = cfg.get_user_config()
        tz_str = user_conf.get("timezone", {}).get(source, "UTC")
        tz = pytz.timezone(tz_str)
        return datetime.now(tz)

    # ✅ 결과 경로 구조
    @staticmethod
    def get_results_path(timestamp: str, base_dir: Path = RESULTS_DIR) -> dict:
        base = base_dir / timestamp
        return {
            "repo": base / "df/repo_df.pkl",
            "info": base / "df/info_df.pkl",
            "strategy": base / "df/strategy_df.pkl",
            "prompt": base / "df/prompt_df.pkl",
            "in": base / "df/in_df.pkl",
            "out": base / "df/out_df.pkl",
            "strategy_in": base / "strategy",
            "strategy_out": base / "strategy",
            "explain_in": base / "explain/in",
            "explain_out": base / "explain/out",
            "mk_msg_in": base / "mk_msg/in",
            "mk_msg_out": base / "mk_msg/out",
            "diff": base / "diff"
        }

    # ✅ 로그 기록 + stdout 출력 옵션 추가
    @staticmethod
    def log(message: str, log_file: Path, echo: bool = False):
        time_str = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{time_str}] {message}"
        if echo:
            print(formatted)
        with log_file.open("a", encoding="utf-8") as f:
            f.write(formatted + "\n")

    @staticmethod
    def init_log_file(timestamp: str, base_log_dir: Path = LOGS_DIR) -> Path:
        log_dir = base_log_dir / timestamp
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "for_debug.log"

    # ✅ 환율 로딩
    @staticmethod
    def get_usd_exchange_rate(log_func=None) -> float:
        log_func = log_func or cfg.log
        try:
            if cfg.EXCHANGE_RATE_CACHE.exists():
                last_modified = datetime.fromtimestamp(cfg.EXCHANGE_RATE_CACHE.stat().st_mtime)
                if datetime.now() - last_modified < timedelta(hours=24):
                    cached = cfg.EXCHANGE_RATE_CACHE.read_text(encoding="utf-8").strip()
                    if cached:
                        rate = float(cached)
                        log_func(f"💱 환율 캐시 사용: {rate}원")
                        return rate
            log_func("🌐 환율 정보 새로 요청 중...")
            html = requests.get("https://finance.naver.com/marketindex/", timeout=5).text
            soup = BeautifulSoup(html, "html.parser")
            value_el = soup.select_one("div.head_info > span.value")
            if not value_el:
                raise ValueError("환율 파싱 실패: selector 결과 없음")
            rate = float(value_el.text.replace(",", ""))
            cfg.EXCHANGE_RATE_CACHE.parent.mkdir(parents=True, exist_ok=True)
            cfg.EXCHANGE_RATE_CACHE.write_text(str(rate), encoding="utf-8")
            log_func(f"✅ 환율 정보 갱신 완료: {rate}원")
            return rate
        except Exception as e:
            log_func(f"⚠️ 환율 정보 가져오기 실패: {e} → fallback {cfg.EXCHANGE_RATE_FALLBACK}")
            return cfg.EXCHANGE_RATE_FALLBACK

    # ⏱ 고정 타임스탬프
    TIMESTAMP_FORMAT = "%y%m%d_%H%M"
    _timestamp_fixed = datetime.now()
    TIMESTAMP = _timestamp_fixed.strftime(TIMESTAMP_FORMAT)
    get_timestamp = staticmethod(lambda: cfg.TIMESTAMP)

    # 📁 파일 구조 정리
    @staticmethod
    def build_llm_file_structure(base_path: Path, valid_ext={".py", ".sh", ".js", ".ts", ".html", ".css"}) -> tuple[list[str], list[str]]:
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
        folder_lines = [f"{idx}={folder} ({folder.count('/') + 1 if folder else 1})" for idx, folder in enumerate(folder_list)]
        file_lines = [f"[{folder_index[f]}]/{name}" for f, name in sorted(file_list)]
        return folder_lines, file_lines

    # 📂 경로 요약
    @classmethod
    def path_summary(cls) -> dict:
        return {
            "base": cls.BASE_DIR,
            "results": cls.RESULTS_DIR,
            "logs": cls.LOGS_DIR,
            "user_config": cls.USER_CONFIG_PATH,
            "rate_cache": cls.EXCHANGE_RATE_CACHE,
        }
