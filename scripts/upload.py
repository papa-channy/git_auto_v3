import subprocess
import json
from pathlib import Path
from datetime import datetime
from notify import discord, gmail, kakao, slack
from record import notion, google_drive

def get_repo_name():
    import subprocess
    try:
        url = subprocess.run("git config --get remote.origin.url", shell=True, capture_output=True, text=True).stdout.strip()
        repo = url.rstrip(".git").split("/")[-1] if url else "Unknown"
        return repo.replace("-", " ").title()
    except Exception:
        return "Unknown Repo"

def log(message: str, log_file: Path):
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")

def do_git_commit(file_path: str, commit_msg: str) -> bool:
    try:
        # FILE별 커밋: 해당 FILE만 add
        subprocess.run(["git", "add", file_path], check=True)
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def send_notification(platforms: list, message: str, log_func):
    for platform in platforms:
        try:
            if platform == "discord":
                discord.send(message)
            elif platform == "gmail":
                gmail.send(message)
            elif platform == "kakao":
                kakao.send(message)
            elif platform == "slack":
                slack.send(message)
        except Exception as e:
            log_func(f"[ERROR] {platform} 알림 실패: {e}")

def write_records(platforms: list, message: str, log_func):
    repo_name = get_repo_name()
    for platform in platforms:
        try:
            if platform == "notion":
                notion.upload_date_based_record("", "", message)
            elif platform == "google_drive":
                google_drive.send(message)
            elif platform == "slack":
                slack.send(message)
        except Exception as e:
            log_func(f"[ERROR] {platform} 기록 실패: {e}")

def upload_main(timestamp: str, log_file: Path):
    # 폴더: logs/{timestamp}
    log_dir = Path(f"logs/{timestamp}")

    # 커밋 메시지 처리: commit_out_*.txt
    commit_files = list(log_dir.glob("commit_out_*.txt"))
    commit_results = {}
    commit_msgs = []

    for file in commit_files:
        # key: FILE명만 (접두어 제거)
        key = file.name.replace("commit_out_", "").replace(".txt", "")
        commit_msg = file.read_text(encoding="utf-8").strip()
        # FILE 경로 처리: 여기선 간단히 key를 그대로 사용 (필요 시 실제 경로로 확장)
        file_path = key  
        success = do_git_commit(file_path, commit_msg)
        commit_results[key] = "Success" if success else "Failure"
        commit_msgs.append(f"{key}: {commit_msg}")

    # 알림 메시지 구성
    summary_msg = f"커밋 파이프라인 결과: {json.dumps(commit_results, ensure_ascii=False)}"
    cost_summary = "💸 총 비용: 계산 완료"  # 실제 비용은 cost_calc 모듈에서 받아오기
    review_path = Path("results/manual_review.json")
    review_files = []
    if review_path.exists():
        try:
            review_files = json.loads(review_path.read_text(encoding="utf-8"))
        except Exception:
            review_files = []
    notify_msg = (
        f"{summary_msg}\n"
        f"커밋 메시지:\n" + "\n".join(commit_msgs) + "\n"
        f"{cost_summary}\n"
        f"중요도 9 이상 FILE: {review_files}"
    )

    # 기록 메시지 처리: fx_out_*.txt
    record_files = list(log_dir.glob("fx_out_*.txt"))
    record_msgs = {}
    for file in record_files:
        key = file.name.replace("fx_out_", "").replace(".txt", "")
        record_msgs[key] = file.read_text(encoding="utf-8")

    # 로그 업로드 메시지 기록
    log(f"✅ 업로드: {notify_msg}", log_file)
    send_notification(["kakao", "discord", "gmail", "slack"], notify_msg, lambda m: log(m, log_file))

    # 각 FILE별 기록 메시지 업로드
    for key, msg in record_msgs.items():
        write_records(["notion", "google_drive", "slack"], msg, lambda m: log(m, log_file))

    log("✅ 업로드 처리 완료", log_file)

if __name__ == "__main__":
    # timestamp는 runall.py에서 생성한 값을 사용 (예시로 고정)
    timestamp = "250514_1234"  # 실제 사용 시 동적으로 받아오기
    log_file = Path(f"logs/{timestamp}/trigger.log")
    upload_main(timestamp, log_file)
