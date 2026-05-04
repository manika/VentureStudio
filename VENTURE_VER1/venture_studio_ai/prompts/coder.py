def coder_prompt(task: str, code_context: str = "") -> str:
    return f"Return only code. Minimal changes. No unrelated edits. Simple Python.\n\nTask: {task}\n\nContext:\n{code_context}"
