"""Pydantic models — mirror gateway-internal.v1.yaml."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class RefRequest(BaseModel):
    ref: str


class Column(BaseModel):
    name: str
    type: str
    nullable: bool


class DetectResponse(BaseModel):
    format: str
    confidence: float
    schema_: list[Column] = Field(alias="schema")

    model_config = {"populate_by_name": True}


class ColumnFilterSpec(BaseModel):
    kind: str
    keep: list[str]


class FilterRequest(BaseModel):
    """Plan C extends the filter contract to a generic dict so column / row /
    expression / regex specs all flow through the same route. The dispatcher
    validates per-kind."""
    ref: str
    filter: dict[str, Any]
    sampleSize: int = 20


class FilterResponse(BaseModel):
    schema_: list[Column] = Field(alias="schema")
    rows: list[dict[str, Any]]
    model_config = {"populate_by_name": True}


class ConvertRequest(BaseModel):
    ref: str
    filter: ColumnFilterSpec
    outputFormat: str


class ConvertResponse(BaseModel):
    resultRef: str


class AnalyzeRequest(BaseModel):
    ref: str
    analysis: dict[str, Any]
    filter: dict[str, Any] | None = None


class AnalyzeResponse(BaseModel):
    kind: str
    payload: dict[str, Any]
    warnings: list[str]


class ErrorEnvelope(BaseModel):
    code: str
    pluginId: str | None = None
    message: str
    traceId: str
