"""Data Plane entrypoint.

Starts the MCP Data Plane server (LLM-facing, read-only).
This module deliberately avoids importing any CLI or admin modules
so it can be used as a minimal container entrypoint.

Usage:
    python -m ad_injector.main_runtime
    # or via the script entrypoint:
    ad-data-plane
"""

from __future__ import annotations

from .mcp.server import create_server


def main() -> None:
    from .mcp.auth import check_scope
    check_scope("data")
    server = create_server(mode="data")
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
