"""MatchService — Data Plane orchestration.

Single public method: ``match(request) -> (MatchResponse, audit_trace)``.
All business logic for ad matching lives here; MCP tools are thin wrappers.
Produces response DTOs and audit trace for ads.explain.
"""

from __future__ import annotations

import re
from typing import Any

from ..domain.filters import VectorFilter
from ..models.mcp_requests import MatchRequest
from ..models.mcp_responses import AdCandidate, MatchResponse
from ..ports.embedding import EmbeddingProvider
from ..ports.id_gen import (
    MatchIdProvider,
    RequestIdProvider,
    UuidMatchIdProvider,
    UuidRequestIdProvider,
)
from ..ports.vector_store import VectorHit, VectorStorePort
from .policy_engine import PolicyEngine
from .targeting_engine import TargetingEngine

_WHITESPACE_RE = re.compile(r"\s+")


class MatchService:
    """Orchestrates the full ad-match pipeline."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStorePort,
        targeting_engine: TargetingEngine | None = None,
        policy_engine: PolicyEngine | None = None,
        request_id_provider: RequestIdProvider | None = None,
        match_id_provider: MatchIdProvider | None = None,
        logger: Any = None,
    ) -> None:
        self._embed = embedding_provider
        self._store = vector_store
        self._targeting = targeting_engine or TargetingEngine()
        self._policy = policy_engine or PolicyEngine()
        self._req_id = request_id_provider or UuidRequestIdProvider()
        self._match_id = match_id_provider or UuidMatchIdProvider()
        self._logger = logger

    def match(self, request: MatchRequest) -> tuple[MatchResponse, dict[str, Any]]:
        # 1. Generate request_id (trace_id)
        request_id = self._req_id.new_request_id()
        if self._logger:
            self._logger.info(
                "match_start",
                extra={
                    "trace_id": request_id,
                    "placement": request.placement.placement,
                    "top_k": request.top_k,
                },
            )

        # 2. Normalize input text
        text = _WHITESPACE_RE.sub(" ", request.context_text.strip())

        # 3. Embed
        vector = self._embed.embed(text)

        # 4. Build filter from typed constraints
        vector_filter = self._targeting.build_filter(
            request.constraints, request.placement
        )

        # 5. Query vector store
        raw_hits = self._store.query(
            vector=vector,
            vector_filter=vector_filter,
            top_k=request.top_k,
        )

        # 6. Policy: compute reason per hit for audit
        decisions: list[dict[str, Any]] = []
        eligible: list[VectorHit] = []
        for hit in raw_hits:
            reason = self._policy.reason(
                hit, request.constraints, request.placement
            )
            decisions.append({
                "ad_id": hit.ad_id,
                "score": hit.score,
                "reason": reason,
            })
            if reason == "allowed":
                eligible.append(hit)

        # 7. Convert to AdCandidates and assign match_id
        candidates: list[AdCandidate] = []
        for hit in eligible:
            c = self._hit_to_candidate(hit, request_id)
            candidates.append(c)
            for d in decisions:
                if d["ad_id"] == hit.ad_id:
                    d["match_id"] = c.match_id
                    break

        response = MatchResponse(
            candidates=candidates,
            request_id=request_id,
            placement=request.placement.placement,
        )
        audit_trace: dict[str, Any] = {
            "request_id": request_id,
            "placement": request.placement.placement,
            "context_text": request.context_text[:500],
            "constraints": request.constraints.model_dump(),
            "decisions": decisions,
        }
        if self._logger:
            self._logger.info(
                "match_done",
                extra={
                    "trace_id": request_id,
                    "placement": request.placement.placement,
                    "candidates_count": len(candidates),
                },
            )
        return response, audit_trace

    def _hit_to_candidate(self, hit: VectorHit, request_id: str) -> AdCandidate:
        score = max(0.0, min(1.0, hit.score))
        match_id = self._match_id.new_match_id(request_id, hit.ad_id)

        return AdCandidate(
            ad_id=hit.ad_id,
            advertiser_id=hit.advertiser_id,
            title=hit.payload["title"],
            body=hit.payload["body"],
            cta_text=hit.payload["cta_text"],
            landing_url=hit.payload["landing_url"],
            score=score,
            match_id=match_id,
        )
