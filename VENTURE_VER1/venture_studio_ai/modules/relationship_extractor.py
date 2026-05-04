"""
Extract relationships between entities from redacted text chunks using the local LLM.
Returns generalized, anonymized relationship descriptions.
"""

import json
import logging
from .llm_client import safe_generate

logger = logging.getLogger(__name__)

RELATIONSHIP_PROMPT_TEMPLATE = """You are an information extraction assistant.
Extract relationships between entities from the following redacted text chunk.
Return ONLY a JSON array of objects. Each object must have:
  "source": entity label (subject)
  "target": entity label (object)
  "relationship": short verb phrase describing the relationship
  "evidence_summary": one sentence generalized summary (no reconstructed PII)

Rules:
- Do NOT reconstruct redacted values (e.g. [EMAIL], [AMOUNT], [DATE]).
- Limit to at most 6 relationships.
- Return ONLY valid JSON, no explanation.

Text:
{chunk}

JSON array:"""


def _parse_json_response(raw: str) -> list:
    """Attempt to parse JSON array from LLM response."""
    raw = raw.strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        return json.loads(raw[start: end + 1])
    except json.JSONDecodeError:
        return []


def extract_relationships(chunk_text: str, source_doc: str = "") -> list:
    """Extract relationships from a single text chunk.

    Returns a list of relationship dicts:
      source, target, relationship, evidence_summary, source_doc
    """
    if not chunk_text or not chunk_text.strip():
        return []

    prompt = RELATIONSHIP_PROMPT_TEMPLATE.format(chunk=chunk_text[:2000])
    raw = safe_generate(prompt, max_tokens=512)

    relationships = _parse_json_response(raw)

    if not relationships:
        # One retry
        retry_prompt = (
            f"List up to 4 relationships in this text as JSON array "
            f'[{{"source":"...", "target":"...", "relationship":"...", "evidence_summary":"..."}}].\n'
            f"Text: {chunk_text[:800]}\nJSON:"
        )
        raw2 = safe_generate(retry_prompt, max_tokens=300)
        relationships = _parse_json_response(raw2)

    result = []
    for r in relationships:
        if isinstance(r, dict) and r.get("source") and r.get("target"):
            result.append({
                "source": str(r.get("source", ""))[:100],
                "target": str(r.get("target", ""))[:100],
                "relationship": str(r.get("relationship", "related_to"))[:100],
                "evidence_summary": str(r.get("evidence_summary", ""))[:300],
                "source_doc": source_doc,
            })

    if not result:
        logger.warning("Relationship extraction returned no results for source: %s", source_doc)

    return result
