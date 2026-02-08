"""Adapter: wraps embedding_service for use by application services."""

from __future__ import annotations

from ..embedding_service import generate_embedding as _generate


class EmbeddingProvider:
    """Generate text embeddings via the configured local model."""

    def embed(self, text: str) -> list[float]:
        """Return an embedding vector for *text*."""
        return _generate(text)
