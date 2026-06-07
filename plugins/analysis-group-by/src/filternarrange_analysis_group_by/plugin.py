"""group_by analysis plugin — dict-shaped rows."""
from __future__ import annotations
import statistics
from collections import defaultdict
from typing import Optional

from filternarrange_engine.core.analysis import AnalysisResult, AnalysisSpec
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.plugin_protocols import FilterManifest, load_manifest


_AGGS = {
    "sum":    lambda vs: sum(vs),
    "count":  lambda vs: len(vs),
    "avg":    lambda vs: statistics.fmean(vs) if vs else 0,
    "min":    lambda vs: min(vs) if vs else None,
    "max":    lambda vs: max(vs) if vs else None,
    "median": lambda vs: statistics.median(vs) if vs else None,
}


class _GroupByPlugin:
    manifest: FilterManifest = load_manifest(__file__, "../../manifest.toml")  # type: ignore[assignment]

    async def analyze(self, data: TabularData, options: dict) -> AnalysisResult:
        by: list[str] = list(options.get("by", []))
        agg: dict[str, list[str]] = dict(options.get("agg", {}))

        buckets: dict[tuple, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        async for row in data.rows:
            key = tuple(row.get(b) for b in by)
            for col, fns in agg.items():
                v = row.get(col)
                if v is None:
                    continue
                try:
                    buckets[key][col].append(float(v))
                except (TypeError, ValueError):
                    if "count" in fns:
                        buckets[key][col].append(v)

        groups: list[dict] = []
        for key, cols in buckets.items():
            entry: dict = dict(zip(by, key))
            for col, fns in agg.items():
                vs = cols.get(col, [])
                numeric_vs = [v for v in vs if isinstance(v, (int, float))]
                for fn in fns:
                    if fn == "count":
                        entry[f"{col}_count"] = len(vs)
                    elif fn in _AGGS:
                        entry[f"{col}_{fn}"] = _AGGS[fn](numeric_vs)
                    else:
                        entry[f"{col}_{fn}"] = None
            groups.append(entry)

        return AnalysisResult(kind="group_by", payload={"groups": groups}, warnings=[])

    def validate(self, spec: AnalysisSpec, schema: Optional[list[Column]] = None) -> list[str]:
        errors: list[str] = []
        opts = spec.options
        if "by" not in opts or not opts["by"]:
            errors.append("group_by requires non-empty 'by'")
        if schema is not None:
            names = {c.name for c in schema}
            for col in opts.get("by", []):
                if col not in names:
                    errors.append(f"unknown column in 'by': {col!r}")
            for col in opts.get("agg", {}):
                if col not in names:
                    errors.append(f"unknown column in 'agg': {col!r}")
        for col, fns in opts.get("agg", {}).items():
            for fn in fns:
                if fn not in _AGGS:
                    errors.append(f"unknown aggregator: {fn!r}")
        return errors


plugin = _GroupByPlugin()
