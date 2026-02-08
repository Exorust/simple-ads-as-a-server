"""MCP request DTOs for the Data Plane ads.match tool."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlacementContext(BaseModel):
    """Where the ad will be rendered."""

    placement: str = Field(
        default="inline",
        description="Placement slot identifier (e.g. 'inline', 'sidebar', 'banner')",
    )
    surface: str = Field(
        default="chat",
        description="Surface type (e.g. 'chat', 'search', 'feed')",
    )


class MatchConstraints(BaseModel):
    """Typed constraints for ad matching — no raw dict filters."""

    topics: list[str] | None = Field(
        default=None,
        description="Restrict matches to these topics",
    )
    locale: str | None = Field(
        default=None,
        description="Required locale code (e.g. 'en-US')",
    )
    verticals: list[str] | None = Field(
        default=None,
        description="Restrict matches to these verticals",
    )
    exclude_advertiser_ids: list[str] | None = Field(
        default=None,
        description="Advertiser IDs to exclude from results",
    )
    exclude_ad_ids: list[str] | None = Field(
        default=None,
        description="Ad IDs to exclude from results",
    )
    age_restricted_ok: bool = Field(
        default=False,
        description="Whether age-restricted ads are allowed",
    )
    sensitive_ok: bool = Field(
        default=False,
        description="Whether sensitive-content ads are allowed",
    )


class MatchRequest(BaseModel):
    """Input DTO for the ads.match tool."""

    context_text: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="Conversational / page context to match against",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Number of ad candidates to return",
    )
    placement: PlacementContext = Field(
        default_factory=PlacementContext,
        description="Where the ad will be shown",
    )
    constraints: MatchConstraints = Field(
        default_factory=MatchConstraints,
        description="Typed match constraints",
    )
