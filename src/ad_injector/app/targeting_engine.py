"""TargetingEngine: builds typed VectorFilters from MatchConstraints."""

from __future__ import annotations

from qdrant_client.models import FieldCondition, MatchAny, MatchValue

from ..models.mcp_requests import MatchConstraints, PlacementContext
from .vector_store import VectorFilter


class TargetingEngine:
    """Translate typed MatchConstraints into a VectorFilter for Qdrant."""

    def build_filter(
        self,
        constraints: MatchConstraints,
        placement: PlacementContext,
    ) -> VectorFilter:
        vf = VectorFilter()

        # --- must conditions ---
        if constraints.topics:
            vf.must.append(
                FieldCondition(key="topics", match=MatchAny(any=constraints.topics))
            )

        if constraints.locale:
            vf.must.append(
                FieldCondition(key="locale", match=MatchAny(any=[constraints.locale]))
            )

        if constraints.verticals:
            vf.must.append(
                FieldCondition(key="verticals", match=MatchAny(any=constraints.verticals))
            )

        # --- must_not conditions ---
        if constraints.exclude_advertiser_ids:
            vf.must_not.append(
                FieldCondition(
                    key="advertiser_id",
                    match=MatchAny(any=constraints.exclude_advertiser_ids),
                )
            )

        if constraints.exclude_ad_ids:
            vf.must_not.append(
                FieldCondition(
                    key="ad_id",
                    match=MatchAny(any=constraints.exclude_ad_ids),
                )
            )

        return vf
