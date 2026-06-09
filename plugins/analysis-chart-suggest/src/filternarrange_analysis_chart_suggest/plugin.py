"""chart_suggest analysis plugin — schema-driven Vega-Lite suggestions."""
from __future__ import annotations
from collections import defaultdict
from typing import Any, Optional

from filternarrange_engine.core.analysis import AnalysisResult, AnalysisSpec
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.plugin_protocols import FilterManifest, load_manifest
from filternarrange_engine.core.types import TypeTag


NUMERIC = {TypeTag.NUMBER, TypeTag.INTEGER}
TEMPORAL = {TypeTag.DATETIME}
CATEGORICAL = {TypeTag.STRING, TypeTag.BOOLEAN}

# Cap raw-pair series so we don't ship megabytes of JSON or wedge the
# ECharts renderer on a 100k-row table.
SCATTER_SAMPLE_LIMIT = 1000


def _vl(mark: str, x: str, y: str, score: float, rationale: str,
        x_type: str, y_type: str) -> dict:
    return {
        "mark": mark,
        "score": score,
        "rationale": rationale,
        "spec": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": mark,
            "encoding": {
                "x": {"field": x, "type": x_type},
                "y": {"field": y, "type": y_type},
            },
        },
    }


def _aggregate(mark: str, x_field: str, y_field: str, rows: list[dict]) -> list[list[Any]]:
    """Compute the series data for a chart spec from the buffered rows.

    bar     → sum(y) grouped by x; missing values dropped
    line    → (x, y) pairs sorted by x; missing values dropped
    point   → raw (x, y) pairs, capped at SCATTER_SAMPLE_LIMIT
    """
    if mark == "bar":
        sums: dict[Any, float] = defaultdict(float)
        for r in rows:
            x = r.get(x_field)
            y = r.get(y_field)
            if x is None or y is None:
                continue
            sums[x] += float(y)
        return [[k, v] for k, v in sums.items()]

    if mark == "line":
        pairs = [
            [r[x_field], r[y_field]]
            for r in rows
            if r.get(x_field) is not None and r.get(y_field) is not None
        ]
        pairs.sort(key=lambda p: p[0])
        return pairs

    # scatter (point)
    out: list[list[Any]] = []
    for r in rows:
        x = r.get(x_field)
        y = r.get(y_field)
        if x is None or y is None:
            continue
        out.append([x, y])
        if len(out) >= SCATTER_SAMPLE_LIMIT:
            break
    return out


class _ChartSuggestPlugin:
    manifest: FilterManifest = load_manifest(__file__, "../../manifest.toml")  # type: ignore[assignment]

    async def analyze(self, data: TabularData, options: dict) -> AnalysisResult:
        cols = data.schema
        charts: list[dict] = []
        for i, a in enumerate(cols):
            for b in cols[i + 1:]:
                if a.type in TEMPORAL and b.type in NUMERIC:
                    charts.append(_vl("line", a.name, b.name, 0.95, "temporal × numeric → line", "temporal", "quantitative"))
                elif b.type in TEMPORAL and a.type in NUMERIC:
                    charts.append(_vl("line", b.name, a.name, 0.95, "temporal × numeric → line", "temporal", "quantitative"))
                elif a.type in CATEGORICAL and b.type in NUMERIC:
                    charts.append(_vl("bar", a.name, b.name, 0.85, "categorical × numeric → bar", "nominal", "quantitative"))
                elif b.type in CATEGORICAL and a.type in NUMERIC:
                    charts.append(_vl("bar", b.name, a.name, 0.85, "categorical × numeric → bar", "nominal", "quantitative"))
                elif a.type in NUMERIC and b.type in NUMERIC:
                    charts.append(_vl("point", a.name, b.name, 0.7, "two numerics → scatter", "quantitative", "quantitative"))

        # Buffer rows once so we can aggregate per-spec without re-reading
        # the source. For very wide tables the bar/line group-by could be
        # streamed, but for the upload sizes this plugin targets (a few MB
        # canonical TabularData) the simple buffer is fine.
        rows: list[dict] = [r async for r in data.rows]

        for c in charts:
            enc = c["spec"]["encoding"]
            c["data"] = _aggregate(c["mark"], enc["x"]["field"], enc["y"]["field"], rows)

        charts.sort(key=lambda c: c["score"], reverse=True)
        return AnalysisResult(kind="chart_suggest", payload={"charts": charts}, warnings=[])

    def validate(self, spec: AnalysisSpec, schema: Optional[list[Column]] = None) -> list[str]:
        return []


plugin = _ChartSuggestPlugin()
