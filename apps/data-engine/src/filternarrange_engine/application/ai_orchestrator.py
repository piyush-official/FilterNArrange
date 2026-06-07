"""AI orchestrator (Plan E §6).

Single entry-point for AI capability execution. Applies the three things every
caller needs: cache lookup, bounded concurrency, and model selection — so the
capability plugins themselves stay free of cross-cutting concerns.
"""
from __future__ import annotations

import asyncio
from typing import Mapping

from filternarrange_engine.adapters.llm.cache import AiCache
from filternarrange_engine.adapters.llm.registry import AiCapabilityRegistry
from filternarrange_engine.core.llm import AIOutput, JsonSchema, LLMProvider


class _ModelPinnedLlm:
    """Wraps an LLMProvider so capabilities don't need to know their model name."""

    def __init__(self, inner: LLMProvider, model: str | None) -> None:
        self._inner = inner
        self._model = model

    async def complete(
        self,
        prompt: str,
        *,
        schema: JsonSchema | None = None,
        model: str | None = None,
        system: str | None = None,
    ):
        return await self._inner.complete(
            prompt,
            schema=schema,
            model=model or self._model,
            system=system,
        )

    async def embed(self, texts, *, model: str | None = None):
        return await self._inner.embed(texts, model=model or self._model)


class AiOrchestrator:
    def __init__(
        self,
        *,
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
        cap = self._registry.get(capability_name)
        cached = await self._cache.get(capability_name, payload)
        if cached is not None:
            return AIOutput(
                capability=capability_name,
                result=cached,
                model=self._models.get(capability_name),
                cache_hit=True,
            )
        async with self._sem:
            pinned = _ModelPinnedLlm(self._llm, self._models.get(capability_name))
            result = await cap.run(pinned, payload)
        await self._cache.set(capability_name, payload, result)
        return AIOutput(
            capability=capability_name,
            result=result,
            model=self._models.get(capability_name),
            cache_hit=False,
        )


__all__ = ["AiOrchestrator"]
