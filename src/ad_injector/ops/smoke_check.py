"""Smoke check: verify Qdrant and embedding provider are reachable."""

from __future__ import annotations


def run_smoke_check() -> dict:
    """Run a minimal health check (Qdrant + embedding).

    Returns:
        Dict with keys: ok (bool), qdrant (str), embedding (str), error (str | None).
    """
    result: dict = {"ok": False, "qdrant": "unknown", "embedding": "unknown", "error": None}
    try:
        from ..config.runtime import get_settings
        from ..adapters.qdrant_vector_store import QdrantVectorStore
        from ..adapters.fastembed_provider import FastEmbedProvider

        settings = get_settings()
        # Qdrant reachable?
        try:
            store = QdrantVectorStore(settings)
            _ = store._get_client().get_collections()
            result["qdrant"] = "ok"
        except Exception:
            result["qdrant"] = "error"
        # Embedding model
        try:
            embed = FastEmbedProvider(model_id=settings.embedding_model_id)
            vec = embed.embed("test")
            result["embedding"] = "ok" if vec and len(vec) == settings.embedding_dimension else "fail"
        except Exception:
            result["embedding"] = "error"
        result["ok"] = result["qdrant"] == "ok" and result["embedding"] == "ok"
    except Exception as e:
        result["error"] = str(e)
    return result
