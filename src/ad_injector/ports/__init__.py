"""Port interfaces (Protocols).

Application services depend only on these — never on concrete adapters.
No Qdrant, fastembed, or other infrastructure imports allowed here.
"""

from .embedding import EmbeddingProvider
from .id_gen import MatchIdProvider, RequestIdProvider
from .vector_store import VectorHit, VectorStorePort

__all__ = [
    "EmbeddingProvider",
    "MatchIdProvider",
    "RequestIdProvider",
    "VectorHit",
    "VectorStorePort",
]
