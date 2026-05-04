def architect_prompt(task: str, context: str = "") -> str:
    return (
        f'Return JSON only. No prose.\n\nTask: {task}\n\nContext: {context}\n\n'
        f'{{"components": [], "data_flow": "", "risks": [], "next_steps": []}}'
    )
