"""
Context compression utilities: deduplication, trimming, and compact context building.
"""

from config import MAX_CHUNK_CHARS


def deduplicate_chunks(chunks: list) -> list:
    """Remove chunks with near-identical content (based on first 200 chars)."""
    seen = set()
    unique = []
    for chunk in chunks:
        text = chunk.get("text", "")
        key = text[:200].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(chunk)
    return unique


def compress_chunks(chunks: list, max_chars: int = MAX_CHUNK_CHARS * 5) -> list:
    """Trim chunks list so total character count stays within max_chars."""
    result = []
    total = 0
    for chunk in chunks:
        text = chunk.get("text", "")
        if total + len(text) > max_chars:
            # Add a partial chunk if there's room
            remaining = max_chars - total
            if remaining > 100:
                partial = dict(chunk)
                partial["text"] = text[:remaining] + "..."
                result.append(partial)
            break
        result.append(chunk)
        total += len(text)
    return result


def build_compact_context(chunks: list, graph_nodes: list, graph_relationships: list) -> str:
    """Combine retrieved chunks and graph data into a compact context string."""
    parts = []

    if graph_nodes:
        parts.append("### Relevant Knowledge Graph Nodes")
        for node in graph_nodes:
            node_id = node.get("id", "unknown")
            desc = node.get("generalized_description", "")
            ntype = node.get("node_type", "")
            parts.append(f"- [{ntype}] {node_id}: {desc}")

    if graph_relationships:
        parts.append("\n### Relevant Relationships")
        for rel in graph_relationships:
            src = rel.get("source", "?")
            tgt = rel.get("target", "?")
            rtype = rel.get("relationship_type", rel.get("relationship", "related_to"))
            evidence = rel.get("generalized_evidence_summary", rel.get("evidence_summary", ""))
            parts.append(f"- {src} --[{rtype}]--> {tgt}: {evidence}")

    if chunks:
        parts.append("\n### Retrieved Document Chunks")
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source", chunk.get("path", "unknown"))
            text = chunk.get("text", "")[:MAX_CHUNK_CHARS]
            parts.append(f"\n[Chunk {i} | Source: {source}]\n{text}")

    return "\n".join(parts)
