"""Convert orchestration: filter then emit to chosen format → write blob."""
from __future__ import annotations
import io as _io
import uuid
from typing import Protocol

from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.core.canonical import TabularData
from filternarrange_engine.platform.config import EngineSettings
from filternarrange_engine.platform.errors import EngineError


class _Store(Protocol):
    def get(self, ref: str): ...
    def put(self, ref: str, data, size: int, content_type: str): ...


class ConvertService:
    def __init__(self, store: _Store, registry: PluginRegistry, settings: EngineSettings):
        self.store = store; self.registry = registry; self.settings = settings

    def run(self, ref: str, spec: dict, output_format: str) -> dict:
        try:
            blob = self.store.get(ref).read()
        except FileNotFoundError as e:
            raise EngineError(code="NOT_FOUND", message=str(e), http_status=404) from e

        choice = self.registry.detect_format(blob[:65536])
        if choice is None:
            raise EngineError(code="UNKNOWN_FORMAT", message="no plugin matched", http_status=422)
        fid, _ = choice
        in_plugin = self.registry.get_format(fid)
        try:
            out_plugin = self.registry.get_format(output_format)
        except KeyError as e:
            raise EngineError(code="UNKNOWN_OUTPUT_FORMAT",
                              message=f"no plugin for {output_format}", http_status=400) from e

        parsed = in_plugin.parse(_io.BytesIO(blob))
        if isinstance(parsed, TabularData):
            try:
                filter_plugin = self.registry.get_filter(spec.get("kind", ""))
                parsed = filter_plugin.apply(parsed, spec)
            except KeyError as e:
                raise EngineError(code="UNKNOWN_FILTER", message=str(e), http_status=422) from e

        result_id = uuid.uuid4()
        result_ref = f"{self.settings.minio_results_bucket}/{result_id}.{output_format}"
        sink = _io.BytesIO()
        out_plugin.emit(parsed, sink)
        body = sink.getvalue()
        self.store.put(result_ref, _io.BytesIO(body), len(body),
                       _ct(output_format))
        return {"resultRef": result_ref}


def _ct(fmt: str) -> str:
    return {"csv": "text/csv", "json": "application/json"}.get(fmt, "application/octet-stream")


__all__ = ["ConvertService"]
