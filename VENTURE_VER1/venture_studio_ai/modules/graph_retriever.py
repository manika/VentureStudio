"""
GraphRAG retriever: combines knowledge graph traversal with vector store retrieval.
"""

import logging
from config import MAX_GRAPH_NODES, MAX_GRAPH_RELATIONSHIPS, MAX_RETRIEVED_CHUNKS

from . import knowledge_graph as kg
from .vector_store import ChromaStore
from .context_compressor import deduplicate_chunks, compress_chunks, build_compact_context

logger = logging.getLogger(__name__)

# Module-level shared ChromaStore instance
_chroma_store: ChromaStore = None


def _get_chroma_store() -> ChromaStore:
    global _chroma_store
    if _chroma_store is None:
        _chroma_store = ChromaStore()
    return _chroma_store


def retrieve(query: str) -> tuple:
    """Run GraphRAG retrieval for a query.

    Returns:
        compact_context (str): combined context string
        metadata (dict): retrieval stats
    """
    # 1. Search knowledge graph nodes
    matched_nodes = kg.search_nodes(query)[:MAX_GRAPH_NODES]

    # 2. Expand 1-hop neighbors
    expanded_node_ids = set(n["id"] for n in matched_nodes)
    for node in list(matched_nodes):
        neighbors = kg.get_neighbors(node["id"])
        for neighbor in neighbors:
            if len(expanded_node_ids) >= MAX_GRAPH_NODES:
                break
            expanded_node_ids.add(neighbor)

    # Collect full node data for expanded set
    all_graph_nodes = matched_nodes[:]
    g = kg._get_graph()
    for nid in expanded_node_ids:
        if nid not in {n["id"] for n in all_graph_nodes}:
            if g.has_node(nid):
                data = dict(g.nodes[nid])
                all_graph_nodes.append({"id": nid, **data})

    # 3. Collect relevant edges
    graph_relationships = []
    for src, tgt, data in g.edges(data=True):
        if src in expanded_node_ids or tgt in expanded_node_ids:
            graph_relationships.append({"source": src, "target": tgt, **data})
            if len(graph_relationships) >= MAX_GRAPH_RELATIONSHIPS:
                break

    # 4. Query vector store
    store = _get_chroma_store()
    raw_chunks = store.query(query, top_k=MAX_RETRIEVED_CHUNKS)

    # 5. Deduplicate and compress
    deduped = deduplicate_chunks(raw_chunks)
    compressed = compress_chunks(deduped)

    # 6. Build compact context
    compact_context = build_compact_context(compressed, all_graph_nodes, graph_relationships)

    metadata = {
        "graph_nodes_used": len(all_graph_nodes),
        "graph_relationships_used": len(graph_relationships),
        "chunks_retrieved": len(raw_chunks),
        "chunks_after_dedup": len(deduped),
        "chunks_after_compression": len(compressed),
        "input_chars": len(compact_context),
        "compression_applied": len(raw_chunks) > len(compressed),
    }

    return compact_context, metadata
