"""
Knowledge graph manager using NetworkX.
Nodes represent generalized entities; edges represent relationships.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import networkx as nx

from config import KNOWLEDGE_GRAPH_PATH, KNOWLEDGE_GRAPH_JSON

logger = logging.getLogger(__name__)

# Module-level singleton graph
_graph: Optional[nx.DiGraph] = None


def _get_graph() -> nx.DiGraph:
    global _graph
    if _graph is None:
        _graph = nx.DiGraph()
    return _graph


def load_graph() -> nx.DiGraph:
    """Load graph from disk if it exists, otherwise return empty graph."""
    global _graph
    path = Path(KNOWLEDGE_GRAPH_PATH)
    if path.exists():
        try:
            _graph = nx.read_graphml(str(path))
            logger.info("Loaded knowledge graph: %d nodes, %d edges",
                        _graph.number_of_nodes(), _graph.number_of_edges())
            return _graph
        except Exception as e:
            logger.warning("Could not load graph from %s: %s", path, e)
    _graph = nx.DiGraph()
    return _graph


def save_graph() -> None:
    """Persist graph to both .graphml and .json formats."""
    g = _get_graph()
    path = Path(KNOWLEDGE_GRAPH_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        nx.write_graphml(g, str(path))
    except Exception as e:
        logger.warning("Could not save graphml: %s", e)

    json_path = Path(KNOWLEDGE_GRAPH_JSON)
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(export_json(), f, indent=2)
    except Exception as e:
        logger.warning("Could not save graph JSON: %s", e)


def add_entities(entities: list, source_doc: str = "") -> None:
    """Add entity nodes to the graph."""
    g = _get_graph()
    now = datetime.now(timezone.utc).isoformat()
    for entity in entities:
        label = entity.get("label", "").strip()
        if not label:
            continue
        if g.has_node(label):
            # Update existing node: increment confidence, update source list
            existing = g.nodes[label]
            sources = existing.get("source_document", "")
            if source_doc and source_doc not in sources:
                g.nodes[label]["source_document"] = sources + "|" + source_doc
            g.nodes[label]["confidence"] = min(1.0, float(existing.get("confidence", 0.5)) + 0.1)
        else:
            g.add_node(
                label,
                node_type=entity.get("type", "OTHER"),
                generalized_description=entity.get("description", ""),
                source_document=source_doc,
                confidence=0.7,
                created_at=now,
            )


def add_relationships(relationships: list, source_doc: str = "") -> None:
    """Add relationship edges to the graph."""
    g = _get_graph()
    for rel in relationships:
        src = rel.get("source", "").strip()
        tgt = rel.get("target", "").strip()
        if not src or not tgt:
            continue
        # Ensure nodes exist (minimal)
        if not g.has_node(src):
            g.add_node(src, node_type="OTHER", generalized_description="", source_document=source_doc,
                       confidence=0.5, created_at=datetime.now(timezone.utc).isoformat())
        if not g.has_node(tgt):
            g.add_node(tgt, node_type="OTHER", generalized_description="", source_document=source_doc,
                       confidence=0.5, created_at=datetime.now(timezone.utc).isoformat())

        if g.has_edge(src, tgt):
            g[src][tgt]["confidence"] = min(1.0, float(g[src][tgt].get("confidence", 0.5)) + 0.1)
        else:
            g.add_edge(
                src,
                tgt,
                relationship_type=rel.get("relationship", "related_to"),
                generalized_evidence_summary=rel.get("evidence_summary", ""),
                source_document=source_doc,
                confidence=0.7,
            )


def export_json() -> dict:
    """Export graph as a JSON-serialisable dict."""
    g = _get_graph()
    nodes = []
    for node_id, data in g.nodes(data=True):
        nodes.append({"id": node_id, **{k: str(v) for k, v in data.items()}})
    edges = []
    for src, tgt, data in g.edges(data=True):
        edges.append({"source": src, "target": tgt, **{k: str(v) for k, v in data.items()}})
    return {"nodes": nodes, "edges": edges}


def get_neighbors(node: str) -> list:
    """Return list of neighbor node IDs (1-hop)."""
    g = _get_graph()
    if not g.has_node(node):
        return []
    return list(nx.neighbors(g, node))


def search_nodes(query: str) -> list:
    """Return nodes whose label or description contains the query substring (case-insensitive)."""
    g = _get_graph()
    q = query.lower()
    results = []
    for node_id, data in g.nodes(data=True):
        label_match = q in node_id.lower()
        desc_match = q in str(data.get("generalized_description", "")).lower()
        if label_match or desc_match:
            results.append({"id": node_id, **data})
    return results


def get_graph_stats() -> dict:
    """Return basic graph statistics."""
    g = _get_graph()
    return {
        "nodes": g.number_of_nodes(),
        "edges": g.number_of_edges(),
        "is_dag": nx.is_directed_acyclic_graph(g) if g.number_of_nodes() > 0 else True,
    }


def reset_graph() -> None:
    """Clear the in-memory graph (used before full rebuilds)."""
    global _graph
    _graph = nx.DiGraph()
