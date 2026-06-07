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
        out = await llm.complete(
            build_prompt(dict(payload)),
            schema=CHART_OUTPUT_SCHEMA,
            system=SYSTEM,
        )
        assert isinstance(out, dict)
        return out
