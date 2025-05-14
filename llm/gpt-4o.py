import os
import openai
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

def call(prompt: str, llm_param: dict) -> str:
    if not API_KEY:
        raise ValueError("OPENAI_API_KEY 없음")

    openai.api_key = API_KEY

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=llm_param.get("temperature", 0.7),
        max_tokens=llm_param.get("max_tokens", 1024),
        top_p=llm_param.get("top_p", 0.8),
        frequency_penalty=0,
        presence_penalty=0
    )

    return response.choices[0].message["content"].strip()
