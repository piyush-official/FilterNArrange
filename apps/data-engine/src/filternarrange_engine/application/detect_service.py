"""Detect orchestration: load sample → run all plugins → choose best."""
from __future__ import annotations
from typing import Protocol

from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.core.canonical import TabularData, TreeData
from filternarrange_engine.platform.config import EngineSettings
from filternarrange_engine.platform.errors import EngineError


class _Store(Protocol):
    def get(self, ref: str): ...


class DetectService:
    def __init__(self, store: _Store, registry: PluginRegistry, settings: EngineSettings):
        self.store = store; self.registry = registry; self.settings = settings

    def run(self, ref: str) -> dict:
        try:
            blob = self.store.get(ref).read()
        except FileNotFoundError as e:
            raise EngineError(code="NOT_FOUND", message=str(e), http_status=404) from e
        sample = blob[:self.settings.sample_bytes]
        choice = self.registry.detect_format(sample)
        if choice is None or choice[1] < 0.4:
            raise EngineError(code="UNKNOWN_FORMAT", message="No plugin matched", http_status=422)
        fid, confidence = choice
        plugin = self.registry.get_format(fid)
        import io as _io
        parsed = plugin.parse(_io.BytesIO(blob))
        schema = _schema_of(parsed)
        return {"format": fid, "confidence": confidence, "schema": schema}


def _schema_of(parsed) -> list[dict]:
    if isinstance(parsed, TabularData):
        return [{"name": c.name, "type": c.type.value, "nullable": c.nullable} for c in parsed.schema]
    if isinstance(parsed, TreeData):
        return [{"name": "$", "type": "null", "nullable": True}]
    return []


__all__ = ["DetectService"]
