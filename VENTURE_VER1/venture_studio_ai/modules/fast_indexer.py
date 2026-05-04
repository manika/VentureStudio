# modules/fast_indexer.py
"""
Fast document indexer: extract -> redact -> chunk -> embed -> ChromaDB.
No LLM calls during indexing. Uses sentence-transformers for embeddings.
"""

import logging
from pathlib import Path

from . import cache_manager, redaction, chunker, embedder
from .document_loader import EXTRACTORS
from .vector_store import ChromaStore

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = set(EXTRACTORS.keys())  # .pdf, .docx, .txt, .md, .csv, .xlsx

# Module-level singleton so the same ChromaStore is reused across calls
_chroma_store: ChromaStore | None = None


def _get_store() -> ChromaStore:
    global _chroma_store
    if _chroma_store is None:
        _chroma_store = ChromaStore()
    return _chroma_store


def _list_files(folder_path: Path) -> list[Path]:
    """Recursively list all supported files under folder_path."""
    files = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(folder_path.rglob(f"*{ext}"))
    return sorted(files)


def index_folder(folder_path: str, progress_callback=None) -> dict:
    """
    Index all supported documents in folder_path into ChromaDB.

    For each file:
      1. Check hash cache — skip if unchanged.
      2. Extract text.
      3. Redact text.
      4. Chunk redacted text.
      5. Batch-embed all chunks.
      6. Upsert into ChromaDB with metadata.
      7. Update hash cache.

    Args:
        folder_path: Path to directory containing documents.
        progress_callback: Optional callable(str) for progress messages.

    Returns:
        dict with keys: files_processed, files_skipped, chunks_added,
                        total_files, errors
    """
    folder = Path(folder_path)
    if not folder.exists():
        msg = f"Folder not found: {folder}"
        logger.warning(msg)
        if progress_callback:
            progress_callback(msg)
        return {
            "files_processed": 0,
            "files_skipped": 0,
            "chunks_added": 0,
            "total_files": 0,
            "errors": [msg],
        }

    files = _list_files(folder)
    total_files = len(files)
    files_processed = 0
    files_skipped = 0
    chunks_added = 0
    errors = []

    store = _get_store()

    if progress_callback:
        progress_callback(f"Found {total_files} files to scan in {folder}")

    for file_path in files:
        file_str = str(file_path)
        try:
            # --- Hash check ---
            if not cache_manager.should_reprocess(file_str):
                files_skipped += 1
                if progress_callback:
                    progress_callback(f"[SKIP] {file_path.name} (unchanged)")
                continue

            if progress_callback:
                progress_callback(f"[INDEX] {file_path.name}")

            # --- Extract text ---
            ext = file_path.suffix.lower()
            extractor = EXTRACTORS.get(ext)
            if extractor is None:
                raise ValueError(f"No extractor for extension '{ext}'")
            raw_text = extractor(file_path)

            if not raw_text or not raw_text.strip():
                logger.debug("Empty text from %s — skipping", file_path.name)
                cache_manager.update_hash(file_str)
                files_skipped += 1
                continue

            # --- Redact ---
            redact_result = redaction.redact_text(raw_text)
            redacted_text = redact_result["redacted_text"]

            # --- Chunk ---
            chunks = chunker.chunk_text(redacted_text)
            if not chunks:
                logger.debug("No chunks from %s — skipping", file_path.name)
                cache_manager.update_hash(file_str)
                files_skipped += 1
                continue

            # --- Batch embed ---
            # Prepend filename (without extension) to each chunk so queries
            # referencing the document name ("2024 Steri-Tek audit") score well
            # even when the chunk body is sparse boilerplate.
            doc_label = file_path.stem
            chunk_texts = [f"[{doc_label}] {c['text']}" for c in chunks]
            embeddings = embedder.embed_texts(chunk_texts)

            # --- Store in ChromaDB ---
            source_doc = file_path.name
            doc_type = ext.lstrip(".")

            enriched_chunks = []
            for chunk in chunks:
                enriched_chunks.append({
                    **chunk,
                    "source_document": source_doc,
                    "document_type": doc_type,
                    "redaction_status": "redacted",
                })

            store.add_chunks(
                chunks=enriched_chunks,
                source_doc=source_doc,
                embeddings=embeddings,
            )

            chunks_added += len(chunks)
            cache_manager.update_hash(file_str)
            files_processed += 1

            if progress_callback:
                progress_callback(
                    f"  -> {file_path.name}: {len(chunks)} chunks indexed "
                    f"({redact_result['redaction_count']} redactions)"
                )

        except Exception as exc:
            msg = f"[ERROR] {file_path.name}: {exc}"
            logger.exception("Error indexing %s", file_path)
            errors.append(msg)
            if progress_callback:
                progress_callback(msg)

    summary = {
        "files_processed": files_processed,
        "files_skipped": files_skipped,
        "chunks_added": chunks_added,
        "total_files": total_files,
        "errors": errors,
    }

    if progress_callback:
        progress_callback(
            f"Done: {files_processed} indexed, {files_skipped} skipped, "
            f"{chunks_added} chunks added, {len(errors)} errors"
        )

    return summary
