"""
Graph pipeline orchestrator: builds knowledge graph and vector store from a folder of documents.
"""

import logging
from pathlib import Path
from typing import Callable, Optional

from .file_utils import list_files
from .document_loader import extract_text
from .redaction import redact_text
from .chunker import chunk_text
from .entity_extractor import extract_entities
from .relationship_extractor import extract_relationships
from . import knowledge_graph as kg
from .vector_store import ChromaStore
from .cache_manager import should_reprocess, update_hash, set_cache, get_cache

logger = logging.getLogger(__name__)


def build_knowledge_graph(
    folder_path: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> dict:
    """Orchestrate full pipeline: text extraction → redaction → chunking →
    entity/relationship extraction → graph + vector store building.

    Args:
        folder_path: Path to folder containing source documents.
        progress_callback: Optional callable(message: str) for progress reporting.

    Returns:
        stats dict with counts of files, chunks, entities, relationships, nodes, edges.
    """
    folder = Path(folder_path)
    if not folder.exists():
        return {"error": f"Folder not found: {folder_path}"}

    def _log(msg: str):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    # Reset graph for full rebuild
    kg.reset_graph()
    kg.load_graph()

    chroma_store = ChromaStore()

    files = list_files(folder)
    _log(f"Found {len(files)} files in {folder_path}")

    stats = {
        "files_found": len(files),
        "files_processed": 0,
        "files_skipped": 0,
        "total_chunks": 0,
        "total_entities": 0,
        "total_relationships": 0,
    }

    for file_path in files:
        file_str = str(file_path)
        source_name = file_path.name

        # Check cache
        if not should_reprocess(file_str):
            _log(f"  [skip] {source_name} (unchanged)")
            stats["files_skipped"] += 1
            continue

        _log(f"  [process] {source_name}")

        # 1. Extract text
        try:
            raw_text = extract_text(file_path)
        except Exception as e:
            _log(f"  [error] Could not extract text from {source_name}: {e}")
            continue

        if not raw_text or not raw_text.strip():
            _log(f"  [skip] {source_name} (empty text)")
            stats["files_skipped"] += 1
            continue

        # 2. Redact
        try:
            redaction_result = redact_text(raw_text)
            redacted = redaction_result["redacted_text"]
            _log(f"    Redacted {redaction_result['redaction_count']} items "
                 f"({redaction_result['redaction_types']})")
            set_cache("redacted_text", file_str, {
                "redaction_count": redaction_result["redaction_count"],
                "redaction_types": redaction_result["redaction_types"],
            })
        except Exception as e:
            _log(f"  [error] Redaction failed for {source_name}: {e}")
            redacted = raw_text

        # 3. Chunk
        try:
            chunks = chunk_text(redacted)
            _log(f"    Created {len(chunks)} chunks")
        except Exception as e:
            _log(f"  [error] Chunking failed for {source_name}: {e}")
            chunks = [{"text": redacted[:2000], "chunk_id": 0, "char_start": 0}]

        stats["total_chunks"] += len(chunks)

        # 4. Add chunks to vector store
        try:
            chroma_store.add_chunks(chunks, source_doc=source_name)
        except Exception as e:
            _log(f"  [warn] Vector store add failed for {source_name}: {e}")

        # 5. Extract entities and relationships (from first few chunks to limit LLM calls)
        MAX_CHUNKS_FOR_EXTRACTION = 5
        file_entities = []
        file_relationships = []

        for chunk in chunks[:MAX_CHUNKS_FOR_EXTRACTION]:
            chunk_text_str = chunk.get("text", "")

            # Entities
            try:
                entities = extract_entities(chunk_text_str, source_doc=source_name)
                file_entities.extend(entities)
            except Exception as e:
                _log(f"  [warn] Entity extraction error: {e}")

            # Relationships
            try:
                rels = extract_relationships(chunk_text_str, source_doc=source_name)
                file_relationships.extend(rels)
            except Exception as e:
                _log(f"  [warn] Relationship extraction error: {e}")

        _log(f"    Entities: {len(file_entities)}, Relationships: {len(file_relationships)}")

        # 6. Add to knowledge graph
        kg.add_entities(file_entities, source_doc=source_name)
        kg.add_relationships(file_relationships, source_doc=source_name)

        # Cache entity/relationship extraction results
        set_cache("entity_extractions", file_str, file_entities)
        set_cache("relationship_extractions", file_str, file_relationships)

        stats["total_entities"] += len(file_entities)
        stats["total_relationships"] += len(file_relationships)
        stats["files_processed"] += 1

        # Update file hash so we don't reprocess next time
        update_hash(file_str)

    # Save graph
    try:
        kg.save_graph()
        _log("Knowledge graph saved.")
    except Exception as e:
        _log(f"[error] Could not save graph: {e}")

    graph_stats = kg.get_graph_stats()
    stats["graph_nodes"] = graph_stats["nodes"]
    stats["graph_edges"] = graph_stats["edges"]
    stats["vector_store"] = chroma_store.get_stats()

    _log(f"Pipeline complete: {stats}")
    return stats
