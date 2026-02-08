"""MCP server factory.

Creates either a Data Plane or Control Plane server depending on
the requested mode. Each plane registers only its own tool set.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .tools import register_control_plane_tools, register_data_plane_tools

_SERVER_NAMES = {
    "data": "ad-data-plane",
    "admin": "ad-control-plane",
}


def create_server(mode: str = "data") -> FastMCP:
    """Build and return a configured FastMCP server.

    Args:
        mode: ``"data"`` for the Data Plane (LLM-facing, read-only)
              or ``"admin"`` for the Control Plane.

    Returns:
        A FastMCP instance with the appropriate tools registered.
    """
    if mode not in _SERVER_NAMES:
        raise ValueError(f"Unknown MCP mode {mode!r}; expected 'data' or 'admin'")

    server = FastMCP(_SERVER_NAMES[mode])

    if mode == "data":
        register_data_plane_tools(server)
    else:
        register_control_plane_tools(server)

    return server


if __name__ == "__main__":
    server = create_server("data")
    server.run(transport="stdio")
