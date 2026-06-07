import pytest
from unittest.mock import patch

from filternarrange_engine.adapters.llm.registry import (
    AiCapabilityRegistry,
    CapabilityNotFoundError,
)


class _FakeCap:
    def __init__(self, name: str) -> None:
        self.name = name
        self.required_tier = "free"
        self.default_model_setting = "auto_summary"

    async def run(self, llm, payload):
        return {"echoed": payload}


def _ep(name: str, obj):
    class _EP:
        def __init__(self, n, o):
            self.name = n
            self._o = o

        def load(self):
            return self._o

    return _EP(name, obj)


def test_loads_from_entry_points():
    eps = [
        _ep("auto_summary", _FakeCap("auto_summary")),
        _ep("chart_suggest", _FakeCap("chart_suggest")),
    ]
    with patch(
        "filternarrange_engine.adapters.llm.registry.entry_points",
        return_value=eps,
    ):
        reg = AiCapabilityRegistry.load(disabled=frozenset())
    assert sorted(reg.names()) == ["auto_summary", "chart_suggest"]


def test_respects_disabled_set():
    eps = [
        _ep("auto_summary", _FakeCap("auto_summary")),
        _ep("anomaly_detect", _FakeCap("anomaly_detect")),
    ]
    with patch(
        "filternarrange_engine.adapters.llm.registry.entry_points",
        return_value=eps,
    ):
        reg = AiCapabilityRegistry.load(disabled=frozenset({"anomaly_detect"}))
    assert reg.names() == ["auto_summary"]
    assert not reg.is_enabled("anomaly_detect")


def test_get_raises_for_disabled_or_missing():
    eps = [_ep("auto_summary", _FakeCap("auto_summary"))]
    with patch(
        "filternarrange_engine.adapters.llm.registry.entry_points",
        return_value=eps,
    ):
        reg = AiCapabilityRegistry.load(disabled=frozenset({"chart_suggest"}))
    with pytest.raises(CapabilityNotFoundError):
        reg.get("chart_suggest")
    with pytest.raises(CapabilityNotFoundError):
        reg.get("does_not_exist")


def test_get_returns_capability():
    cap = _FakeCap("auto_summary")
    eps = [_ep("auto_summary", cap)]
    with patch(
        "filternarrange_engine.adapters.llm.registry.entry_points",
        return_value=eps,
    ):
        reg = AiCapabilityRegistry.load(disabled=frozenset())
    assert reg.get("auto_summary") is cap
