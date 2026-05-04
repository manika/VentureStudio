import pickle
import logging
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer

from config import CHROMA_DIR

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try to import chromadb; fall back gracefully if unavailable
# ---------------------------------------------------------------------------
try:
    import chromadb
    _CHROMA_AVAILABLE = True
except ImportError:
    _CHROMA_AVAILABLE = False
    logger.warning("chromadb not available — ChromaStore will use TF-IDF fallback")
except Exception as e:
    _CHROMA_AVAILABLE = False
    logger.warning("chromadb failed to load (%s) — ChromaStore will use TF-IDF fallback", e)


# ---------------------------------------------------------------------------
# Original TF-IDF store (keep intact)
# ---------------------------------------------------------------------------

class TFIDFStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.vectorizer = None
        self.doc_texts = []

    def build(self, docs):
        texts = [d.get("text", "") for d in docs]
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        self.vectorizer.fit_transform(texts)
        self.doc_texts = docs
        self._save()

    def _save(self):
        with open(self.path, "wb") as f:
            pickle.dump({"vectorizer": self.vectorizer, "docs": self.doc_texts}, f)

    def load(self):
        if not self.path.exists():
            return False
        with open(self.path, "rb") as f:
            data = pickle.load(f)
        self.vectorizer = data["vectorizer"]
        self.doc_texts = data["docs"]
        return True

    def query(self, text, top_k=3):
        if self.vectorizer is None:
            return []
        import numpy as np
        vec = self.vectorizer.transform([text])
        X = self.vectorizer.transform([d.get("text", "") for d in self.doc_texts])
        sims = (X @ vec.T).toarray().ravel()
        idx = sims.argsort()[::-1][:top_k]
        return [self.doc_texts[i] for i in idx]

    def get_stats(self) -> dict:
        return {
            "type": "tfidf",
            "documents": len(self.doc_texts),
        }


# ---------------------------------------------------------------------------
# ChromaStore — wraps chromadb with TF-IDF fallback
# ---------------------------------------------------------------------------

class ChromaStore:
    """Persistent vector store backed by chromadb.

    Falls back to in-memory TF-IDF if chromadb is unavailable.
    """

    COLLECTION_NAME = "venture_studio_chunks"

    def __init__(self, chroma_dir: Path = None):
        self._chroma_dir = Path(chroma_dir or CHROMA_DIR)
        self._client = None
        self._collection = None
        self._fallback = None  # TFIDFStore fallback
        self._fallback_docs: list = []
        self._use_chroma = _CHROMA_AVAILABLE
        self._init()

    def _init(self):
        if not self._use_chroma:
            self._init_fallback()
            return
        try:
            self._client = chromadb.PersistentClient(path=str(self._chroma_dir))
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaStore initialized at %s", self._chroma_dir)
        except Exception as e:
            logger.warning("ChromaStore init failed (%s) — using TF-IDF fallback", e)
            self._use_chroma = False
            self._init_fallback()

    def _init_fallback(self):
        from config import VEC_STORE_PATH
        self._fallback = TFIDFStore(VEC_STORE_PATH)
        self._fallback.load()

    def add_chunks(self, chunks: list, source_doc: str = "", embeddings: list = None) -> None:
        """Add text chunks to the store.

        Args:
            chunks: List of chunk dicts (must contain 'text' and 'chunk_id').
            source_doc: Identifier for the source document.
            embeddings: Optional pre-computed embeddings (one per chunk).
                        When provided they are passed directly to ChromaDB,
                        bypassing ChromaDB's own embedding function.
        """
        if not chunks:
            return

        if self._use_chroma:
            try:
                docs_text = [c.get("text", "") for c in chunks]
                ids = [
                    f"{source_doc}_chunk_{c.get('chunk_id', i)}"
                    for i, c in enumerate(chunks)
                ]
                metadatas = [
                    {
                        "source_doc": c.get("source_document", source_doc),
                        "document_type": c.get("document_type", ""),
                        "redaction_status": c.get("redaction_status", ""),
                        "chunk_id": c.get("chunk_id", i),
                        "char_start": c.get("char_start", 0),
                    }
                    for i, c in enumerate(chunks)
                ]
                upsert_kwargs: dict = {
                    "documents": docs_text,
                    "ids": ids,
                    "metadatas": metadatas,
                }
                if embeddings is not None:
                    upsert_kwargs["embeddings"] = embeddings
                # Chroma upsert handles duplicates
                self._collection.upsert(**upsert_kwargs)
                return
            except Exception as e:
                logger.warning("ChromaStore.add_chunks error (%s) — using fallback", e)
                self._use_chroma = False
                self._init_fallback()

        # Fallback: accumulate docs for TF-IDF
        for c in chunks:
            self._fallback_docs.append({
                "text": c.get("text", ""),
                "path": source_doc,
                "source": source_doc,
                "chunk_id": c.get("chunk_id", 0),
            })
        if self._fallback and self._fallback_docs:
            self._fallback.build(self._fallback_docs)

    def query(self, query_text: str, top_k: int = 5) -> list:
        """Return top_k relevant chunks as list of dicts with text and metadata.

        When ChromaDB is available the query is embedded using sentence-transformers
        (via embedder.embed_query) and the pre-computed vector is passed directly
        to ChromaDB so no second embedding function is invoked.
        """
        if self._use_chroma:
            try:
                count = self._collection.count()
                if count == 0:
                    return []
                n_results = min(top_k, count)

                # Use our embedder for the query vector
                try:
                    from . import embedder as _embedder
                    query_vec = _embedder.embed_query(query_text)
                    results = self._collection.query(
                        query_embeddings=[query_vec],
                        n_results=n_results,
                    )
                except Exception:
                    # Fall back to chroma's built-in text query if embedder fails
                    results = self._collection.query(
                        query_texts=[query_text],
                        n_results=n_results,
                    )

                chunks = []
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                for text, meta in zip(docs, metas):
                    chunks.append({
                        "text": text,
                        "path": meta.get("source_doc", ""),
                        "source": meta.get("source_doc", ""),
                        "chunk_id": meta.get("chunk_id", 0),
                        "document_type": meta.get("document_type", ""),
                        "redaction_status": meta.get("redaction_status", ""),
                    })
                return chunks
            except Exception as e:
                logger.warning("ChromaStore.query error (%s) — using fallback", e)
                self._use_chroma = False
                self._init_fallback()

        if self._fallback:
            return self._fallback.query(query_text, top_k=top_k)
        return []

    def get_chunks_by_source(
        self,
        source_names: list[str],
        chunk_ids: list[int] | None = None,
    ) -> list[dict]:
        """Fetch specific chunks from named source documents using metadata filters.

        Args:
            source_names: List of source_doc values to match.
            chunk_ids: If given, only return chunks whose chunk_id is in this list.
                       Pass [0] to retrieve only the first (cover-page) chunk per source.

        Returns:
            List of chunk dicts with text and metadata.
        """
        if not source_names or not self._use_chroma:
            return []
        try:
            count = self._collection.count()
            if count == 0:
                return []

            if len(source_names) == 1:
                source_filter: dict = {"source_doc": {"$eq": source_names[0]}}
            else:
                source_filter = {"source_doc": {"$in": source_names}}

            if chunk_ids is not None:
                if len(chunk_ids) == 1:
                    chunk_filter: dict = {"chunk_id": {"$eq": chunk_ids[0]}}
                else:
                    chunk_filter = {"chunk_id": {"$in": chunk_ids}}
                where: dict = {"$and": [source_filter, chunk_filter]}
            else:
                where = source_filter

            results = self._collection.get(where=where, include=["documents", "metadatas"])

            chunks = []
            for text, meta in zip(
                results.get("documents", []), results.get("metadatas", [])
            ):
                chunks.append({
                    "text": text,
                    "path": meta.get("source_doc", ""),
                    "source": meta.get("source_doc", ""),
                    "chunk_id": meta.get("chunk_id", 0),
                    "document_type": meta.get("document_type", ""),
                    "redaction_status": meta.get("redaction_status", ""),
                })
            return chunks
        except Exception as e:
            logger.warning("ChromaStore.get_chunks_by_source error (%s)", e)
            return []

    def get_stats(self) -> dict:
        if self._use_chroma:
            try:
                count = self._collection.count()
                return {"type": "chroma", "chunks": count, "collection": self.COLLECTION_NAME}
            except Exception:
                pass
        return {"type": "tfidf_fallback", "chunks": len(self._fallback_docs)}
