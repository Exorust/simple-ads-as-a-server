"""Port: vector store for ad retrieval and management."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from ..domain.filters import VectorFilter


class VectorHit(BaseModel):
    """A single result from a vector similarity query."""

    ad_id: str = Field(..., description="Ad identifier")
    advertiser_id: str = Field(..., description="Advertiser identifier")
    score: float = Field(..., description="Similarity score")
    payload: dict = Field(..., description="Full stored metadata")


@runtime_checkable
class VectorStorePort(Protocol):
    """Read/write interface for the vector database."""

    # --- queries ---

    def query(
        self,
        vector: list[float],
        vector_filter: VectorFilter | None,
        top_k: int,
    ) -> list[VectorHit]: ...

    # --- mutations ---

    def ensure_collection(self, dimension: int) -> dict: ...

    def delete_collection(self) -> None: ...

    def collection_info(self) -> dict: ...

    def upsert_batch(
        self, ads_with_embeddings: list[tuple[object, list[float]]]
    ) -> int: ...

    def delete_ad(self, ad_id: str) -> None: ...

    def get_ad(self, ad_id: str) -> dict | None: ...

    def bulk_disable(self, filter_spec: dict) -> int: ...
