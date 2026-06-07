"""summary_stats analysis plugin — works on dict-shaped TabularData rows."""
from __future__ import annotations
import statistics
from collections import Counter
from typing import Optional

from filternarrange_engine.core.analysis import AnalysisResult, AnalysisSpec
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.plugin_protocols import FilterManifest, load_manifest
from filternarrange_engine.core.types import TypeTag


NUMERIC = {TypeTag.NUMBER, TypeTag.INTEGER}


class _SummaryStatsPlugin:
    manifest: FilterManifest = load_manifest(__file__, "../../manifest.toml")  # type: ignore[assignment]

    async def analyze(self, data: TabularData, options: dict) -> AnalysisResult:
        top_n = int(options.get("top_n", 10))
        per_col: dict[str, dict] = {
            c.name: {"count": 0, "nulls": 0, "values": []} for c in data.schema
        }
        async for row in data.rows:
            for c in data.schema:
                v = row.get(c.name)
                if v is None or v == "":
                    per_col[c.name]["nulls"] += 1
                else:
                    per_col[c.name]["count"] += 1
                    per_col[c.name]["values"].append(v)

        out_cols: list[dict] = []
        for c in data.schema:
            bucket = per_col[c.name]
            values = bucket["values"]
            entry = {
                "name": c.name,
                "type": c.type.name.lower(),
                "count": bucket["count"],
                "nulls": bucket["nulls"],
                "distinct": len(set(values)) if all(_hashable(v) for v in values) else len(values),
            }
            if c.type in NUMERIC and values:
                nums = [float(v) for v in values if v is not None]
                if nums:
                    entry["min"] = min(nums)
                    entry["max"] = max(nums)
                    entry["mean"] = statistics.fmean(nums)
                    entry["median"] = statistics.median(nums)
                    entry["stddev"] = statistics.pstdev(nums) if len(nums) > 1 else 0.0
            else:
                top = Counter(values).most_common(top_n) if all(_hashable(v) for v in values) else []
                entry["top"] = [{"value": v, "count": n} for v, n in top]
            out_cols.append(entry)

        return AnalysisResult(kind="summary_stats", payload={"columns": out_cols}, warnings=[])

    def validate(self, spec: AnalysisSpec, schema: Optional[list[Column]] = None) -> list[str]:
        return []


def _hashable(v) -> bool:
    try:
        hash(v)
        return True
    except TypeError:
        return False


plugin = _SummaryStatsPlugin()
