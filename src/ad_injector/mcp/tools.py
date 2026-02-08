"""Tool registry for MCP servers.

Data Plane tools  – read-only, LLM-facing
Control Plane tools – admin/provisioning ops
"""

import json


def register_data_plane_tools(mcp):
    """Register Data Plane (runtime / LLM-facing) tools on *mcp*."""

    @mcp.tool()
    def ads_match(query: str, top_k: int = 10) -> str:
        """Match ads by semantic text query (read-only).

        Args:
            query: Text to match against ads
            top_k: Number of results to return (1-100, default 10)

        Returns:
            JSON string with matching ads, scores, and metadata
        """
        raise NotImplementedError("ads_match: wiring to MatchService pending")

    @mcp.tool()
    def ads_explain(match_id: str) -> str:
        """Return an audit/debug trace for a prior match result.

        Args:
            match_id: The match ID returned by ads_match

        Returns:
            JSON string with eligibility trace
        """
        raise NotImplementedError("ads_explain: wiring pending")

    @mcp.tool()
    def ads_health() -> str:
        """Lightweight health / readiness check.

        Returns:
            JSON string with status and capabilities
        """
        return json.dumps({"status": "ok", "plane": "data", "version": "0.1.0"})


def register_control_plane_tools(mcp):
    """Register Control Plane (admin) tools on *mcp*."""

    @mcp.tool()
    def collection_ensure(dimension: int = 384, embedding_model_id: str = "BAAI/bge-small-en-v1.5", schema_version: str = "1") -> str:
        """Ensure the ads collection exists with the given config.

        Args:
            dimension: Embedding vector dimension
            embedding_model_id: Model used for embeddings
            schema_version: Schema version tag

        Returns:
            JSON string with collection status
        """
        raise NotImplementedError("collection_ensure: wiring to Qdrant adapter pending")

    @mcp.tool()
    def collection_info() -> str:
        """Return metadata about the current ads collection.

        Returns:
            JSON string with collection stats
        """
        raise NotImplementedError("collection_info: wiring pending")

    @mcp.tool()
    def ads_upsert_batch(ads_json: str) -> str:
        """Upsert a batch of ads.

        Args:
            ads_json: JSON array of ad objects

        Returns:
            JSON string with upsert results
        """
        raise NotImplementedError("ads_upsert_batch: wiring pending")

    @mcp.tool()
    def ads_delete(ad_id: str) -> str:
        """Delete a single ad by ID.

        Args:
            ad_id: The ad identifier to delete

        Returns:
            JSON confirmation
        """
        raise NotImplementedError("ads_delete: wiring pending")

    @mcp.tool()
    def ads_get(ad_id: str) -> str:
        """Get a single ad by ID (debugging).

        Args:
            ad_id: The ad identifier

        Returns:
            JSON string with ad data
        """
        raise NotImplementedError("ads_get: wiring pending")
