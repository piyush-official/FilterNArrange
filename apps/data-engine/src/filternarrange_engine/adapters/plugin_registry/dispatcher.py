"""Dispatcher boundary — wraps plugin calls in a PluginResult."""
from __future__ import annotations
from typing import Callable, TypeVar
import structlog

from filternarrange_engine.core.plugin_api import PluginResult

log = structlog.get_logger(__name__)

T = TypeVar("T")


def dispatch_plugin_call(plugin_id: str, plugin_version: str, trace_id: str,
                         call: Callable[[], T]) -> PluginResult[T]:
    """Run `call`; convert any exception into a structured PluginResult.error."""
    try:
        value = call()
        return PluginResult.ok(value)
    except Exception as exc:
        log.warning("plugin_failure",
                    plugin_id=plugin_id, plugin_version=plugin_version,
                    trace_id=trace_id, error=str(exc),
                    error_type=type(exc).__name__)
        return PluginResult.error(
            code="PLUGIN_FAILURE",
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            message=f"{type(exc).__name__}: {exc}",
            trace_id=trace_id,
        )


__all__ = ["dispatch_plugin_call"]
