import pytest

from filternarrange_engine.adapters.llm.mock import MockLLMProvider
from filternarrange_engine.core.llm import SchemaValidationError
from filternarrange_ai_nl_to_filter.plugin import NlToFilterCapability


@pytest.mark.asyncio
async def test_returns_filter_spec_for_simple_query():
    llm = MockLLMProvider(
        structured_response={
            "filter_spec": {
                "kind": "row",
                "predicate": {"op": "gt", "column": "age", "value": 18},
            },
            "confidence": 0.92,
        }
    )
    cap = NlToFilterCapability()
    out = await cap.run(
        llm,
        {
            "query": "show rows where age is greater than 18",
            "schema": [{"name": "age", "type": "integer"}],
        },
    )
    assert out["filter_spec"]["kind"] == "row"
    assert 0.0 <= out["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_rejects_unknown_filter_kind():
    llm = MockLLMProvider(
        structured_response={
            "filter_spec": {"kind": "telepathy", "predicate": {}},
            "confidence": 0.5,
        }
    )
    cap = NlToFilterCapability()
    with pytest.raises(SchemaValidationError):
        await cap.run(llm, {"query": "x", "schema": []})


@pytest.mark.asyncio
async def test_uses_correct_model_setting():
    cap = NlToFilterCapability()
    assert cap.default_model_setting == "nl_to_filter"
    assert cap.name == "nl_to_filter"
