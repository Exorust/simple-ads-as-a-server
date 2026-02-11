"""PolicyEngine: non-negotiable post-query filtering."""

from __future__ import annotations

from ..models.mcp_requests import MatchConstraints, PlacementContext
from ..ports.vector_store import VectorHit


class PolicyEngine:
    """Filter vector hits by policy rules.

    Policy is enforced *after* the vector query so it cannot be bypassed
    by crafting filter expressions. Provides allow/deny + reason for audit.
    """

    def apply(
        self,
        hits: list[VectorHit],
        constraints: MatchConstraints,
        placement: PlacementContext,
    ) -> list[VectorHit]:
        """Return only hits that pass all policy checks."""
        eligible: list[VectorHit] = []
        for hit in hits:
            if self._allowed(hit, constraints):
                eligible.append(hit)
        return eligible

    def reason(
        self,
        hit: VectorHit,
        constraints: MatchConstraints,
        placement: PlacementContext,
    ) -> str:
        """Return audit reason for this hit: 'allowed' or 'denied: <reason>'."""
        meta = hit.payload
        if meta.get("age_restricted", False) and not constraints.age_restricted_ok:
            return "denied: age_restricted"
        if meta.get("sensitive", False) and not constraints.sensitive_ok:
            return "denied: sensitive"
        blocked = set(meta.get("blocked_keywords", []))
        if blocked and constraints.topics and (blocked & set(constraints.topics)):
            return "denied: blocked_keywords"
        return "allowed"

    def _allowed(
        self,
        hit: VectorHit,
        constraints: MatchConstraints,
    ) -> bool:
        meta = hit.payload
        if meta.get("age_restricted", False) and not constraints.age_restricted_ok:
            return False
        if meta.get("sensitive", False) and not constraints.sensitive_ok:
            return False
        blocked = set(meta.get("blocked_keywords", []))
        if blocked and constraints.topics and (blocked & set(constraints.topics)):
            return False
        return True
