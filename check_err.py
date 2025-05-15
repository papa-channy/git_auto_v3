import os, json, subprocess, requests, shutil
from pathlib import Path
from dotenv import load_dotenv
import getpass
from config.cfg import get_git_root
# ────────────────────────────────
# 🔹 환경변수 로딩
# ────────────────────────────────
def load_env_and_api_key():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    api_key = os.getenv("FIREWORKS_API_KEY", "")
    if not api_key:
        print_status(".env 설정", "FIREWORKS_API_KEY 누락", "fail")
        exit(1)

    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }, api_key


# ────────────────────────────────
# 🔹 상태 출력 헬퍼
# ────────────────────────────────
def print_status(label, value, status="ok"):
    symbols = {"ok": "✅", "warn": "⚠️", "fail": "❌"}
    print(f"{symbols[status]} {label}: {value}")

def run(cmd): return subprocess.run(cmd, shell=True, text=True, capture_output=True).stdout.strip()

# ────────────────────────────────
# 🔹 Git 설정 자동 등록
# ────────────────────────────────
def check_git_user_config():
    if not run("git config --global user.name"):
        subprocess.run('git config --global user.name "git-llm-user"', shell=True)
    if not run("git config --global user.email"):
        subprocess.run('git config --global user.email "git@llm.com"', shell=True)
    print_status("Git 사용자 설정", "등록됨")

def enforce_git_core_config():
    subprocess.run("git config --global core.autocrlf input", shell=True)
    subprocess.run("git config --global core.quotepath false", shell=True)
    print_status("core.autocrlf / quotepath", "적용 완료")

# ────────────────────────────────
# 🔹 필수 FILE (.editorconfig, .gitattributes)
# ────────────────────────────────
def ensure_required_files():
    base = Path(__file__).parent.resolve()
    if not (base / ".gitattributes").exists():
        (base / ".gitattributes").write_text("* text=auto\n", encoding="utf-8")
    if not (base / ".editorconfig").exists():
        (base / ".editorconfig").write_text(
            "[*]\nend_of_line = lf\ninsert_final_newline = true\ncharset = utf-8\n", encoding="utf-8"
        )
    print_status("필수 설정 FILE", "확인 완료")

# ────────────────────────────────
# 🔹 Git 레포 상태 점검
# ────────────────────────────────
def check_git_repo():
    if subprocess.run("git rev-parse --is-inside-work-tree", shell=True).returncode != 0:
        print_status("Git 레포", ".git 없음", "fail")
        exit(1)
    print_status("Git 레포", "확인됨")

def check_git_remote():
    remote = run("git config --get remote.origin.url")
    if not remote:
        print_status("remote.origin.url", "없음", "fail"); exit(1)
    if subprocess.run(f"git ls-remote {remote}", shell=True, capture_output=True).returncode != 0:
        print_status("원격 저장소 접근", "실패", "fail"); exit(1)
    print_status("원격 저장소", "접근 성공")

# ────────────────────────────────
# 🔹 설정 FILE 로딩 (config/*.json)
# ────────────────────────────────
def load_config():
    base_path = Path(__file__).parent.resolve() / "config"
    required_configs = ["llm.json", "style.json", "noti.json", "cost.json"]

    for cfg in required_configs:
        cfg_path = base_path / cfg
        if not cfg_path.exists():
            print_status(f"설정 FILE {cfg}", "없음", "fail")
            exit(1)

    print_status("모든 설정 FILE", "확인 완료")
    return json.loads((base_path / "noti.json").read_text(encoding="utf-8"))

# ────────────────────────────────
# 🔹 알림 플랫폼 ping 함수 호출
# ────────────────────────────────
def check_notify_platforms(pf_list):
    import notify.discord as discord
    import notify.kakao as kakao
    import notify.gmail as gmail
    import notify.slack as slack

    ping_map = {"discord": discord.ping, "kakao": kakao.ping, "gmail": gmail.ping, "slack": slack.ping}

    for pf in pf_list:
        if pf not in ping_map:
            print_status(f"{pf} 알림 테스트", "지원되지 않음", "warn")
            continue
        if ping_map[pf]():
            print_status(f"{pf} 알림 테스트", "성공", "ok")
        else:
            print_status(f"{pf} 알림 테스트", "실패", "fail")
            exit(1)

# ────────────────────────────────
def register_task_scheduler():
    task_name = "GitAutoWatcher"
    username = getpass.getuser()
    bash_path = "C:\\Program Files\\Git\\bin\\bash.exe"
    sh_script = str(get_git_root() / "auto_git.sh").replace("/", "\\")

    # 🛑 이미 등록된 경우 skip
    check_cmd = f'schtasks /Query /TN {task_name}'
    if subprocess.run(check_cmd, shell=True, capture_output=True).returncode == 0:
        print_status("작업 스케줄러 등록", "이미 존재 → 생략", "ok")
        return

    # # ✅ 등록 명령
    # cmd = (
    #     f'schtasks /Create /SC ONLOGON '
    #     f'/TN {task_name} /TR "\\"{bash_path}\\" --login -i \\"{sh_script}\\"" '
    #     f'/F'
    # )

    # try:
    #     subprocess.run(cmd, shell=True, check=True)
    #     print_status("작업 스케줄러 등록", "성공", "ok")
    # except Exception as e:
    #     print_status("작업 스케줄러 등록 실패", str(e), "fail")
# ────────────────────────────────
# 🔹 Main 실행
# ────────────────────────────────
def main():
    print("\n🔍 check_err: 자동화 사전 점검 및 설정 시작\n")

    global HEADERS
    HEADERS, api_key = load_env_and_api_key()

    check_git_user_config()
    enforce_git_core_config()
    ensure_required_files()
    check_git_repo()
    check_git_remote()
    # register_task_scheduler()
    config = load_config()
    check_notify_platforms(config.get("noti_pf", []))

    print("\n🎉 모든 점검 및 설정 완료. 자동화 준비 OK.\n")

if __name__ == "__main__":
    main()
