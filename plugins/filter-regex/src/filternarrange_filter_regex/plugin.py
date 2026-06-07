"""filter-regex plugin entry-point."""
from __future__ import annotations
from typing import Optional

from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.filter_spec import RegexSpec
from filternarrange_engine.core.plugin_protocols import FilterManifest, load_manifest

from .apply import apply as _apply
from .validate import validate as _validate


class _RegexFilterPlugin:
    manifest: FilterManifest = load_manifest(__file__, "../../manifest.toml")  # type: ignore[assignment]

    def apply(self, data: TabularData, spec: RegexSpec) -> TabularData:
        return _apply(data, spec)

    def validate(self, spec: RegexSpec, schema: Optional[list[Column]] = None) -> list[str]:
        return _validate(spec, schema)

    def explain(self, spec: RegexSpec) -> str:
        flags = ",".join(spec.flags) or "—"
        return f"keep rows where any string col matches /{spec.pattern}/ (flags: {flags})"


plugin = _RegexFilterPlugin()
