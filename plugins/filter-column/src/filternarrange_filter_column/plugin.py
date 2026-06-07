"""Column-projection filter plugin."""
from __future__ import annotations
from typing import Union

from filternarrange_engine.core.canonical import Column, TabularData, TreeData
from filternarrange_engine.core.plugin_api import (
    FilterManifest, FilterSpec, ValidationError,
)


class _ColumnFilter:
    manifest = FilterManifest(
        id="filter-column",
        display_name="Column projection",
        version="1.0.0",
        license="Apache-2.0",
        author="FilterNArrange Core",
        kinds=["column"],
    )

    def apply(self, data: Union[TabularData, TreeData], spec: FilterSpec) -> TabularData:
        if not isinstance(data, TabularData):
            raise ValueError("filter-column requires TabularData input")
        keep = list(spec["keep"])
        keep_set = set(keep)
        new_schema = [c for c in data.schema if c.name in keep_set]
        # preserve user-requested order
        order_map = {name: i for i, name in enumerate(keep)}
        new_schema.sort(key=lambda c: order_map.get(c.name, 1_000_000))

        async def project():
            async for row in data.rows:
                yield {k: row[k] for k in keep if k in row}

        return TabularData(schema=new_schema, rows=project(), meta=data.meta)

    def validate(self, spec: FilterSpec) -> list[ValidationError]:
        errs: list[ValidationError] = []
        kind = spec.get("kind") if isinstance(spec, dict) else None
        if kind is None:
            errs.append(ValidationError(field="kind", message="kind is required"))
        elif kind != "column":
            errs.append(ValidationError(field="kind", message=f"unsupported kind '{kind}'"))
        keep = spec.get("keep") if isinstance(spec, dict) else None
        if not keep or not isinstance(keep, list):
            errs.append(ValidationError(field="keep", message="keep must be a non-empty list of column names"))
        return errs

    def explain(self, spec: FilterSpec) -> str:
        keep = spec.get("keep", [])
        return f"keep columns: {', '.join(keep)}"


plugin = _ColumnFilter()
