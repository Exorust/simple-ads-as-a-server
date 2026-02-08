"""Adapter: wraps qdrant_service for use by application services."""

from __future__ import annotations

import uuid

from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    VectorParams,
)

from ..config.qdrant import AD_ID_NAMESPACE, COLLECTION_NAME, get_qdrant_client
from ..models import Ad


def _ad_id_to_uuid(ad_id: str) -> str:
    return str(uuid.uuid5(AD_ID_NAMESPACE, ad_id))


class VectorFilter:
    """Internal typed filter — translated to Qdrant Filter at query time."""

    def __init__(self) -> None:
        self.must: list[FieldCondition] = []
        self.must_not: list[FieldCondition] = []

    def to_qdrant(self) -> Filter | None:
        if not self.must and not self.must_not:
            return None
        return Filter(
            must=self.must or None,
            must_not=self.must_not or None,
        )


class VectorStore:
    """Read/write adapter over Qdrant."""

    # ------------------------------------------------------------------
    # Queries (Data Plane)
    # ------------------------------------------------------------------

    def query(
        self,
        vector: list[float],
        vector_filter: VectorFilter | None,
        top_k: int,
    ) -> list[dict]:
        """Return raw hits: list of {id, score, metadata}."""
        client = get_qdrant_client()
        qf = vector_filter.to_qdrant() if vector_filter else None
        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=top_k,
            query_filter=qf,
        )
        return [
            {"id": hit.id, "score": hit.score, "metadata": hit.payload}
            for hit in response.points
        ]

    # ------------------------------------------------------------------
    # Mutations (Control Plane / IndexService)
    # ------------------------------------------------------------------

    def ensure_collection(self, dimension: int) -> dict:
        client = get_qdrant_client()
        collections = [c.name for c in client.get_collections().collections]
        created = False
        if COLLECTION_NAME not in collections:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
            created = True
        return {"name": COLLECTION_NAME, "created": created}

    def delete_collection(self) -> None:
        client = get_qdrant_client()
        client.delete_collection(COLLECTION_NAME)

    def collection_info(self) -> dict:
        client = get_qdrant_client()
        info = client.get_collection(COLLECTION_NAME)
        return {
            "name": COLLECTION_NAME,
            "indexed_vectors_count": info.indexed_vectors_count,
            "points_count": info.points_count,
            "status": str(info.status),
        }

    def upsert_batch(self, ads_with_embeddings: list[tuple[Ad, list[float]]]) -> int:
        """Upsert a batch of (Ad, embedding) pairs. Returns count upserted."""
        client = get_qdrant_client()
        points = [
            PointStruct(
                id=_ad_id_to_uuid(ad.ad_id),
                vector=embedding,
                payload=ad.to_pinecone_metadata(),
            )
            for ad, embedding in ads_with_embeddings
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        return len(points)

    def delete_ad(self, ad_id: str) -> None:
        client = get_qdrant_client()
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=[_ad_id_to_uuid(ad_id)],
        )

    def get_ad(self, ad_id: str) -> dict | None:
        """Retrieve a single ad's payload by ad_id, or None if missing."""
        client = get_qdrant_client()
        point_id = _ad_id_to_uuid(ad_id)
        results = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[point_id],
            with_payload=True,
        )
        if not results:
            return None
        return results[0].payload
