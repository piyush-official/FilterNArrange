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
