import pytest

from filternarrange_engine.adapters.llm.mock import MockLLMProvider
from filternarrange_engine.core.llm import SchemaValidationError


@pytest.mark.asyncio
async def test_returns_canned_text():
    llm = MockLLMProvider(text_response="hello world")
    out = await llm.complete("anything")
    assert out == "hello world"


@pytest.mark.asyncio
async def test_returns_canned_structured():
    llm = MockLLMProvider(
        structured_response={"summary": "ok", "key_observations": []}
    )
    out = await llm.complete("p", schema={"type": "object"})
    assert out == {"summary": "ok", "key_observations": []}


@pytest.mark.asyncio
async def test_validates_against_schema():
    llm = MockLLMProvider(structured_response={"wrong": True})
    schema = {
        "type": "object",
        "required": ["summary"],
        "properties": {"summary": {"type": "string"}},
    }
    with pytest.raises(SchemaValidationError):
        await llm.complete("p", schema=schema)


@pytest.mark.asyncio
async def test_records_calls():
    llm = MockLLMProvider(text_response="x")
    await llm.complete("a", model="llama3.1:8b")
    await llm.complete("b", model="qwen2.5:7b")
    assert [c.prompt for c in llm.calls] == ["a", "b"]
    assert [c.model for c in llm.calls] == ["llama3.1:8b", "qwen2.5:7b"]


@pytest.mark.asyncio
async def test_embed_returns_canned():
    llm = MockLLMProvider(embed_response=[[0.1, 0.2]])
    vecs = await llm.embed(["a"])
    assert vecs == [[0.1, 0.2]]
