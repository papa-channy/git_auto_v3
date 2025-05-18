import pandas as pd
from pathlib import Path
from utils.cfg import cfg
results = cfg.get_results_path(cfg.get_timestamp())
REPO_PATH = results["repo"]
INFO_PATH = results["info"]
STRATEGY_PATH = results["strategy"]
PROMPT_PATH = results["prompt"]
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
        "Diff list",       # diff 감지 FILE들
        "Diff stat",       # git diff --stat
        "Readme token"     # README.md 토큰 수
    ])

def init_info_df(file_list: list[str]) -> pd.DataFrame:
    return pd.DataFrame({
        "id" : [Path(f).name for f in file_list],
        "file": [Path(f).name for f in file_list],
        "file type": [Path(f).suffix for f in file_list],
        "path": [str(Path(f).parent) for f in file_list],
        "file token": [0] * len(file_list),
        "diff var name": [""] * len(file_list),
        "diff token": [0] * len(file_list),
        "Files in folder": [0] * len(file_list),
        "last commit time": [[] for _ in file_list],
        "5 latest commit": [[] for _ in file_list],
        "name4save": [None] * len(file_list),
        "save_path": [None] * len(file_list)
    })

def init_strategy_df(file_list: list[str]) -> pd.DataFrame:
    return pd.DataFrame({
        "id": [Path(f).name for f in file_list],
        "File": file_list,
        "File strategy": [None] * len(file_list),
        "Num of extract file": [3] * len(file_list),
        "Required Commit Detail": [None] * len(file_list),
        "Recommended length": [None] * len(file_list),  # 토큰 기준 숫자
        "Component Type": [None] * len(file_list),
        "Importance": [None] * len(file_list),
        "Most Related Files": [[] for _ in file_list],
        "Readme strategy": [[False, "x"]] * len(file_list),  # ex: [True, "summary"]
        "name4save": [None] * len(file_list),
        "save_path": [None] * len(file_list)})

def init_in_df() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "id","name4save","save_path","prompt", "llm","meta data",
        "token", "cost($)", "cost(krw)"
    ])

def init_out_df() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "id","name4save","save_path","prompt","llm", "purpose", "Is upload", "upload pf",
        "token", "cost($)", "cost(krw)"
    ])

def convert_columns_to_kor(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    return df.rename(columns=mapping)

def save_df(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(path)

def load_df(path: Path) -> pd.DataFrame:
    return pd.read_pickle(path) if path.exists() else None

# 🧱 빈 데이터프레임 초기 생성 및 저장
def init_df_and_save():
    """
    전체 주요 DataFrame 구조를 빈 상태로 초기화하고,
    설정된 전역 경로에 저장합니다.
    """
    save_df(init_repo_df(), REPO_PATH)
    save_df(init_info_df([]), INFO_PATH)
    save_df(init_strategy_df([]), STRATEGY_PATH)

    # 입력/출력 프롬프트용
    save_df(init_in_df(), PROMPT_PATH.with_name("in_prompt_df.pkl"))
    save_df(init_out_df(), PROMPT_PATH.with_name("out_prompt_df.pkl"))