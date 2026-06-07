import pytest

from filternarrange_engine.adapters.llm.mock import MockLLMProvider
from filternarrange_engine.core.llm import SchemaValidationError
from filternarrange_ai_auto_summary.plugin import AutoSummaryCapability


@pytest.mark.asyncio
async def test_returns_summary_and_observations():
    llm = MockLLMProvider(
        structured_response={
            "summary": "120 users mostly in IN.",
            "key_observations": ["age range 18-34", "country = IN dominates"],
        }
    )
    cap = AutoSummaryCapability()
    out = await cap.run(
        llm,
        {
            "schema": [
                {"name": "id", "type": "integer"},
                {"name": "country", "type": "string"},
            ],
            "sample_rows": [{"id": 1, "country": "IN"}],
            "total_rows": 120,
            "total_size_bytes": 4823,
        },
    )
    assert out["summary"] == "120 users mostly in IN."
    assert len(out["key_observations"]) == 2


@pytest.mark.asyncio
async def test_rejects_bad_schema_response():
    llm = MockLLMProvider(structured_response={"summary": "ok"})
    cap = AutoSummaryCapability()
    with pytest.raises(SchemaValidationError):
        await cap.run(
            llm,
            {
                "schema": [],
                "sample_rows": [],
                "total_rows": 0,
                "total_size_bytes": 0,
            },
        )


def test_manifest_fields():
    cap = AutoSummaryCapability()
    assert cap.name == "auto_summary"
    assert cap.required_tier in ("free", "paid")
    assert cap.default_model_setting == "auto_summary"
