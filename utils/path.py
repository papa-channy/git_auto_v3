from pathlib import Path
from datetime import datetime
import subprocess

def get_repo_name() -> str:
    url = subprocess.run("git config --get remote.origin.url", shell=True, capture_output=True, text=True).stdout.strip()
    return url.rstrip(".git").split("/")[-1].replace("-", " ").title() if url else "Unknown Repo"

# 🔍 Git 루트 경로 탐지
def get_git_root() -> Path:
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True, capture_output=True, text=True
        ).stdout.strip()
        return Path(root)
    except subprocess.CalledProcessError:
        return Path.cwd()

# 📁 결과 경로 생성기 (전체 구조 대응)
def get_result_paths(timestamp: str) -> dict:
    dt = datetime.strptime(timestamp, "%Y%m%d_%H%M")
    date_key = dt.strftime("%y%m%d_%H%M")
    base = get_git_root() / "results" / date_key

    paths = {
        "base": base,

        # 🔹 context
        "context_by_file": base / "context" / "by_file",
        "context_summary_dir": base / "context" / "sum",  # b1~bn 입력, sum1~final 출력

        # 🔹 diff
        "diff_chunks": base / "diff" / "chunk",           # 원본 청크 저장
        "diff_commit_dir": base / "diff" / "sum",         # c1~cn 입력, chunk_1_commit.txt~ 출력

        # 🔹 final
        "final_commit_dir": base / "final" / "commit",    # d1~dn 입력, final_1_commit.txt~ 출력
        "final_record_dir": base / "final" / "record",    # e1~en 입력, final_1_record.txt~ 출력
    }

    # 📁 디렉토리 생성
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    return paths

# 📊 LLM 비용 로그 경로
def get_cost_log_path(timestamp: str) -> Path:
    dt = datetime.strptime(timestamp, "%Y%m%d_%H%M")
    base = get_git_root() / "cost" / dt.strftime("%y%m%d_%H%M")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"llm_{timestamp}.jsonl"
