"""
Reasoner: takes compact context + company profile + query, calls LLM, returns formatted response.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from config import SAVE_PROMPT_LOGS, OUTPUTS_DIR
from .prompt_builder import build_graphrag_prompt
from .llm_client import safe_generate

logger = logging.getLogger(__name__)


def reason(company_profile: dict, user_query: str, compact_context: str) -> str:
    """Build a GraphRAG prompt and call the LLM.

    Returns the formatted response string.
    """
    prompt = build_graphrag_prompt(company_profile, user_query, compact_context)

    if SAVE_PROMPT_LOGS:
        _save_prompt_log(prompt)

    response = safe_generate(prompt)
    return response


def _save_prompt_log(prompt: str) -> None:
    """Save prompt to outputs/prompt_logs/ for audit."""
    try:
        log_dir = Path(OUTPUTS_DIR) / "prompt_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_path = log_dir / f"prompt_{timestamp}.txt"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(prompt)
    except Exception as e:
        logger.warning("Could not save prompt log: %s", e)
