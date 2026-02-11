"""Port: ID generation strategies."""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable


@runtime_checkable
class RequestIdProvider(Protocol):
    """Generate a unique request ID."""

    def new_request_id(self) -> str: ...


@runtime_checkable
class MatchIdProvider(Protocol):
    """Generate a deterministic match ID from request_id + ad_id."""

    def new_match_id(self, request_id: str, ad_id: str) -> str: ...


# ---------------------------------------------------------------------------
# Default implementations (pure stdlib, no infra deps)
# ---------------------------------------------------------------------------


class UuidRequestIdProvider:
    """Uses uuid4 for request IDs."""

    def new_request_id(self) -> str:
        return str(uuid.uuid4())


class UuidMatchIdProvider:
    """Uses uuid5(request_id, ad_id) for deterministic match IDs."""

    def new_match_id(self, request_id: str, ad_id: str) -> str:
        return str(uuid.uuid5(uuid.UUID(request_id), ad_id))
