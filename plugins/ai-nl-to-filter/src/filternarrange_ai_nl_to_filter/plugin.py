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
        out = await llm.complete(
            build_prompt(dict(payload)),
            schema=NL2FILTER_OUTPUT_SCHEMA,
            system=SYSTEM,
        )
        assert isinstance(out, dict)
        return out
