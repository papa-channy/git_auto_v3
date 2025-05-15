import subprocess
import pandas as pd
import tiktoken
from pathlib import Path
from datetime import datetime
from dateutil.parser import parse
from scripts.dataframe import init_info_df, init_strategy_df, save_df
from config.cfg import REPO_PATH, INFO_PATH, STRATEGY_PATH, get_now, log
from config.cfg import BASE_DIR as root

USER_CONFIG_PATH = Path("config/user_config.yml")

def run_git(args: list[str], cwd: Path = Path.cwd()) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return result.stdout.strip()

def extract_repo_info(readme_token: int) -> pd.DataFrame:
    root = Path(run_git(["git", "rev-parse", "--show-toplevel"]))
    branches = run_git(["git", "branch", "--format=%(refname:short)"]).splitlines()
    head = run_git(["git", "symbolic-ref", "--short", "HEAD"])
    default_branch = next((b for b in ["main", "master"] if b in branches), branches[0] if branches else None)
    contributors = run_git(["git", "shortlog", "-sne"]).splitlines()
    recent_commit_count = len(run_git(["git", "log", "--since=14 days ago", "--oneline"]).splitlines())
    
    diff_files = run_git(["git", "diff", "--name-only"]).splitlines()
    diff_stat = run_git(["git", "diff", "--stat"])

    return pd.DataFrame([{
        "Repo": root.name,
        "Main branch": default_branch,
        "Branch list": branches,
        "Current branch": head,
        "Contributors": len(contributors),
        "Root path": str(root),
        "Commit frequency": recent_commit_count,
        "File count": count_filetypes(diff_files),
        "diff list": diff_files,
        "diff stat": diff_stat,
        "Readme token": readme_token
    }])


  # ← 전역 기준 루트 사용

def extract_info_and_strategy(files: list[str], readme_strategy: list) -> tuple:
    info_df = init_info_df(files)
    strat_df = init_strategy_df(files)
    enc = tiktoken.encoding_for_model("gpt-4")

    for i, row in info_df.iterrows():
        f = Path(files[i])
        full_path = root / f
        folder_path = full_path.parent

        # 🔸 FILE 본문 읽기 (안전하게)
        try:
            text = full_path.read_text(encoding='utf-8')
        except Exception:
            text = ""

        # 🔸 diff 추출 및 토큰 계산
        diff = run_git(["git", "diff", "--", str(f)])
        diff_token = len(enc.encode(diff))

        # 🔸 수정 시간 기록
        date_strs = run_git(["git", "log", "--pretty=format:%ad", "--date=iso", "--", str(f)]).splitlines()
        times = [parse(d).strftime("%y/%m/%d %H:%M") for d in date_strs if d.strip()]
        third_date = (
            parse(date_strs[2]) if len(date_strs) >= 3
            else parse(date_strs[-1]) if date_strs else None
        )

        # 🔸 커밋 메시지 추출
        msg_count = decide_commit_count(third_date)
        recent_msgs = run_git([
            "git", "log", "--since=" + (third_date or datetime(2000, 1, 1)).strftime('%Y-%m-%d'),
            "--pretty=format:%s", "--", str(f)
        ]).splitlines()
        recent_msgs = (recent_msgs + [""] * 5)[:5]  # 최소 길이 보장

        # 🔸 update info_df
        info_df.at[i, "file token"] = len(enc.encode(text))
        info_df.at[i, "diff var name"] = f"diff_{f.stem}"
        info_df.at[i, "diff token"] = diff_token
        info_df.at[i, "Files in folder"] = len([p for p in folder_path.iterdir() if p.is_file()])
        info_df.at[i, "LAST COMMIT TIME"] = times
        info_df.at[i, "5 LATEST COMMIT"] = recent_msgs

        # 🔸 update strategy_df
        strat_df.at[i, "FILE"] = f.name
        strat_df.at[i, "NUM OF EXTRACT FILE"] = msg_count
        strat_df.at[i, "readme strategy"] = readme_strategy

    return info_df, strat_df

def extract_readme_token_and_strategy() -> tuple:
    root = Path(run_git(["git", "rev-parse", "--show-toplevel"]))
    readme_path = root / "README.md"
    enc = tiktoken.encoding_for_model("gpt-4")
    if not readme_path.exists():
        return 0, [False, "x"]
    content = readme_path.read_text(encoding='utf-8')
    token_len = len(enc.encode(content))
    if token_len < 30:
        return token_len, [False, "x"]
    elif token_len <= 150:
        return token_len, [True, "full"]
    else:
        return token_len, [True, "summary"]

def count_filetypes(file_list: list[str]) -> dict:
    from collections import Counter
    return dict(Counter([Path(f).suffix for f in file_list if "." in f]))

def decide_commit_count(third_date: datetime | None) -> int:
    if not third_date:
        return 3
    now = get_now("commit")
    days = (now - third_date).days
    if days > 10:
        return 5
    elif days > 5:
        return 4
    return 3

# 🚀 전체 실행
def extract_all_info():
    readme_token, readme_strategy = extract_readme_token_and_strategy()
    repo_df = extract_repo_info(readme_token)
    files = repo_df.iloc[0]["변경 FILE 목록"]

    if not files:
        log(f"⚠️ 변경된 FILE이 없습니다. info/strategy 생략됨.")
        info_df = init_info_df([])
        strat_df = init_strategy_df([])
    else:
        info_df, strat_df = extract_info_and_strategy(files, readme_strategy)

    save_df(repo_df, REPO_PATH)
    save_df(info_df, INFO_PATH)
    save_df(strat_df, STRATEGY_PATH)
