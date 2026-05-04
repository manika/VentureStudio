def format_output(raw_text: str, docs: list) -> str:
    # For Stage 1 we return the raw LLM text and append source list
    sources = []
    for d in docs:
        sources.append(d.get('path','unknown'))
    source_md = "\n\n**Sources:**\n" + "\n".join(f"- {s}" for s in sources) if sources else "\n\n**Sources:** None"
    return raw_text + source_md
