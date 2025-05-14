import subprocess
from notify import discord, gmail, kakao, slack
from record import notion, google_drive
from utils.path import get_repo_name

def do_git_commit(commit_msg: str) -> bool:
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        subprocess.run(["git", "push"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def send_notification(platforms: list[str], messages: list[str], log):
    for platform in platforms:
        for msg in messages:
            try:
                if platform == "discord":
                    discord.send(msg)
                elif platform == "gmail":
                    gmail.send(msg)
                elif platform == "kakao":
                    kakao.send(msg)
                elif platform == "slack":
                    slack.send(msg)
            except Exception as e:
                log(f"[ERROR] {platform} 알림 실패: {e}")

def write_records(platforms: list[str], messages: list[str], log):
    context, chunk_summary, record_msg = messages
    repo_name = get_repo_name()

    for platform in platforms:
        try:
            if platform == "notion":
                notion.upload_date_based_record(context, chunk_summary, record_msg)
                notion.upload_sequential_record(repo_name, [record_msg])
            elif platform == "google_drive":
                google_drive.send(messages)
            elif platform == "slack":
                slack.send("\n\n".join(messages))
        except Exception as e:
            log(f"[ERROR] {platform} 기록 실패: {e}")
