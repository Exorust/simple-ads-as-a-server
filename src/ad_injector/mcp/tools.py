"""Tool registry for MCP servers.

Data Plane tools  – read-only, LLM-facing (explicit allowlist)
Control Plane tools – admin/provisioning ops
"""

from __future__ import annotations

import json

from ..models.mcp_requests import MatchRequest
from ..models.mcp_responses import AdCandidate, MatchResponse

# ---------------------------------------------------------------------------
# Data Plane – explicit allowlist of tool names
# ---------------------------------------------------------------------------
DATA_PLANE_ALLOWED_TOOLS = frozenset({"ads_match"})


def _get_match_service():
    """Composition root: build a MatchService with real adapters.

    Lazy import so the MCP layer stays free of heavy deps at registration
    time.  Called once per request (the adapters are lightweight).
    """
    from ..app.match_service import MatchService

    return MatchService()


def register_data_plane_tools(mcp):
    """Register Data Plane (runtime / LLM-facing) tools on *mcp*.

    Only tools listed in ``DATA_PLANE_ALLOWED_TOOLS`` are registered.
    No destructive or write operations are permitted.
    """

    @mcp.tool()
    def ads_match(
        context_text: str,
        top_k: int = 5,
        placement: str = "inline",
        surface: str = "chat",
        topics: list[str] | None = None,
        locale: str | None = None,
        verticals: list[str] | None = None,
        exclude_advertiser_ids: list[str] | None = None,
        exclude_ad_ids: list[str] | None = None,
        age_restricted_ok: bool = False,
        sensitive_ok: bool = False,
    ) -> str:
        """Match ads by semantic context (read-only).

        Args:
            context_text: Conversational / page context to match against
            top_k: Number of candidates to return (1-100, default 5)
            placement: Placement slot (e.g. 'inline', 'sidebar', 'banner')
            surface: Surface type (e.g. 'chat', 'search', 'feed')
            topics: Restrict to these topics
            locale: Required locale (e.g. 'en-US')
            verticals: Restrict to these verticals
            exclude_advertiser_ids: Advertiser IDs to exclude
            exclude_ad_ids: Ad IDs to exclude
            age_restricted_ok: Allow age-restricted ads
            sensitive_ok: Allow sensitive-content ads

        Returns:
            JSON string with ranked ad candidates
        """
        from ..models.mcp_requests import MatchConstraints, PlacementContext

        # Validate through DTOs
        request = MatchRequest(
            context_text=context_text,
            top_k=top_k,
            placement=PlacementContext(placement=placement, surface=surface),
            constraints=MatchConstraints(
                topics=topics,
                locale=locale,
                verticals=verticals,
                exclude_advertiser_ids=exclude_advertiser_ids,
                exclude_ad_ids=exclude_ad_ids,
                age_restricted_ok=age_restricted_ok,
                sensitive_ok=sensitive_ok,
            ),
        )

        # Delegate to MatchService — all business logic lives there
        service = _get_match_service()
        response = service.match(request)
        return response.model_dump_json(indent=2)


# ---------------------------------------------------------------------------
# Control Plane – admin / provisioning ops
# ---------------------------------------------------------------------------

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
