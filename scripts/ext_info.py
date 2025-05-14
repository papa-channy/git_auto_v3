import subprocess
from datetime import datetime
import pandas as pd
from pathlib import Path

# 🔧 Git 명령어 실행 유틸
def run_git(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    return result.stdout.strip()

# 1️⃣ 변경된 파일 목록 추출
def get_diff_files() -> list[str]:
    output = run_git(["git", "diff", "--name-only"])
    return [line.strip() for line in output.splitlines() if line.strip()]

# 2️⃣ 파일별 전체 커밋 날짜 추출
def get_commit_dates(file: str) -> list[datetime]:
    log = run_git(["git", "log", "--pretty=format:%ad", "--date=iso", "--", file])
    return [datetime.fromisoformat(line) for line in log.splitlines() if line.strip()]

# 3️⃣ 동적 커밋 메시지 개수 결정 (고정 전략)
def decide_commit_count(third_date: datetime | None) -> int:
    if not third_date:
        return 3  # 커밋 없음 → 기본값
    days_diff = (datetime.now() - third_date).days
    if days_diff > 10:
        return 5
    elif days_diff > 5:
        return 4
    return 3

# 4️⃣ 기준 날짜 이후의 커밋 메시지 추출
def get_recent_commits_after(file: str, since: datetime, count: int) -> list[str]:
    log = run_git([
        "git", "log",
        f"--since={since.strftime('%Y-%m-%d')}",
        "--pretty=format:%s", "--", file
    ])
    return [line.strip() for line in log.splitlines() if line.strip()][:count]

# 5️⃣ 전체 파이프라인 실행
def extract_git_info_to_df() -> pd.DataFrame:
    files = get_diff_files()
    rows = []

    for file in files:
        commit_dates = get_commit_dates(file)

        if len(commit_dates) >= 3:
            third_date = commit_dates[2]
        elif commit_dates:
            third_date = commit_dates[-1]
        else:
            third_date = None

        count = decide_commit_count(third_date)
        commits = get_recent_commits_after(file, third_date or datetime(2000, 1, 1), count)

        rows.append({
            "file": file,
            "commit_count_total": len(commit_dates),
            "third_commit_date": third_date.isoformat() if third_date else None,
            "commit_fetch_count": count,
            "commit_messages": commits
        })

    return pd.DataFrame(rows)
