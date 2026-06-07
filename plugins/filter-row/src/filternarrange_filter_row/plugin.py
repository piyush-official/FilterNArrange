"""filter-row plugin entry-point."""
from __future__ import annotations
from typing import Optional

from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.filter_spec import RowSpec
from filternarrange_engine.core.plugin_protocols import FilterManifest, load_manifest

from .apply import apply as _apply
from .validate import validate as _validate


class _RowFilterPlugin:
    manifest: FilterManifest = load_manifest(__file__, "../../manifest.toml")  # type: ignore[assignment]

    def apply(self, data: TabularData, spec: RowSpec) -> TabularData:
        return _apply(data, spec)

    def validate(self, spec: RowSpec, schema: Optional[list[Column]] = None) -> list[str]:
        return _validate(spec, schema)

    def explain(self, spec: RowSpec) -> str:
        p = spec.predicate
        return f"keep rows where {p.col} {p.op} {p.value!r}"


plugin = _RowFilterPlugin()
