"""
Extract entities from redacted text chunks using the local LLM.
Returns generalized, anonymized entity descriptions — no reconstruction of redacted values.
"""

import json
import logging
from .llm_client import generate_fast

logger = logging.getLogger(__name__)

ENTITY_PROMPT_TEMPLATE = """You are an information extraction assistant.
Extract entities from the following redacted text chunk.
Return ONLY a JSON array of objects. Each object must have:
  "label": short descriptive name (generalized, no reconstructed PII)
  "type": one of [ORGANIZATION, PROCESS, TECHNOLOGY, CONCEPT, ROLE, DOCUMENT, OTHER]
  "description": one sentence generalized description

Rules:
- Do NOT reconstruct redacted values (e.g. [EMAIL], [AMOUNT], [DATE]).
- Limit to at most 8 entities.
- Return ONLY valid JSON, no explanation.

Text:
{chunk}

JSON array:"""


def _parse_json_response(raw: str) -> list:
    """Attempt to parse JSON array from LLM response."""
    raw = raw.strip()
    # Find first '[' and last ']'
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        return json.loads(raw[start: end + 1])
    except json.JSONDecodeError:
        return []


def extract_entities(chunk_text: str, source_doc: str = "") -> list:
    """Extract entities from a single text chunk.

    Returns a list of entity dicts:
      label, type, description, source_doc
    """
    if not chunk_text or not chunk_text.strip():
        return []

    prompt = ENTITY_PROMPT_TEMPLATE.format(chunk=chunk_text[:2000])
    raw = safe_generate(prompt, max_tokens=512)

    entities = _parse_json_response(raw)

    if not entities:
        # One retry with a simpler prompt
        retry_prompt = (
            f"Extract up to 5 key concepts from this text as a JSON array "
            f'[{{"label":"...", "type":"CONCEPT", "description":"..."}}].\n'
            f"Text: {chunk_text[:800]}\nJSON:"
        )
        raw2 = safe_generate(retry_prompt, max_tokens=300)
        entities = _parse_json_response(raw2)

    result = []
    for e in entities:
        if isinstance(e, dict) and e.get("label"):
            result.append({
                "label": str(e.get("label", ""))[:100],
                "type": str(e.get("type", "OTHER")),
                "description": str(e.get("description", ""))[:300],
                "source_doc": source_doc,
            })

    if not result:
        logger.warning("Entity extraction returned no results for source: %s", source_doc)

    return result
