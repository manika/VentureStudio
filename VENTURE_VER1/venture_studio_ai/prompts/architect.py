def architect_prompt(task: str, context: str = "") -> str:
    return (
        "You are an expert venture studio advisor.\n\n"
        f"QUESTION: {task}\n\n"
        "Use the context sections below to answer.\n"
        "- For factual questions (who, what, how many, tell me about), answer directly and concisely from the most relevant section.\n"
        "- For advisory questions (how should we, what practices, recommendations), give structured guidance with Key Risks and Next Steps.\n"
        "- Do not return JSON.\n\n"
        f"{context}\n\n"
        f"Answer: "
    )
