"""Configuration package.

Legacy Qdrant config is available via ``ad_injector.config.qdrant``.
New runtime settings via ``ad_injector.config.runtime``.
"""

from .runtime import McpMode, RuntimeSettings, get_settings

__all__ = [
    "McpMode",
    "RuntimeSettings",
    "get_settings",
]
