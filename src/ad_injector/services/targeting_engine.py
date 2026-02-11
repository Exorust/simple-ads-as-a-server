"""TargetingEngine: builds typed VectorFilters from MatchConstraints."""

from __future__ import annotations

from ..domain.filters import FieldFilter, FilterOp, VectorFilter
from ..models.mcp_requests import MatchConstraints, PlacementContext


class TargetingEngine:
    """Translate typed MatchConstraints into a domain VectorFilter."""

    def build_filter(
        self,
        constraints: MatchConstraints,
        placement: PlacementContext,
    ) -> VectorFilter:
        must: list[FieldFilter] = []
        must_not: list[FieldFilter] = []

        if constraints.topics:
            must.append(FieldFilter(field="topics", op=FilterOp.any_of, value=constraints.topics))

        if constraints.locale:
            must.append(FieldFilter(field="locale", op=FilterOp.any_of, value=[constraints.locale]))

        if constraints.verticals:
            must.append(FieldFilter(field="verticals", op=FilterOp.any_of, value=constraints.verticals))

        if constraints.exclude_advertiser_ids:
            must_not.append(FieldFilter(field="advertiser_id", op=FilterOp.not_in, value=constraints.exclude_advertiser_ids))

        if constraints.exclude_ad_ids:
            must_not.append(FieldFilter(field="ad_id", op=FilterOp.not_in, value=constraints.exclude_ad_ids))

        return VectorFilter(must=must, must_not=must_not)
