import pandas as pd
from pathlib import Path
from config.cfg import INFO_PATH, STRATEGY_PATH, REPO_PATH, PROMPT_PATH

def init_repo_df() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "Repo",               # 레포 이름
        "Main branch",           # default/main
        "Branch list",         # 전체 브랜치
        "Current branch",         # 현재 사용 중인 브랜치
        "Contributors",           # 커밋한 사람 수
        "Root path",           # 절대 경로
        "Commit frequency",  # 최근 N일 커밋 수
        "File count",     # .py, .sh 등 카운트
        "diff list",       # diff 감지 FILE들
        "diff stat",       # git diff --stat
        "Readme token"     # README.md 토큰 수
    ])

def extract_file_parts(file_path: str):
    full_path = Path(file_path).resolve()
    return [part for part in full_path.parts if part not in [":", "/", "\\"]]

def init_info_df(file_list: list[str]) -> pd.DataFrame:
    return pd.DataFrame({
        "file": [Path(f).name for f in file_list],
        "file type": [Path(f).suffix for f in file_list],
        "Path": [str(Path(f).parent) for f in file_list],
        "file token": [0] * len(file_list),
        "diff var name": [""] * len(file_list),
        "diff token": [0] * len(file_list),
        "Files in folder": [0] * len(file_list),
        "last commit time": [[] for _ in file_list],
        "5 latest commit": [[] for _ in file_list],
    })

def init_strategy_df(file_list: list[str]) -> pd.DataFrame:
    return pd.DataFrame({
        "file": file_list,
        "file strategy": [None] * len(file_list),
        "Num of extract file": [3] * len(file_list),
        "Required Commit Detail": [None] * len(file_list),
        "Recommended length": [None] * len(file_list),  # 토큰 기준 숫자
        "Component Type": [None] * len(file_list),
        "Importance": [None] * len(file_list),
        "Most Related Files": [[] for _ in file_list],
        "Readme strategy": [[False, "x"]] * len(file_list),  # ex: [True, "summary"]
    })

def init_prompt_df() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "In/Out","var name", "model name","meta(in)or purpose(out)", "save path",
        "Is upload", "upload pf",
        "token", "cost($)", "cost(krw)"
    ])

def convert_columns_to_english(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    return df.rename(columns=mapping)

def save_df(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(path)

def load_df(path: Path) -> pd.DataFrame:
    return pd.read_pickle(path) if path.exists() else None
