"""Observability: structured logs (trace_id, tool, latency_ms), optional metrics stub."""

from __future__ import annotations

import logging
import time
from typing import Any

_LOGGER = logging.getLogger("ad_injector.mcp")

# Optional metrics stub: tool_calls[name] = count, errors[name] = count
METRICS: dict[str, dict[str, int]] = {"tool_calls": {}, "errors": {}}


def get_logger() -> logging.Logger:
    return _LOGGER


def log_tool_invocation(
    tool: str,
    trace_id: str | None,
    latency_ms: float,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit structured log and update metrics stub."""
    payload: dict[str, Any] = {
        "tool": tool,
        "trace_id": trace_id,
        "latency_ms": round(latency_ms, 2),
    }
    if error:
        payload["error"] = error
    if extra:
        payload.update(extra)
    _LOGGER.info("tool_invocation", extra=payload)
    # Metrics stub
    METRICS["tool_calls"][tool] = METRICS["tool_calls"].get(tool, 0) + 1
    if error:
        METRICS["errors"][tool] = METRICS["errors"].get(tool, 0) + 1


def metrics_snapshot() -> dict[str, dict[str, int]]:
    """Return current metrics (for optional /metrics endpoint or health)."""
    return {k: dict(v) for k, v in METRICS.items()}
