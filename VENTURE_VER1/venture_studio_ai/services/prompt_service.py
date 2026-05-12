from prompts.architect import architect_prompt
from prompts.coder import coder_prompt
from prompts.reviewer import reviewer_prompt

def build_advisor_prompt(prompt_type: str, task: str, context: str = "") -> str:
    if prompt_type == "architect":
        return architect_prompt(task, context)
    if prompt_type == "coder":
        return coder_prompt(task, context)
    if prompt_type == "reviewer":
        return reviewer_prompt(context or task)
    raise ValueError(f"Unknown prompt type: {prompt_type}")
