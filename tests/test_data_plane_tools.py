"""Tests that the Data Plane MCP server exposes only the allowed tool set.

No destructive or admin tools (collection create/delete, upsert, delete_ad,
query_ads) may be registered on the Data Plane.
"""

from ad_injector.mcp.server import create_server
from ad_injector.mcp.tools import DATA_PLANE_ALLOWED_TOOLS

# Tools that must NEVER appear on the Data Plane
FORBIDDEN_TOOLS = {
    "collection_ensure",
    "collection_info",
    "collection_migrate",
    "collection_delete",
    "collection_create",
    "ads_upsert_batch",
    "ads_delete",
    "ads_bulk_disable",
    "ads_get",
    "query_ads",
    "delete_ad",
    "upsert_ad",
    "create_collection",
    "delete_collection",
}


def _get_tool_names(server) -> set[str]:
    """Extract registered tool names from a FastMCP server."""
    # FastMCP stores tools in _tool_manager._tools dict
    tools = server._tool_manager._tools
    return set(tools.keys())


def test_data_plane_exposes_only_ads_match():
    """Data Plane must expose exactly the tools in DATA_PLANE_ALLOWED_TOOLS."""
    server = create_server("data")
    tool_names = _get_tool_names(server)
    assert tool_names == DATA_PLANE_ALLOWED_TOOLS, (
        f"Expected {DATA_PLANE_ALLOWED_TOOLS}, got {tool_names}"
    )


def test_data_plane_has_no_forbidden_tools():
    """No destructive / admin tool may be registered on the Data Plane."""
    server = create_server("data")
    tool_names = _get_tool_names(server)
    overlap = tool_names & FORBIDDEN_TOOLS
    assert not overlap, f"Forbidden tools found on Data Plane: {overlap}"


def test_control_plane_has_admin_tools():
    """Control Plane must have admin tools and NOT ads_match."""
    server = create_server("admin")
    tool_names = _get_tool_names(server)
    assert "collection_ensure" in tool_names
    assert "ads_upsert_batch" in tool_names
    assert "ads_delete" in tool_names
    assert "ads_match" not in tool_names, "ads_match must not be on Control Plane"
