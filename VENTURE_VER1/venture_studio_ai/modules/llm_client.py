import requests
from config import OLLAMA_URL, MODEL_NAME, MAX_INPUT_CHARS, MAX_OUTPUT_TOKENS


def generate_response(prompt: str, max_tokens: int = MAX_OUTPUT_TOKENS, timeout: int = 300) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "num_predict": max_tokens,
            "num_ctx": 4096,
            "num_thread": 8,
            "temperature": 0.3,
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


def safe_generate(prompt: str, max_tokens: int = MAX_OUTPUT_TOKENS) -> str:
    if len(prompt) > MAX_INPUT_CHARS:
        prompt = prompt[:MAX_INPUT_CHARS] + "\n[Context trimmed for token limit]"
    return generate_response(prompt, max_tokens=max_tokens)
