"""LLMProvider implementation talking to Ollama's HTTP API (Plan E §6).

Uses ``POST /api/generate`` with ``format: "json"`` when a JSON schema is
supplied; uses ``POST /api/embeddings`` for embeddings. Temperature is
pinned to 0 for deterministic, cacheable, repeatable structured output.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

import httpx
from jsonschema import Draft202012Validator, ValidationError

from filternarrange_engine.core.llm import (
    JsonSchema,
    LLMError,
    LLMTimeoutError,
    SchemaValidationError,
    Vector,
)


class OllamaProvider:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: int = 30,
        default_model: str = "llama3.1:8b",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._default_model = default_model
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "OllamaProvider":
        self._client = httpx.AsyncClient(
            base_url=self._base_url, timeout=self._timeout
        )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _client_or_raise(self) -> httpx.AsyncClient:
        if self._client is None:
            raise LLMError(
                "OllamaProvider must be used as an async context manager"
            )
        return self._client

    async def complete(
        self,
        prompt: str,
        *,
        schema: JsonSchema | None = None,
        model: str | None = None,
        system: str | None = None,
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
            raise LLMTimeoutError(
                f"ollama timed out after {self._timeout}s"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"ollama transport error: {exc}") from exc

        if resp.status_code >= 400:
            raise LLMError(
                f"ollama returned HTTP {resp.status_code}: {resp.text}"
            )
        data = resp.json()
        text = data.get("response", "")

        if schema is None:
            return text

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SchemaValidationError(
                f"ollama returned non-JSON output: {text!r}"
            ) from exc

        try:
            Draft202012Validator(schema).validate(parsed)
        except ValidationError as exc:
            raise SchemaValidationError(str(exc)) from exc

        return parsed

    async def embed(
        self, texts: Sequence[str], *, model: str | None = None
    ) -> list[Vector]:
        client = self._client_or_raise()
        m = model or self._default_model
        out: list[Vector] = []
        for t in texts:
            try:
                resp = await client.post(
                    "/api/embeddings", json={"model": m, "prompt": t}
                )
            except httpx.TimeoutException as exc:
                raise LLMTimeoutError("ollama embed timed out") from exc
            if resp.status_code >= 400:
                raise LLMError(
                    f"ollama embed HTTP {resp.status_code}: {resp.text}"
                )
            out.append(list(resp.json().get("embedding", [])))
        return out


__all__ = ["OllamaProvider"]
