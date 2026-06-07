"""Deterministic LLM provider for unit tests."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator, ValidationError

from filternarrange_engine.core.llm import (
    JsonSchema,
    SchemaValidationError,
    Vector,
)


@dataclass
class _Call:
    prompt: str
    model: str | None
    schema: JsonSchema | None
    system: str | None


class MockLLMProvider:
    """Returns canned responses and records every call for assertions.

    Validates structured responses against the caller-provided schema so
    capability tests catch malformed canned data the same way a real
    provider would.
    """

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
        self,
        prompt: str,
        *,
        schema: JsonSchema | None = None,
        model: str | None = None,
        system: str | None = None,
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

    async def embed(
        self, texts: Sequence[str], *, model: str | None = None
    ) -> list[Vector]:
        self.calls.append(
            _Call(prompt=f"<embed {len(texts)}>", model=model, schema=None, system=None)
        )
        return list(self.embed_response)


__all__ = ["MockLLMProvider"]
