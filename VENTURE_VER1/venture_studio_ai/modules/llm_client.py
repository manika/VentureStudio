import requests
from config import (
    OLLAMA_URL,
    MODEL_NAME,
    MODEL_FAST,
    MODEL_REASONING,
    MAX_INPUT_CHARS,
    MAX_OUTPUT_TOKENS,
)


def generate_response(
    prompt: str,
    model: str = MODEL_REASONING,
    max_tokens: int = MAX_OUTPUT_TOKENS,
    timeout: int = 300,
    temperature: float = 0.3,
) -> str:
    # Backward compatibility: legacy callers may pass max_tokens as second positional arg
    if isinstance(model, int):
        max_tokens = model
        model = MODEL_NAME

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "num_predict": max_tokens,
            "num_ctx": 4096,
            "num_thread": 8,
            "temperature": temperature,
        },
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        response = data.get("response", "").strip()
        if not response:
            response = data.get("thinking", "").strip()
        return response or "[No response received from model]"
    except requests.RequestException as e:
        return f"[Error] Unable to contact Ollama at {OLLAMA_URL}: {e}"


def safe_generate(
    prompt: str,
    model: str = MODEL_REASONING,
    max_tokens: int = MAX_OUTPUT_TOKENS,
    timeout: int = 300,
    temperature: float = 0.3,
) -> str:
    # Backward compatibility: legacy callers may pass max_tokens as second positional arg
    if isinstance(model, int):
        max_tokens = model
        model = MODEL_NAME

    if len(prompt) > MAX_INPUT_CHARS:
        prompt = prompt[:MAX_INPUT_CHARS] + "\n[Context trimmed for token limit]"
    return generate_response(
        prompt,
        model=model,
        max_tokens=max_tokens,
        timeout=timeout,
        temperature=temperature,
    )


def generate_fast(prompt: str, max_tokens: int = 512) -> str:
    return safe_generate(prompt, model=MODEL_FAST, max_tokens=max_tokens)


def generate_reasoning(prompt: str, max_tokens: int = MAX_OUTPUT_TOKENS) -> str:
    return safe_generate(prompt, model=MODEL_REASONING, max_tokens=max_tokens)
