"""HTTP surface for AI capabilities (Plan E §T12).

Routes are thin envelopes: parse request → dispatch to the orchestrator →
return the capability's result dict. Cross-cutting concerns (cache, model
selection, concurrency) live in the orchestrator; capability-specific shape
validation lives in each plugin's schema.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Mapping

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from filternarrange_engine.adapters.llm.registry import CapabilityNotFoundError
from filternarrange_engine.core.llm import (
    LLMError,
    LLMTimeoutError,
    SchemaValidationError,
)

_log = logging.getLogger(__name__)


# Pydantic v2 reserves ``schema`` as a BaseModel method, so we name the field
# ``data_schema`` and alias it to ``schema`` on the wire. populate_by_name keeps
# constructor calls in unit tests working with the Python-side attribute name.
_REQUEST_MODEL_CONFIG = ConfigDict(populate_by_name=True)


class NlToFilterRequest(BaseModel):
    model_config = _REQUEST_MODEL_CONFIG
    ref: str
    query: str = Field(min_length=1, max_length=2000)
    data_schema: list[dict] = Field(default_factory=list, alias="schema")


class SummaryRequest(BaseModel):
    model_config = _REQUEST_MODEL_CONFIG
    ref: str
    data_schema: list[dict] = Field(alias="schema")
    sample_rows: list[dict]
    total_rows: int
    total_size_bytes: int


class ChartSuggestRequest(BaseModel):
    model_config = _REQUEST_MODEL_CONFIG
    ref: str
    data_schema: list[dict] = Field(alias="schema")
    cardinality_per_column: dict[str, int]


class AnomalyRequest(BaseModel):
    model_config = _REQUEST_MODEL_CONFIG
    ref: str
    data_schema: list[dict] = Field(alias="schema")
    sample_rows: list[dict]
    summary_stats: dict[str, Any]


def _err_envelope(
    code: str, message: str, plugin_id: str | None = None
) -> dict:
    return {
        "code": code,
        "plugin_id": plugin_id,
        "message": message,
        "trace_id": str(uuid.uuid4()),
    }


def build_ai_router(orchestrator, enabled_names: set[str]) -> APIRouter:
    router = APIRouter(tags=["ai"])

    def _guard(name: str) -> None:
        if name not in enabled_names:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_err_envelope(
                    "AI_CAPABILITY_DISABLED",
                    f"AI capability '{name}' is disabled by configuration",
                    plugin_id=name,
                ),
            )

    async def _run(name: str, payload: Mapping) -> Mapping:
        _guard(name)
        try:
            out = await orchestrator.run(name, payload)
            return out.result
        except CapabilityNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=_err_envelope(
                    "AI_CAPABILITY_NOT_FOUND", str(exc), plugin_id=name
                ),
            )
        except SchemaValidationError as exc:
            raise HTTPException(
                status_code=502,
                detail=_err_envelope(
                    "AI_LLM_OUTPUT_INVALID", str(exc), plugin_id=name
                ),
            )
        except LLMTimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail=_err_envelope(
                    "AI_LLM_TIMEOUT", str(exc), plugin_id=name
                ),
            )
        except LLMError as exc:
            raise HTTPException(
                status_code=502,
                detail=_err_envelope(
                    "AI_LLM_ERROR", str(exc), plugin_id=name
                ),
            )

    @router.post("/nl-to-filter")
    async def nl_to_filter(req: NlToFilterRequest):
        return await _run("nl_to_filter", req.model_dump(by_alias=True))

    @router.post("/summary")
    async def summary(req: SummaryRequest):
        return await _run("auto_summary", req.model_dump(by_alias=True))

    @router.post("/chart-suggest")
    async def chart_suggest(req: ChartSuggestRequest):
        return await _run("chart_suggest", req.model_dump(by_alias=True))

    @router.post("/anomaly")
    async def anomaly(req: AnomalyRequest):
        return await _run("anomaly_detect", req.model_dump(by_alias=True))

    return router


__all__ = ["build_ai_router"]
