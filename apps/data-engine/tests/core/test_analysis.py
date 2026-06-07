from filternarrange_engine.core.analysis import (
    AnalysisSpec, AnalysisResult, parse_analysis_spec,
)


def test_parse_analysis_spec_summary():
    spec = parse_analysis_spec({"kind": "summary_stats", "options": {}})
    assert isinstance(spec, AnalysisSpec)
    assert spec.kind == "summary_stats"
    assert spec.options == {}


def test_analysis_result_envelope():
    res = AnalysisResult(kind="summary_stats", payload={"rows": 100}, warnings=[])
    assert res.kind == "summary_stats"
    assert res.payload["rows"] == 100
