# modules/smart_advisor.py
"""
Smart Advisor query pipeline.
Semantic search ChromaDB -> deduplicate/compress chunks -> single Qwen LLM call.
"""

import logging
from config import MAX_CHUNK_CHARS

from .vector_store import ChromaStore
from .llm_client import generate_reasoning
from services.prompt_service import build_prompt

logger = logging.getLogger(__name__)

# Module-level singleton ChromaStore
_chroma_store: ChromaStore | None = None


def _get_store() -> ChromaStore:
    global _chroma_store
    if _chroma_store is None:
        _chroma_store = ChromaStore()
    return _chroma_store


def _build_profile_text(company_profile: dict) -> str:
    """Render company profile fields as a compact string."""
    lines = []
    field_labels = {
        "name": "Company",
        "stage": "Stage",
        "product_type": "Product Type",
        "regulatory": "Regulatory Area",
        "notes": "Notes",
    }
    for key, label in field_labels.items():
        value = company_profile.get(key, "").strip()
        if value:
            lines.append(f"- {label}: {value}")
    # Also include any extra keys not in the standard set
    for key, value in company_profile.items():
        if key not in field_labels and value:
            lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    return "\n".join(lines) if lines else "(no profile provided)"


def _deduplicate_chunks(chunks: list[dict]) -> list[dict]:
    """Remove exact duplicate chunk texts, preserving order."""
    seen = set()
    unique = []
    for chunk in chunks:
        text = chunk.get("text", "")
        if text not in seen:
            seen.add(text)
            unique.append(chunk)
    return unique


def _diverse_chunks(chunks: list[dict], max_per_source: int = 2, final_k: int = 8) -> list[dict]:
    """Re-rank chunks for source diversity: take up to max_per_source per source,
    preserving semantic rank order, then return final_k total."""
    seen_sources: dict[str, int] = {}
    selected = []
    for chunk in chunks:
        src = chunk.get("source", chunk.get("path", ""))
        count = seen_sources.get(src, 0)
        if count < max_per_source:
            selected.append(chunk)
            seen_sources[src] = count + 1
        if len(selected) >= final_k:
            break
    return selected


def ask(
    query: str,
    company_profile: dict,
    top_k: int = 8,
    progress_callback=None,
    extra_chunks: list | None = None,
) -> tuple[str, dict]:
    """
    Run the Smart Advisor pipeline for a single query.

    Steps:
      1. Semantic search ChromaDB (knowledgebase).
      2. Merge extra_chunks (company/founder TF-IDF hits) if provided.
      3. Source-diversity re-rank.
      4. Deduplicate and truncate.
      5. Build compact prompt.
      6. Single LLM call.

    Returns:
        (response_text, debug_meta)
    """
    def _progress(msg: str):
        if progress_callback:
            progress_callback(msg)

    store = _get_store()

    # 1. Wide semantic search over knowledgebase
    _progress("Searching knowledge base...")
    candidate_k = top_k * 3
    kb_chunks = store.query(query_text=query, top_k=candidate_k)
    chunks_retrieved = len(kb_chunks)
    _progress(f"Found {chunks_retrieved} candidate chunks — ranking by relevance...")

    # 2. Source-diversity re-rank on knowledgebase chunks only
    diverse = _diverse_chunks(kb_chunks, max_per_source=2, final_k=top_k)

    # 3. Deduplicate knowledgebase results
    unique_chunks = _deduplicate_chunks(diverse)
    compression_applied = len(unique_chunks) < chunks_retrieved

    # 4. Merge company/founder extra chunks — always included, not subject to ranking cutoff
    if extra_chunks:
        existing_texts = {c.get("text", "") for c in unique_chunks}
        new_extra = [c for c in extra_chunks if c.get("text", "").strip() and c.get("text", "") not in existing_texts]
        if new_extra:
            _progress(f"Adding {len(new_extra)} chunk(s) from company/founder docs...")
        unique_chunks = new_extra + unique_chunks

    # 3a. Inject opening chunks (chunk_ids 0 and 1) for every source in semantic results.
    #     Cover pages carry dates / version headers that don't rank well semantically
    #     because their bodies are boilerplate-heavy. Fetching the first two chunks
    #     (CHUNK_SIZE ~1000 chars each) maximises the chance of capturing the date line.
    #     These chunks bypass MAX_CHUNK_CHARS truncation so no date is cut off.
    unique_sources = list({
        c.get("source", c.get("path", ""))
        for c in unique_chunks
        if c.get("source") or c.get("path")
    })
    _progress(f"Selected {len(unique_sources)} source file(s) — loading document headers...")
    cover_chunk_texts: set[str] = set()
    if unique_sources:
        cover_chunks = store.get_chunks_by_source(unique_sources, chunk_ids=[0, 1])
        existing_texts = {c.get("text", "") for c in unique_chunks}
        new_covers = [c for c in cover_chunks if c.get("text", "") not in existing_texts]
        for c in new_covers:
            c["_no_truncate"] = True
            cover_chunk_texts.add(c.get("text", ""))
        unique_chunks = new_covers + unique_chunks

    # 4. Truncate each chunk and collect source names
    sources_used = []
    context_parts = []
    for i, chunk in enumerate(unique_chunks, start=1):
        text = chunk.get("text", "").strip()
        if not text:
            continue
        if not chunk.get("_no_truncate") and len(text) > MAX_CHUNK_CHARS:
            text = text[:MAX_CHUNK_CHARS] + "…"
            compression_applied = True
        source = chunk.get("source", chunk.get("path", "unknown"))
        context_parts.append(f"[Chunk {i} | Source: {source}]\n{text}")
        if source and source not in sources_used:
            sources_used.append(source)

    knowledge_block = "\n\n".join(context_parts) if context_parts else "(no relevant knowledge found)"

    # 5. Build prompt
    _progress("Building prompt and calling advisor model...")
    profile_text = _build_profile_text(company_profile)
    context = (
        f"## Company Profile\n{profile_text}"
        f"\n\n## Knowledge Chunks (from knowledgebase, company docs, and founder experience)\n{knowledge_block}"
    )
    prompt = build_prompt(prompt_type="architect", task=query, context=context)

    input_chars = len(prompt)

    # 6. Single LLM call
    try:
        # Use generate_reasoning for final advisory responses (do not use generate_fast)
        response_text = generate_reasoning(prompt)
    except Exception as exc:
        logger.exception("smart_advisor LLM call failed")
        response_text = f"[Error] LLM call failed: {exc}"

    # 7. Return
    debug_meta = {
        "chunks_retrieved": chunks_retrieved,
        "sources_used": sources_used,
        "input_chars": input_chars,
        "compression_applied": compression_applied,
    }

    return response_text, debug_meta
