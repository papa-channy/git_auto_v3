import pandas as pd
from pathlib import Path

# ───────────────────────────────
# 📁 경로 설정
BASE_DIR = Path("results")
INFO_PATH = BASE_DIR / "info_df.pkl"
STRATEGY_PATH = BASE_DIR / "strategy_df.pkl"
REPO_PATH = BASE_DIR / "repo_df.pkl"
PROMPT_PATH = BASE_DIR / "prompt_df.pkl"

# ───────────────────────────────
# 🧱 1. 레포 단위 메타데이터
def init_repo_df() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "Repo",               # 레포 이름
        "주 브랜치",           # default/main
        "브랜치 list",         # 전체 브랜치
        "현재 브랜치",         # 현재 사용 중인 브랜치
        "작업인원",           # 커밋한 사람 수
        "루트 path",           # 절대 경로
        "특정 기간 커밋 횟수",  # 최근 N일 커밋 수
        "파일 유형별 개수",     # .py, .sh 등 카운트
        "변경 파일 목록",       # diff 감지 파일들
        "변경 요약 통계",       # git diff --stat
        "readme 토큰 수"     # README.md 토큰 수
    ])

# ───────────────────────────────
# 🧱 2. 파일 단위 info_df
def extract_file_parts(file_path: str):
    full_path = Path(file_path).resolve()
    return [part for part in full_path.parts if part not in [":", "/", "\\"]]

def init_info_df(file_list: list[str]) -> pd.DataFrame:
    return pd.DataFrame({
        "파일": [Path(f).name for f in file_list],
        "파일 유형": [Path(f).suffix for f in file_list],
        "파일 위치": [extract_file_parts(f) for f in file_list],
        "파일 토큰 수": [0] * len(file_list),
        "diff 변수명": [""] * len(file_list),
        "diff 토큰 수": [0] * len(file_list),
        "소속 폴더 파일개수": [0] * len(file_list),
        "최근 수정 시간": [[] for _ in file_list],
        "최근 커밋 메시지 5개": [[] for _ in file_list],
    })

# ───────────────────────────────
# 🧠 3. 전략 전용 strategy_df
def init_strategy_df(file_list: list[str]) -> pd.DataFrame:
    return pd.DataFrame({
        "파일": file_list,
        "분석 전략": [None] * len(file_list),
        "추출할 커밋 메시지 개수": [3] * len(file_list),
        "작성 디테일 등급": [None] * len(file_list),
        "작성 권장 길이": [None] * len(file_list),  # 토큰 기준 숫자
        "기능 유형": [None] * len(file_list),
        "중요도 점수": [None] * len(file_list),
        "연관도 높은 파일 리스트": [[] for _ in file_list],
        "readme 전략": [[False, "x"]] * len(file_list),  # ex: [True, "summary"]
    })

# ───────────────────────────────
# 🧠 4. 프롬프트 추적
def init_prompt_df() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "입력/출력","변수명", "사용 모델","사용한 정보(입력)or목적(출력)", "저장 위치",
        "업로드 여부", "upload platform",
        "token값", "비용($)", "비용(krw)"
    ])

# ───────────────────────────────
# 📦 공용 유틸
def convert_columns_to_english(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    return df.rename(columns=mapping)

def save_df(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(path)

def load_df(path: Path) -> pd.DataFrame:
    return pd.read_pickle(path) if path.exists() else None
