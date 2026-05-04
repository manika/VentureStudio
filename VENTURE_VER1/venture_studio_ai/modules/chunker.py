from config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list:
    """Split text into overlapping character-based chunks.

    Returns a list of dicts:
      - text: str
      - chunk_id: int
      - char_start: int
    """
    if not text or not text.strip():
        return []

    chunks = []
    start = 0
    chunk_id = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text_slice = text[start:end]

        # Prefer to break on a sentence/word boundary if possible
        if end < len(text):
            last_period = chunk_text_slice.rfind(". ")
            last_newline = chunk_text_slice.rfind("\n")
            break_point = max(last_period, last_newline)
            if break_point > chunk_size // 2:
                chunk_text_slice = chunk_text_slice[: break_point + 1]

        if chunk_text_slice.strip():
            chunks.append({
                "text": chunk_text_slice.strip(),
                "chunk_id": chunk_id,
                "char_start": start,
            })
            chunk_id += 1

        # Advance by chunk_size - overlap
        advance = len(chunk_text_slice) - chunk_overlap
        if advance <= 0:
            advance = max(1, len(chunk_text_slice))
        start += advance

    return chunks
