"""
Services package — thin dispatch layer between modules and prompt templates.
"""
from .prompt_service import build_advisor_prompt

__all__ = ["build_advisor_prompt"]
