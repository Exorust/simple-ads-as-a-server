"""Qdrant service for ad storage and retrieval."""

import uuid
from pathlib import Path

from qdrant_client.models import Distance, PointStruct, VectorParams

from .config.qdrant import AD_ID_NAMESPACE, COLLECTION_NAME, EMBEDDING_DIMENSION, get_qdrant_client
from .embedding_service import generate_embedding
from .models import Ad

# Debug log path - relative to workspace root
_DEBUG_LOG_PATH = Path(__file__).parent.parent.parent / ".cursor" / "debug.log"


def _ad_id_to_uuid(ad_id: str) -> str:
    """Convert a string ad_id to a deterministic UUID string for Qdrant."""
    return str(uuid.uuid5(AD_ID_NAMESPACE, ad_id))


def create_collection(dimension: int = EMBEDDING_DIMENSION) -> None:
    """Create the Qdrant collection if it doesn't exist.

    Args:
        dimension: Embedding vector dimension (default: 384 for BAAI/bge-small-en-v1.5)
    """
    client = get_qdrant_client()
    collections = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )
        print(f"Created collection: {COLLECTION_NAME}")
    else:
        print(f"Collection already exists: {COLLECTION_NAME}")


def delete_collection() -> None:
    """Delete the Qdrant collection."""
    client = get_qdrant_client()
    client.delete_collection(COLLECTION_NAME)
    print(f"Deleted collection: {COLLECTION_NAME}")


def upsert_ad(ad: Ad, embedding: list[float]) -> None:
    """Upsert a single ad into Qdrant.

    Args:
        ad: The ad to upsert
        embedding: The embedding vector for the ad
    """
    client = get_qdrant_client()
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=_ad_id_to_uuid(ad.ad_id),
                vector=embedding,
                payload=ad.to_pinecone_metadata(),  # Reusing the same metadata format
            )
        ],
    )


def upsert_ads(ads: list[tuple[Ad, list[float]]]) -> None:
    """Upsert multiple ads into Qdrant.

    Args:
        ads: List of (ad, embedding) tuples
    """
    client = get_qdrant_client()
    points = [
        PointStruct(
            id=_ad_id_to_uuid(ad.ad_id),
            vector=embedding,
            payload=ad.to_pinecone_metadata(),
        )
        for ad, embedding in ads
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points)


def query_ads(
    embedding: list[float],
    top_k: int = 10,
    filter_dict: dict | None = None,
) -> list[dict]:
    """Query ads by embedding similarity.

    Args:
        embedding: Query embedding vector
        top_k: Number of results to return
        filter_dict: Optional Qdrant filter conditions

    Returns:
        List of matching ads with scores
    """
    client = get_qdrant_client()
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=embedding,
        limit=top_k,
        query_filter=filter_dict,
    )
    return [
        {
            "id": hit.id,
            "score": hit.score,
            "metadata": hit.payload,
        }
        for hit in response.points
    ]


def delete_ad(ad_id: str) -> None:
    """Delete an ad from Qdrant.

    Args:
        ad_id: The ID of the ad to delete
    """
    client = get_qdrant_client()
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=[_ad_id_to_uuid(ad_id)],
    )


def get_collection_info() -> dict:
    """Get information about the Qdrant collection.

    Returns:
        Collection info including vector count
    """
    client = get_qdrant_client()
    info = client.get_collection(COLLECTION_NAME)
    return {
        "name": COLLECTION_NAME,
        "indexed_vectors_count": info.indexed_vectors_count,
        "points_count": info.points_count,
        "status": str(info.status),
    }


def match_ads(text: str, top_k: int = 10) -> list[dict]:
    """Match ads by text query (read-only, safe wrapper).
    
    This is a safe wrapper around query_ads that:
    - Accepts text instead of embedding vectors
    - Generates embeddings internally
    - Explicitly disables filter_dict to prevent abuse
    
    Args:
        text: Text query to match against ads
        top_k: Number of results to return (default: 10)
        
    Returns:
        List of matching ads with scores and metadata
    """
    embedding = generate_embedding(text)
    # Explicitly pass filter_dict=None to prevent any filtering
    return query_ads(embedding=embedding, top_k=top_k, filter_dict=None)
