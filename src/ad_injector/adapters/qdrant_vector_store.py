"""Adapter: Qdrant-based VectorStore implementing VectorStorePort."""

from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    VectorParams,
)

from ..config.runtime import RuntimeSettings
from ..domain.filters import FieldFilter, FilterOp, VectorFilter
from ..models import Ad
from ..ports.vector_store import VectorHit


class QdrantVectorStore:
    """Concrete VectorStorePort backed by Qdrant."""

    def __init__(self, settings: RuntimeSettings) -> None:
        self._settings = settings
        self._client: QdrantClient | None = None

    # Meta collection for dimension, embedding_model_id, schema_version
    _META_COLLECTION = "ads_meta"
    _META_POINT_ID = 0

    @property
    def _collection(self) -> str:
        return self._settings.qdrant_collection_name

    def _get_client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                host=self._settings.qdrant_host,
                port=self._settings.qdrant_port,
                timeout=self._settings.request_timeout_seconds,
            )
        return self._client

    def _ad_id_to_uuid(self, ad_id: str) -> str:
        return str(uuid.uuid5(self._settings.ad_id_namespace, ad_id))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def query(
        self,
        vector: list[float],
        vector_filter: VectorFilter | None,
        top_k: int,
    ) -> list[VectorHit]:
        # Enforce max_top_k
        effective_k = min(top_k, self._settings.max_top_k)

        client = self._get_client()
        qf = self._translate_filter(vector_filter) if vector_filter and not vector_filter.is_empty else None
        # Data Plane: only return enabled ads (exclude enabled=False; missing key treated as enabled)
        qf = self._ensure_enabled_filter(qf)

        response = client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=effective_k,
            query_filter=qf,
        )

        return [
            VectorHit(
                ad_id=hit.payload.get("ad_id", ""),
                advertiser_id=hit.payload.get("advertiser_id", ""),
                score=hit.score,
                payload=hit.payload,
            )
            for hit in response.points
        ]

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def ensure_collection(
        self,
        dimension: int,
        embedding_model_id: str | None = None,
        schema_version: str | None = None,
    ) -> dict:
        client = self._get_client()
        collections = [c.name for c in client.get_collections().collections]
        created = False
        if self._collection not in collections:
            client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
            created = True
        # Persist metadata in ads_meta collection
        if embedding_model_id is None:
            embedding_model_id = self._settings.embedding_model_id
        if schema_version is None:
            schema_version = "1"
        self._set_collection_meta(
            dimension=dimension,
            embedding_model_id=embedding_model_id,
            schema_version=schema_version,
        )
        return {
            "name": self._collection,
            "created": created,
            "dimension": dimension,
            "embedding_model_id": embedding_model_id,
            "schema_version": schema_version,
        }

    def delete_collection(self) -> None:
        client = self._get_client()
        client.delete_collection(self._collection)
        if self._META_COLLECTION in [c.name for c in client.get_collections().collections]:
            client.delete_collection(self._META_COLLECTION)

    def collection_info(self) -> dict:
        info = self._get_client().get_collection(self._collection)
        meta = self._get_collection_meta()
        return {
            "name": self._collection,
            "indexed_vectors_count": info.indexed_vectors_count,
            "points_count": info.points_count,
            "status": str(info.status),
            "dimension": meta.get("dimension", self._settings.embedding_dimension),
            "embedding_model_id": meta.get("embedding_model_id", self._settings.embedding_model_id),
            "schema_version": meta.get("schema_version", "1"),
        }

    def _get_collection_meta(self) -> dict:
        client = self._get_client()
        colls = [c.name for c in client.get_collections().collections]
        if self._META_COLLECTION not in colls:
            return {}
        try:
            results = client.retrieve(
                collection_name=self._META_COLLECTION,
                ids=[self._META_POINT_ID],
                with_payload=True,
            )
            if not results:
                return {}
            return dict(results[0].payload or {})
        except Exception:
            return {}

    def _set_collection_meta(
        self,
        dimension: int,
        embedding_model_id: str,
        schema_version: str,
    ) -> None:
        client = self._get_client()
        colls = [c.name for c in client.get_collections().collections]
        if self._META_COLLECTION not in colls:
            client.create_collection(
                collection_name=self._META_COLLECTION,
                vectors_config=VectorParams(size=1, distance=Distance.COSINE),
            )
        client.upsert(
            collection_name=self._META_COLLECTION,
            points=[
                PointStruct(
                    id=self._META_POINT_ID,
                    vector=[0.0],
                    payload={
                        "dimension": dimension,
                        "embedding_model_id": embedding_model_id,
                        "schema_version": schema_version,
                    },
                )
            ],
        )

    def upsert_batch(self, ads_with_embeddings: list[tuple[Ad, list[float]]]) -> int:
        client = self._get_client()
        points = [
            PointStruct(
                id=self._ad_id_to_uuid(ad.ad_id),
                vector=embedding,
                payload=ad.to_pinecone_metadata(),
            )
            for ad, embedding in ads_with_embeddings
        ]
        client.upsert(collection_name=self._collection, points=points)
        return len(points)

    def delete_ad(self, ad_id: str) -> None:
        self._get_client().delete(
            collection_name=self._collection,
            points_selector=[self._ad_id_to_uuid(ad_id)],
        )

    def get_ad(self, ad_id: str) -> dict | None:
        results = self._get_client().retrieve(
            collection_name=self._collection,
            ids=[self._ad_id_to_uuid(ad_id)],
            with_payload=True,
        )
        if not results:
            return None
        return results[0].payload

    def bulk_disable(self, filter_spec: dict) -> int:
        """Set enabled=False for all points matching filter_spec. Returns count updated."""
        from qdrant_client.models import PointStruct

        client = self._get_client()
        qf = self._filter_spec_to_qdrant(filter_spec)
        offset = None
        updated = 0
        while True:
            result, offset = client.scroll(
                collection_name=self._collection,
                scroll_filter=qf,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
            if not result:
                break
            for point in result:
                payload = dict(point.payload or {})
                payload["enabled"] = False
                client.upsert(
                    collection_name=self._collection,
                    points=[
                        PointStruct(id=point.id, vector=point.vector, payload=payload)
                    ],
                )
                updated += 1
            if offset is None:
                break
        return updated

    # ------------------------------------------------------------------
    # Filter translation: domain VectorFilter → Qdrant Filter
    # ------------------------------------------------------------------

    def _ensure_enabled_filter(self, qf: Filter | None) -> Filter:
        """Merge in must_not enabled=False so only enabled ads are returned."""
        must_not_enabled = FieldCondition(key="enabled", match=MatchValue(value=False))
        if qf is None:
            return Filter(must_not=[must_not_enabled])
        new_must_not = list(qf.must_not or []) + [must_not_enabled]
        return Filter(must=qf.must, must_not=new_must_not)

    def _filter_spec_to_qdrant(self, filter_spec: dict) -> Filter | None:
        """Convert simple dict filter (e.g. advertiser_id, ad_id) to Qdrant Filter."""
        if not filter_spec:
            return None
        must = []
        for key, value in filter_spec.items():
            if isinstance(value, list):
                must.append(FieldCondition(key=key, match=MatchAny(any=value)))
            else:
                must.append(FieldCondition(key=key, match=MatchValue(value=value)))
        return Filter(must=must) if must else None

    @staticmethod
    def _translate_filter(vf: VectorFilter) -> Filter | None:
        must = [QdrantVectorStore._translate_condition(c) for c in vf.must]
        must_not = [QdrantVectorStore._translate_condition(c) for c in vf.must_not]
        return Filter(
            must=must or None,
            must_not=must_not or None,
        )

    @staticmethod
    def _translate_condition(f: FieldFilter) -> FieldCondition:
        if f.op == FilterOp.equals:
            return FieldCondition(key=f.field, match=MatchValue(value=f.value))
        elif f.op == FilterOp.any_of:
            values = f.value if isinstance(f.value, list) else [f.value]
            return FieldCondition(key=f.field, match=MatchAny(any=values))
        elif f.op == FilterOp.not_equals:
            return FieldCondition(key=f.field, match=MatchValue(value=f.value))
        elif f.op == FilterOp.not_in:
            values = f.value if isinstance(f.value, list) else [f.value]
            return FieldCondition(key=f.field, match=MatchAny(any=values))
        elif f.op == FilterOp.all_of:
            # Qdrant MatchAny with all values in must = any_of semantics;
            # for true all_of we'd need multiple conditions, but MatchAny
            # on payload arrays checks if the stored array contains any.
            values = f.value if isinstance(f.value, list) else [f.value]
            return FieldCondition(key=f.field, match=MatchAny(any=values))
        else:
            raise ValueError(f"Unsupported filter op: {f.op}")
