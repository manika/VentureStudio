import re

# Redaction targets genuine PII and financial data only.
# Dates and document/standard numbers (ISO 13485, SOP numbers, etc.) are NOT
# redacted — they are factual operational data the advisor needs to answer
# questions accurately (e.g. "when was the last audit?").
REDACTION_PATTERNS = [
    # Contact info
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
    (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE]'),
    # Financial data
    (r'\$[\d,]+(?:\.\d{2})?|\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|dollars?|million|billion)\b',
     '[AMOUNT]'),
    # Contractual identifiers
    (r'\b(?:Contract|Agreement|Order|Invoice|PO|SOW|MSA|NDA)\s*(?:#|No\.?|Number)?\s*[A-Z0-9-]+\b',
     '[CONTRACT_ID]'),
    (r'\b(?:Account|Acct)\s*(?:#|No\.?)?\s*\d{4,}\b', '[ACCOUNT_ID]'),
    # SSN
    (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),
]


def redact_text(text: str) -> dict:
    """Apply all redaction patterns to text.

    Returns a dict with keys:
      - redacted_text: str
      - redaction_count: int
      - redaction_types: list[str]
    """
    redacted = text
    redaction_types = set()
    count = 0
    for pattern, placeholder in REDACTION_PATTERNS:
        matches = re.findall(pattern, redacted, flags=re.IGNORECASE)
        if matches:
            redacted = re.sub(pattern, placeholder, redacted, flags=re.IGNORECASE)
            redaction_types.add(placeholder.strip("[]"))
            count += len(matches)
    return {
        "redacted_text": redacted,
        "redaction_count": count,
        "redaction_types": list(redaction_types),
    }
