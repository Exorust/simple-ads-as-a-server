"""Port: embedding provider."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Generate a vector embedding from text."""

    def embed(self, text: str) -> list[float]: ...
