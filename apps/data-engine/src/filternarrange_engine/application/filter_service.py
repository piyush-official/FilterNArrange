"""Filter orchestration: detect → parse → filter → collect N rows."""
from __future__ import annotations
import asyncio
import io as _io
from typing import Protocol

from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.core.canonical import TabularData
from filternarrange_engine.platform.errors import EngineError


class _Store(Protocol):
    def get(self, ref: str): ...


class FilterService:
    def __init__(self, store: _Store, registry: PluginRegistry):
        self.store = store; self.registry = registry

    def run(self, ref: str, spec: dict, sample_size: int) -> dict:
        try:
            blob = self.store.get(ref).read()
        except FileNotFoundError as e:
            raise EngineError(code="NOT_FOUND", message=str(e), http_status=404) from e

        choice = self.registry.detect_format(blob[:65536])
        if choice is None:
            raise EngineError(code="UNKNOWN_FORMAT", message="no plugin matched", http_status=422)
        fid, _ = choice
        format_plugin = self.registry.get_format(fid)
        parsed = format_plugin.parse(_io.BytesIO(blob))
        if not isinstance(parsed, TabularData):
            raise EngineError(code="NOT_TABULAR", message="filter requires tabular data", http_status=422)

        kind = spec.get("kind")
        try:
            filter_plugin = self.registry.get_filter(kind)
        except KeyError as e:
            raise EngineError(code="UNKNOWN_FILTER", message=f"no filter for kind={kind}",
                              http_status=422) from e

        errs = filter_plugin.validate(spec)
        if errs:
            raise EngineError(code="VALIDATION_FAILED",
                              message="; ".join(f"{e.field}: {e.message}" for e in errs),
                              http_status=400)
        filtered = filter_plugin.apply(parsed, spec)

        async def collect():
            out = []
            async for r in filtered.rows:
                out.append(r)
                if len(out) >= sample_size:
                    break
            return out

        rows = asyncio.new_event_loop().run_until_complete(collect())
        return {
            "schema": [{"name": c.name, "type": c.type.value, "nullable": c.nullable} for c in filtered.schema],
            "rows": rows,
        }


__all__ = ["FilterService"]
