"""PolicyEngine: non-negotiable post-query filtering."""

from __future__ import annotations

from ..models.mcp_requests import MatchConstraints, PlacementContext


class PolicyEngine:
    """Filter raw vector hits by policy rules.

    Policy is enforced *after* the vector query so it cannot be bypassed
    by crafting filter expressions.
    """

    def apply(
        self,
        hits: list[dict],
        constraints: MatchConstraints,
        placement: PlacementContext,
    ) -> list[dict]:
        """Return only hits that pass all policy checks."""
        eligible: list[dict] = []
        for hit in hits:
            meta = hit.get("metadata", {})

            # Age-restricted gate
            if meta.get("age_restricted", False) and not constraints.age_restricted_ok:
                continue

            # Sensitive-content gate
            if meta.get("sensitive", False) and not constraints.sensitive_ok:
                continue

            # Blocked-keywords gate: if any of the ad's blocked keywords
            # appear in the targeting topics requested, skip.
            blocked = set(meta.get("blocked_keywords", []))
            if blocked and constraints.topics:
                if blocked & set(constraints.topics):
                    continue

            eligible.append(hit)

        return eligible
