import pytest
from filternarrange_engine.adapters.plugin_registry.dispatcher import dispatch_plugin_call
from filternarrange_engine.core.plugin_api import PluginResult


def test_dispatch_success():
    result = dispatch_plugin_call("csv", "1.0.0", "trace-1", lambda: {"ok": True})
    assert result.is_ok and result.value == {"ok": True}


def test_dispatch_catches_exception_and_returns_envelope():
    def boom():
        raise ValueError("kaboom")
    result = dispatch_plugin_call("csv", "1.0.0", "trace-9", boom)
    assert not result.is_ok
    assert result.code == "PLUGIN_FAILURE"
    assert result.plugin_id == "csv"
    assert result.plugin_version == "1.0.0"
    assert "kaboom" in result.message
    assert result.trace_id == "trace-9"
