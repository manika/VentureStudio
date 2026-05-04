"""
Simple JSON-file-backed cache manager.

Cache files live in CACHE_DIR and are named after the cache type:
  file_hashes.json, extracted_text.json, redacted_text.json,
  chunk_summaries.json, entity_extractions.json,
  relationship_extractions.json, query_cache.json
"""

import json
import hashlib
from pathlib import Path
from typing import Any, Optional

from config import CACHE_DIR

CACHE_NAMES = [
    "file_hashes",
    "extracted_text",
    "redacted_text",
    "chunk_summaries",
    "entity_extractions",
    "relationship_extractions",
    "query_cache",
]

# In-memory cache to avoid re-reading files repeatedly
_memory: dict = {}


def _cache_path(cache_name: str) -> Path:
    return Path(CACHE_DIR) / f"{cache_name}.json"


def _load(cache_name: str) -> dict:
    if cache_name in _memory:
        return _memory[cache_name]
    p = _cache_path(cache_name)
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            _memory[cache_name] = data
            return data
        except (json.JSONDecodeError, OSError):
            pass
    _memory[cache_name] = {}
    return _memory[cache_name]


def _save(cache_name: str) -> None:
    p = _cache_path(cache_name)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(_memory.get(cache_name, {}), f, indent=2)


def get_cache(cache_name: str, key: str) -> Optional[Any]:
    """Retrieve a cached value by cache name and key."""
    data = _load(cache_name)
    return data.get(key)


def set_cache(cache_name: str, key: str, value: Any) -> None:
    """Store a value in a named cache."""
    data = _load(cache_name)
    data[key] = value
    _save(cache_name)


def get_file_hash(file_path: str) -> str:
    """Return MD5 hex digest of a file."""
    hasher = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                hasher.update(block)
        return hasher.hexdigest()
    except (OSError, IOError):
        return ""


def should_reprocess(file_path: str) -> bool:
    """Return True if file has changed since last hash was stored."""
    current_hash = get_file_hash(file_path)
    stored_hash = get_cache("file_hashes", str(file_path))
    return current_hash != stored_hash


def update_hash(file_path: str) -> None:
    """Store current file hash to mark it as processed."""
    h = get_file_hash(file_path)
    set_cache("file_hashes", str(file_path), h)
