"""Pydantic-based runtime settings for MCP servers.

Loads from environment variables (with optional .env file).
Missing required values fail fast at import time.
"""

from __future__ import annotations

import uuid
from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class McpMode(str, Enum):
    data = "data"
    admin = "admin"


class RuntimeSettings(BaseSettings):
    """All configuration for MCP runtime, validated at startup."""

    model_config = {"env_prefix": "", "env_file": ".env", "env_file_encoding": "utf-8"}

    # --- Server mode ---
    mcp_mode: McpMode = Field(
        default=McpMode.data,
        description="Which MCP plane to start: 'data' (LLM-facing) or 'admin' (control plane)",
    )

    # --- Qdrant ---
    qdrant_host: str = Field(default="localhost", description="Qdrant server host")
    qdrant_port: int = Field(default=6333, description="Qdrant server port")
    qdrant_collection_name: str = Field(default="ads", description="Qdrant collection name")

    # --- Embeddings ---
    embedding_model_id: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="Embedding model identifier",
    )
    embedding_dimension: int = Field(default=384, description="Embedding vector dimension")

    # --- ID namespace ---
    ad_id_namespace: uuid.UUID = Field(
        default=uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890"),
        description="UUID namespace for deterministic ad ID generation",
    )

    # --- Auth (optional: require key for production) ---
    require_admin_key: bool = Field(default=False, description="If True, Control Plane requires MCP_ADMIN_KEY env")
    require_data_key: bool = Field(default=False, description="If True, Data Plane requires MCP_DATA_KEY env")

    # --- Limits ---
    max_top_k: int = Field(default=100, ge=1, le=1000, description="Maximum top_k for match queries")
    max_batch_size: int = Field(default=500, ge=1, le=10000, description="Maximum ads per upsert batch")
    request_timeout_seconds: float = Field(default=30.0, gt=0, description="Per-request timeout")

    @field_validator("qdrant_port")
    @classmethod
    def _port_range(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"qdrant_port must be 1-65535, got {v}")
        return v


@lru_cache(maxsize=1)
def get_settings() -> RuntimeSettings:
    """Return the singleton RuntimeSettings (cached after first call)."""
    return RuntimeSettings()
