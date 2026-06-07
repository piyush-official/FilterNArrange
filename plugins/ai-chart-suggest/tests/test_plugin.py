import pytest

from filternarrange_engine.adapters.llm.mock import MockLLMProvider
from filternarrange_engine.core.llm import SchemaValidationError
from filternarrange_ai_chart_suggest.plugin import ChartSuggestCapability


@pytest.mark.asyncio
async def test_returns_recommended_chart():
    llm = MockLLMProvider(
        structured_response={
            "recommended_chart": {
                "kind": "bar",
                "x": "country",
                "y": "count",
                "justification": "Categorical x with numeric aggregation reads best as bars.",
            }
        }
    )
    cap = ChartSuggestCapability()
    out = await cap.run(
        llm,
        {
            "schema": [
                {"name": "country", "type": "string"},
                {"name": "count", "type": "integer"},
            ],
            "cardinality_per_column": {"country": 12, "count": 220},
        },
    )
    assert out["recommended_chart"]["kind"] == "bar"
    assert out["recommended_chart"]["justification"]


@pytest.mark.asyncio
async def test_rejects_unknown_chart_kind():
    llm = MockLLMProvider(
        structured_response={
            "recommended_chart": {"kind": "circles", "justification": "uh"}
        }
    )
    cap = ChartSuggestCapability()
    with pytest.raises(SchemaValidationError):
        await cap.run(llm, {"schema": [], "cardinality_per_column": {}})


def test_manifest_fields():
    cap = ChartSuggestCapability()
    assert cap.name == "chart_suggest"
    assert cap.default_model_setting == "chart_suggest"
