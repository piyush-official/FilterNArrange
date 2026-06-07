import json

import httpx
import pytest
import respx
from httpx import Response

from filternarrange_engine.adapters.llm.ollama import OllamaProvider
from filternarrange_engine.core.llm import LLMTimeoutError, SchemaValidationError


@pytest.mark.asyncio
@respx.mock
async def test_complete_text():
    route = respx.post("http://ollama:11434/api/generate").mock(
        return_value=Response(200, json={"response": "hello", "done": True})
    )
    async with OllamaProvider(base_url="http://ollama:11434", timeout_seconds=30) as p:
        out = await p.complete("hi", model="llama3.1:8b")
    assert out == "hello"
    assert route.called
    req = json.loads(route.calls[0].request.content)
    assert req["model"] == "llama3.1:8b"
    assert req["prompt"] == "hi"
    assert req["stream"] is False
    assert req["options"]["temperature"] == 0


@pytest.mark.asyncio
@respx.mock
async def test_complete_structured_returns_parsed_dict():
    respx.post("http://ollama:11434/api/generate").mock(
        return_value=Response(
            200,
            json={
                "response": '{"summary": "ok", "key_observations": []}',
                "done": True,
            },
        )
    )
    schema = {
        "type": "object",
        "required": ["summary", "key_observations"],
        "properties": {
            "summary": {"type": "string"},
            "key_observations": {"type": "array", "items": {"type": "string"}},
        },
    }
    async with OllamaProvider(base_url="http://ollama:11434", timeout_seconds=30) as p:
        out = await p.complete("prompt", schema=schema, model="llama3.1:8b")
    assert out == {"summary": "ok", "key_observations": []}


@pytest.mark.asyncio
@respx.mock
async def test_complete_structured_validates_and_raises_on_bad_schema():
    respx.post("http://ollama:11434/api/generate").mock(
        return_value=Response(
            200, json={"response": '{"wrong": true}', "done": True}
        )
    )
    schema = {
        "type": "object",
        "required": ["summary"],
        "properties": {"summary": {"type": "string"}},
    }
    async with OllamaProvider(base_url="http://ollama:11434", timeout_seconds=30) as p:
        with pytest.raises(SchemaValidationError):
            await p.complete("p", schema=schema)


@pytest.mark.asyncio
@respx.mock
async def test_complete_structured_raises_on_non_json_response():
    respx.post("http://ollama:11434/api/generate").mock(
        return_value=Response(
            200, json={"response": "not json at all", "done": True}
        )
    )
    async with OllamaProvider(base_url="http://ollama:11434", timeout_seconds=30) as p:
        with pytest.raises(SchemaValidationError):
            await p.complete("p", schema={"type": "object"})


@pytest.mark.asyncio
@respx.mock
async def test_structured_sets_format_json():
    route = respx.post("http://ollama:11434/api/generate").mock(
        return_value=Response(200, json={"response": "{}", "done": True})
    )
    async with OllamaProvider(base_url="http://ollama:11434", timeout_seconds=30) as p:
        await p.complete("p", schema={"type": "object"})
    body = json.loads(route.calls[0].request.content)
    assert body["format"] == "json"


@pytest.mark.asyncio
@respx.mock
async def test_timeout_maps_to_llm_timeout_error():
    respx.post("http://ollama:11434/api/generate").mock(
        side_effect=httpx.TimeoutException("slow")
    )
    async with OllamaProvider(base_url="http://ollama:11434", timeout_seconds=1) as p:
        with pytest.raises(LLMTimeoutError):
            await p.complete("p")


@pytest.mark.asyncio
@respx.mock
async def test_embed_returns_list_of_vectors():
    respx.post("http://ollama:11434/api/embeddings").mock(
        side_effect=[
            Response(200, json={"embedding": [0.1, 0.2]}),
            Response(200, json={"embedding": [0.3, 0.4]}),
        ]
    )
    async with OllamaProvider(base_url="http://ollama:11434", timeout_seconds=30) as p:
        vecs = await p.embed(["a", "b"], model="llama3.1:8b")
    assert vecs == [[0.1, 0.2], [0.3, 0.4]]
