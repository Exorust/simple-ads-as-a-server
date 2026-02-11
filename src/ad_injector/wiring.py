"""Composition root — single place where all wiring happens.

Call ``build_match_service()`` or ``build_index_service()`` to get a
fully-constructed service with real adapters.  No ad-hoc construction
elsewhere.
"""

from __future__ import annotations

from .adapters.fastembed_provider import FastEmbedProvider
from .adapters.qdrant_vector_store import QdrantVectorStore
from .config.runtime import RuntimeSettings, get_settings
from .services.index_service import IndexService
from .services.match_service import MatchService


def build_match_service(settings: RuntimeSettings | None = None) -> MatchService:
    """Construct a MatchService with real adapters."""
    settings = settings or get_settings()
    return MatchService(
        embedding_provider=FastEmbedProvider(model_id=settings.embedding_model_id),
        vector_store=QdrantVectorStore(settings),
    )


def build_index_service(settings: RuntimeSettings | None = None) -> IndexService:
    """Construct an IndexService with real adapters."""
    settings = settings or get_settings()
    return IndexService(
        embedding_provider=FastEmbedProvider(model_id=settings.embedding_model_id),
        vector_store=QdrantVectorStore(settings),
        settings=settings,
    )
