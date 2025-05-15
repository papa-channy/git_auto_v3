import subprocess
from pathlib import Path
from datetime import datetime
import pandas as pd
import tiktoken
from dataframe import (
    init_repo_df, init_info_df, init_strategy_df,
    save_df, REPO_PATH, INFO_PATH, STRATEGY_PATH
)

# 🔧 git 명령 실행 유틸
def run_git(args: list[str], cwd: Path = Path.cwd()) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return result.stdout.strip()

# 📁 레포 메타 수집
def extract_repo_info(readme_token: int) -> pd.DataFrame:
    root = Path(run_git(["git", "rev-parse", "--show-toplevel"]))
    branches = run_git(["git", "branch", "--format=%(refname:short)"]).splitlines()
    head = run_git(["git", "symbolic-ref", "--short", "HEAD"])
    default_branch = "main" if "main" in branches else (branches[0] if branches else None)
    contributors = run_git(["git", "shortlog", "-sne"]).splitlines()
    recent_commit_count = len(run_git(["git", "log", "--since=14 days ago", "--oneline"]).splitlines())
    diff_files = run_git(["git", "diff", "--name-only"]).splitlines()
    diff_stat = run_git(["git", "diff", "--stat"])

    return pd.DataFrame([{
        "Repo": root.name,
        "주 브랜치": default_branch,
        "브랜치 list": branches,
        "현재 브랜치": head,
        "작업인원": len(contributors),
        "루트 path": str(root),
        "특정 기간 커밋 횟수": recent_commit_count,
        "파일 유형별 개수": count_filetypes(diff_files),
        "변경 파일 목록": diff_files,
        "변경 요약 통계": diff_stat,
        "readme 토큰 수": readme_token
    }])

def count_filetypes(file_list: list[str]) -> dict:
    from collections import Counter
    return dict(Counter([Path(f).suffix for f in file_list if "." in f]))

# 📄 파일 메타 + 전략 수집
def extract_info_and_strategy(files: list[str], readme_strategy: list) -> tuple:
    info_df = init_info_df(files)
    strat_df = init_strategy_df(files)
    root = Path(run_git(["git", "rev-parse", "--show-toplevel"]))
    enc = tiktoken.encoding_for_model("gpt-4")

    for i, row in info_df.iterrows():
        f = Path(files[i])
        full_path = root / f
        folder_path = full_path.parent
        text = full_path.read_text(encoding='utf-8') if full_path.exists() else ""
        diff = run_git(["git", "diff", "--", str(f)])
        diff_token = len(enc.encode(diff))

        # 수정 시간
        dates = run_git(["git", "log", "--pretty=format:%ad", "--date=iso", "--", str(f)]).splitlines()
        times = [datetime.fromisoformat(d).strftime("%y/%m/%d %H:%M") for d in dates if d.strip()]
        third_date = datetime.fromisoformat(dates[2]) if len(dates) >= 3 else (
            datetime.fromisoformat(dates[-1]) if dates else None)

        # 커밋 메시지
        msg_count = decide_commit_count(third_date)
        recent_msgs = run_git([
            "git", "log", "--since=" + (third_date or datetime(2000, 1, 1)).strftime('%Y-%m-%d'),
            "--pretty=format:%s", "--", str(f)
        ]).splitlines()[:5]

        # update info_df
        info_df.at[i, "파일 토큰 수"] = len(enc.encode(text))
        info_df.at[i, "diff 변수명"] = f"diff_{f.stem}"
        info_df.at[i, "diff 토큰 수"] = diff_token
        info_df.at[i, "소속 폴더 파일개수"] = len([p for p in folder_path.iterdir() if p.is_file()])
        info_df.at[i, "최근 수정 시간"] = times
        info_df.at[i, "최근 커밋 메시지 5개"] = recent_msgs

        # update strategy_df
        strat_df.at[i, "파일"] = f.name
        strat_df.at[i, "추출할 커밋 메시지 개수"] = msg_count
        strat_df.at[i, "readme 전략"] = readme_strategy

    return info_df, strat_df

# 📖 README 처리
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

# ✅ 커밋 메시지 수 결정 기준
def decide_commit_count(third_date: datetime | None) -> int:
    if not third_date:
        return 3
    days = (datetime.now() - third_date).days
    if days > 10:
        return 5
    elif days > 5:
        return 4
    return 3

# 🚀 전체 실행
def extract_all_info():
    readme_token, readme_strategy = extract_readme_token_and_strategy()
    repo_df = extract_repo_info(readme_token)
    files = repo_df.iloc[0]["변경 파일 목록"]
    info_df, strat_df = extract_info_and_strategy(files, readme_strategy)
    save_df(repo_df, REPO_PATH)
    save_df(info_df, INFO_PATH)
    save_df(strat_df, STRATEGY_PATH)
