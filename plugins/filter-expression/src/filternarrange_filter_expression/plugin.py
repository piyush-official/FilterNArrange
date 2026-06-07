"""filter-expression plugin entry-point."""
from __future__ import annotations
from typing import Callable, Optional

from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.filter_spec import ExpressionSpec
from filternarrange_engine.core.plugin_protocols import FilterManifest, load_manifest

from .apply import apply as _apply, register_function as _register_function, registered_functions as _registered_functions
from .validate import validate as _validate


class _ExpressionFilterPlugin:
    manifest: FilterManifest = load_manifest(__file__, "../../manifest.toml")  # type: ignore[assignment]

    def apply(self, data: TabularData, spec: ExpressionSpec) -> TabularData:
        return _apply(data, spec)

    def validate(self, spec: ExpressionSpec, schema: Optional[list[Column]] = None) -> list[str]:
        return _validate(spec, schema)

    def register_function(self, name: str, fn: Callable, signature: str) -> None:
        _register_function(name, fn, signature)

    def registered_functions(self) -> dict[str, str]:
        return _registered_functions()

    def explain(self, spec: ExpressionSpec) -> str:
        return f"keep rows matching expression: {spec.expr}"


plugin = _ExpressionFilterPlugin()
