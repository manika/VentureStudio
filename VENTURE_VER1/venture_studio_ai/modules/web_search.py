import logging

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 4) -> list[dict]:
    """
    Search DuckDuckGo and return results as doc chunks compatible with the
    retrieval/smart_advisor context format.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.warning("ddgs package not installed. Run: pip install ddgs")
            return []

    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = (r.get("title", "") or "").split("\n")[0].strip()[:120]
                body = (r.get("body", "") or "").strip()
                url = r.get("href", "")
                text = f"{title}\n{body}".strip()
                if text:
                    results.append({
                        "source": f"🌐 {title or url}",
                        "path": url,
                        "text": text,
                        "_web": True,
                    })
    except Exception as e:
        logger.warning("Web search failed: %s", e)

    return results
