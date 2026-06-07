"""Analysis spec, result envelope, and AnalysisPlugin protocol."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol, Union, runtime_checkable

from .canonical import TabularData, TreeData


@dataclass(frozen=True)
class AnalysisSpec:
    kind: str
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AnalysisResult:
    kind: str
    payload: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


def parse_analysis_spec(payload: dict) -> AnalysisSpec:
    return AnalysisSpec(kind=payload["kind"], options=dict(payload.get("options", {})))


@runtime_checkable
class AnalysisPlugin(Protocol):
    manifest: Any

    def analyze(self, data: Union[TabularData, TreeData], options: dict) -> AnalysisResult: ...
    def validate(self, spec: AnalysisSpec, schema: list | None = None) -> list[str]: ...


__all__ = [
    "AnalysisSpec", "AnalysisResult", "parse_analysis_spec", "AnalysisPlugin",
]
