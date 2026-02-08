"""Qdrant configuration and client setup."""

import os
import uuid

from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "ads")
EMBEDDING_DIMENSION = 384  # BAAI/bge-small-en-v1.5 dimension

# Namespace UUID for generating deterministic UUIDs from ad_id strings
# Can be overridden via AD_ID_NAMESPACE environment variable
_AD_ID_NAMESPACE_STR = os.getenv(
    "AD_ID_NAMESPACE", "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
)
AD_ID_NAMESPACE = uuid.UUID(_AD_ID_NAMESPACE_STR)


def get_qdrant_client() -> QdrantClient:
    """Get a configured Qdrant client for local instance."""
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
