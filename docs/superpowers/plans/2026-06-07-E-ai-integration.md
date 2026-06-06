# Plan E — AI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up the four AI capabilities (NL→filter, auto-summary, chart-suggest, anomaly-detect) on top of a local Ollama runtime, exposed via data-engine HTTP endpoints, gateway pass-through, and a frontend AI UI — all OSS, all local, all plugin-driven.

**Architecture:** A small `LLMProvider` Protocol with one concrete `OllamaProvider` (httpx-async, structured-output via `format: json`). Each AI capability is its own pip-installable plugin under `plugins/ai-*/`, discovered via the `filternarrange.ai_capabilities` entry-point group. A registry composes them, a shared semaphore caps concurrent LLM calls, Redis caches deterministic results, and FastAPI routes them. The gateway adds thin pass-throughs under `/api/v1/ai/*`; the frontend gets a 5th filter mode ("AI Filter"), auto-runs summary + chart suggestion on upload, and surfaces anomalies in a dedicated tab.

**Tech Stack:** Python 3.12, FastAPI, httpx async, Ollama HTTP API (`/api/generate`), pydantic v2, jsonschema, redis-py async, pytest + pytest-asyncio, respx (HTTP mock), Spring Boot 3 + WebClient, React + TypeScript + Vite, Vitest, Playwright.

---

## File Structure

**Data-engine (Python):**
- Create `apps/data-engine/src/filternarrange_engine/core/llm.py` — `LLMProvider` Protocol + `AICapability` Protocol + canonical IO types.
- Create `apps/data-engine/src/filternarrange_engine/adapters/llm/__init__.py`
- Create `apps/data-engine/src/filternarrange_engine/adapters/llm/ollama.py` — `OllamaProvider`.
- Create `apps/data-engine/src/filternarrange_engine/adapters/llm/mock.py` — `MockLLMProvider` for tests.
- Create `apps/data-engine/src/filternarrange_engine/adapters/llm/cache.py` — Redis cache wrapper.
- Create `apps/data-engine/src/filternarrange_engine/adapters/llm/registry.py` — capability discovery + dispatch.
- Create `apps/data-engine/src/filternarrange_engine/application/ai_orchestrator.py` — semaphore-bounded runner.
- Create `apps/data-engine/src/filternarrange_engine/api/ai_routes.py` — FastAPI router for `/ai/*`.
- Modify `apps/data-engine/src/filternarrange_engine/api/__init__.py` — register the new router.
- Modify `apps/data-engine/src/filternarrange_engine/platform/config.py` — add AI env settings.

**Plugins (each its own pip-installable sub-package):**
- Create `plugins/ai-nl-to-filter/{pyproject.toml,manifest.toml,src/filternarrange_ai_nl_to_filter/{__init__.py,plugin.py,prompts.py,schema.py},tests/test_plugin.py}`
- Create `plugins/ai-auto-summary/{pyproject.toml,manifest.toml,src/filternarrange_ai_auto_summary/{__init__.py,plugin.py,prompts.py,schema.py},tests/test_plugin.py}`
- Create `plugins/ai-chart-suggest/{pyproject.toml,manifest.toml,src/filternarrange_ai_chart_suggest/{__init__.py,plugin.py,prompts.py,schema.py},tests/test_plugin.py}`
- Create `plugins/ai-anomaly-detect/{pyproject.toml,manifest.toml,src/filternarrange_ai_anomaly_detect/{__init__.py,plugin.py,prompts.py,schema.py},tests/test_plugin.py}`

**Gateway (Java):**
- Create `apps/gateway/src/main/java/io/filternarrange/gateway/api/AiController.java`
- Create `apps/gateway/src/main/java/io/filternarrange/gateway/application/AiService.java`
- Create `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/http/DataEngineAiClient.java`
- Modify `contracts/openapi/gateway-public.v1.yaml` (additive `/api/v1/ai/*` paths)
- Create `apps/gateway/src/test/java/io/filternarrange/gateway/api/AiControllerTest.java`

**Frontend (TypeScript):**
- Create `apps/frontend/src/features/ai/api.ts`
- Create `apps/frontend/src/features/ai/state.ts`
- Create `apps/frontend/src/features/ai/ui/AiFilterMode.tsx`
- Create `apps/frontend/src/features/ai/ui/AutoSummary.tsx`
- Create `apps/frontend/src/features/ai/ui/ChartSuggestion.tsx`
- Create `apps/frontend/src/features/ai/ui/AnomaliesPanel.tsx`
- Create `apps/frontend/src/features/ai/ui/AiUnavailable.tsx`
- Create `apps/frontend/src/features/ai/index.ts`
- Modify `apps/frontend/src/features/filter/ui/FilterModePicker.tsx` (add 5th tab)
- Modify `apps/frontend/src/pages/AnalyzePage.tsx` (Anomalies tab + auto summary)
- Create `apps/frontend/src/features/ai/__tests__/AiFilterMode.test.tsx`

**Tests (integration):**
- Create `tests/integration/test_ai_capabilities_real.py` (gated by `RUN_OLLAMA_TESTS=1`)

---

## Task 1: Settings and configuration scaffolding

**Files:**
- Modify: `apps/data-engine/src/filternarrange_engine/platform/config.py`
- Test: `apps/data-engine/tests/unit/platform/test_config_ai.py`

- [ ] **Step 1: Write the failing test**

Create `apps/data-engine/tests/unit/platform/test_config_ai.py`:

```python
import os
import pytest
from filternarrange_engine.platform.config import AiSettings, load_ai_settings


def test_defaults(monkeypatch):
    for k in ["AI_MAX_CONCURRENT", "OLLAMA_BASE_URL", "OLLAMA_TIMEOUT_SECONDS",
              "NL2FILTER_MODEL", "SUMMARY_MODEL", "CHART_MODEL", "ANOMALY_MODEL",
              "FILTERNARRANGE_DISABLED_AI", "AI_CACHE_TTL_SECONDS"]:
        monkeypatch.delenv(k, raising=False)
    s = load_ai_settings()
    assert s.max_concurrent == 4
    assert s.ollama_base_url == "http://ollama:11434"
    assert s.ollama_timeout_seconds == 30
    assert s.models["nl_to_filter"] == "qwen2.5:7b"
    assert s.models["auto_summary"] == "llama3.1:8b"
    assert s.models["chart_suggest"] == "llama3.1:8b"
    assert s.models["anomaly_detect"] == "llama3.1:8b"
    assert s.disabled == frozenset()
    assert s.cache_ttl_seconds == 3600


def test_disabled_parses_csv(monkeypatch):
    monkeypatch.setenv("FILTERNARRANGE_DISABLED_AI", "anomaly_detect, chart_suggest ")
    s = load_ai_settings()
    assert s.disabled == frozenset({"anomaly_detect", "chart_suggest"})


def test_overrides(monkeypatch):
    monkeypatch.setenv("AI_MAX_CONCURRENT", "8")
    monkeypatch.setenv("NL2FILTER_MODEL", "qwen2.5:14b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    s = load_ai_settings()
    assert s.max_concurrent == 8
    assert s.models["nl_to_filter"] == "qwen2.5:14b"
    assert s.ollama_base_url == "http://localhost:11434"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/data-engine && uv run pytest tests/unit/platform/test_config_ai.py -v
```

Expected: FAIL with `ImportError: cannot import name 'AiSettings'`.

- [ ] **Step 3: Write minimal implementation**

Append to `apps/data-engine/src/filternarrange_engine/platform/config.py`:

```python
import os
from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class AiSettings:
    max_concurrent: int
    ollama_base_url: str
    ollama_timeout_seconds: int
    models: Mapping[str, str]
    disabled: frozenset[str]
    cache_ttl_seconds: int


_DEFAULT_MODELS = {
    "nl_to_filter": "qwen2.5:7b",
    "auto_summary": "llama3.1:8b",
    "chart_suggest": "llama3.1:8b",
    "anomaly_detect": "llama3.1:8b",
}

_ENV_KEYS = {
    "nl_to_filter": "NL2FILTER_MODEL",
    "auto_summary": "SUMMARY_MODEL",
    "chart_suggest": "CHART_MODEL",
    "anomaly_detect": "ANOMALY_MODEL",
}


def load_ai_settings() -> AiSettings:
    models = {cap: os.environ.get(env, default) for cap, default in _DEFAULT_MODELS.items()
              for env in [_ENV_KEYS[cap]]}
    raw_disabled = os.environ.get("FILTERNARRANGE_DISABLED_AI", "")
    disabled = frozenset(x.strip() for x in raw_disabled.split(",") if x.strip())
    return AiSettings(
        max_concurrent=int(os.environ.get("AI_MAX_CONCURRENT", "4")),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"),
        ollama_timeout_seconds=int(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "30")),
        models=models,
        disabled=disabled,
        cache_ttl_seconds=int(os.environ.get("AI_CACHE_TTL_SECONDS", "3600")),
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/data-engine && uv run pytest tests/unit/platform/test_config_ai.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/platform/config.py \
        apps/data-engine/tests/unit/platform/test_config_ai.py
git commit -m "feat(data-engine): add AI settings loader"
```

---

## Task 2: Core LLMProvider + AICapability Protocols and canonical IO types

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/core/llm.py`
- Test: `apps/data-engine/tests/unit/core/test_llm_types.py`

- [ ] **Step 1: Write the failing test**

`apps/data-engine/tests/unit/core/test_llm_types.py`:

```python
from typing import get_type_hints
from filternarrange_engine.core.llm import (
    LLMProvider, AICapability, AIInput, AIOutput, JsonSchema, Vector,
    LLMError, SchemaValidationError,
)


def test_protocols_are_runtime_checkable():
    assert hasattr(LLMProvider, "__call__") is False  # not a function
    # AICapability must declare name + run
    assert "name" in AICapability.__annotations__
    assert "run" in AICapability.__dict__


def test_ai_input_output_serialize():
    inp = AIInput(capability="auto_summary", payload={"foo": 1})
    assert inp.payload == {"foo": 1}
    out = AIOutput(capability="auto_summary", result={"summary": "ok"})
    assert out.result == {"summary": "ok"}


def test_errors_are_exceptions():
    assert issubclass(LLMError, Exception)
    assert issubclass(SchemaValidationError, LLMError)


def test_vector_alias():
    v: Vector = [0.1, 0.2, 0.3]
    assert isinstance(v, list)


def test_json_schema_is_mapping():
    s: JsonSchema = {"type": "object"}
    assert s["type"] == "object"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/data-engine && uv run pytest tests/unit/core/test_llm_types.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write the module**

`apps/data-engine/src/filternarrange_engine/core/llm.py`:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


JsonSchema = Mapping[str, Any]
Vector = list[float]


class LLMError(Exception):
    """Base class for LLM provider errors."""


class SchemaValidationError(LLMError):
    """Raised when an LLM response fails JSON-schema validation."""


class LLMTimeoutError(LLMError):
    """Raised when an LLM call exceeds the configured timeout."""


@dataclass(frozen=True)
class AIInput:
    capability: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class AIOutput:
    capability: str
    result: Mapping[str, Any]
    model: str | None = None
    cache_hit: bool = False


@runtime_checkable
class LLMProvider(Protocol):
    async def complete(
        self, prompt: str, *, schema: JsonSchema | None = None,
        model: str | None = None, system: str | None = None,
    ) -> str | Mapping[str, Any]:
        """Run a completion. When schema is non-None, return a parsed
        dict validated against the schema; raise SchemaValidationError on bad
        output. When schema is None, return raw text."""
        ...

    async def embed(self, texts: Sequence[str], *, model: str | None = None) -> list[Vector]:
        ...


class AICapability(Protocol):
    name: str
    required_tier: str
    default_model_setting: str
    async def run(self, llm: LLMProvider, payload: Mapping[str, Any]) -> Mapping[str, Any]: ...
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/data-engine && uv run pytest tests/unit/core/test_llm_types.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/core/llm.py \
        apps/data-engine/tests/unit/core/test_llm_types.py
git commit -m "feat(data-engine): add LLMProvider and AICapability protocols"
```

---

## Task 3: MockLLMProvider for unit tests

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/adapters/llm/__init__.py` (empty marker)
- Create: `apps/data-engine/src/filternarrange_engine/adapters/llm/mock.py`
- Test: `apps/data-engine/tests/unit/adapters/llm/test_mock.py`

- [ ] **Step 1: Write the failing test**

`apps/data-engine/tests/unit/adapters/llm/test_mock.py`:

```python
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
    llm = MockLLMProvider(structured_response={"summary": "ok", "key_observations": []})
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/data-engine && uv run pytest tests/unit/adapters/llm/test_mock.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write the module**

`apps/data-engine/src/filternarrange_engine/adapters/llm/__init__.py`:

```python
```

`apps/data-engine/src/filternarrange_engine/adapters/llm/mock.py`:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, ValidationError

from filternarrange_engine.core.llm import (
    JsonSchema, LLMProvider, SchemaValidationError, Vector,
)


@dataclass
class _Call:
    prompt: str
    model: str | None
    schema: JsonSchema | None
    system: str | None


class MockLLMProvider:
    """Deterministic LLM provider for unit tests. Returns canned responses;
    optionally validates structured responses against the provided schema."""

    def __init__(
        self,
        *,
        text_response: str = "",
        structured_response: Mapping[str, Any] | None = None,
        embed_response: list[Vector] | None = None,
    ) -> None:
        self.text_response = text_response
        self.structured_response = structured_response
        self.embed_response = embed_response or []
        self.calls: list[_Call] = []

    async def complete(
        self, prompt: str, *, schema: JsonSchema | None = None,
        model: str | None = None, system: str | None = None,
    ) -> str | Mapping[str, Any]:
        self.calls.append(_Call(prompt=prompt, model=model, schema=schema, system=system))
        if schema is None:
            return self.text_response
        if self.structured_response is None:
            raise SchemaValidationError("no canned structured_response set")
        try:
            Draft202012Validator(schema).validate(self.structured_response)
        except ValidationError as exc:
            raise SchemaValidationError(str(exc)) from exc
        return self.structured_response

    async def embed(self, texts: Sequence[str], *, model: str | None = None) -> list[Vector]:
        self.calls.append(_Call(prompt=f"<embed {len(texts)}>", model=model, schema=None, system=None))
        return list(self.embed_response)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/data-engine && uv run pytest tests/unit/adapters/llm/test_mock.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/adapters/llm/__init__.py \
        apps/data-engine/src/filternarrange_engine/adapters/llm/mock.py \
        apps/data-engine/tests/unit/adapters/llm/test_mock.py
git commit -m "test(data-engine): add MockLLMProvider for unit testing"
```

---

## Task 4: OllamaProvider — happy path + structured output

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/adapters/llm/ollama.py`
- Test: `apps/data-engine/tests/unit/adapters/llm/test_ollama.py`

- [ ] **Step 1: Write the failing test**

`apps/data-engine/tests/unit/adapters/llm/test_ollama.py`:

```python
import json
import pytest
import respx
from httpx import Response

from filternarrange_engine.adapters.llm.ollama import OllamaProvider
from filternarrange_engine.core.llm import SchemaValidationError, LLMTimeoutError


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
        return_value=Response(200, json={"response": '{"summary": "ok", "key_observations": []}', "done": True})
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
        return_value=Response(200, json={"response": '{"wrong": true}', "done": True})
    )
    schema = {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}}
    async with OllamaProvider(base_url="http://ollama:11434", timeout_seconds=30) as p:
        with pytest.raises(SchemaValidationError):
            await p.complete("p", schema=schema)


@pytest.mark.asyncio
@respx.mock
async def test_complete_structured_raises_on_non_json_response():
    respx.post("http://ollama:11434/api/generate").mock(
        return_value=Response(200, json={"response": "not json at all", "done": True})
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
    import httpx
    respx.post("http://ollama:11434/api/generate").mock(side_effect=httpx.TimeoutException("slow"))
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/data-engine && uv add --dev respx jsonschema
uv run pytest tests/unit/adapters/llm/test_ollama.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write the module**

`apps/data-engine/src/filternarrange_engine/adapters/llm/ollama.py`:

```python
from __future__ import annotations
import json
from typing import Any, Mapping, Sequence

import httpx
from jsonschema import Draft202012Validator, ValidationError

from filternarrange_engine.core.llm import (
    JsonSchema, LLMError, LLMProvider, LLMTimeoutError,
    SchemaValidationError, Vector,
)


class OllamaProvider:
    """LLMProvider implementation talking to Ollama's HTTP API.

    Uses `POST /api/generate` with `format: "json"` when a JSON schema is
    supplied; uses `POST /api/embeddings` for embeddings. Temperature is
    pinned to 0 for deterministic, cacheable, repeatable structured output."""

    def __init__(self, *, base_url: str, timeout_seconds: int = 30,
                 default_model: str = "llama3.1:8b") -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._default_model = default_model
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "OllamaProvider":
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _client_or_raise(self) -> httpx.AsyncClient:
        if self._client is None:
            raise LLMError("OllamaProvider must be used as an async context manager")
        return self._client

    async def complete(
        self, prompt: str, *, schema: JsonSchema | None = None,
        model: str | None = None, system: str | None = None,
    ) -> str | Mapping[str, Any]:
        client = self._client_or_raise()
        body: dict[str, Any] = {
            "model": model or self._default_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
        if system is not None:
            body["system"] = system
        if schema is not None:
            body["format"] = "json"
        try:
            resp = await client.post("/api/generate", json=body)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"ollama timed out after {self._timeout}s") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"ollama transport error: {exc}") from exc
        if resp.status_code >= 400:
            raise LLMError(f"ollama returned HTTP {resp.status_code}: {resp.text}")
        data = resp.json()
        text = data.get("response", "")
        if schema is None:
            return text
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SchemaValidationError(f"ollama returned non-JSON output: {text!r}") from exc
        try:
            Draft202012Validator(schema).validate(parsed)
        except ValidationError as exc:
            raise SchemaValidationError(str(exc)) from exc
        return parsed

    async def embed(self, texts: Sequence[str], *, model: str | None = None) -> list[Vector]:
        client = self._client_or_raise()
        m = model or self._default_model
        out: list[Vector] = []
        for t in texts:
            try:
                resp = await client.post("/api/embeddings", json={"model": m, "prompt": t})
            except httpx.TimeoutException as exc:
                raise LLMTimeoutError("ollama embed timed out") from exc
            if resp.status_code >= 400:
                raise LLMError(f"ollama embed HTTP {resp.status_code}: {resp.text}")
            out.append(list(resp.json().get("embedding", [])))
        return out
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/data-engine && uv run pytest tests/unit/adapters/llm/test_ollama.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/adapters/llm/ollama.py \
        apps/data-engine/tests/unit/adapters/llm/test_ollama.py \
        apps/data-engine/pyproject.toml apps/data-engine/uv.lock
git commit -m "feat(data-engine): add OllamaProvider with structured output"
```

---

## Task 5: Redis cache wrapper for AI calls

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/adapters/llm/cache.py`
- Test: `apps/data-engine/tests/unit/adapters/llm/test_cache.py`

- [ ] **Step 1: Write the failing test**

`apps/data-engine/tests/unit/adapters/llm/test_cache.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock

from filternarrange_engine.adapters.llm.cache import AiCache, canonical_hash


def test_canonical_hash_stable_across_key_order():
    a = {"x": 1, "y": [3, 2], "z": {"b": 2, "a": 1}}
    b = {"z": {"a": 1, "b": 2}, "y": [3, 2], "x": 1}
    assert canonical_hash(a) == canonical_hash(b)


def test_canonical_hash_differs_on_value_change():
    assert canonical_hash({"x": 1}) != canonical_hash({"x": 2})


@pytest.mark.asyncio
async def test_get_returns_parsed_value():
    redis = AsyncMock()
    redis.get.return_value = json.dumps({"foo": "bar"})
    c = AiCache(redis=redis, ttl_seconds=3600)
    out = await c.get("auto_summary", {"k": 1})
    assert out == {"foo": "bar"}
    expected_key = f"py:cache:ai:auto_summary:{canonical_hash({'k': 1})}"
    redis.get.assert_awaited_with(expected_key)


@pytest.mark.asyncio
async def test_get_returns_none_when_missing():
    redis = AsyncMock()
    redis.get.return_value = None
    c = AiCache(redis=redis, ttl_seconds=3600)
    assert await c.get("x", {"k": 1}) is None


@pytest.mark.asyncio
async def test_set_writes_with_ttl():
    redis = AsyncMock()
    c = AiCache(redis=redis, ttl_seconds=3600)
    await c.set("auto_summary", {"k": 1}, {"v": 2})
    expected_key = f"py:cache:ai:auto_summary:{canonical_hash({'k': 1})}"
    redis.set.assert_awaited_with(expected_key, json.dumps({"v": 2}), ex=3600)


@pytest.mark.asyncio
async def test_redis_failure_is_swallowed_get():
    redis = AsyncMock()
    redis.get.side_effect = RuntimeError("redis down")
    c = AiCache(redis=redis, ttl_seconds=3600)
    assert await c.get("x", {"k": 1}) is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/data-engine && uv run pytest tests/unit/adapters/llm/test_cache.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write the module**

`apps/data-engine/src/filternarrange_engine/adapters/llm/cache.py`:

```python
from __future__ import annotations
import hashlib
import json
import logging
from typing import Any, Mapping, Protocol


_log = logging.getLogger(__name__)


class _AsyncRedis(Protocol):
    async def get(self, key: str) -> str | bytes | None: ...
    async def set(self, key: str, value: str, *, ex: int | None = None) -> Any: ...


def canonical_hash(payload: Mapping[str, Any]) -> str:
    """Canonical, key-sorted JSON serialization hashed with SHA-256."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AiCache:
    """Wraps Redis with the AI cache key convention from spec §5."""

    def __init__(self, *, redis: _AsyncRedis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    def _key(self, capability: str, payload: Mapping[str, Any]) -> str:
        return f"py:cache:ai:{capability}:{canonical_hash(payload)}"

    async def get(self, capability: str, payload: Mapping[str, Any]) -> dict | None:
        try:
            raw = await self._redis.get(self._key(capability, payload))
        except Exception as exc:  # cache must never break the request path
            _log.warning("redis get failed: %s", exc)
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set(self, capability: str, payload: Mapping[str, Any], value: Mapping[str, Any]) -> None:
        try:
            await self._redis.set(self._key(capability, payload), json.dumps(value), ex=self._ttl)
        except Exception as exc:
            _log.warning("redis set failed: %s", exc)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/data-engine && uv run pytest tests/unit/adapters/llm/test_cache.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/adapters/llm/cache.py \
        apps/data-engine/tests/unit/adapters/llm/test_cache.py
git commit -m "feat(data-engine): add Redis cache wrapper for AI capabilities"
```

---

## Task 6: AI capability registry (entry-point discovery + disable filtering)

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/adapters/llm/registry.py`
- Test: `apps/data-engine/tests/unit/adapters/llm/test_registry.py`

- [ ] **Step 1: Write the failing test**

`apps/data-engine/tests/unit/adapters/llm/test_registry.py`:

```python
import pytest
from importlib.metadata import EntryPoint
from unittest.mock import patch

from filternarrange_engine.adapters.llm.registry import (
    AiCapabilityRegistry, CapabilityNotFoundError,
)


class _FakeCap:
    def __init__(self, name: str) -> None:
        self.name = name
        self.required_tier = "free"
        self.default_model_setting = "auto_summary"
    async def run(self, llm, payload):
        return {"echoed": payload}


def _ep(name: str, obj):
    class _EP:
        def __init__(self, n, o):
            self.name = n
            self._o = o
        def load(self):
            return self._o
    return _EP(name, obj)


def test_loads_from_entry_points():
    eps = [_ep("auto_summary", _FakeCap("auto_summary")),
           _ep("chart_suggest", _FakeCap("chart_suggest"))]
    with patch("filternarrange_engine.adapters.llm.registry.entry_points", return_value=eps):
        reg = AiCapabilityRegistry.load(disabled=frozenset())
    assert sorted(reg.names()) == ["auto_summary", "chart_suggest"]


def test_respects_disabled_set():
    eps = [_ep("auto_summary", _FakeCap("auto_summary")),
           _ep("anomaly_detect", _FakeCap("anomaly_detect"))]
    with patch("filternarrange_engine.adapters.llm.registry.entry_points", return_value=eps):
        reg = AiCapabilityRegistry.load(disabled=frozenset({"anomaly_detect"}))
    assert reg.names() == ["auto_summary"]
    assert not reg.is_enabled("anomaly_detect")


def test_get_raises_for_disabled_or_missing():
    eps = [_ep("auto_summary", _FakeCap("auto_summary"))]
    with patch("filternarrange_engine.adapters.llm.registry.entry_points", return_value=eps):
        reg = AiCapabilityRegistry.load(disabled=frozenset({"chart_suggest"}))
    with pytest.raises(CapabilityNotFoundError):
        reg.get("chart_suggest")
    with pytest.raises(CapabilityNotFoundError):
        reg.get("does_not_exist")


def test_get_returns_capability():
    cap = _FakeCap("auto_summary")
    eps = [_ep("auto_summary", cap)]
    with patch("filternarrange_engine.adapters.llm.registry.entry_points", return_value=eps):
        reg = AiCapabilityRegistry.load(disabled=frozenset())
    assert reg.get("auto_summary") is cap
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/data-engine && uv run pytest tests/unit/adapters/llm/test_registry.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write the module**

`apps/data-engine/src/filternarrange_engine/adapters/llm/registry.py`:

```python
from __future__ import annotations
from importlib.metadata import entry_points
from typing import Iterable

from filternarrange_engine.core.llm import AICapability


GROUP = "filternarrange.ai_capabilities"


class CapabilityNotFoundError(LookupError):
    """Raised when a capability is missing or disabled."""


class AiCapabilityRegistry:
    def __init__(self, capabilities: dict[str, AICapability]) -> None:
        self._caps = capabilities

    @classmethod
    def load(cls, *, disabled: frozenset[str]) -> "AiCapabilityRegistry":
        eps: Iterable = entry_points(group=GROUP)  # type: ignore[arg-type]
        loaded: dict[str, AICapability] = {}
        for ep in eps:
            if ep.name in disabled:
                continue
            obj = ep.load()
            cap = obj() if callable(obj) and not hasattr(obj, "name") else obj
            loaded[cap.name] = cap
        return cls(loaded)

    def names(self) -> list[str]:
        return sorted(self._caps.keys())

    def is_enabled(self, name: str) -> bool:
        return name in self._caps

    def get(self, name: str) -> AICapability:
        try:
            return self._caps[name]
        except KeyError as exc:
            raise CapabilityNotFoundError(name) from exc
```

Note: in real life `entry_points(group=...)` may return an `EntryPoints` object in 3.10+ which is iterable; for Python 3.12 this works. The patched test uses a plain list.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/data-engine && uv run pytest tests/unit/adapters/llm/test_registry.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/adapters/llm/registry.py \
        apps/data-engine/tests/unit/adapters/llm/test_registry.py
git commit -m "feat(data-engine): add AI capability registry with disable filtering"
```

---

## Task 7: AI orchestrator — semaphore + cache + dispatch

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/application/ai_orchestrator.py`
- Test: `apps/data-engine/tests/unit/application/test_ai_orchestrator.py`

- [ ] **Step 1: Write the failing test**

`apps/data-engine/tests/unit/application/test_ai_orchestrator.py`:

```python
import asyncio
import pytest
from unittest.mock import AsyncMock

from filternarrange_engine.application.ai_orchestrator import AiOrchestrator
from filternarrange_engine.adapters.llm.registry import (
    AiCapabilityRegistry, CapabilityNotFoundError,
)
from filternarrange_engine.adapters.llm.mock import MockLLMProvider


class _FakeCap:
    name = "auto_summary"
    required_tier = "free"
    default_model_setting = "auto_summary"
    def __init__(self):
        self.calls = 0
    async def run(self, llm, payload):
        self.calls += 1
        await asyncio.sleep(0.05)
        return {"summary": f"v={payload['n']}", "key_observations": []}


@pytest.mark.asyncio
async def test_runs_capability_and_returns_result():
    cap = _FakeCap()
    reg = AiCapabilityRegistry({cap.name: cap})
    cache = AsyncMock()
    cache.get.return_value = None
    orch = AiOrchestrator(registry=reg, llm=MockLLMProvider(), cache=cache, max_concurrent=4,
                          models={"auto_summary": "llama3.1:8b"})
    out = await orch.run("auto_summary", {"n": 1})
    assert out.result == {"summary": "v=1", "key_observations": []}
    assert out.cache_hit is False
    assert out.model == "llama3.1:8b"
    cache.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_returns_cached_result_without_calling_capability():
    cap = _FakeCap()
    reg = AiCapabilityRegistry({cap.name: cap})
    cache = AsyncMock()
    cache.get.return_value = {"summary": "cached", "key_observations": []}
    orch = AiOrchestrator(registry=reg, llm=MockLLMProvider(), cache=cache, max_concurrent=4,
                          models={"auto_summary": "llama3.1:8b"})
    out = await orch.run("auto_summary", {"n": 1})
    assert out.cache_hit is True
    assert out.result["summary"] == "cached"
    assert cap.calls == 0
    cache.set.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_capability_raises():
    reg = AiCapabilityRegistry({})
    cache = AsyncMock(); cache.get.return_value = None
    orch = AiOrchestrator(registry=reg, llm=MockLLMProvider(), cache=cache,
                          max_concurrent=4, models={})
    with pytest.raises(CapabilityNotFoundError):
        await orch.run("nope", {})


@pytest.mark.asyncio
async def test_semaphore_caps_concurrency():
    """Run 10 concurrent calls with max_concurrent=4; observe peak concurrency <= 4."""
    peak = 0
    current = 0
    lock = asyncio.Lock()

    class _Cap:
        name = "auto_summary"
        required_tier = "free"
        default_model_setting = "auto_summary"
        async def run(self, llm, payload):
            nonlocal peak, current
            async with lock:
                current += 1
                peak = max(peak, current)
            await asyncio.sleep(0.05)
            async with lock:
                current -= 1
            return {"summary": "x", "key_observations": []}

    cap = _Cap()
    reg = AiCapabilityRegistry({cap.name: cap})
    cache = AsyncMock(); cache.get.return_value = None
    orch = AiOrchestrator(registry=reg, llm=MockLLMProvider(), cache=cache,
                          max_concurrent=4, models={"auto_summary": "llama3.1:8b"})
    await asyncio.gather(*[orch.run("auto_summary", {"n": i}) for i in range(10)])
    assert peak <= 4
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/data-engine && uv run pytest tests/unit/application/test_ai_orchestrator.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write the module**

`apps/data-engine/src/filternarrange_engine/application/ai_orchestrator.py`:

```python
from __future__ import annotations
import asyncio
from typing import Mapping

from filternarrange_engine.adapters.llm.cache import AiCache
from filternarrange_engine.adapters.llm.registry import AiCapabilityRegistry
from filternarrange_engine.core.llm import AIOutput, LLMProvider


class AiOrchestrator:
    """Dispatches AI capability calls. Applies:
      - Redis cache lookup keyed by canonical(payload)
      - Bounded concurrency via a single ai-async semaphore
      - Model selection per capability
    """

    def __init__(
        self, *,
        registry: AiCapabilityRegistry,
        llm: LLMProvider,
        cache: AiCache,
        max_concurrent: int,
        models: Mapping[str, str],
    ) -> None:
        self._registry = registry
        self._llm = llm
        self._cache = cache
        self._models = models
        self._sem = asyncio.Semaphore(max_concurrent)

    async def run(self, capability_name: str, payload: Mapping) -> AIOutput:
        cap = self._registry.get(capability_name)  # raises CapabilityNotFoundError
        cached = await self._cache.get(capability_name, payload)
        if cached is not None:
            return AIOutput(
                capability=capability_name, result=cached,
                model=self._models.get(capability_name), cache_hit=True,
            )
        async with self._sem:
            # The capability gets the LLM provider and the model for its slot
            # via a thin LLM proxy that pins the model. To keep things simple,
            # we pass model through the payload's caller — capabilities call
            # llm.complete(..., model=model_for_capability).
            result = await cap.run(_ModelPinnedLlm(self._llm, self._models.get(capability_name)), payload)
        await self._cache.set(capability_name, payload, result)
        return AIOutput(
            capability=capability_name, result=result,
            model=self._models.get(capability_name), cache_hit=False,
        )


class _ModelPinnedLlm:
    """Wraps an LLMProvider so capabilities don't need to know their model name."""
    def __init__(self, inner: LLMProvider, model: str | None) -> None:
        self._inner = inner
        self._model = model

    async def complete(self, prompt, *, schema=None, model=None, system=None):
        return await self._inner.complete(prompt, schema=schema, model=model or self._model, system=system)

    async def embed(self, texts, *, model=None):
        return await self._inner.embed(texts, model=model or self._model)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/data-engine && uv run pytest tests/unit/application/test_ai_orchestrator.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/application/ai_orchestrator.py \
        apps/data-engine/tests/unit/application/test_ai_orchestrator.py
git commit -m "feat(data-engine): add AI orchestrator with cache and semaphore"
```

---

## Task 8: ai-auto-summary plugin

**Files:**
- Create: `plugins/ai-auto-summary/pyproject.toml`
- Create: `plugins/ai-auto-summary/manifest.toml`
- Create: `plugins/ai-auto-summary/src/filternarrange_ai_auto_summary/__init__.py`
- Create: `plugins/ai-auto-summary/src/filternarrange_ai_auto_summary/plugin.py`
- Create: `plugins/ai-auto-summary/src/filternarrange_ai_auto_summary/prompts.py`
- Create: `plugins/ai-auto-summary/src/filternarrange_ai_auto_summary/schema.py`
- Test: `plugins/ai-auto-summary/tests/test_plugin.py`

- [ ] **Step 1: Write the failing test**

`plugins/ai-auto-summary/tests/test_plugin.py`:

```python
import pytest
from filternarrange_engine.adapters.llm.mock import MockLLMProvider
from filternarrange_ai_auto_summary.plugin import AutoSummaryCapability


@pytest.mark.asyncio
async def test_returns_summary_and_observations():
    llm = MockLLMProvider(structured_response={
        "summary": "120 users mostly in IN.",
        "key_observations": ["age range 18-34", "country = IN dominates"],
    })
    cap = AutoSummaryCapability()
    out = await cap.run(llm, {
        "schema": [{"name": "id", "type": "integer"}, {"name": "country", "type": "string"}],
        "sample_rows": [{"id": 1, "country": "IN"}],
        "total_rows": 120,
        "total_size_bytes": 4823,
    })
    assert out["summary"] == "120 users mostly in IN."
    assert len(out["key_observations"]) == 2


@pytest.mark.asyncio
async def test_rejects_bad_schema_response():
    from filternarrange_engine.core.llm import SchemaValidationError
    llm = MockLLMProvider(structured_response={"summary": "ok"})  # missing key_observations
    cap = AutoSummaryCapability()
    with pytest.raises(SchemaValidationError):
        await cap.run(llm, {"schema": [], "sample_rows": [], "total_rows": 0,
                            "total_size_bytes": 0})


def test_manifest_fields():
    cap = AutoSummaryCapability()
    assert cap.name == "auto_summary"
    assert cap.required_tier in ("free", "paid")
    assert cap.default_model_setting == "auto_summary"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd plugins/ai-auto-summary && uv pip install -e . && pytest tests/ -v
```

Expected: ImportError (no plugin module yet).

- [ ] **Step 3: Write the plugin**

`plugins/ai-auto-summary/manifest.toml`:

```toml
[plugin]
id = "auto_summary"
display_name = "AI: Auto Summary"
version = "1.0.0"
license = "Apache-2.0"
author = "FilterNArrange Core"
kind = "ai_capability"

[ai]
required_tier = "free"
default_model_setting = "auto_summary"
```

`plugins/ai-auto-summary/pyproject.toml`:

```toml
[project]
name = "filternarrange-ai-auto-summary"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = ["filternarrange-engine"]

[project.entry-points."filternarrange.ai_capabilities"]
auto_summary = "filternarrange_ai_auto_summary.plugin:AutoSummaryCapability"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/filternarrange_ai_auto_summary"]
```

`plugins/ai-auto-summary/src/filternarrange_ai_auto_summary/__init__.py`:

```python
from .plugin import AutoSummaryCapability

__all__ = ["AutoSummaryCapability"]
```

`plugins/ai-auto-summary/src/filternarrange_ai_auto_summary/schema.py`:

```python
SUMMARY_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["summary", "key_observations"],
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string", "minLength": 1, "maxLength": 1000},
        "key_observations": {
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 300},
            "maxItems": 10,
        },
    },
}
```

`plugins/ai-auto-summary/src/filternarrange_ai_auto_summary/prompts.py`:

```python
SYSTEM = (
    "You are a data-analysis assistant. Given a dataset's schema, a small "
    "sample of rows, and row/byte counts, write a short plain-English summary "
    "describing what the data is about and what stands out. "
    "Respond ONLY in the JSON shape requested. Do not invent statistics."
)

def build_prompt(payload: dict) -> str:
    return (
        f"Schema: {payload['schema']}\n"
        f"Sample rows (truncated to 50): {payload['sample_rows'][:50]}\n"
        f"Total rows: {payload['total_rows']}\n"
        f"Total size (bytes): {payload['total_size_bytes']}\n\n"
        "Produce JSON: {\"summary\": <string, 1-3 sentences>, "
        "\"key_observations\": [<short bullet, 0-10>]}"
    )
```

`plugins/ai-auto-summary/src/filternarrange_ai_auto_summary/plugin.py`:

```python
from __future__ import annotations
from typing import Mapping

from filternarrange_engine.core.llm import LLMProvider
from .prompts import SYSTEM, build_prompt
from .schema import SUMMARY_OUTPUT_SCHEMA


class AutoSummaryCapability:
    name = "auto_summary"
    required_tier = "free"
    default_model_setting = "auto_summary"

    async def run(self, llm: LLMProvider, payload: Mapping) -> Mapping:
        result = await llm.complete(
            build_prompt(dict(payload)),
            schema=SUMMARY_OUTPUT_SCHEMA,
            system=SYSTEM,
        )
        assert isinstance(result, dict)
        return result
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd plugins/ai-auto-summary && uv pip install -e . && pytest tests/ -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/ai-auto-summary/
git commit -m "feat(plugins): add ai-auto-summary capability plugin"
```

---

## Task 9: ai-chart-suggest plugin

**Files:**
- Create: `plugins/ai-chart-suggest/{pyproject.toml,manifest.toml,src/.../plugin.py,prompts.py,schema.py,__init__.py,tests/test_plugin.py}`

- [ ] **Step 1: Write the failing test**

`plugins/ai-chart-suggest/tests/test_plugin.py`:

```python
import pytest
from filternarrange_engine.adapters.llm.mock import MockLLMProvider
from filternarrange_engine.core.llm import SchemaValidationError
from filternarrange_ai_chart_suggest.plugin import ChartSuggestCapability


@pytest.mark.asyncio
async def test_returns_recommended_chart():
    llm = MockLLMProvider(structured_response={
        "recommended_chart": {
            "kind": "bar", "x": "country", "y": "count",
            "justification": "Categorical x with numeric aggregation reads best as bars."
        }
    })
    cap = ChartSuggestCapability()
    out = await cap.run(llm, {
        "schema": [{"name": "country", "type": "string"}, {"name": "count", "type": "integer"}],
        "cardinality_per_column": {"country": 12, "count": 220},
    })
    assert out["recommended_chart"]["kind"] == "bar"
    assert out["recommended_chart"]["justification"]


@pytest.mark.asyncio
async def test_rejects_unknown_chart_kind():
    llm = MockLLMProvider(structured_response={
        "recommended_chart": {"kind": "circles", "justification": "uh"}
    })
    cap = ChartSuggestCapability()
    with pytest.raises(SchemaValidationError):
        await cap.run(llm, {"schema": [], "cardinality_per_column": {}})


def test_manifest_fields():
    cap = ChartSuggestCapability()
    assert cap.name == "chart_suggest"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd plugins/ai-chart-suggest && uv pip install -e . && pytest tests/ -v
```

Expected: ImportError.

- [ ] **Step 3: Write the plugin**

`plugins/ai-chart-suggest/manifest.toml`:

```toml
[plugin]
id = "chart_suggest"
display_name = "AI: Chart Suggestion"
version = "1.0.0"
license = "Apache-2.0"
author = "FilterNArrange Core"
kind = "ai_capability"

[ai]
required_tier = "free"
default_model_setting = "chart_suggest"
```

`plugins/ai-chart-suggest/pyproject.toml`:

```toml
[project]
name = "filternarrange-ai-chart-suggest"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = ["filternarrange-engine"]

[project.entry-points."filternarrange.ai_capabilities"]
chart_suggest = "filternarrange_ai_chart_suggest.plugin:ChartSuggestCapability"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/filternarrange_ai_chart_suggest"]
```

`plugins/ai-chart-suggest/src/filternarrange_ai_chart_suggest/__init__.py`:

```python
from .plugin import ChartSuggestCapability
__all__ = ["ChartSuggestCapability"]
```

`plugins/ai-chart-suggest/src/filternarrange_ai_chart_suggest/schema.py`:

```python
CHART_KINDS = ["line", "bar", "pie", "histogram", "scatter", "heatmap"]

CHART_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["recommended_chart"],
    "additionalProperties": False,
    "properties": {
        "recommended_chart": {
            "type": "object",
            "required": ["kind", "justification"],
            "additionalProperties": False,
            "properties": {
                "kind": {"enum": CHART_KINDS},
                "x": {"type": ["string", "null"]},
                "y": {"type": ["string", "null"]},
                "color": {"type": ["string", "null"]},
                "justification": {"type": "string", "minLength": 1, "maxLength": 400},
            },
        }
    },
}
```

`plugins/ai-chart-suggest/src/filternarrange_ai_chart_suggest/prompts.py`:

```python
from .schema import CHART_KINDS

SYSTEM = (
    "You are a data-visualization advisor. Given a dataset schema and the "
    "cardinality (distinct-value count) of each column, recommend exactly ONE "
    f"chart from this set: {CHART_KINDS}. Pick x/y/color columns when "
    "meaningful. Provide a one-line justification. Respond ONLY in JSON."
)


def build_prompt(payload: dict) -> str:
    return (
        f"Schema: {payload['schema']}\n"
        f"Cardinality per column: {payload['cardinality_per_column']}\n\n"
        "Produce JSON: "
        "{\"recommended_chart\": {\"kind\": <one of "
        f"{CHART_KINDS}>, \"x\"?: <column>, \"y\"?: <column>, "
        "\"color\"?: <column>, \"justification\": <one sentence>}}"
    )
```

`plugins/ai-chart-suggest/src/filternarrange_ai_chart_suggest/plugin.py`:

```python
from __future__ import annotations
from typing import Mapping
from filternarrange_engine.core.llm import LLMProvider
from .prompts import SYSTEM, build_prompt
from .schema import CHART_OUTPUT_SCHEMA


class ChartSuggestCapability:
    name = "chart_suggest"
    required_tier = "free"
    default_model_setting = "chart_suggest"

    async def run(self, llm: LLMProvider, payload: Mapping) -> Mapping:
        out = await llm.complete(build_prompt(dict(payload)),
                                 schema=CHART_OUTPUT_SCHEMA, system=SYSTEM)
        assert isinstance(out, dict)
        return out
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd plugins/ai-chart-suggest && pytest tests/ -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/ai-chart-suggest/
git commit -m "feat(plugins): add ai-chart-suggest capability plugin"
```

---

## Task 10: ai-anomaly-detect plugin

**Files:**
- Create: `plugins/ai-anomaly-detect/{pyproject.toml,manifest.toml,src/.../{plugin,prompts,schema,__init__}.py,tests/test_plugin.py}`

- [ ] **Step 1: Write the failing test**

`plugins/ai-anomaly-detect/tests/test_plugin.py`:

```python
import pytest
from filternarrange_engine.adapters.llm.mock import MockLLMProvider
from filternarrange_engine.core.llm import SchemaValidationError
from filternarrange_ai_anomaly_detect.plugin import AnomalyDetectCapability


@pytest.mark.asyncio
async def test_returns_findings():
    llm = MockLLMProvider(structured_response={
        "findings": [
            {"kind": "missing_values", "column": "email",
             "severity": "medium", "description": "30% nulls in email",
             "suggested_action": "drop rows or coerce"},
            {"kind": "outlier", "column": "amount",
             "severity": "high", "description": "row 42 amount=1e9 vs median=42"},
        ]
    })
    cap = AnomalyDetectCapability()
    out = await cap.run(llm, {
        "schema": [{"name": "email", "type": "string"}, {"name": "amount", "type": "integer"}],
        "sample_rows": [{"email": None, "amount": 1_000_000_000}],
        "summary_stats": {"amount": {"min": 1, "max": 1_000_000_000, "median": 42}},
    })
    assert len(out["findings"]) == 2
    assert out["findings"][0]["kind"] == "missing_values"


@pytest.mark.asyncio
async def test_rejects_unknown_kind():
    llm = MockLLMProvider(structured_response={
        "findings": [{"kind": "aliens", "severity": "low", "description": "x"}]
    })
    cap = AnomalyDetectCapability()
    with pytest.raises(SchemaValidationError):
        await cap.run(llm, {"schema": [], "sample_rows": [], "summary_stats": {}})


@pytest.mark.asyncio
async def test_empty_findings_ok():
    llm = MockLLMProvider(structured_response={"findings": []})
    cap = AnomalyDetectCapability()
    out = await cap.run(llm, {"schema": [], "sample_rows": [], "summary_stats": {}})
    assert out["findings"] == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd plugins/ai-anomaly-detect && uv pip install -e . && pytest tests/ -v
```

Expected: ImportError.

- [ ] **Step 3: Write the plugin**

`plugins/ai-anomaly-detect/manifest.toml`:

```toml
[plugin]
id = "anomaly_detect"
display_name = "AI: Anomaly & Data-Quality Detection"
version = "1.0.0"
license = "Apache-2.0"
author = "FilterNArrange Core"
kind = "ai_capability"

[ai]
required_tier = "free"
default_model_setting = "anomaly_detect"
```

`plugins/ai-anomaly-detect/pyproject.toml`:

```toml
[project]
name = "filternarrange-ai-anomaly-detect"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = ["filternarrange-engine"]

[project.entry-points."filternarrange.ai_capabilities"]
anomaly_detect = "filternarrange_ai_anomaly_detect.plugin:AnomalyDetectCapability"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/filternarrange_ai_anomaly_detect"]
```

`plugins/ai-anomaly-detect/src/filternarrange_ai_anomaly_detect/__init__.py`:

```python
from .plugin import AnomalyDetectCapability
__all__ = ["AnomalyDetectCapability"]
```

`plugins/ai-anomaly-detect/src/filternarrange_ai_anomaly_detect/schema.py`:

```python
FINDING_KINDS = ["outlier", "missing_values", "format_inconsistency",
                 "possible_duplicate", "type_drift"]
SEVERITY = ["low", "medium", "high"]

ANOMALY_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["findings"],
    "additionalProperties": False,
    "properties": {
        "findings": {
            "type": "array",
            "maxItems": 40,
            "items": {
                "type": "object",
                "required": ["kind", "severity", "description"],
                "additionalProperties": False,
                "properties": {
                    "kind": {"enum": FINDING_KINDS},
                    "column": {"type": ["string", "null"]},
                    "severity": {"enum": SEVERITY},
                    "description": {"type": "string", "minLength": 1, "maxLength": 400},
                    "suggested_action": {"type": ["string", "null"], "maxLength": 300},
                },
            },
        }
    },
}
```

`plugins/ai-anomaly-detect/src/filternarrange_ai_anomaly_detect/prompts.py`:

```python
from .schema import FINDING_KINDS, SEVERITY

SYSTEM = (
    "You are a data-quality reviewer. Given a schema, sample rows, and "
    "per-column summary statistics, identify problems. Each finding's "
    f"kind must be one of {FINDING_KINDS} and severity one of {SEVERITY}. "
    "Only emit findings you have evidence for. Respond ONLY in JSON."
)


def build_prompt(payload: dict) -> str:
    return (
        f"Schema: {payload['schema']}\n"
        f"Sample rows: {payload['sample_rows']}\n"
        f"Summary stats: {payload['summary_stats']}\n\n"
        "Produce JSON: {\"findings\": ["
        "{\"kind\": <one of " f"{FINDING_KINDS}>, "
        "\"column\"?: <column or null>, "
        "\"severity\": <low|medium|high>, "
        "\"description\": <one sentence>, "
        "\"suggested_action\"?: <one sentence>}]}"
    )
```

`plugins/ai-anomaly-detect/src/filternarrange_ai_anomaly_detect/plugin.py`:

```python
from __future__ import annotations
from typing import Mapping
from filternarrange_engine.core.llm import LLMProvider
from .prompts import SYSTEM, build_prompt
from .schema import ANOMALY_OUTPUT_SCHEMA


class AnomalyDetectCapability:
    name = "anomaly_detect"
    required_tier = "free"
    default_model_setting = "anomaly_detect"

    async def run(self, llm: LLMProvider, payload: Mapping) -> Mapping:
        out = await llm.complete(build_prompt(dict(payload)),
                                 schema=ANOMALY_OUTPUT_SCHEMA, system=SYSTEM)
        assert isinstance(out, dict)
        return out
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd plugins/ai-anomaly-detect && pytest tests/ -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/ai-anomaly-detect/
git commit -m "feat(plugins): add ai-anomaly-detect capability plugin"
```

---

## Task 11: ai-nl-to-filter plugin (uses FilterSpec from Plan C)

**Files:**
- Create: `plugins/ai-nl-to-filter/{pyproject.toml,manifest.toml,src/.../{plugin,prompts,schema,__init__}.py,tests/test_plugin.py}`

- [ ] **Step 1: Write the failing test**

`plugins/ai-nl-to-filter/tests/test_plugin.py`:

```python
import pytest
from filternarrange_engine.adapters.llm.mock import MockLLMProvider
from filternarrange_engine.core.llm import SchemaValidationError
from filternarrange_ai_nl_to_filter.plugin import NlToFilterCapability


@pytest.mark.asyncio
async def test_returns_filter_spec_for_simple_query():
    llm = MockLLMProvider(structured_response={
        "filter_spec": {
            "kind": "row",
            "predicate": {"op": "gt", "column": "age", "value": 18}
        },
        "confidence": 0.92,
    })
    cap = NlToFilterCapability()
    out = await cap.run(llm, {
        "query": "show rows where age is greater than 18",
        "schema": [{"name": "age", "type": "integer"}],
    })
    assert out["filter_spec"]["kind"] == "row"
    assert 0.0 <= out["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_rejects_unknown_filter_kind():
    llm = MockLLMProvider(structured_response={
        "filter_spec": {"kind": "telepathy", "predicate": {}},
        "confidence": 0.5,
    })
    cap = NlToFilterCapability()
    with pytest.raises(SchemaValidationError):
        await cap.run(llm, {"query": "x", "schema": []})


@pytest.mark.asyncio
async def test_uses_correct_model_setting():
    cap = NlToFilterCapability()
    assert cap.default_model_setting == "nl_to_filter"
    assert cap.name == "nl_to_filter"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd plugins/ai-nl-to-filter && uv pip install -e . && pytest tests/ -v
```

Expected: ImportError.

- [ ] **Step 3: Write the plugin**

`plugins/ai-nl-to-filter/manifest.toml`:

```toml
[plugin]
id = "nl_to_filter"
display_name = "AI: Natural-Language to Filter"
version = "1.0.0"
license = "Apache-2.0"
author = "FilterNArrange Core"
kind = "ai_capability"

[ai]
required_tier = "free"
default_model_setting = "nl_to_filter"
```

`plugins/ai-nl-to-filter/pyproject.toml`:

```toml
[project]
name = "filternarrange-ai-nl-to-filter"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = ["filternarrange-engine"]

[project.entry-points."filternarrange.ai_capabilities"]
nl_to_filter = "filternarrange_ai_nl_to_filter.plugin:NlToFilterCapability"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/filternarrange_ai_nl_to_filter"]
```

`plugins/ai-nl-to-filter/src/filternarrange_ai_nl_to_filter/__init__.py`:

```python
from .plugin import NlToFilterCapability
__all__ = ["NlToFilterCapability"]
```

`plugins/ai-nl-to-filter/src/filternarrange_ai_nl_to_filter/schema.py`:

```python
"""NL→Filter output schema. Wraps the FilterSpec schema established by
Plan C (plugins/filter-*). Plan C exports FILTER_SPEC_SCHEMA from
`filternarrange_filter_core.schema`. We import it lazily to avoid a hard
dependency for unit tests that don't need it.
"""

try:
    from filternarrange_filter_core.schema import FILTER_SPEC_SCHEMA
except ImportError:  # tests / dev environments without filter-core installed
    FILTER_SPEC_SCHEMA = {
        "type": "object",
        "required": ["kind"],
        "properties": {
            "kind": {"enum": ["column", "row", "expression", "regex"]},
            "columns": {"type": "array", "items": {"type": "string"}},
            "predicate": {"type": "object"},
            "expression": {"type": "string"},
            "pattern": {"type": "string"},
        },
    }


NL2FILTER_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["filter_spec", "confidence"],
    "additionalProperties": False,
    "properties": {
        "filter_spec": FILTER_SPEC_SCHEMA,
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
}
```

`plugins/ai-nl-to-filter/src/filternarrange_ai_nl_to_filter/prompts.py`:

```python
SYSTEM = (
    "You convert natural-language data questions into a structured FilterSpec. "
    "A FilterSpec has one of four kinds: 'column' (project columns), 'row' "
    "(predicate over rows), 'expression' (free-form SQL-like), 'regex' (match "
    "pattern). Use 'row' for value comparisons, 'column' for column projection, "
    "'expression' only when row predicates don't suffice, 'regex' for pattern "
    "search. Respond ONLY in JSON. Include a confidence in [0,1]."
)


def build_prompt(payload: dict) -> str:
    return (
        f"Detected schema: {payload['schema']}\n"
        f"User query: {payload['query']!r}\n\n"
        "Return JSON: {\"filter_spec\": <FilterSpec>, \"confidence\": <0-1>}"
    )
```

`plugins/ai-nl-to-filter/src/filternarrange_ai_nl_to_filter/plugin.py`:

```python
from __future__ import annotations
from typing import Mapping

from filternarrange_engine.core.llm import LLMProvider
from .prompts import SYSTEM, build_prompt
from .schema import NL2FILTER_OUTPUT_SCHEMA


class NlToFilterCapability:
    name = "nl_to_filter"
    required_tier = "free"
    default_model_setting = "nl_to_filter"

    async def run(self, llm: LLMProvider, payload: Mapping) -> Mapping:
        out = await llm.complete(build_prompt(dict(payload)),
                                 schema=NL2FILTER_OUTPUT_SCHEMA, system=SYSTEM)
        assert isinstance(out, dict)
        return out
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd plugins/ai-nl-to-filter && pytest tests/ -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/ai-nl-to-filter/
git commit -m "feat(plugins): add ai-nl-to-filter capability plugin"
```

---

## Task 12: FastAPI routes for /ai/* in data-engine

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/api/ai_routes.py`
- Modify: `apps/data-engine/src/filternarrange_engine/api/__init__.py`
- Test: `apps/data-engine/tests/unit/api/test_ai_routes.py`

- [ ] **Step 1: Write the failing test**

`apps/data-engine/tests/unit/api/test_ai_routes.py`:

```python
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock

from filternarrange_engine.api.ai_routes import build_ai_router
from filternarrange_engine.core.llm import AIOutput
from filternarrange_engine.adapters.llm.registry import CapabilityNotFoundError


def _make_app(orch):
    app = FastAPI()
    app.include_router(build_ai_router(orch, enabled_names={"nl_to_filter", "auto_summary",
                                                            "chart_suggest", "anomaly_detect"}),
                       prefix="/ai")
    return app


@pytest.mark.asyncio
async def test_nl_to_filter_endpoint():
    orch = AsyncMock()
    orch.run.return_value = AIOutput(
        capability="nl_to_filter",
        result={"filter_spec": {"kind": "row"}, "confidence": 0.9},
        model="qwen2.5:7b",
    )
    app = _make_app(orch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/ai/nl-to-filter", json={"ref": "uploads/x.csv", "query": "age > 18",
                                                    "schema": [{"name": "age", "type": "integer"}]})
    assert r.status_code == 200
    assert r.json()["filter_spec"]["kind"] == "row"
    assert r.json()["confidence"] == 0.9


@pytest.mark.asyncio
async def test_summary_endpoint():
    orch = AsyncMock()
    orch.run.return_value = AIOutput(
        capability="auto_summary",
        result={"summary": "ok", "key_observations": []},
    )
    app = _make_app(orch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/ai/summary", json={"ref": "uploads/x.csv",
                                               "schema": [], "sample_rows": [],
                                               "total_rows": 0, "total_size_bytes": 0})
    assert r.status_code == 200
    assert r.json() == {"summary": "ok", "key_observations": []}


@pytest.mark.asyncio
async def test_disabled_capability_returns_404():
    orch = AsyncMock()
    app = FastAPI()
    app.include_router(build_ai_router(orch, enabled_names={"auto_summary"}), prefix="/ai")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/ai/anomaly", json={"ref": "x", "schema": [], "sample_rows": [],
                                               "summary_stats": {}})
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == "AI_CAPABILITY_DISABLED"


@pytest.mark.asyncio
async def test_capability_not_found_propagates_as_404():
    orch = AsyncMock()
    orch.run.side_effect = CapabilityNotFoundError("nl_to_filter")
    app = _make_app(orch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/ai/nl-to-filter", json={"ref": "x", "query": "q", "schema": []})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_schema_validation_error_returns_502():
    from filternarrange_engine.core.llm import SchemaValidationError
    orch = AsyncMock()
    orch.run.side_effect = SchemaValidationError("bad llm output")
    app = _make_app(orch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/ai/summary", json={"ref": "x", "schema": [], "sample_rows": [],
                                               "total_rows": 0, "total_size_bytes": 0})
    assert r.status_code == 502
    assert r.json()["code"] == "AI_LLM_OUTPUT_INVALID"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/data-engine && uv run pytest tests/unit/api/test_ai_routes.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write the router**

`apps/data-engine/src/filternarrange_engine/api/ai_routes.py`:

```python
from __future__ import annotations
import logging
import uuid
from typing import Any, Mapping

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from filternarrange_engine.application.ai_orchestrator import AiOrchestrator
from filternarrange_engine.adapters.llm.registry import CapabilityNotFoundError
from filternarrange_engine.core.llm import (
    LLMError, LLMTimeoutError, SchemaValidationError,
)

_log = logging.getLogger(__name__)


class NlToFilterRequest(BaseModel):
    ref: str
    query: str = Field(min_length=1, max_length=2000)
    schema: list[dict] = Field(default_factory=list)


class SummaryRequest(BaseModel):
    ref: str
    schema: list[dict]
    sample_rows: list[dict]
    total_rows: int
    total_size_bytes: int


class ChartSuggestRequest(BaseModel):
    ref: str
    schema: list[dict]
    cardinality_per_column: dict[str, int]


class AnomalyRequest(BaseModel):
    ref: str
    schema: list[dict]
    sample_rows: list[dict]
    summary_stats: dict[str, Any]


def _err_envelope(code: str, message: str, plugin_id: str | None = None) -> dict:
    return {
        "code": code, "plugin_id": plugin_id, "message": message,
        "trace_id": str(uuid.uuid4()),
    }


def build_ai_router(orchestrator: AiOrchestrator, enabled_names: set[str]) -> APIRouter:
    router = APIRouter(tags=["ai"])

    def _guard(name: str) -> None:
        if name not in enabled_names:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_err_envelope("AI_CAPABILITY_DISABLED",
                                     f"AI capability '{name}' is disabled by configuration",
                                     plugin_id=name),
            )

    async def _run(name: str, payload: Mapping) -> Mapping:
        _guard(name)
        try:
            out = await orchestrator.run(name, payload)
            return out.result
        except CapabilityNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=_err_envelope("AI_CAPABILITY_NOT_FOUND", str(exc), plugin_id=name),
            )
        except SchemaValidationError as exc:
            raise HTTPException(
                status_code=502,
                detail=_err_envelope("AI_LLM_OUTPUT_INVALID", str(exc), plugin_id=name),
            )
        except LLMTimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail=_err_envelope("AI_LLM_TIMEOUT", str(exc), plugin_id=name),
            )
        except LLMError as exc:
            raise HTTPException(
                status_code=502,
                detail=_err_envelope("AI_LLM_ERROR", str(exc), plugin_id=name),
            )

    @router.post("/nl-to-filter")
    async def nl_to_filter(req: NlToFilterRequest):
        return await _run("nl_to_filter", req.model_dump())

    @router.post("/summary")
    async def summary(req: SummaryRequest):
        return await _run("auto_summary", req.model_dump())

    @router.post("/chart-suggest")
    async def chart_suggest(req: ChartSuggestRequest):
        return await _run("chart_suggest", req.model_dump())

    @router.post("/anomaly")
    async def anomaly(req: AnomalyRequest):
        return await _run("anomaly_detect", req.model_dump())

    return router
```

Modify `apps/data-engine/src/filternarrange_engine/api/__init__.py` to expose the router builder:

```python
from .ai_routes import build_ai_router

__all__ = ["build_ai_router"]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/data-engine && uv run pytest tests/unit/api/test_ai_routes.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/api/ai_routes.py \
        apps/data-engine/src/filternarrange_engine/api/__init__.py \
        apps/data-engine/tests/unit/api/test_ai_routes.py
git commit -m "feat(data-engine): expose /ai/* HTTP endpoints"
```

---

## Task 13: Wire the AI subsystem into the FastAPI app at startup

**Files:**
- Modify: `apps/data-engine/src/filternarrange_engine/main.py` (created by Plan B; this task extends it)
- Test: `apps/data-engine/tests/integration/test_ai_wiring.py`

- [ ] **Step 1: Write the failing integration test**

`apps/data-engine/tests/integration/test_ai_wiring.py`:

```python
import os
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from filternarrange_engine.main import create_app


@pytest.mark.asyncio
async def test_ai_endpoints_registered_with_default_set(monkeypatch):
    monkeypatch.delenv("FILTERNARRANGE_DISABLED_AI", raising=False)
    # Inject a stub orchestrator that returns canned outputs by capability.
    from filternarrange_engine.core.llm import AIOutput

    class _StubOrch:
        async def run(self, name, payload):
            return AIOutput(capability=name, result={"ok": True, "name": name})

    app = create_app(orchestrator_override=_StubOrch(),
                     enabled_names={"nl_to_filter","auto_summary","chart_suggest","anomaly_detect"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/ai/summary", json={"ref":"x","schema":[],"sample_rows":[],
                                               "total_rows":0,"total_size_bytes":0})
        assert r.status_code == 200
        assert r.json() == {"ok": True, "name": "auto_summary"}


@pytest.mark.asyncio
async def test_disabled_via_env_does_not_expose(monkeypatch):
    monkeypatch.setenv("FILTERNARRANGE_DISABLED_AI", "anomaly_detect")
    from filternarrange_engine.core.llm import AIOutput

    class _StubOrch:
        async def run(self, name, payload):
            return AIOutput(capability=name, result={"ok": True})

    app = create_app(orchestrator_override=_StubOrch(),
                     enabled_names={"nl_to_filter","auto_summary","chart_suggest"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/ai/anomaly", json={"ref":"x","schema":[],"sample_rows":[],
                                               "summary_stats":{}})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "AI_CAPABILITY_DISABLED"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/data-engine && uv run pytest tests/integration/test_ai_wiring.py -v
```

Expected: FAIL — `create_app` does not accept those kwargs yet OR the /ai routes are not registered.

- [ ] **Step 3: Modify create_app**

Extend `apps/data-engine/src/filternarrange_engine/main.py`. Locate the existing `create_app()` factory (created by Plan B) and adapt:

```python
from __future__ import annotations
from typing import Any
from fastapi import FastAPI

from filternarrange_engine.api.ai_routes import build_ai_router
from filternarrange_engine.platform.config import load_ai_settings
from filternarrange_engine.adapters.llm.registry import AiCapabilityRegistry
from filternarrange_engine.adapters.llm.ollama import OllamaProvider
from filternarrange_engine.adapters.llm.cache import AiCache
from filternarrange_engine.application.ai_orchestrator import AiOrchestrator


def create_app(*, orchestrator_override: Any | None = None,
               enabled_names: set[str] | None = None) -> FastAPI:
    app = FastAPI(title="FilterNArrange Data Engine")

    settings = load_ai_settings()
    if orchestrator_override is not None:
        orch = orchestrator_override
        names = enabled_names or set()
    else:
        registry = AiCapabilityRegistry.load(disabled=settings.disabled)
        names = set(registry.names())
        # Provider + cache constructed lazily on app start; for tests use override.
        ollama = OllamaProvider(base_url=settings.ollama_base_url,
                                timeout_seconds=settings.ollama_timeout_seconds)
        # Real redis client constructed in Plan B's lifespan; here we accept None
        # and only build orchestrator when both are available.
        orch = None  # populated at lifespan start

    app.include_router(build_ai_router(orch, enabled_names=names), prefix="/ai")
    return app
```

Document the env-driven path: production wiring happens in the lifespan handler (Plan B owns the lifespan; add a follow-up TODO comment to attach `orch` from real Ollama + Redis there).

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/data-engine && uv run pytest tests/integration/test_ai_wiring.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/main.py \
        apps/data-engine/tests/integration/test_ai_wiring.py
git commit -m "feat(data-engine): wire AI subsystem into FastAPI app factory"
```

---

## Task 14: Cache-roundtrip integration test (same input → second call doesn't hit LLM)

**Files:**
- Create: `apps/data-engine/tests/integration/test_ai_cache_roundtrip.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import AsyncMock

from filternarrange_engine.application.ai_orchestrator import AiOrchestrator
from filternarrange_engine.adapters.llm.registry import AiCapabilityRegistry
from filternarrange_engine.adapters.llm.cache import AiCache
from filternarrange_engine.adapters.llm.mock import MockLLMProvider


class _CountingCap:
    name = "auto_summary"
    required_tier = "free"
    default_model_setting = "auto_summary"
    def __init__(self): self.calls = 0
    async def run(self, llm, payload):
        self.calls += 1
        return {"summary": "x", "key_observations": []}


class _InMemRedis:
    def __init__(self): self.data: dict[str, str] = {}
    async def get(self, k): return self.data.get(k)
    async def set(self, k, v, *, ex=None): self.data[k] = v


@pytest.mark.asyncio
async def test_second_identical_call_is_cache_hit():
    cap = _CountingCap()
    reg = AiCapabilityRegistry({cap.name: cap})
    cache = AiCache(redis=_InMemRedis(), ttl_seconds=3600)
    orch = AiOrchestrator(registry=reg, llm=MockLLMProvider(), cache=cache,
                          max_concurrent=4, models={"auto_summary": "llama3.1:8b"})

    payload = {"schema": [], "sample_rows": [], "total_rows": 0, "total_size_bytes": 0}
    a = await orch.run("auto_summary", payload)
    b = await orch.run("auto_summary", payload)
    assert a.cache_hit is False
    assert b.cache_hit is True
    assert cap.calls == 1


@pytest.mark.asyncio
async def test_different_payload_is_separate_cache_entry():
    cap = _CountingCap()
    reg = AiCapabilityRegistry({cap.name: cap})
    cache = AiCache(redis=_InMemRedis(), ttl_seconds=3600)
    orch = AiOrchestrator(registry=reg, llm=MockLLMProvider(), cache=cache,
                          max_concurrent=4, models={"auto_summary": "llama3.1:8b"})
    await orch.run("auto_summary", {"schema": [], "sample_rows": [], "total_rows": 1,
                                     "total_size_bytes": 0})
    await orch.run("auto_summary", {"schema": [], "sample_rows": [], "total_rows": 2,
                                     "total_size_bytes": 0})
    assert cap.calls == 2
```

- [ ] **Step 2: Run test to verify it passes**

```bash
cd apps/data-engine && uv run pytest tests/integration/test_ai_cache_roundtrip.py -v
```

Expected: 2 passed (orchestrator + cache already implemented).

- [ ] **Step 3: Commit**

```bash
git add apps/data-engine/tests/integration/test_ai_cache_roundtrip.py
git commit -m "test(data-engine): AI cache deduplicates identical payloads"
```

---

## Task 15: Real Ollama integration test (gated)

**Files:**
- Create: `tests/integration/test_ai_capabilities_real.py`

- [ ] **Step 1: Write the gated test**

`tests/integration/test_ai_capabilities_real.py`:

```python
"""Real Ollama integration test.

SKIPPED unless RUN_OLLAMA_TESTS=1. CI runs this nightly on a self-hosted
runner that has Ollama up with llama3.1:8b and qwen2.5:7b pulled.
"""
import os
import pytest

from filternarrange_engine.adapters.llm.ollama import OllamaProvider
from filternarrange_ai_auto_summary.plugin import AutoSummaryCapability
from filternarrange_ai_nl_to_filter.plugin import NlToFilterCapability


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_OLLAMA_TESTS") != "1",
    reason="set RUN_OLLAMA_TESTS=1 to run against a live Ollama",
)


BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


@pytest.mark.asyncio
async def test_auto_summary_against_real_ollama():
    async with OllamaProvider(base_url=BASE, timeout_seconds=60,
                               default_model="llama3.1:8b") as llm:
        cap = AutoSummaryCapability()
        out = await cap.run(llm, {
            "schema": [{"name": "country", "type": "string"},
                       {"name": "signups", "type": "integer"}],
            "sample_rows": [
                {"country": "IN", "signups": 220},
                {"country": "US", "signups": 130},
                {"country": "DE", "signups": 90},
            ],
            "total_rows": 3,
            "total_size_bytes": 256,
        })
    assert isinstance(out["summary"], str) and len(out["summary"]) > 10
    assert isinstance(out["key_observations"], list)


@pytest.mark.asyncio
async def test_nl_to_filter_against_real_ollama():
    async with OllamaProvider(base_url=BASE, timeout_seconds=60,
                               default_model="qwen2.5:7b") as llm:
        cap = NlToFilterCapability()
        out = await cap.run(llm, {
            "query": "rows where signups > 100",
            "schema": [{"name": "country", "type": "string"},
                       {"name": "signups", "type": "integer"}],
        })
    assert out["filter_spec"]["kind"] in {"column", "row", "expression", "regex"}
    assert 0.0 <= out["confidence"] <= 1.0
```

- [ ] **Step 2: Verify skip without env var**

```bash
pytest tests/integration/test_ai_capabilities_real.py -v
```

Expected: 2 SKIPPED.

- [ ] **Step 3: Verify run with env var (manual, optional)**

With Ollama running locally and models pulled:

```bash
RUN_OLLAMA_TESTS=1 OLLAMA_BASE_URL=http://localhost:11434 \
  pytest tests/integration/test_ai_capabilities_real.py -v
```

Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_ai_capabilities_real.py
git commit -m "test(integration): real Ollama gated suite for AI capabilities"
```

---

## Task 16: Gateway DataEngineAiClient (calls data-engine /ai/*)

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/http/DataEngineAiClient.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/http/DataEngineAiClientTest.java`

- [ ] **Step 1: Write the failing test**

`apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/http/DataEngineAiClientTest.java`:

```java
package io.filternarrange.gateway.infrastructure.http;

import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class DataEngineAiClientTest {
    private MockWebServer server;
    private DataEngineAiClient client;

    @BeforeEach
    void setUp() throws Exception {
        server = new MockWebServer();
        server.start();
        client = new DataEngineAiClient(WebClient.builder().baseUrl(server.url("/").toString()).build());
    }

    @AfterEach
    void tearDown() throws Exception { server.shutdown(); }

    @Test
    void nlToFilter_returnsParsedResult() {
        server.enqueue(new MockResponse()
            .setHeader("Content-Type", "application/json")
            .setBody("{\"filter_spec\":{\"kind\":\"row\"},\"confidence\":0.91}"));
        Map<String, Object> out = client.nlToFilter(Map.of("ref","x","query","q","schema",java.util.List.of())).block();
        assertThat(out).containsKey("filter_spec");
        assertThat(out.get("confidence")).isEqualTo(0.91);
    }

    @Test
    void disabledCapability404_isMappedToCapabilityDisabledException() {
        server.enqueue(new MockResponse().setResponseCode(404)
            .setHeader("Content-Type","application/json")
            .setBody("{\"detail\":{\"code\":\"AI_CAPABILITY_DISABLED\",\"message\":\"x\",\"trace_id\":\"t\"}}"));
        assertThatThrownBy(() ->
            client.anomaly(Map.of("ref","x","schema",java.util.List.of(),
                                  "sample_rows",java.util.List.of(),"summary_stats",Map.of())).block()
        ).isInstanceOf(AiCapabilityDisabledException.class);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/gateway && ./gradlew test --tests DataEngineAiClientTest
```

Expected: compile error — class missing.

- [ ] **Step 3: Write the client**

`apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/http/DataEngineAiClient.java`:

```java
package io.filternarrange.gateway.infrastructure.http;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.Map;

@Component
public class DataEngineAiClient {
    private final WebClient client;

    public DataEngineAiClient(@Qualifier("dataEngineWebClient") WebClient client) {
        this.client = client;
    }

    public Mono<Map<String, Object>> nlToFilter(Map<String, Object> req) {
        return post("/ai/nl-to-filter", req);
    }
    public Mono<Map<String, Object>> summary(Map<String, Object> req) { return post("/ai/summary", req); }
    public Mono<Map<String, Object>> chartSuggest(Map<String, Object> req) { return post("/ai/chart-suggest", req); }
    public Mono<Map<String, Object>> anomaly(Map<String, Object> req) { return post("/ai/anomaly", req); }

    @SuppressWarnings("unchecked")
    private Mono<Map<String, Object>> post(String path, Map<String, Object> body) {
        return client.post().uri(path).bodyValue(body).retrieve()
            .onStatus(s -> s.value() == 404, resp -> resp.bodyToMono(Map.class).flatMap(b -> {
                Map<String, Object> detail = (Map<String, Object>) b.getOrDefault("detail", Map.of());
                String code = String.valueOf(detail.getOrDefault("code", ""));
                if ("AI_CAPABILITY_DISABLED".equals(code)) {
                    return Mono.error(new AiCapabilityDisabledException(detail));
                }
                return Mono.error(new AiUpstreamException(404, detail));
            }))
            .onStatus(s -> s.is5xxServerError(), resp -> resp.bodyToMono(Map.class)
                .flatMap(b -> Mono.error(new AiUpstreamException(502, (Map<String, Object>) b.getOrDefault("detail", Map.of())))))
            .bodyToMono(Map.class).map(m -> (Map<String, Object>) m);
    }
}
```

`apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/http/AiCapabilityDisabledException.java`:

```java
package io.filternarrange.gateway.infrastructure.http;

import java.util.Map;

public class AiCapabilityDisabledException extends RuntimeException {
    private final Map<String, Object> detail;
    public AiCapabilityDisabledException(Map<String, Object> detail) {
        super(String.valueOf(detail.getOrDefault("message", "")));
        this.detail = detail;
    }
    public Map<String, Object> detail() { return detail; }
}
```

`apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/http/AiUpstreamException.java`:

```java
package io.filternarrange.gateway.infrastructure.http;

import java.util.Map;

public class AiUpstreamException extends RuntimeException {
    private final int statusCode;
    private final Map<String, Object> detail;
    public AiUpstreamException(int statusCode, Map<String, Object> detail) {
        super(String.valueOf(detail.getOrDefault("message", "")));
        this.statusCode = statusCode;
        this.detail = detail;
    }
    public int statusCode() { return statusCode; }
    public Map<String, Object> detail() { return detail; }
}
```

If `dataEngineWebClient` bean isn't yet defined by Plan B, add it under `apps/gateway/src/main/java/io/filternarrange/gateway/platform/HttpConfig.java`:

```java
@Configuration
public class HttpConfig {
    @Bean("dataEngineWebClient")
    public WebClient dataEngineWebClient(
        @Value("${filternarrange.data-engine.base-url:http://data-engine:8000}") String baseUrl) {
        return WebClient.builder().baseUrl(baseUrl).build();
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/gateway && ./gradlew test --tests DataEngineAiClientTest
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/http/ \
        apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/http/
git commit -m "feat(gateway): add DataEngineAiClient with error mapping"
```

---

## Task 17: Gateway AiController + AiService + REST endpoints

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/application/AiService.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/AiController.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/api/AiControllerTest.java`

- [ ] **Step 1: Write the failing controller test**

`apps/gateway/src/test/java/io/filternarrange/gateway/api/AiControllerTest.java`:

```java
package io.filternarrange.gateway.api;

import io.filternarrange.gateway.infrastructure.http.AiCapabilityDisabledException;
import io.filternarrange.gateway.infrastructure.http.DataEngineAiClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import reactor.core.publisher.Mono;

import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@ActiveProfiles("test")
class AiControllerTest {

    @Autowired MockMvc mvc;
    @MockBean DataEngineAiClient client;

    @Test
    void postNlToFilter_returnsResult() throws Exception {
        when(client.nlToFilter(any())).thenReturn(Mono.just(Map.of(
            "filter_spec", Map.of("kind","row"), "confidence", 0.9)));
        mvc.perform(post("/api/v1/ai/nl-to-filter")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"ref\":\"x\",\"query\":\"q\"}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.confidence").value(0.9));
    }

    @Test
    void disabledCapability_returns404WithEnvelope() throws Exception {
        when(client.anomaly(any())).thenReturn(Mono.error(
            new AiCapabilityDisabledException(Map.of(
                "code","AI_CAPABILITY_DISABLED","message","off"))));
        mvc.perform(post("/api/v1/ai/anomaly")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"ref\":\"x\"}"))
            .andExpect(status().isNotFound())
            .andExpect(jsonPath("$.code").value("AI_CAPABILITY_DISABLED"));
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/gateway && ./gradlew test --tests AiControllerTest
```

Expected: compile error.

- [ ] **Step 3: Write service + controller**

`apps/gateway/src/main/java/io/filternarrange/gateway/application/AiService.java`:

```java
package io.filternarrange.gateway.application;

import io.filternarrange.gateway.infrastructure.http.DataEngineAiClient;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

import java.util.Map;

@Service
public class AiService {
    private final DataEngineAiClient client;

    public AiService(DataEngineAiClient client) { this.client = client; }

    public Mono<Map<String, Object>> nlToFilter(Map<String, Object> req) { return client.nlToFilter(req); }
    public Mono<Map<String, Object>> summary(Map<String, Object> req) { return client.summary(req); }
    public Mono<Map<String, Object>> chartSuggest(Map<String, Object> req) { return client.chartSuggest(req); }
    public Mono<Map<String, Object>> anomaly(Map<String, Object> req) { return client.anomaly(req); }
}
```

`apps/gateway/src/main/java/io/filternarrange/gateway/api/AiController.java`:

```java
package io.filternarrange.gateway.api;

import io.filternarrange.gateway.application.AiService;
import io.filternarrange.gateway.infrastructure.http.AiCapabilityDisabledException;
import io.filternarrange.gateway.infrastructure.http.AiUpstreamException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/ai")
public class AiController {
    private final AiService svc;

    public AiController(AiService svc) { this.svc = svc; }

    @PostMapping("/nl-to-filter")
    public Mono<Map<String, Object>> nlToFilter(@RequestBody Map<String, Object> body) { return svc.nlToFilter(body); }

    @PostMapping("/summary")
    public Mono<Map<String, Object>> summary(@RequestBody Map<String, Object> body) { return svc.summary(body); }

    @PostMapping("/chart-suggest")
    public Mono<Map<String, Object>> chartSuggest(@RequestBody Map<String, Object> body) { return svc.chartSuggest(body); }

    @PostMapping("/anomaly")
    public Mono<Map<String, Object>> anomaly(@RequestBody Map<String, Object> body) { return svc.anomaly(body); }

    @ExceptionHandler(AiCapabilityDisabledException.class)
    public ResponseEntity<Map<String, Object>> disabled(AiCapabilityDisabledException exc) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(envelope("AI_CAPABILITY_DISABLED", exc.getMessage()));
    }

    @ExceptionHandler(AiUpstreamException.class)
    public ResponseEntity<Map<String, Object>> upstream(AiUpstreamException exc) {
        HttpStatus s = exc.statusCode() == 404 ? HttpStatus.NOT_FOUND
                      : exc.statusCode() == 504 ? HttpStatus.GATEWAY_TIMEOUT
                      : HttpStatus.BAD_GATEWAY;
        return ResponseEntity.status(s).body(envelope(
            String.valueOf(exc.detail().getOrDefault("code", "AI_UPSTREAM_ERROR")), exc.getMessage()));
    }

    private Map<String, Object> envelope(String code, String message) {
        return Map.of("code", code, "plugin_id", "", "message", message,
                      "trace_id", UUID.randomUUID().toString());
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/gateway && ./gradlew test --tests AiControllerTest
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/application/AiService.java \
        apps/gateway/src/main/java/io/filternarrange/gateway/api/AiController.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/api/AiControllerTest.java
git commit -m "feat(gateway): add /api/v1/ai/* REST endpoints"
```

---

## Task 18: OpenAPI additive patch for /api/v1/ai/*

**Files:**
- Modify: `contracts/openapi/gateway-public.v1.yaml`

- [ ] **Step 1: Open the file**

`contracts/openapi/gateway-public.v1.yaml` already exists from Plan B. Locate the `paths:` block and append the following entries (do not modify any existing entries — purely additive):

```yaml
  /api/v1/ai/nl-to-filter:
    post:
      summary: Translate a natural-language query to a FilterSpec
      tags: [ai]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [ref, query]
              properties:
                ref: { type: string }
                query: { type: string, maxLength: 2000 }
                schema:
                  type: array
                  items: { type: object }
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                type: object
                required: [filter_spec, confidence]
                properties:
                  filter_spec: { type: object }
                  confidence: { type: number, minimum: 0, maximum: 1 }
        "404": { $ref: "#/components/responses/ErrorEnvelope" }
        "502": { $ref: "#/components/responses/ErrorEnvelope" }
        "504": { $ref: "#/components/responses/ErrorEnvelope" }
  /api/v1/ai/summary:
    post:
      summary: Generate a plain-English auto-summary of a dataset
      tags: [ai]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [ref, schema, sample_rows, total_rows, total_size_bytes]
              properties:
                ref: { type: string }
                schema: { type: array, items: { type: object } }
                sample_rows: { type: array, items: { type: object }, maxItems: 50 }
                total_rows: { type: integer }
                total_size_bytes: { type: integer }
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                type: object
                required: [summary, key_observations]
                properties:
                  summary: { type: string }
                  key_observations: { type: array, items: { type: string } }
        "404": { $ref: "#/components/responses/ErrorEnvelope" }
        "502": { $ref: "#/components/responses/ErrorEnvelope" }
        "504": { $ref: "#/components/responses/ErrorEnvelope" }
  /api/v1/ai/chart-suggest:
    post:
      summary: Suggest a chart for the dataset
      tags: [ai]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [ref, schema, cardinality_per_column]
              properties:
                ref: { type: string }
                schema: { type: array, items: { type: object } }
                cardinality_per_column:
                  type: object
                  additionalProperties: { type: integer }
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                type: object
                required: [recommended_chart]
                properties:
                  recommended_chart:
                    type: object
                    required: [kind, justification]
                    properties:
                      kind:
                        type: string
                        enum: [line, bar, pie, histogram, scatter, heatmap]
                      x: { type: string, nullable: true }
                      y: { type: string, nullable: true }
                      color: { type: string, nullable: true }
                      justification: { type: string }
        "404": { $ref: "#/components/responses/ErrorEnvelope" }
        "502": { $ref: "#/components/responses/ErrorEnvelope" }
        "504": { $ref: "#/components/responses/ErrorEnvelope" }
  /api/v1/ai/anomaly:
    post:
      summary: Detect anomalies and data-quality issues
      tags: [ai]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [ref, schema, sample_rows, summary_stats]
              properties:
                ref: { type: string }
                schema: { type: array, items: { type: object } }
                sample_rows: { type: array, items: { type: object } }
                summary_stats: { type: object }
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                type: object
                required: [findings]
                properties:
                  findings:
                    type: array
                    items:
                      type: object
                      required: [kind, severity, description]
                      properties:
                        kind:
                          type: string
                          enum: [outlier, missing_values, format_inconsistency, possible_duplicate, type_drift]
                        column: { type: string, nullable: true }
                        severity: { type: string, enum: [low, medium, high] }
                        description: { type: string }
                        suggested_action: { type: string, nullable: true }
        "404": { $ref: "#/components/responses/ErrorEnvelope" }
        "502": { $ref: "#/components/responses/ErrorEnvelope" }
        "504": { $ref: "#/components/responses/ErrorEnvelope" }
```

If `components.responses.ErrorEnvelope` does not yet exist (Plan B should have added it), add under `components: responses:`:

```yaml
    ErrorEnvelope:
      description: Standard error envelope
      content:
        application/json:
          schema:
            type: object
            required: [code, message, trace_id]
            properties:
              code: { type: string }
              plugin_id: { type: string, nullable: true }
              message: { type: string }
              trace_id: { type: string }
```

- [ ] **Step 2: Validate the spec**

```bash
npx --yes @stoplight/spectral-cli lint contracts/openapi/gateway-public.v1.yaml
```

Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add contracts/openapi/gateway-public.v1.yaml
git commit -m "feat(contracts): add /api/v1/ai/* to gateway-public.v1"
```

---

## Task 19: Long-running anomaly job (kind=ai-anomaly-full) — gateway side

**Files:**
- Modify: `apps/gateway/src/main/java/io/filternarrange/gateway/application/JobService.java` (exists from Plan D) — register new kind.
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/application/AiAnomalyFullJobTest.java`

- [ ] **Step 1: Write the failing test**

`apps/gateway/src/test/java/io/filternarrange/gateway/application/AiAnomalyFullJobTest.java`:

```java
package io.filternarrange.gateway.application;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@ActiveProfiles("test")
class AiAnomalyFullJobTest {
    @Autowired MockMvc mvc;

    @Test
    void anomalyFullJob_accepted() throws Exception {
        mvc.perform(post("/api/v1/jobs")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"kind\":\"ai-anomaly-full\",\"params\":{\"ref\":\"uploads/x.csv\"}}"))
            .andExpect(status().isAccepted())
            .andExpect(jsonPath("$.status").value("queued"))
            .andExpect(jsonPath("$.kind").value("ai-anomaly-full"));
    }

    @Test
    void unknownKind_isRejected() throws Exception {
        mvc.perform(post("/api/v1/jobs")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"kind\":\"telepathy\",\"params\":{}}"))
            .andExpect(status().isBadRequest());
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/gateway && ./gradlew test --tests AiAnomalyFullJobTest
```

Expected: FAIL — `ai-anomaly-full` not in the kind enum.

- [ ] **Step 3: Register the kind**

In `JobService.java`, find the `KNOWN_KINDS` constant (added by Plan D) and add `"ai-anomaly-full"` to it. Example:

```java
private static final Set<String> KNOWN_KINDS = Set.of(
    "convert", "analyze", "batch-filter", "ai-anomaly-full"
);
```

In the Kafka producer that emits on `topic.v1.jobs`, no change needed — the message already carries `kind` as a string. The Python worker (Plan D) registers a handler keyed by `kind`. We extend the worker:

`apps/data-engine/src/filternarrange_engine/adapters/kafka/job_handlers.py` (existing) — append:

```python
async def handle_ai_anomaly_full(job, deps):
    """Stream rows, build summary_stats, call AnomalyDetectCapability,
    write findings to MinIO under results/{job_id}.json."""
    from filternarrange_ai_anomaly_detect.plugin import AnomalyDetectCapability
    cap = AnomalyDetectCapability()
    payload = await deps.full_dataset_payload_for(job.params["ref"])
    findings = await cap.run(deps.llm, payload)
    await deps.minio.put_json(f"results/{job.id}.json", findings)
    return {"result_ref": f"results/{job.id}.json"}


JOB_HANDLERS["ai-anomaly-full"] = handle_ai_anomaly_full
```

`full_dataset_payload_for` is a helper added in the same file:

```python
async def _full_dataset_payload_for(ref: str, deps) -> dict:
    rows = await deps.read_all_rows(ref)
    return {
        "schema": deps.schema_of(rows),
        "sample_rows": rows[:200],
        "summary_stats": deps.summary_stats(rows),
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/gateway && ./gradlew test --tests AiAnomalyFullJobTest
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/application/JobService.java \
        apps/data-engine/src/filternarrange_engine/adapters/kafka/job_handlers.py \
        apps/gateway/src/test/java/io/filternarrange/gateway/application/AiAnomalyFullJobTest.java
git commit -m "feat(jobs): add ai-anomaly-full async job kind"
```

---

## Task 20: Frontend — AI api module

**Files:**
- Create: `apps/frontend/src/features/ai/api.ts`
- Test: `apps/frontend/src/features/ai/__tests__/api.test.ts`

- [ ] **Step 1: Write the failing test**

`apps/frontend/src/features/ai/__tests__/api.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { aiApi } from "../api";

describe("aiApi", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("nlToFilter posts the right body", async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true, status: 200, json: async () => ({ filter_spec: { kind: "row" }, confidence: 0.9 }),
    });
    const out = await aiApi.nlToFilter({ ref: "x", query: "q", schema: [] });
    expect(out.filter_spec.kind).toBe("row");
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/v1/ai/nl-to-filter", expect.objectContaining({
      method: "POST", headers: { "Content-Type": "application/json" },
    }));
  });

  it("maps AI_CAPABILITY_DISABLED to AiUnavailableError", async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: false, status: 404,
      json: async () => ({ code: "AI_CAPABILITY_DISABLED", message: "off" }),
    });
    await expect(aiApi.anomaly({ ref: "x" })).rejects.toMatchObject({ name: "AiUnavailableError" });
  });

  it("maps other errors to AiError", async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: false, status: 502, json: async () => ({ code: "AI_LLM_ERROR", message: "ouch" }),
    });
    await expect(aiApi.summary({ ref: "x" })).rejects.toMatchObject({ name: "AiError", code: "AI_LLM_ERROR" });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/frontend && npm run test -- --run src/features/ai/__tests__/api.test.ts
```

Expected: import error.

- [ ] **Step 3: Write the api module**

`apps/frontend/src/features/ai/api.ts`:

```ts
export type FilterSpec = {
  kind: "column" | "row" | "expression" | "regex";
  columns?: string[];
  predicate?: Record<string, unknown>;
  expression?: string;
  pattern?: string;
};

export type NlToFilterResponse = { filter_spec: FilterSpec; confidence: number };

export type SummaryResponse = { summary: string; key_observations: string[] };

export type ChartKind = "line" | "bar" | "pie" | "histogram" | "scatter" | "heatmap";
export type ChartSuggestion = {
  recommended_chart: { kind: ChartKind; x?: string | null; y?: string | null;
                        color?: string | null; justification: string };
};

export type AnomalyFinding = {
  kind: "outlier" | "missing_values" | "format_inconsistency" | "possible_duplicate" | "type_drift";
  column?: string | null;
  severity: "low" | "medium" | "high";
  description: string;
  suggested_action?: string | null;
};

export type AnomalyResponse = { findings: AnomalyFinding[] };

export class AiUnavailableError extends Error {
  override name = "AiUnavailableError";
  constructor(public code: string, message: string) { super(message); }
}
export class AiError extends Error {
  override name = "AiError";
  constructor(public code: string, message: string, public status: number) { super(message); }
}

async function call<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) {
    if (data.code === "AI_CAPABILITY_DISABLED") {
      throw new AiUnavailableError(data.code, data.message ?? "AI capability is disabled");
    }
    throw new AiError(data.code ?? "AI_ERROR", data.message ?? "AI error", r.status);
  }
  return data as T;
}

export const aiApi = {
  nlToFilter: (req: any) => call<NlToFilterResponse>("/api/v1/ai/nl-to-filter", req),
  summary: (req: any) => call<SummaryResponse>("/api/v1/ai/summary", req),
  chartSuggest: (req: any) => call<ChartSuggestion>("/api/v1/ai/chart-suggest", req),
  anomaly: (req: any) => call<AnomalyResponse>("/api/v1/ai/anomaly", req),
};
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/frontend && npm run test -- --run src/features/ai/__tests__/api.test.ts
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/features/ai/api.ts \
        apps/frontend/src/features/ai/__tests__/api.test.ts
git commit -m "feat(frontend): add AI API client with error mapping"
```

---

## Task 21: Frontend — AI Filter Mode tab

**Files:**
- Create: `apps/frontend/src/features/ai/ui/AiFilterMode.tsx`
- Modify: `apps/frontend/src/features/filter/ui/FilterModePicker.tsx`
- Create: `apps/frontend/src/features/ai/__tests__/AiFilterMode.test.tsx`

- [ ] **Step 1: Write the failing test**

`apps/frontend/src/features/ai/__tests__/AiFilterMode.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AiFilterMode } from "../ui/AiFilterMode";
import * as api from "../api";

describe("AiFilterMode", () => {
  it("submits the query and renders the returned spec", async () => {
    vi.spyOn(api.aiApi, "nlToFilter").mockResolvedValue({
      filter_spec: { kind: "row", predicate: { op: "gt", column: "age", value: 18 } } as any,
      confidence: 0.9,
    });
    const onApply = vi.fn();
    render(<AiFilterMode ref_={"x"} schema={[]} onApply={onApply} />);
    fireEvent.change(screen.getByPlaceholderText(/ask about your data/i),
                      { target: { value: "rows where age > 18" }});
    fireEvent.click(screen.getByText(/translate/i));
    await waitFor(() => expect(screen.getByText(/confidence/i)).toBeInTheDocument());
    fireEvent.click(screen.getByText(/apply/i));
    expect(onApply).toHaveBeenCalledWith(expect.objectContaining({ kind: "row" }));
  });

  it("shows AI unavailable message when capability disabled", async () => {
    vi.spyOn(api.aiApi, "nlToFilter").mockRejectedValue(
      new api.AiUnavailableError("AI_CAPABILITY_DISABLED", "off"));
    render(<AiFilterMode ref_={"x"} schema={[]} onApply={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/ask about your data/i),
                      { target: { value: "x" }});
    fireEvent.click(screen.getByText(/translate/i));
    await waitFor(() => expect(screen.getByText(/AI feature unavailable/i)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/frontend && npm run test -- --run src/features/ai/__tests__/AiFilterMode.test.tsx
```

Expected: import error.

- [ ] **Step 3: Write the components**

`apps/frontend/src/features/ai/ui/AiUnavailable.tsx`:

```tsx
import React from "react";

export function AiUnavailable({ message }: { message?: string }) {
  return (
    <div role="status" aria-live="polite" data-testid="ai-unavailable">
      AI feature unavailable.
      {message ? <div className="ai-unavailable__detail">{message}</div> : null}
    </div>
  );
}
```

`apps/frontend/src/features/ai/ui/AiFilterMode.tsx`:

```tsx
import React, { useState } from "react";
import { aiApi, AiUnavailableError, type FilterSpec } from "../api";
import { AiUnavailable } from "./AiUnavailable";

type Props = {
  ref_: string;
  schema: Array<{ name: string; type: string }>;
  onApply: (spec: FilterSpec) => void;
};

export function AiFilterMode({ ref_, schema, onApply }: Props) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ filter_spec: FilterSpec; confidence: number } | null>(null);
  const [unavailable, setUnavailable] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setLoading(true); setError(null); setUnavailable(null);
    try {
      const r = await aiApi.nlToFilter({ ref: ref_, query, schema });
      setResult(r);
    } catch (e: unknown) {
      if (e instanceof AiUnavailableError) setUnavailable(e.message);
      else if (e instanceof Error) setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (unavailable) return <AiUnavailable message={unavailable} />;

  return (
    <div data-testid="ai-filter-mode">
      <textarea
        placeholder="Ask about your data..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button onClick={submit} disabled={loading || !query.trim()}>
        {loading ? "Translating..." : "Translate"}
      </button>
      {error && <div role="alert">{error}</div>}
      {result && (
        <div>
          <div>Confidence: {(result.confidence * 100).toFixed(0)}%</div>
          <pre>{JSON.stringify(result.filter_spec, null, 2)}</pre>
          <button onClick={() => onApply(result.filter_spec)}>Apply</button>
        </div>
      )}
    </div>
  );
}
```

Modify `apps/frontend/src/features/filter/ui/FilterModePicker.tsx` — add a 5th tab. Locate the `MODES` array (or equivalent) and append:

```tsx
import { AiFilterMode } from "../../ai/ui/AiFilterMode";

const MODES = [
  // ...existing 4 modes...
  { id: "ai", label: "AI Filter", render: (ctx: any) =>
      <AiFilterMode ref_={ctx.ref} schema={ctx.schema} onApply={ctx.onApply} /> },
];
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/frontend && npm run test -- --run src/features/ai/__tests__/AiFilterMode.test.tsx
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/features/ai/ui/AiFilterMode.tsx \
        apps/frontend/src/features/ai/ui/AiUnavailable.tsx \
        apps/frontend/src/features/filter/ui/FilterModePicker.tsx \
        apps/frontend/src/features/ai/__tests__/AiFilterMode.test.tsx
git commit -m "feat(frontend): add AI Filter mode tab"
```

---

## Task 22: Frontend — Auto Summary + Chart Suggestion auto-trigger

**Files:**
- Create: `apps/frontend/src/features/ai/ui/AutoSummary.tsx`
- Create: `apps/frontend/src/features/ai/ui/ChartSuggestion.tsx`
- Modify: `apps/frontend/src/pages/AnalyzePage.tsx`
- Test: `apps/frontend/src/features/ai/__tests__/AutoSummary.test.tsx`
- Test: `apps/frontend/src/features/ai/__tests__/ChartSuggestion.test.tsx`

- [ ] **Step 1: Write the failing tests**

`apps/frontend/src/features/ai/__tests__/AutoSummary.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { AutoSummary } from "../ui/AutoSummary";
import * as api from "../api";

describe("AutoSummary", () => {
  it("auto-fetches and renders the summary", async () => {
    vi.spyOn(api.aiApi, "summary").mockResolvedValue({
      summary: "Sales by region", key_observations: ["IN is largest"],
    });
    render(<AutoSummary ref_="x" schema={[]} sampleRows={[]} totalRows={10} totalSizeBytes={100} skip={false} />);
    await waitFor(() => expect(screen.getByText(/Sales by region/)).toBeInTheDocument());
    expect(screen.getByText(/IN is largest/)).toBeInTheDocument();
  });

  it("does not call API when skip=true", async () => {
    const spy = vi.spyOn(api.aiApi, "summary").mockResolvedValue({ summary: "x", key_observations: [] });
    render(<AutoSummary ref_="x" schema={[]} sampleRows={[]} totalRows={0} totalSizeBytes={0} skip={true} />);
    await new Promise((r) => setTimeout(r, 10));
    expect(spy).not.toHaveBeenCalled();
  });

  it("renders AI unavailable on capability disabled", async () => {
    vi.spyOn(api.aiApi, "summary").mockRejectedValue(
      new api.AiUnavailableError("AI_CAPABILITY_DISABLED", "off"));
    render(<AutoSummary ref_="x" schema={[]} sampleRows={[]} totalRows={0} totalSizeBytes={0} skip={false} />);
    await waitFor(() => expect(screen.getByTestId("ai-unavailable")).toBeInTheDocument());
  });
});
```

`apps/frontend/src/features/ai/__tests__/ChartSuggestion.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { ChartSuggestion } from "../ui/ChartSuggestion";
import * as api from "../api";

describe("ChartSuggestion", () => {
  it("renders the suggested chart info", async () => {
    vi.spyOn(api.aiApi, "chartSuggest").mockResolvedValue({
      recommended_chart: { kind: "bar", x: "country", y: "count",
                           justification: "Categorical x with numeric y." }
    });
    render(<ChartSuggestion ref_="x" schema={[]} cardinality={{}} skip={false} />);
    await waitFor(() => expect(screen.getByText(/bar/i)).toBeInTheDocument());
    expect(screen.getByText(/Categorical x with numeric y\./)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd apps/frontend && npm run test -- --run src/features/ai/__tests__/AutoSummary.test.tsx src/features/ai/__tests__/ChartSuggestion.test.tsx
```

Expected: import error.

- [ ] **Step 3: Write the components**

`apps/frontend/src/features/ai/ui/AutoSummary.tsx`:

```tsx
import React, { useEffect, useState } from "react";
import { aiApi, AiUnavailableError, type SummaryResponse } from "../api";
import { AiUnavailable } from "./AiUnavailable";

type Props = {
  ref_: string;
  schema: Array<{ name: string; type: string }>;
  sampleRows: Array<Record<string, unknown>>;
  totalRows: number;
  totalSizeBytes: number;
  skip: boolean;
};

export function AutoSummary({ ref_, schema, sampleRows, totalRows, totalSizeBytes, skip }: Props) {
  const [data, setData] = useState<SummaryResponse | null>(null);
  const [unavailable, setUnavailable] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (skip) return;
    let cancelled = false;
    setLoading(true);
    aiApi.summary({ ref: ref_, schema, sample_rows: sampleRows,
                     total_rows: totalRows, total_size_bytes: totalSizeBytes })
      .then((r) => { if (!cancelled) setData(r); })
      .catch((e) => {
        if (cancelled) return;
        if (e instanceof AiUnavailableError) setUnavailable(e.message);
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ref_, skip, schema, sampleRows, totalRows, totalSizeBytes]);

  if (unavailable) return <AiUnavailable message={unavailable} />;
  if (loading) return <div data-testid="ai-summary-loading">Generating summary…</div>;
  if (!data) return null;

  return (
    <section data-testid="auto-summary">
      <h3>Summary</h3>
      <p>{data.summary}</p>
      {data.key_observations.length > 0 && (
        <ul>
          {data.key_observations.map((o, i) => <li key={i}>{o}</li>)}
        </ul>
      )}
    </section>
  );
}
```

`apps/frontend/src/features/ai/ui/ChartSuggestion.tsx`:

```tsx
import React, { useEffect, useState } from "react";
import { aiApi, AiUnavailableError, type ChartSuggestion as ChartSug } from "../api";
import { AiUnavailable } from "./AiUnavailable";

type Props = {
  ref_: string;
  schema: Array<{ name: string; type: string }>;
  cardinality: Record<string, number>;
  skip: boolean;
};

export function ChartSuggestion({ ref_, schema, cardinality, skip }: Props) {
  const [data, setData] = useState<ChartSug | null>(null);
  const [unavailable, setUnavailable] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (skip) return;
    let cancelled = false;
    setLoading(true);
    aiApi.chartSuggest({ ref: ref_, schema, cardinality_per_column: cardinality })
      .then((r) => { if (!cancelled) setData(r); })
      .catch((e) => {
        if (cancelled) return;
        if (e instanceof AiUnavailableError) setUnavailable(e.message);
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ref_, skip, schema, cardinality]);

  if (unavailable) return <AiUnavailable message={unavailable} />;
  if (loading) return <div data-testid="chart-suggest-loading">Suggesting chart…</div>;
  if (!data) return null;

  const c = data.recommended_chart;
  return (
    <section data-testid="chart-suggestion">
      <h3>Suggested chart</h3>
      <p><strong>{c.kind}</strong> — x={c.x ?? "—"} y={c.y ?? "—"} color={c.color ?? "—"}</p>
      <p>{c.justification}</p>
    </section>
  );
}
```

In `apps/frontend/src/pages/AnalyzePage.tsx`, mount these two components above the chart area. Locate the existing layout (created by Plan C / B) and add:

```tsx
import { AutoSummary } from "../features/ai/ui/AutoSummary";
import { ChartSuggestion } from "../features/ai/ui/ChartSuggestion";
import { useUserSettings } from "../features/account/state";  // assumed from Plan B

export function AnalyzePage(/* existing props */) {
  const settings = useUserSettings();
  const skipAi = settings.skipAi ?? false;
  // ...existing render...
  return (
    <>
      <AutoSummary ref_={ref} schema={schema} sampleRows={sampleRows.slice(0, 50)}
                    totalRows={totalRows} totalSizeBytes={totalSizeBytes} skip={skipAi} />
      <ChartSuggestion ref_={ref} schema={schema} cardinality={cardinality} skip={skipAi} />
      {/* existing charts / tabs */}
    </>
  );
}
```

If `useUserSettings` / `settings.skipAi` does not yet exist, add a minimal stub backed by `localStorage["fna.skipAi"] === "1"`:

`apps/frontend/src/features/account/state.ts` (extend or create):

```ts
export function useUserSettings() {
  return {
    skipAi: typeof window !== "undefined" && window.localStorage.getItem("fna.skipAi") === "1",
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd apps/frontend && npm run test -- --run src/features/ai/__tests__/AutoSummary.test.tsx src/features/ai/__tests__/ChartSuggestion.test.tsx
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/features/ai/ui/AutoSummary.tsx \
        apps/frontend/src/features/ai/ui/ChartSuggestion.tsx \
        apps/frontend/src/features/account/state.ts \
        apps/frontend/src/pages/AnalyzePage.tsx \
        apps/frontend/src/features/ai/__tests__/AutoSummary.test.tsx \
        apps/frontend/src/features/ai/__tests__/ChartSuggestion.test.tsx
git commit -m "feat(frontend): auto-trigger AI summary and chart suggestion"
```

---

## Task 23: Frontend — Anomalies panel

**Files:**
- Create: `apps/frontend/src/features/ai/ui/AnomaliesPanel.tsx`
- Modify: `apps/frontend/src/pages/AnalyzePage.tsx` (add an "Anomalies" tab)
- Test: `apps/frontend/src/features/ai/__tests__/AnomaliesPanel.test.tsx`

- [ ] **Step 1: Write the failing test**

`apps/frontend/src/features/ai/__tests__/AnomaliesPanel.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AnomaliesPanel } from "../ui/AnomaliesPanel";
import * as api from "../api";

describe("AnomaliesPanel", () => {
  it("loads and renders findings with severity icons", async () => {
    vi.spyOn(api.aiApi, "anomaly").mockResolvedValue({
      findings: [
        { kind: "missing_values", column: "email", severity: "medium", description: "30% null" },
        { kind: "outlier", column: "amount", severity: "high", description: "row 42 huge" },
      ],
    });
    render(<AnomaliesPanel ref_="x" schema={[]} sampleRows={[]} summaryStats={{}} />);
    fireEvent.click(screen.getByText(/scan for anomalies/i));
    await waitFor(() => expect(screen.getAllByTestId("finding")).toHaveLength(2));
    expect(screen.getByText(/30% null/)).toBeInTheDocument();
    expect(screen.getByText(/row 42 huge/)).toBeInTheDocument();
  });

  it("renders unavailable when capability disabled", async () => {
    vi.spyOn(api.aiApi, "anomaly").mockRejectedValue(
      new api.AiUnavailableError("AI_CAPABILITY_DISABLED", "off"));
    render(<AnomaliesPanel ref_="x" schema={[]} sampleRows={[]} summaryStats={{}} />);
    fireEvent.click(screen.getByText(/scan for anomalies/i));
    await waitFor(() => expect(screen.getByTestId("ai-unavailable")).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/frontend && npm run test -- --run src/features/ai/__tests__/AnomaliesPanel.test.tsx
```

Expected: import error.

- [ ] **Step 3: Write the component**

`apps/frontend/src/features/ai/ui/AnomaliesPanel.tsx`:

```tsx
import React, { useState } from "react";
import { aiApi, AiUnavailableError, type AnomalyFinding } from "../api";
import { AiUnavailable } from "./AiUnavailable";

type Props = {
  ref_: string;
  schema: Array<{ name: string; type: string }>;
  sampleRows: Array<Record<string, unknown>>;
  summaryStats: Record<string, unknown>;
};

const SEVERITY_ICON = { low: "·", medium: "!", high: "!!" };

export function AnomaliesPanel({ ref_, schema, sampleRows, summaryStats }: Props) {
  const [findings, setFindings] = useState<AnomalyFinding[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [unavailable, setUnavailable] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const scan = async () => {
    setLoading(true); setError(null); setUnavailable(null);
    try {
      const r = await aiApi.anomaly({ ref: ref_, schema, sample_rows: sampleRows, summary_stats: summaryStats });
      setFindings(r.findings);
    } catch (e: unknown) {
      if (e instanceof AiUnavailableError) setUnavailable(e.message);
      else if (e instanceof Error) setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (unavailable) return <AiUnavailable message={unavailable} />;

  return (
    <section data-testid="anomalies-panel">
      <button onClick={scan} disabled={loading}>{loading ? "Scanning…" : "Scan for anomalies"}</button>
      {error && <div role="alert">{error}</div>}
      {findings && (
        <ul>
          {findings.map((f, i) => (
            <li key={i} data-testid="finding" data-severity={f.severity}>
              <span aria-label={`severity ${f.severity}`}>{SEVERITY_ICON[f.severity]}</span>
              <strong>{f.kind}</strong>{f.column ? ` · ${f.column}` : ""} — {f.description}
              {f.suggested_action ? <em> Suggestion: {f.suggested_action}</em> : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
```

Add an "Anomalies" tab to `AnalyzePage.tsx`. Wherever the existing tabs are declared, add:

```tsx
import { AnomaliesPanel } from "../features/ai/ui/AnomaliesPanel";
// ...
const TABS = [
  // ...existing...
  { id: "anomalies", label: "Anomalies", render: (ctx: any) =>
      <AnomaliesPanel ref_={ctx.ref} schema={ctx.schema} sampleRows={ctx.sampleRows}
                       summaryStats={ctx.summaryStats} /> },
];
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/frontend && npm run test -- --run src/features/ai/__tests__/AnomaliesPanel.test.tsx
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/features/ai/ui/AnomaliesPanel.tsx \
        apps/frontend/src/pages/AnalyzePage.tsx \
        apps/frontend/src/features/ai/__tests__/AnomaliesPanel.test.tsx
git commit -m "feat(frontend): add Anomalies panel"
```

---

## Task 24: Frontend — feature index barrel

**Files:**
- Create: `apps/frontend/src/features/ai/index.ts`
- Create: `apps/frontend/src/features/ai/state.ts`

- [ ] **Step 1: Write the barrel + minimal state**

`apps/frontend/src/features/ai/state.ts`:

```ts
// Reserved for future shared AI state (e.g., last-used model preference).
// Empty in v1 — kept so feature folder boundary is unambiguous.
export const aiStateVersion = 1;
```

`apps/frontend/src/features/ai/index.ts`:

```ts
export { AiFilterMode } from "./ui/AiFilterMode";
export { AutoSummary } from "./ui/AutoSummary";
export { ChartSuggestion } from "./ui/ChartSuggestion";
export { AnomaliesPanel } from "./ui/AnomaliesPanel";
export { AiUnavailable } from "./ui/AiUnavailable";
export { aiApi, AiError, AiUnavailableError } from "./api";
export type { FilterSpec, SummaryResponse, ChartSuggestion as ChartSuggestionType,
              AnomalyFinding, AnomalyResponse, NlToFilterResponse, ChartKind } from "./api";
```

- [ ] **Step 2: Run the full frontend test suite**

```bash
cd apps/frontend && npm run test -- --run src/features/ai
```

Expected: all AI tests pass.

- [ ] **Step 3: Commit**

```bash
git add apps/frontend/src/features/ai/index.ts apps/frontend/src/features/ai/state.ts
git commit -m "chore(frontend): add AI feature barrel"
```

---

## Task 25: Concurrency test — 10 in-flight NL→filter requests cap at 4

**Files:**
- Create: `apps/data-engine/tests/integration/test_ai_concurrency.py`

- [ ] **Step 1: Write the failing test**

```python
import asyncio
import pytest

from filternarrange_engine.application.ai_orchestrator import AiOrchestrator
from filternarrange_engine.adapters.llm.registry import AiCapabilityRegistry
from filternarrange_engine.adapters.llm.cache import AiCache
from filternarrange_engine.adapters.llm.mock import MockLLMProvider


class _InMemRedis:
    def __init__(self): self.data: dict[str, str] = {}
    async def get(self, k): return self.data.get(k)
    async def set(self, k, v, *, ex=None): self.data[k] = v


@pytest.mark.asyncio
async def test_semaphore_caps_concurrent_calls_at_four():
    current = 0
    peak = 0
    lock = asyncio.Lock()

    class _Cap:
        name = "nl_to_filter"
        required_tier = "free"
        default_model_setting = "nl_to_filter"
        async def run(self, llm, payload):
            nonlocal current, peak
            async with lock:
                current += 1
                peak = max(peak, current)
            await asyncio.sleep(0.08)
            async with lock:
                current -= 1
            return {"filter_spec": {"kind": "row"}, "confidence": 0.5}

    cap = _Cap()
    reg = AiCapabilityRegistry({cap.name: cap})
    cache = AiCache(redis=_InMemRedis(), ttl_seconds=3600)
    orch = AiOrchestrator(registry=reg, llm=MockLLMProvider(), cache=cache,
                          max_concurrent=4, models={"nl_to_filter": "qwen2.5:7b"})

    # 10 distinct payloads (avoid cache hits)
    coros = [orch.run("nl_to_filter", {"q": i}) for i in range(10)]
    results = await asyncio.gather(*coros)
    assert all(r.result["filter_spec"]["kind"] == "row" for r in results)
    assert peak <= 4
```

- [ ] **Step 2: Run test to verify it passes**

```bash
cd apps/data-engine && uv run pytest tests/integration/test_ai_concurrency.py -v
```

Expected: 1 passed.

- [ ] **Step 3: Commit**

```bash
git add apps/data-engine/tests/integration/test_ai_concurrency.py
git commit -m "test(data-engine): semaphore caps concurrent AI calls at AI_MAX_CONCURRENT"
```

---

## Task 26: End-to-end Playwright test — AI Filter flow

**Files:**
- Create: `apps/frontend/e2e/ai-filter.spec.ts`

- [ ] **Step 1: Write the e2e test**

`apps/frontend/e2e/ai-filter.spec.ts`:

```ts
import { test, expect } from "@playwright/test";

test("AI filter mode translates a query and applies the spec", async ({ page }) => {
  // The dev compose stack pre-seeds a small CSV upload; navigate to it.
  await page.goto("/upload/seeded-sample-csv");
  await expect(page.getByTestId("upload-detected")).toBeVisible();

  // Switch to the AI Filter tab (5th tab)
  await page.getByRole("tab", { name: /AI Filter/i }).click();
  await page.getByPlaceholder(/ask about your data/i).fill("rows where age > 18");
  await page.getByRole("button", { name: /translate/i }).click();

  // Confidence appears within 10s (real Ollama call; test scoped to e2e profile)
  await expect(page.getByText(/Confidence:/)).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: /apply/i }).click();

  // Preview pane reflects applied filter
  await expect(page.getByTestId("filter-preview")).toContainText(/age/);
});
```

This test runs in the `e2e` Playwright project only on the nightly job that brings up the full compose stack (with Ollama models pre-pulled), per spec §7.5.

- [ ] **Step 2: Run e2e locally (optional, requires compose stack + Ollama up)**

```bash
docker compose -f infra/docker-compose.yml up -d
ollama pull llama3.1:8b && ollama pull qwen2.5:7b
cd apps/frontend && npx playwright test ai-filter.spec.ts
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add apps/frontend/e2e/ai-filter.spec.ts
git commit -m "test(e2e): playwright AI filter happy path"
```

---

## Task 27: Documentation update — module READMEs

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/adapters/llm/README.md`
- Create: `plugins/ai-nl-to-filter/README.md`
- Create: `plugins/ai-auto-summary/README.md`
- Create: `plugins/ai-chart-suggest/README.md`
- Create: `plugins/ai-anomaly-detect/README.md`

- [ ] **Step 1: Write each README**

`apps/data-engine/src/filternarrange_engine/adapters/llm/README.md`:

```markdown
# LLM adapters

**Purpose:** Concrete implementations of the `LLMProvider` Protocol from
`filternarrange_engine.core.llm`.

**Public API:**
- `OllamaProvider` — Ollama HTTP API client (default in v1)
- `MockLLMProvider` — test double; deterministic canned responses
- `AiCache` — Redis cache wrapper keyed by canonical-hashed payloads
- `AiCapabilityRegistry` — entry-point discovery + disable filter

**Dependencies:** httpx (async), jsonschema, redis (asyncio API).

**Consumed by:** `application/ai_orchestrator.py`, `api/ai_routes.py`.

**Limitations:**
- Only Ollama in v1. HuggingFace local provider is future work.
- OpenAI/Anthropic deliberately not implemented — OSS-only constraint.
```

`plugins/ai-nl-to-filter/README.md` (and repeat structure for the other three with their specifics):

```markdown
# ai-nl-to-filter

Translates a natural-language query into a structured `FilterSpec`.

**Capability name (entry-point):** `nl_to_filter`
**Default model:** `qwen2.5:7b` (override with `NL2FILTER_MODEL`)
**Required tier:** `free`

**Input:**
```json
{ "ref": "uploads/.../file.csv", "query": "rows where age > 18",
  "schema": [{"name": "age", "type": "integer"}] }
```

**Output:**
```json
{ "filter_spec": { "kind": "row", "predicate": {...} }, "confidence": 0.0..1.0 }
```

`plugins/ai-auto-summary/README.md`:

```markdown
# ai-auto-summary

Generates a plain-English summary plus key observations.

**Capability name:** `auto_summary`
**Default model:** `llama3.1:8b` (override with `SUMMARY_MODEL`)
**Required tier:** `free`

**Input:** `{schema, sample_rows[<=50], total_rows, total_size_bytes}`
**Output:** `{summary, key_observations[]}`
```

`plugins/ai-chart-suggest/README.md`:

```markdown
# ai-chart-suggest

Suggests the single most useful chart for a dataset.

**Capability name:** `chart_suggest`
**Default model:** `llama3.1:8b` (override with `CHART_MODEL`)
**Required tier:** `free`

**Input:** `{schema, cardinality_per_column}`
**Output:** `{recommended_chart: {kind, x?, y?, color?, justification}}`
where `kind ∈ {line, bar, pie, histogram, scatter, heatmap}`.
```

`plugins/ai-anomaly-detect/README.md`:

```markdown
# ai-anomaly-detect

Flags outliers, missing values, format inconsistencies, possible duplicates,
and type drift.

**Capability name:** `anomaly_detect`
**Default model:** `llama3.1:8b` (override with `ANOMALY_MODEL`)
**Required tier:** `free`

**Input:** `{schema, sample_rows, summary_stats}`
**Output:** `{findings: [{kind, column?, severity, description, suggested_action?}]}`
where `kind ∈ {outlier, missing_values, format_inconsistency, possible_duplicate, type_drift}`
and `severity ∈ {low, medium, high}`.

For full-dataset scans (not bounded by sample size), submit
`POST /api/v1/jobs` with `kind: "ai-anomaly-full"`.
```

- [ ] **Step 2: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/adapters/llm/README.md \
        plugins/ai-nl-to-filter/README.md \
        plugins/ai-auto-summary/README.md \
        plugins/ai-chart-suggest/README.md \
        plugins/ai-anomaly-detect/README.md
git commit -m "docs: add AI module/plugin READMEs"
```

---

## Task 28: Final sweep — run all suites, verify green

- [ ] **Step 1: Data-engine full suite**

```bash
cd apps/data-engine && uv run pytest -v
```

Expected: all green (unit + integration; real-Ollama suite SKIPPED).

- [ ] **Step 2: Plugin suites**

```bash
for d in plugins/ai-nl-to-filter plugins/ai-auto-summary plugins/ai-chart-suggest plugins/ai-anomaly-detect; do
  echo "== $d ==" && (cd "$d" && pytest -v) || break
done
```

Expected: all green.

- [ ] **Step 3: Gateway tests**

```bash
cd apps/gateway && ./gradlew test
```

Expected: all green.

- [ ] **Step 4: Frontend tests**

```bash
cd apps/frontend && npm run test -- --run
```

Expected: all green.

- [ ] **Step 5: OpenAPI lint**

```bash
npx --yes @stoplight/spectral-cli lint contracts/openapi/gateway-public.v1.yaml
```

Expected: 0 errors.

- [ ] **Step 6: Architecture lint**

```bash
cd apps/data-engine && uv run lint-imports
```

Expected: 0 violations (AI modules respect domain → application → adapters direction).

- [ ] **Step 7: Final commit (if anything changed during sweep)**

```bash
git status   # should be clean
```

No commit needed if clean.

---

## Self-Review Notes

**Spec coverage (against the brief and §1/§4 of the spec):**

| Requirement | Task(s) |
|---|---|
| `LLMProvider` Protocol | Task 2 |
| `OllamaProvider` via `/api/generate` + structured output | Task 4 |
| `ai-nl-to-filter` plugin | Task 11 |
| `ai-auto-summary` plugin | Task 8 |
| `ai-chart-suggest` plugin | Task 9 |
| `ai-anomaly-detect` plugin | Task 10 |
| `AICapability` Protocol + registry dispatch | Tasks 2, 6 |
| `ai-async` semaphore, `AI_MAX_CONCURRENT=4` default | Tasks 1, 7, 25 |
| Per-capability disable via `FILTERNARRANGE_DISABLED_AI` | Tasks 1, 6, 13 |
| Per-capability model env vars (`NL2FILTER_MODEL`, `SUMMARY_MODEL`, `CHART_MODEL`, `ANOMALY_MODEL`) | Task 1 |
| Redis cache `py:cache:ai:{capability}:{sha256(canonical)}` 1h TTL | Tasks 5, 14 |
| Temperature pinned to 0 | Task 4 |
| Data-engine HTTP endpoints `/ai/*` | Tasks 12, 13 |
| Gateway `/api/v1/ai/*` pass-throughs | Tasks 16, 17 |
| OpenAPI additive patch | Task 18 |
| Async full-dataset anomaly via `POST /api/v1/jobs` `kind=ai-anomaly-full` | Task 19 |
| AI Filter UI tab (5th) | Task 21 |
| Auto-trigger summary + chart suggest on upload | Task 22 |
| Anomalies tab | Task 23 |
| "Skip AI" user setting | Task 22 |
| "AI feature unavailable" with no churn | Tasks 21, 22, 23 |
| MockLLMProvider for unit tests | Task 3 |
| Real Ollama integration test gated by `RUN_OLLAMA_TESTS=1` | Task 15 |
| Schema validation rejects bad LLM output | Tasks 4, 8, 9, 10, 11, 12 |
| Cache deduplication test | Task 14 |
| Disabled-capability returns 404 | Tasks 12, 13 |
| Concurrency cap test (10 → peak ≤ 4) | Task 25 |
| Per-capability error envelope `{code, plugin_id?, message, trace_id}` | Tasks 12, 17 |
| Ollama timeout 30s (§6) | Tasks 1, 4 |

**Out-of-scope items deferred:**
- Tier gating (free vs paid) of AI features → Plan F.
- HuggingFace local provider → future.
- OpenAI/Anthropic providers → excluded by OSS-only constraint.
- Embedding-driven use cases beyond the `embed()` protocol method → future.

**Type consistency check:**
- `AICapability` properties (`name`, `required_tier`, `default_model_setting`, `run`) match across the Protocol (Task 2), all four plugins (Tasks 8–11), and the registry (Task 6).
- `FilterSpec.kind` values (`column | row | expression | regex`) match between the NL→filter plugin schema (Task 11) and the frontend TS type (Task 20).
- `ChartKind` enum matches between `CHART_KINDS` Python list (Task 9), OpenAPI enum (Task 18), and TS type (Task 20).
- Anomaly `FINDING_KINDS` matches between Python (Task 10), OpenAPI enum (Task 18), and TS type (Task 20).
- `severity` enum (`low | medium | high`) matches in all three places.
- Error code strings (`AI_CAPABILITY_DISABLED`, `AI_LLM_OUTPUT_INVALID`, `AI_LLM_TIMEOUT`, `AI_LLM_ERROR`) match between data-engine (Task 12), gateway exception mapping (Tasks 16, 17), and frontend api (Task 20).

**Cross-plan dependencies:**
- Plan A: `ollama-init` must pull `llama3.1:8b` AND `qwen2.5:7b` before integration tests can pass.
- Plan B: `create_app` factory, error-envelope `components.responses.ErrorEnvelope`, gateway WebClient bean.
- Plan C: `filternarrange_filter_core.schema.FILTER_SPEC_SCHEMA` is imported by ai-nl-to-filter. A fallback inline schema is provided in Task 11 to allow the plugin to ship/test before Plan C lands; once Plan C is in, the import path takes over without code change.
- Plan D: `POST /api/v1/jobs`, the Kafka worker job-handler registry, `JOB_HANDLERS` dict, and a `deps` object exposing `llm`, `minio`, `read_all_rows`, `schema_of`, `summary_stats` on the worker side.

Any drift in the above contracts must surface as a CI failure (architecture/contract lint), not silent runtime breakage.
