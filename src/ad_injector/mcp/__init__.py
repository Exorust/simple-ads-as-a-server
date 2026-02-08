"""MCP server package for ad-injector (Control Plane + Data Plane)."""

from .server import create_server

__all__ = ["create_server"]
