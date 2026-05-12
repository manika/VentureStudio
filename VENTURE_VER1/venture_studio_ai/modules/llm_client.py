import os
import requests
from config import (
    OLLAMA_URL,
    MODEL_NAME,
    MODEL_FAST,
    MODEL_REASONING,
    CLAUDE_MODEL,
    OPENAI_MODEL,
    MAX_INPUT_CHARS,
    MAX_OUTPUT_TOKENS,
)

# Module-level backend selector — "qwen" (default), "claude", or "openai"
_backend: str = "qwen"


def set_backend(backend: str) -> None:
    global _backend
    if backend not in ("qwen", "claude", "openai"):
        raise ValueError(f"Unknown backend: {backend}")
    _backend = backend


def get_backend() -> str:
    return _backend


def _generate_ollama(
    prompt: str,
    model: str,
    max_tokens: int,
    timeout: int,
    temperature: float,
) -> str:
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


def _generate_claude(
    prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    try:
        import anthropic
    except ImportError:
        return "[Error] anthropic package not installed. Run: pip install anthropic"

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "[Error] ANTHROPIC_API_KEY environment variable not set."

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        return f"[Error] Claude API call failed: {e}"


def _generate_openai(
    prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    try:
        import openai
    except ImportError:
        return "[Error] openai package not installed. Run: pip install openai"

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return "[Error] OPENAI_API_KEY environment variable not set."

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error] OpenAI API call failed: {e}"


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
        model = MODEL_REASONING

    if _backend == "claude":
        return _generate_claude(prompt, max_tokens=max_tokens, temperature=temperature)
    if _backend == "openai":
        return _generate_openai(prompt, max_tokens=max_tokens, temperature=temperature)
    return _generate_ollama(prompt, model=model, max_tokens=max_tokens, timeout=timeout, temperature=temperature)


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
        model = MODEL_REASONING

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
