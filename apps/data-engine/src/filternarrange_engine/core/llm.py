"""Core LLM contracts for Plan E AI capabilities.

These types form the boundary between the LLM runtime (Ollama or a mock),
the AI capabilities (pip-installed plugins), and the orchestrator. Everything
exchanged across the boundary is plain data; nothing in :mod:`core` knows
about HTTP, Redis, or FastAPI.
"""
from __future__ import annotations

from dataclasses import dataclass
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
        self,
        prompt: str,
        *,
        schema: JsonSchema | None = None,
        model: str | None = None,
        system: str | None = None,
    ) -> str | Mapping[str, Any]:
        """Run a completion.

        When ``schema`` is non-None, the provider must return a dict that
        validates against the schema; otherwise it must return the raw text.
        Any validation failure surfaces as :class:`SchemaValidationError`.
        """
        ...

    async def embed(
        self, texts: Sequence[str], *, model: str | None = None
    ) -> list[Vector]:
        ...


class AICapability(Protocol):
    name: str
    required_tier: str
    default_model_setting: str

    async def run(
        self, llm: LLMProvider, payload: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        ...


__all__ = [
    "JsonSchema",
    "Vector",
    "LLMError",
    "SchemaValidationError",
    "LLMTimeoutError",
    "AIInput",
    "AIOutput",
    "LLMProvider",
    "AICapability",
]
