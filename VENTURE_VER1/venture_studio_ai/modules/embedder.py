# modules/embedder.py
"""
Singleton sentence-transformers model wrapper.
Loads all-MiniLM-L6-v2 once per session (~80MB, downloaded on first use).
"""
from sentence_transformers import SentenceTransformer

_model = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts. Returns list of 384-dim float vectors."""
    if not texts:
        return []
    model = get_model()
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a single query string. Returns a 384-dim float vector."""
    return embed_texts([query])[0]
