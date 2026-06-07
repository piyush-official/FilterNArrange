import pytest

from filternarrange_engine.adapters.llm.mock import MockLLMProvider
from filternarrange_engine.core.llm import SchemaValidationError
from filternarrange_ai_anomaly_detect.plugin import AnomalyDetectCapability


@pytest.mark.asyncio
async def test_returns_findings():
    llm = MockLLMProvider(
        structured_response={
            "findings": [
                {
                    "kind": "missing_values",
                    "column": "email",
                    "severity": "medium",
                    "description": "30% nulls in email",
                    "suggested_action": "drop rows or coerce",
                },
                {
                    "kind": "outlier",
                    "column": "amount",
                    "severity": "high",
                    "description": "row 42 amount=1e9 vs median=42",
                },
            ]
        }
    )
    cap = AnomalyDetectCapability()
    out = await cap.run(
        llm,
        {
            "schema": [
                {"name": "email", "type": "string"},
                {"name": "amount", "type": "integer"},
            ],
            "sample_rows": [{"email": None, "amount": 1_000_000_000}],
            "summary_stats": {
                "amount": {"min": 1, "max": 1_000_000_000, "median": 42}
            },
        },
    )
    assert len(out["findings"]) == 2
    assert out["findings"][0]["kind"] == "missing_values"


@pytest.mark.asyncio
async def test_rejects_unknown_kind():
    llm = MockLLMProvider(
        structured_response={
            "findings": [
                {"kind": "aliens", "severity": "low", "description": "x"}
            ]
        }
    )
    cap = AnomalyDetectCapability()
    with pytest.raises(SchemaValidationError):
        await cap.run(
            llm, {"schema": [], "sample_rows": [], "summary_stats": {}}
        )


@pytest.mark.asyncio
async def test_empty_findings_ok():
    llm = MockLLMProvider(structured_response={"findings": []})
    cap = AnomalyDetectCapability()
    out = await cap.run(
        llm, {"schema": [], "sample_rows": [], "summary_stats": {}}
    )
    assert out["findings"] == []
