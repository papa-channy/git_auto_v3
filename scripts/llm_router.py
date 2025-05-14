import importlib

def call_llm(prompt: str, llm_cfg: dict) -> str:
    providers = llm_cfg["provider"]
    models = llm_cfg["model"]
    llm_param = {
        "temperature": llm_cfg.get("temperature", 0.7),
        "top_p": llm_cfg.get("top_p", 0.9),
        "top_k": llm_cfg.get("top_k", 80),
        "max_tokens": llm_cfg.get("max_tokens", 1024)
    }

    for provider, model in zip(providers, models):
        try:
            module = importlib.import_module(f"llm.{model}")
            return module.call(prompt, llm_param)
        except Exception as e:
            continue

    raise RuntimeError("❌ 모든 LLM 호출 실패: fallback 실패")
