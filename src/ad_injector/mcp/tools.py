"""Tool registry for MCP servers.

Strict JSON schemas via Pydantic; request shaping (limits, timeouts);
response allowlists (field-level).
"""

from __future__ import annotations

import json
import time
from typing import Any

from .observability import log_tool_invocation

from ..config.runtime import get_settings
from ..models import Ad
from ..models.mcp_requests import MatchConstraints, MatchRequest, PlacementContext

# ---------------------------------------------------------------------------
# Response allowlists (field-level)
# ---------------------------------------------------------------------------
ALLOWED_MATCH_CANDIDATE_KEYS = frozenset({
    "ad_id", "advertiser_id", "title", "body", "cta_text", "landing_url", "score", "match_id",
})
ALLOWED_MATCH_RESPONSE_KEYS = frozenset({"candidates", "request_id", "placement"})
ALLOWED_COLLECTION_INFO_KEYS = frozenset({
    "name", "points_count", "indexed_vectors_count", "status",
    "dimension", "embedding_model_id", "schema_version",
})
ALLOWED_COLLECTION_ENSURE_KEYS = frozenset({"name", "created", "dimension", "embedding_model_id", "schema_version"})
ALLOWED_ADS_GET_KEYS = frozenset({
    "ad_id", "advertiser_id", "title", "body", "cta_text", "landing_url",
    "topics", "locale", "verticals", "blocked_keywords", "sensitive", "age_restricted", "enabled",
})

# In-memory trace store for ads.explain (match_id -> audit_trace), optional TTL
_trace_store: dict[str, dict[str, Any]] = {}
_TRACE_STORE_MAX = 10_000


def _shape_match_response(response: Any) -> dict:
    """Return only allowed fields for ads.match response."""
    d = response.model_dump() if hasattr(response, "model_dump") else response
    out: dict = {k: d[k] for k in ALLOWED_MATCH_RESPONSE_KEYS if k in d}
    if "candidates" in out:
        out["candidates"] = [
            {k: c.get(k) for k in ALLOWED_MATCH_CANDIDATE_KEYS if k in c}
            for c in out["candidates"]
        ]
    return out


def _shape_collection_info(d: dict) -> dict:
    return {k: d[k] for k in ALLOWED_COLLECTION_INFO_KEYS if k in d}


def _shape_collection_ensure(d: dict) -> dict:
    return {k: d[k] for k in ALLOWED_COLLECTION_ENSURE_KEYS if k in d}


def _shape_ads_get(payload: dict | None) -> dict | None:
    if payload is None:
        return None
    return {k: payload[k] for k in ALLOWED_ADS_GET_KEYS if k in payload}


def _store_trace_for_explain(response: Any, audit_trace: dict[str, Any]) -> None:
    """Store audit trace keyed by each match_id for ads.explain."""
    global _trace_store
    candidates = getattr(response, "candidates", []) or []
    for c in candidates:
        match_id = getattr(c, "match_id", None) or (c.get("match_id") if isinstance(c, dict) else None)
        if match_id:
            _trace_store[match_id] = audit_trace
    while len(_trace_store) > _TRACE_STORE_MAX:
        # Drop oldest (arbitrary)
        _trace_store.pop(next(iter(_trace_store)))


def _get_match_service():
    from ..wiring import build_match_service
    return build_match_service()


def _get_index_service():
    from ..wiring import build_index_service
    return build_index_service()


# ---------------------------------------------------------------------------
# Data Plane tools
# ---------------------------------------------------------------------------
DATA_PLANE_ALLOWED_TOOLS = frozenset({"ads_match", "ads_explain", "ads_health", "ads_capabilities"})


def register_data_plane_tools(mcp):
    """Register Data Plane (runtime / LLM-facing) tools with request shaping and response allowlist."""

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
        """Match ads by semantic context (read-only). Returns ranked candidates and match_id for explain.

        Args:
            context_text: Conversational / page context to match against (max 10000 chars)
            top_k: Number of candidates (1-100, default 5)
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
            JSON with candidates (ad_id, title, cta_text, landing_url, score, match_id), request_id, placement
        """
        t0 = time.monotonic()
        request = MatchRequest(
            context_text=context_text[:10_000],
            top_k=max(1, min(100, top_k)),
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
        service = _get_match_service()
        response, audit_trace = service.match(request)
        _store_trace_for_explain(response, audit_trace)
        latency_ms = (time.monotonic() - t0) * 1000
        log_tool_invocation("ads_match", response.request_id, latency_ms, extra={"candidates_count": len(response.candidates)})
        return json.dumps(_shape_match_response(response), indent=2)

    @mcp.tool()
    def ads_explain(match_id: str) -> str:
        """Return audit trace for a prior match (why eligible/ineligible, filters, scores).

        Args:
            match_id: Opaque ID returned with each candidate from ads_match

        Returns:
            JSON trace with request_id, placement, context_text, constraints, decisions (ad_id, score, reason)
        """
        trace = _trace_store.get(match_id)
        if trace is None:
            return json.dumps({"error": "match_id not found", "match_id": match_id})
        return json.dumps(trace, indent=2)

    @mcp.tool()
    def ads_health() -> str:
        """Liveness/readiness: Qdrant and embedding provider reachable."""
        try:
            from ..ops.smoke_check import run_smoke_check
            result = run_smoke_check()
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    @mcp.tool()
    def ads_capabilities() -> str:
        """Supported placements, constraint keys, embedding model, schema version."""
        settings = get_settings()
        info = _get_index_service().collection_info()
        if isinstance(info, dict):
            embedding_model_id = info.get("embedding_model_id") or settings.embedding_model_id
            schema_version = info.get("schema_version") or "1"
        else:
            embedding_model_id = settings.embedding_model_id
            schema_version = "1"
        return json.dumps({
            "placements": ["inline", "sidebar", "banner"],
            "constraint_keys": ["topics", "locale", "verticals", "exclude_advertiser_ids", "exclude_ad_ids", "age_restricted_ok", "sensitive_ok"],
            "embedding_model_id": embedding_model_id,
            "schema_version": schema_version,
        })


# ---------------------------------------------------------------------------
# Control Plane tools
# ---------------------------------------------------------------------------

def register_control_plane_tools(mcp):
    """Register Control Plane (admin) tools with response allowlists."""

    @mcp.tool()
    def collection_ensure(
        dimension: int = 384,
        embedding_model_id: str = "BAAI/bge-small-en-v1.5",
        schema_version: str = "1",
    ) -> str:
        """Ensure the ads collection exists with the given config.

        Args:
            dimension: Embedding vector dimension
            embedding_model_id: Model used for embeddings
            schema_version: Schema version tag

        Returns:
            JSON with name, created, dimension, embedding_model_id, schema_version
        """
        from ..mcp.auth import require_admin_scope
        require_admin_scope()
        svc = _get_index_service()
        result = svc.ensure_collection(
            dimension=dimension,
            embedding_model_id=embedding_model_id,
            schema_version=schema_version,
        )
        return json.dumps(_shape_collection_ensure(result))

    @mcp.tool()
    def collection_info() -> str:
        """Return metadata about the current ads collection.

        Returns:
            JSON with name, points_count, status, dimension, embedding_model_id, schema_version
        """
        from ..mcp.auth import require_admin_scope
        require_admin_scope()
        result = _get_index_service().collection_info()
        return json.dumps(_shape_collection_info(result))

    @mcp.tool()
    def collection_migrate(from_version: str, to_version: str) -> str:
        """Optional: run schema migrations / re-index between versions.

        Args:
            from_version: Current schema version
            to_version: Target schema version

        Returns:
            JSON status
        """
        from ..mcp.auth import require_admin_scope
        require_admin_scope()
        return json.dumps({
            "status": "noop",
            "message": "collection_migrate not implemented",
            "from_version": from_version,
            "to_version": to_version,
        })

    @mcp.tool()
    def ads_upsert_batch(ads_json: str) -> str:
        """Upsert a batch of ads. Validate Ad schema, embed, upsert. Size limit from config.

        Args:
            ads_json: JSON array of ad objects

        Returns:
            JSON with upserted count
        """
        from ..mcp.auth import require_admin_scope
        require_admin_scope()
        settings = get_settings()
        raw = json.loads(ads_json)
        if not isinstance(raw, list):
            return json.dumps({"error": "ads_json must be a JSON array"})
        ads: list[Ad] = []
        for i, item in enumerate(raw):
            try:
                ads.append(Ad.model_validate(item))
            except Exception as e:
                return json.dumps({"error": f"invalid ad at index {i}", "detail": str(e)})
        batch_size = min(len(ads), settings.max_batch_size)
        ads = ads[:batch_size]
        svc = _get_index_service()
        count = svc.upsert_ads(ads)
        return json.dumps({"upserted": count})

    @mcp.tool()
    def ads_delete(ad_id: str) -> str:
        """Delete a single ad by ID.

        Args:
            ad_id: The ad identifier to delete

        Returns:
            JSON confirmation
        """
        from ..mcp.auth import require_admin_scope
        require_admin_scope()
        _get_index_service().delete_ad(ad_id)
        return json.dumps({"deleted": ad_id})

    @mcp.tool()
    def ads_bulk_disable(filter_json: str) -> str:
        """Set enabled=false for all ads matching the filter.

        Args:
            filter_json: JSON object e.g. {"advertiser_id": "x"} or {"ad_id": ["a","b"]}

        Returns:
            JSON with count of disabled ads
        """
        from ..mcp.auth import require_admin_scope
        require_admin_scope()
        try:
            filter_spec = json.loads(filter_json)
        except Exception as e:
            return json.dumps({"error": "invalid filter_json", "detail": str(e)})
        if not isinstance(filter_spec, dict):
            return json.dumps({"error": "filter_json must be a JSON object"})
        count = _get_index_service().bulk_disable(filter_spec)
        return json.dumps({"disabled": count})

    @mcp.tool()
    def ads_get(ad_id: str) -> str:
        """Get a single ad by ID (debugging).

        Args:
            ad_id: The ad identifier

        Returns:
            JSON with ad payload (allowlisted fields)
        """
        from ..mcp.auth import require_admin_scope
        require_admin_scope()
        payload = _get_index_service().get_ad(ad_id)
        if payload is None:
            return json.dumps({"error": "not found", "ad_id": ad_id})
        payload.setdefault("enabled", True)
        shaped = _shape_ads_get(payload)
        return json.dumps(shaped or payload)
