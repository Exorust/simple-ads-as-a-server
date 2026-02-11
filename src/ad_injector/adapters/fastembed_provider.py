"""Adapter: FastEmbed-based EmbeddingProvider."""

from __future__ import annotations

from fastembed import TextEmbedding

from ..ports.embedding import EmbeddingProvider


class FastEmbedProvider:
    """Implements ``EmbeddingProvider`` using local FastEmbed models."""

    def __init__(self, model_id: str = "BAAI/bge-small-en-v1.5") -> None:
        self._model_id = model_id
        self._model: TextEmbedding | None = None

    def _get_model(self) -> TextEmbedding:
        if self._model is None:
            self._model = TextEmbedding(model_name=self._model_id)
        return self._model

    def embed(self, text: str) -> list[float]:
        model = self._get_model()
        embedding = next(model.embed([text]))
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        return [vec.tolist() for vec in model.embed(texts)]
