"""Legacy MCP server for read-only ad matching.

Uses wiring.build_match_service() — no direct Qdrant or embedding imports.
"""

import json

from mcp.server.fastmcp import FastMCP

from .models.mcp_requests import MatchConstraints, MatchRequest, PlacementContext
from .wiring import build_match_service


# Initialize FastMCP server
mcp = FastMCP("ad-injector")


@mcp.tool()
def ads_match(query: str, top_k: int = 10) -> str:
    """Match ads by text query. Returns similar ads based on semantic similarity.

    Args:
        query: Text query to match against ads
        top_k: Number of results to return (default: 10, max: 100)

    Returns:
        JSON string containing list of matching ads with scores and metadata
    """
    if not query or not isinstance(query, str):
        raise ValueError("query parameter is required and must be a string")

    if not isinstance(top_k, int) or top_k < 1 or top_k > 100:
        raise ValueError("top_k must be an integer between 1 and 100")

    service = build_match_service()
    request = MatchRequest(
        context_text=query[:10_000],
        top_k=top_k,
        placement=PlacementContext(placement="inline", surface="chat"),
        constraints=MatchConstraints(),
    )
    response, _ = service.match(request)

    # Convert to legacy-style list of dicts for backward compatibility
    results = [
        {
            "id": c.ad_id,
            "score": c.score,
            "metadata": {
                "ad_id": c.ad_id,
                "advertiser_id": c.advertiser_id,
                "title": c.title,
                "body": c.body,
                "cta_text": c.cta_text,
                "landing_url": c.landing_url,
            },
        }
        for c in response.candidates
    ]
    return json.dumps(results, indent=2)


def run_server():
    """Run the MCP server using stdio transport."""
    mcp.run(transport="stdio")
