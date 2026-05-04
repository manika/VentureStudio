import hashlib
from pathlib import Path
from .document_loader import load_documents
from .vector_store import TFIDFStore
from . import cache_manager
from config import VEC_STORE_PATH

_store: TFIDFStore | None = None
_store_doc_hash: str = ""


def _get_store(DATA_DIR: Path) -> TFIDFStore:
    global _store, _store_doc_hash
    docs = load_documents(DATA_DIR)
    # Hash the list of file paths+sizes as a cheap change detector
    fingerprint = hashlib.md5(
        str(sorted((str(d["path"]), len(d.get("text", ""))) for d in docs)).encode()
    ).hexdigest()
    if _store is None or fingerprint != _store_doc_hash:
        _store = TFIDFStore(VEC_STORE_PATH)
        if docs:
            _store.build(docs)
        else:
            _store.load()
        _store_doc_hash = fingerprint
    return _store


def retrieve_context(query: str, DATA_DIR: Path, use_founder=True, use_company=True, use_templates=True):
    cache_key = hashlib.md5(f"{query}|{DATA_DIR}|{use_founder}|{use_company}|{use_templates}".encode()).hexdigest()
    cached = cache_manager.get_cache("query_cache", cache_key)
    if cached is not None:
        return cached

    store = _get_store(DATA_DIR)
    hits = store.query(query, top_k=3)
    cache_manager.set_cache("query_cache", cache_key, hits)
    return hits
