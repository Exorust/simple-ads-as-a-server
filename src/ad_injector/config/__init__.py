"""Configuration package.

Single source of truth: ``RuntimeSettings`` via ``get_settings()``.
"""

from .runtime import McpMode, RuntimeSettings, get_settings

__all__ = [
    "McpMode",
    "RuntimeSettings",
    "get_settings",
]
