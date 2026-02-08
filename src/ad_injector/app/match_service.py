"""MatchService — Data Plane orchestration.

Single public method: ``match(request) -> MatchResponse``.
All business logic for ad matching lives here; MCP tools are thin wrappers.
"""

from __future__ import annotations

import re
import uuid

from ..models.mcp_requests import MatchRequest
from ..models.mcp_responses import AdCandidate, MatchResponse
from .embedding_provider import EmbeddingProvider
from .policy_engine import PolicyEngine
from .targeting_engine import TargetingEngine
from .vector_store import VectorStore

_WHITESPACE_RE = re.compile(r"\s+")


class MatchService:
    """Orchestrates the full ad-match pipeline."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
        targeting_engine: TargetingEngine | None = None,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        self._embed = embedding_provider or EmbeddingProvider()
        self._store = vector_store or VectorStore()
        self._targeting = targeting_engine or TargetingEngine()
        self._policy = policy_engine or PolicyEngine()

    def match(self, request: MatchRequest) -> MatchResponse:
        # 1. Generate request_id
        request_id = str(uuid.uuid4())

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

        # 6. Policy enforcement (post-query, cannot be bypassed)
        eligible = self._policy.apply(
            raw_hits, request.constraints, request.placement
        )

        # 7. Convert to AdCandidates
        candidates = [
            self._hit_to_candidate(hit, request_id) for hit in eligible
        ]

        return MatchResponse(
            candidates=candidates,
            request_id=request_id,
            placement=request.placement.placement,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hit_to_candidate(hit: dict, request_id: str) -> AdCandidate:
        meta = hit["metadata"]
        ad_id = meta["ad_id"]

        # Deterministic match_id: uuid5(request_id, ad_id)
        match_id = str(uuid.uuid5(uuid.UUID(request_id), ad_id))

        # Score: cosine similarity from Qdrant is already 0-1
        score = max(0.0, min(1.0, hit["score"]))

        return AdCandidate(
            ad_id=ad_id,
            advertiser_id=meta["advertiser_id"],
            title=meta["title"],
            body=meta["body"],
            cta_text=meta["cta_text"],
            landing_url=meta["landing_url"],
            score=score,
            match_id=match_id,
        )
