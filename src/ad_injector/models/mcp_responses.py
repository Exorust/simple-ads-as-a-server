"""MCP response DTOs for the Data Plane ads.match tool."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AdCandidate(BaseModel):
    """A single ad candidate returned by ads.match."""

    ad_id: str = Field(..., description="Unique ad identifier")
    advertiser_id: str = Field(..., description="Advertiser identifier")
    title: str = Field(..., description="Ad headline")
    body: str = Field(..., description="Ad body text")
    cta_text: str = Field(..., description="Call-to-action text")
    landing_url: str = Field(..., description="Click-through URL")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    match_id: str = Field(..., description="Opaque ID for ads.explain lookups")


class MatchResponse(BaseModel):
    """Output DTO for the ads.match tool."""

    candidates: list[AdCandidate] = Field(
        default_factory=list,
        description="Ranked ad candidates",
    )
    request_id: str = Field(..., description="Trace ID for this request")
    placement: str = Field(..., description="Placement slot that was requested")
