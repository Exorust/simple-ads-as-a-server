"""MCP auth: roles/scopes (admin vs read-only). Gate and reject unauthorized."""

from __future__ import annotations

import os


def require_admin_scope() -> None:
    """Require admin scope for Control Plane. Raises PermissionError if not allowed."""
    from ..config.runtime import get_settings

    settings = get_settings()
    if not getattr(settings, "require_admin_key", False):
        return
    if not os.environ.get("MCP_ADMIN_KEY"):
        raise PermissionError("Control Plane requires MCP_ADMIN_KEY to be set")


def require_data_scope() -> None:
    """Require data (read-only) scope for Data Plane. Raises PermissionError if not allowed."""
    from ..config.runtime import get_settings

    settings = get_settings()
    if not getattr(settings, "require_data_key", False):
        return
    if not os.environ.get("MCP_DATA_KEY"):
        raise PermissionError("Data Plane requires MCP_DATA_KEY to be set")


def check_scope(mode: str) -> None:
    """Check scope for the given server mode. Call at server start or per-request."""
    if mode == "admin":
        require_admin_scope()
    elif mode == "data":
        require_data_scope()
    else:
        raise ValueError(f"Unknown mode: {mode!r}")
