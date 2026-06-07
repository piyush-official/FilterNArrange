"""Analysis orchestration: detect → parse → (optional filter) → analyze.

Mirrors FilterService's dispatch shape — the filter step reuses
FilterService when a `filter` payload is provided.
"""
from __future__ import annotations
import io as _io
from typing import Any, Optional, Protocol

from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.core.analysis import parse_analysis_spec
from filternarrange_engine.core.canonical import TabularData, TreeData
from filternarrange_engine.core.filter_spec import parse_filter_spec
from filternarrange_engine.platform.errors import EngineError


class _Store(Protocol):
    def get(self, ref: str): ...


def _format_errors(errs: list[Any]) -> str:
    rendered: list[str] = []
    for e in errs:
        if hasattr(e, "field") and hasattr(e, "message"):
            rendered.append(f"{e.field}: {e.message}")
        else:
            rendered.append(str(e))
    return "; ".join(rendered)


class AnalysisService:
    def __init__(self, store: _Store, registry: PluginRegistry):
        self.store = store
        self.registry = registry

    async def run(self, ref: str, analysis_spec: dict, filter_spec: Optional[dict] = None) -> dict:
        try:
            blob = self.store.get(ref).read()
        except FileNotFoundError as e:
            raise EngineError(code="NOT_FOUND", message=str(e), http_status=404) from e

        choice = self.registry.detect_format(blob[:65536])
        if choice is None:
            raise EngineError(code="UNKNOWN_FORMAT", message="no plugin matched", http_status=422)
        fid, _ = choice
        format_plugin = self.registry.get_format(fid)
        data: TabularData | TreeData = format_plugin.parse(_io.BytesIO(blob))

        if filter_spec:
            data = self._apply_filter(data, filter_spec)

        try:
            spec = parse_analysis_spec(analysis_spec)
        except (KeyError, ValueError) as e:
            raise EngineError(code="VALIDATION_FAILED", message=f"bad analysis spec: {e}", http_status=400) from e

        try:
            plugin = self.registry.get_analysis(spec.kind)
        except KeyError as e:
            raise EngineError(code="UNKNOWN_ANALYSIS", message=f"no analysis plugin for kind={spec.kind!r}",
                              http_status=422) from e

        schema = data.schema if isinstance(data, TabularData) else None
        if hasattr(plugin, "validate"):
            try:
                errs = plugin.validate(spec, schema=schema)  # type: ignore[call-arg]
            except TypeError:
                errs = plugin.validate(spec)  # type: ignore[arg-type]
            if errs:
                raise EngineError(code="VALIDATION_FAILED",
                                  message=_format_errors(list(errs)),
                                  http_status=400)

        result = await plugin.analyze(data, dict(spec.options))
        return {"kind": result.kind, "payload": result.payload, "warnings": list(result.warnings)}

    def _apply_filter(self, data: TabularData | TreeData, filter_spec: dict) -> TabularData | TreeData:
        if not isinstance(data, TabularData):
            raise EngineError(code="NOT_TABULAR", message="filter step requires tabular data",
                              http_status=422)
        kind = filter_spec.get("kind")
        if not isinstance(kind, str):
            raise EngineError(code="VALIDATION_FAILED", message="filter.kind must be a string",
                              http_status=400)
        try:
            plugin = self.registry.get_filter(kind)
        except KeyError as e:
            raise EngineError(code="UNKNOWN_FILTER", message=f"no filter for kind={kind}",
                              http_status=422) from e
        if kind == "column":
            errs = plugin.validate(filter_spec)  # type: ignore[arg-type]
            if errs:
                raise EngineError(code="VALIDATION_FAILED",
                                  message=_format_errors(list(errs)), http_status=400)
            return plugin.apply(data, filter_spec)  # type: ignore[arg-type]
        try:
            dc_spec = parse_filter_spec(filter_spec)
        except (ValueError, KeyError) as e:
            raise EngineError(code="VALIDATION_FAILED", message=str(e), http_status=400) from e
        try:
            errs = plugin.validate(dc_spec, schema=data.schema)  # type: ignore[call-arg,arg-type]
        except TypeError:
            errs = plugin.validate(dc_spec)  # type: ignore[arg-type]
        if errs:
            raise EngineError(code="VALIDATION_FAILED",
                              message=_format_errors(list(errs)), http_status=400)
        return plugin.apply(data, dc_spec)  # type: ignore[arg-type]


__all__ = ["AnalysisService"]
