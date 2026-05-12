import hashlib
from pathlib import Path
from .document_loader import load_documents
from .vector_store import TFIDFStore
from . import cache_manager
from config import VEC_STORE_PATH

_store: TFIDFStore | None = None
_store_doc_hash: str = ""


def _get_store(docs: list) -> TFIDFStore:
    global _store, _store_doc_hash
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


def retrieve_context(
    query: str,
    DATA_DIR: Path,
    use_founder: bool = True,
    use_company: bool = True,
    use_templates: bool = True,
    selected_company: str = "",
) -> list:
    cache_key = hashlib.md5(
        f"{query}|{DATA_DIR}|{use_founder}|{use_company}|{use_templates}|{selected_company}".encode()
    ).hexdigest()
    cached = cache_manager.get_cache("query_cache", cache_key)
    if cached is not None:
        return cached

    dirs_to_load: list[Path] = []
    if use_founder:
        d = DATA_DIR / "founder_startup"
        if d.exists():
            dirs_to_load.append(d)
    if use_company and selected_company:
        d = DATA_DIR / "companies" / selected_company
        if d.exists():
            dirs_to_load.append(d)
    if use_templates:
        d = DATA_DIR / "shared_templates"
        if d.exists():
            dirs_to_load.append(d)

    docs: list = []
    for d in dirs_to_load:
        docs.extend(load_documents(d))

    if not docs:
        cache_manager.set_cache("query_cache", cache_key, [])
        return []

    store = _get_store(docs)
    hits = store.query(query, top_k=6)
    cache_manager.set_cache("query_cache", cache_key, hits)
    return hits
