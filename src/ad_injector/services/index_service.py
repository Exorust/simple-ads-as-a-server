"""IndexService — Control Plane orchestration.

Handles collection management and ad ingestion.
CLI and MCP admin tools call this service.

Depends only on ports — never on concrete adapters.
"""

from __future__ import annotations

from ..config.runtime import RuntimeSettings
from ..models import Ad  # for upsert_ads
from ..ports.embedding import EmbeddingProvider
from ..ports.vector_store import VectorStorePort


class IndexService:
    """Manage the ads collection and ad lifecycle."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStorePort,
        settings: RuntimeSettings,
    ) -> None:
        self._embed = embedding_provider
        self._store = vector_store
        self._settings = settings

    def ensure_collection(
        self,
        dimension: int | None = None,
        embedding_model_id: str | None = None,
        schema_version: str | None = None,
    ) -> dict:
        if dimension is None:
            dimension = self._settings.embedding_dimension
        return self._store.ensure_collection(
            dimension,
            embedding_model_id=embedding_model_id,
            schema_version=schema_version,
        )

    def delete_collection(self) -> None:
        self._store.delete_collection()

    def collection_info(self) -> dict:
        return self._store.collection_info()

    def upsert_ads(self, ads: list[Ad]) -> int:
        batch_size = self._settings.max_batch_size
        total = 0
        for i in range(0, len(ads), batch_size):
            batch = ads[i : i + batch_size]
            ads_with_embeddings = [
                (ad, self._embed.embed(ad.embedding_text)) for ad in batch
            ]
            total += self._store.upsert_batch(ads_with_embeddings)
        return total

    def delete_ad(self, ad_id: str) -> None:
        self._store.delete_ad(ad_id)

    def get_ad(self, ad_id: str) -> dict | None:
        """Return raw ad payload (flat dict from store) or None. For MCP/CLI use."""
        return self._store.get_ad(ad_id)

    def bulk_disable(self, filter_spec: dict) -> int:
        """Set enabled=False for all ads matching filter_spec. Returns count updated."""
        return self._store.bulk_disable(filter_spec)
