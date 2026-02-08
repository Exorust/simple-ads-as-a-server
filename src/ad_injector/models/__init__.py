"""Domain and MCP request/response models."""

from .ad import Ad, AdPolicy, AdTargeting
from .mcp_requests import MatchConstraints, MatchRequest, PlacementContext
from .mcp_responses import AdCandidate, MatchResponse

__all__ = [
    # Domain
    "Ad",
    "AdPolicy",
    "AdTargeting",
    # MCP requests
    "MatchRequest",
    "MatchConstraints",
    "PlacementContext",
    # MCP responses
    "MatchResponse",
    "AdCandidate",
]
