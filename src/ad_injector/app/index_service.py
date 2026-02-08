"""IndexService — Control Plane orchestration.

Handles collection management and ad ingestion.
CLI and future MCP admin tools call this service.
"""

from __future__ import annotations

from ..config.runtime import get_settings
from ..models import Ad
from .embedding_provider import EmbeddingProvider
from .vector_store import VectorStore


class IndexService:
    """Manage the ads collection and ad lifecycle."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self._embed = embedding_provider or EmbeddingProvider()
        self._store = vector_store or VectorStore()

    def ensure_collection(self, dimension: int | None = None) -> dict:
        """Create the collection if it doesn't exist.

        Returns:
            dict with ``name`` and ``created`` (bool).
        """
        if dimension is None:
            dimension = get_settings().embedding_dimension
        return self._store.ensure_collection(dimension)

    def delete_collection(self) -> None:
        """Delete the collection."""
        self._store.delete_collection()

    def collection_info(self) -> dict:
        """Return collection metadata."""
        return self._store.collection_info()

    def upsert_ads(self, ads: list[Ad]) -> int:
        """Embed and upsert ads in batches. Returns total count upserted."""
        settings = get_settings()
        batch_size = settings.max_batch_size
        total = 0

        for i in range(0, len(ads), batch_size):
            batch = ads[i : i + batch_size]
            ads_with_embeddings = [
                (ad, self._embed.embed(ad.embedding_text)) for ad in batch
            ]
            total += self._store.upsert_batch(ads_with_embeddings)

        return total

    def delete_ad(self, ad_id: str) -> None:
        """Delete a single ad."""
        self._store.delete_ad(ad_id)

    def get_ad(self, ad_id: str) -> Ad | None:
        """Fetch a single ad by ID, or None if not found."""
        payload = self._store.get_ad(ad_id)
        if payload is None:
            return None
        return Ad.model_validate(payload)
