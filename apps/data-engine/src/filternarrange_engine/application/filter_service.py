"""Filter orchestration: detect → parse → filter → collect N rows.

Plan B shipped this against a single Plan-B-style filter-column plugin whose
spec is a TypedDict and whose validate() returns ValidationError dataclasses.
Plan C extends with row / expression / regex plugins whose specs are
dataclasses (`core.filter_spec.{ColumnSpec,RowSpec,ExpressionSpec,RegexSpec}`)
and whose validate() returns list[str] and is schema-aware.

This dispatcher handles both:

- kind == "column" → Plan B legacy: pass the raw dict through filter-column
- otherwise → parse to FilterSpec dataclass and dispatch to the kind plugin
"""
from __future__ import annotations
import asyncio
import io as _io
from typing import Any, Protocol, cast

from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.core.canonical import TabularData
from filternarrange_engine.core.filter_spec import parse_filter_spec
from filternarrange_engine.core.plugin_api import ColumnFilterSpec
from filternarrange_engine.platform.errors import EngineError


class _Store(Protocol):
    def get(self, ref: str): ...


def _format_errors(errs: list[Any]) -> str:
    """Render validate() output regardless of whether it's strings or
    Plan B ValidationError dataclasses."""
    rendered: list[str] = []
    for e in errs:
        if hasattr(e, "field") and hasattr(e, "message"):
            rendered.append(f"{e.field}: {e.message}")
        else:
            rendered.append(str(e))
    return "; ".join(rendered)


class FilterService:
    def __init__(self, store: _Store, registry: PluginRegistry):
        self.store = store
        self.registry = registry

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
        if not isinstance(kind, str):
            raise EngineError(code="VALIDATION_FAILED", message="filter.kind must be a string", http_status=400)
        try:
            filter_plugin = self.registry.get_filter(kind)
        except KeyError as e:
            raise EngineError(code="UNKNOWN_FILTER", message=f"no filter for kind={kind}",
                              http_status=422) from e

        if kind == "column":
            # Plan B legacy: filter-column expects ColumnFilterSpec (TypedDict)
            typed_spec = cast(ColumnFilterSpec, spec)
            errs = filter_plugin.validate(typed_spec)
            if errs:
                raise EngineError(
                    code="VALIDATION_FAILED",
                    message=_format_errors(list(errs)),
                    http_status=400,
                )
            filtered = filter_plugin.apply(parsed, typed_spec)
        else:
            # Plan C: parse into dataclass and call validate with schema
            try:
                dc_spec = parse_filter_spec(spec)
            except (ValueError, KeyError) as e:
                raise EngineError(code="VALIDATION_FAILED", message=str(e), http_status=400) from e
            try:
                errs = filter_plugin.validate(dc_spec, schema=parsed.schema)  # type: ignore[call-arg,arg-type]
            except TypeError:
                errs = filter_plugin.validate(dc_spec)  # type: ignore[arg-type]
            if errs:
                raise EngineError(
                    code="VALIDATION_FAILED",
                    message=_format_errors(list(errs)),
                    http_status=400,
                )
            filtered = filter_plugin.apply(parsed, dc_spec)  # type: ignore[arg-type]

        assert isinstance(filtered, TabularData), "filter must return tabular data"

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
