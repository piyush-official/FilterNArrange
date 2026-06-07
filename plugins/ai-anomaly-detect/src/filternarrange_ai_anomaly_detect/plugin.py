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
        out = await llm.complete(
            build_prompt(dict(payload)),
            schema=ANOMALY_OUTPUT_SCHEMA,
            system=SYSTEM,
        )
        assert isinstance(out, dict)
        return out
