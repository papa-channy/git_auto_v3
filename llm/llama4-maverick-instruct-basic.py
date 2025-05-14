import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("FIREWORKS_API_KEY")

def call(prompt: str, llm_param: dict) -> str:
    if not API_KEY:
        raise ValueError("FIREWORKS_API_KEY 없음")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "model": "accounts/fireworks/models/llama4-maverick-instruct-basic",
        "max_tokens": llm_param.get("max_tokens", 1024),
        "top_p": llm_param.get("top_p", 0.8),
        "top_k": llm_param.get("top_k", 40),
        "temperature": llm_param.get("temperature", 0.7),
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
            }
        ]
    }

    response = requests.post(
        "https://api.fireworks.ai/inference/v1/chat/completions",
        headers=headers, json=payload, timeout=60
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()
