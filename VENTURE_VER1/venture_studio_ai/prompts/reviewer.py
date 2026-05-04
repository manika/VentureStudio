def reviewer_prompt(code: str) -> str:
    return (
        f'Review this code. Return JSON only.\n\n{code}\n\n'
        f'{{"issues": [], "security_risks": [], "token_optimization": [], "recommended_changes": []}}'
    )
