import os
import requests
import random
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_API_KEY")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")

NOTION_URL_BASE = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

COLORS = [
    "gray_background", "brown_background", "orange_background",
    "yellow_background", "green_background", "blue_background",
    "purple_background", "pink_background"
]

NUM_EMOJIS = ['①','②','③','④','⑤','⑥','⑦','⑧','⑨','⑩','⑪','⑫','⑬','⑭','⑮','⑯','⑰','⑱','⑲','⑳']

def get_repo_name():
    import subprocess
    try:
        url = subprocess.run("git config --get remote.origin.url", shell=True, capture_output=True, text=True).stdout.strip()
        repo = url.rstrip(".git").split("/")[-1] if url else "Unknown"
        return repo.replace("-", " ").title()
    except Exception:
        return "Unknown Repo"

def get_notion_blocks(parent_id):
    url = f"{NOTION_URL_BASE}/blocks/{parent_id}/children?page_size=100"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get("results", [])

def find_or_create_toggle_block(parent_id, title_text):
    try:
        children = get_notion_blocks(parent_id)
        for block in children:
            if block["type"] == "toggle" and \
               block["toggle"]["rich_text"][0]["text"]["content"] == title_text:
                return block["id"]
    except Exception:
        pass

    payload = {
        "children": [{
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"type": "text", "text": {"content": title_text}}],
                "children": []
            }
        }]
    }

    resp = requests.patch(f"{NOTION_URL_BASE}/blocks/{parent_id}/children", headers=HEADERS, json=payload)
    resp.raise_for_status()
    return resp.json()["results"][0]["id"]

def create_paragraph_block(title: str, text: str):
    full_text = f"{title}\n\n{text}" if title else text
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{
                "type": "text",
                "text": { "content": full_text }
            }],
            "color": random.choice(COLORS)
        }
    }

# ✅ 날짜별 기록 업로드 (fx_out 단일 묶음)
def upload_fx_record(filename: str, fx_text: str):
    now = datetime.now()
    repo_name = get_repo_name()
    top_toggle = f"📁 {repo_name}"
    mid_toggle = f"📅 {now.strftime('%y년 %m월')}"
    time_toggle = f"🕒 {now.strftime('%d일 %p %I시 %M분').replace('AM', '오전').replace('PM', '오후')}"

    try:
        top_id = find_or_create_toggle_block(NOTION_PAGE_ID, top_toggle)
        mid_id = find_or_create_toggle_block(top_id, mid_toggle)
        time_id = find_or_create_toggle_block(mid_id, time_toggle)

        blocks = [
            create_paragraph_block(f"📘 FILE: {filename}", fx_text)
        ]
        requests.patch(
            f"{NOTION_URL_BASE}/blocks/{time_id}/children",
            headers=HEADERS,
            json={"children": blocks}
        )
    except Exception as e:
        print(f"[NOTION] ❌ fx 기록 업로드 실패: {e}")

