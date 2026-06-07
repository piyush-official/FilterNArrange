"""chart_suggest analysis plugin — schema-driven Vega-Lite suggestions."""
from __future__ import annotations
from typing import Optional

from filternarrange_engine.core.analysis import AnalysisResult, AnalysisSpec
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.plugin_protocols import FilterManifest, load_manifest
from filternarrange_engine.core.types import TypeTag


NUMERIC = {TypeTag.NUMBER, TypeTag.INTEGER}
TEMPORAL = {TypeTag.DATETIME}
CATEGORICAL = {TypeTag.STRING, TypeTag.BOOLEAN}


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

        # Drain the async iterator so the caller's loop is not held open.
        async for _row in data.rows:
            break

        charts.sort(key=lambda c: c["score"], reverse=True)
        return AnalysisResult(kind="chart_suggest", payload={"charts": charts}, warnings=[])

    def validate(self, spec: AnalysisSpec, schema: Optional[list[Column]] = None) -> list[str]:
        return []


plugin = _ChartSuggestPlugin()
