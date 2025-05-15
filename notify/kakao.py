import os
import json
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 🔹 환경 설정
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN")  # ✅ refresh_token은 .env에서 불러옴
TOKEN_PATH = Path("config/kakao.json")       # ✅ access_token은 FILE로 저장됨
API_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"

# 🔧 토큰 FILE 로드
def load_tokens():
    if TOKEN_PATH.exists():
        return json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    return {}

# 🔧 토큰 FILE 저장
def save_tokens(data: dict):
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# 🔧 access_token 갱신
def refresh_access_token(refresh_token: str) -> str:
    if not CLIENT_ID or not refresh_token:
        return None

    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token
    }

    try:
        resp = requests.post(TOKEN_URL, data=data, timeout=5)
        resp.raise_for_status()
        new_token = resp.json().get("access_token")
        if new_token:
            tokens = load_tokens()
            tokens["access_token"] = new_token
            tokens["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_tokens(tokens)
            return new_token
    except Exception as e:
        print(f"[KAKAO] ❌ 토큰 갱신 실패: {e}")
    return None

# 🔧 헤더 구성
def build_headers(token: str):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
    }

# 🔧 메시지 전송 로직
def _send_msg(token: str, msg: str) -> bool:
    headers = build_headers(token)
    template = {
        "object_type": "text",
        "text": msg,
        "link": {
            "web_url": "https://github.com",
            "mobile_web_url": "https://github.com"
        }
    }
    try:
        data = { "template_object": json.dumps(template, ensure_ascii=False) }
        resp = requests.post(API_URL, headers=headers, data=data, timeout=5)
        if resp.status_code == 401:
            print("[KAKAO] ❗ 토큰 만료로 인해 401 반환됨")
            return False
        return resp.status_code == 200 and resp.json().get("result_code") == 0
    except Exception as e:
        print(f"[KAKAO] ❌ 전송 실패: {e}")
        return False

# ✅ 최종 공개 함수
def send(commit_msg: str, status: str = "success") -> bool:
    tokens = load_tokens()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    if not access_token or not refresh_token:
        print("[KAKAO] ❌ access_token or refresh_token 없음")
        return False

    prefix = "✅ Git Push 성공" if status == "success" else "❌ Git Push 실패"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"{prefix}\n🕒 {time_str}\n\n📝 Commit Message:\n{commit_msg}"

    success = _send_msg(access_token, full_msg)
    if success:
        print("[KAKAO] ✅ 메시지 전송 성공")
        return True

    new_token = refresh_access_token(refresh_token)
    if not new_token:
        return False
    return _send_msg(new_token, full_msg)

# 🔔 Ping 테스트용
def ping() -> bool:
    tokens = load_tokens()
    return _send_msg(tokens.get("access_token", ""), "✅ [Ping 테스트] 카카오 알림 연결 성공")
