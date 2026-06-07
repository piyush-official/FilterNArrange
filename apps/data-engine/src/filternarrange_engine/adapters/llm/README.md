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
