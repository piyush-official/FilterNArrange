"""Plugin contracts.

Every format / filter / analysis / AI plugin imports from this module and only
this module. Core code can change internals freely as long as these signatures
stay stable.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, BinaryIO, Generic, Literal, Protocol, TypeVar, TypedDict, Union

from .canonical import TabularData, TreeData


# ---------- Manifests ----------

@dataclass(frozen=True)
class FormatManifest:
    id: str
    display_name: str
    version: str
    license: str
    author: str
    mime_types: list[str]
    extensions: list[str]
    shape: Literal["tabular", "tree"]
    parse: bool
    emit: bool
    streaming: bool
    magic_bytes: list[bytes] = field(default_factory=list)
    confidence_strategy: str = "content-sniff"
    required_tier: Literal["free", "paid"] = "free"


@dataclass(frozen=True)
class FilterManifest:
    id: str
    display_name: str
    version: str
    license: str
    author: str
    kinds: list[str]
    required_tier: Literal["free", "paid"] = "free"


# ---------- Detection ----------

@dataclass(frozen=True)
class DetectResult:
    format: str
    confidence: float


# ---------- Filter specs ----------

class ColumnFilterSpec(TypedDict):
    kind: Literal["column"]
    keep: list[str]


FilterSpec = ColumnFilterSpec  # union grows in Plan C (row/expression/regex)


@dataclass(frozen=True)
class ValidationError:
    field: str
    message: str


# ---------- Result envelope ----------

T = TypeVar("T")


@dataclass
class PluginResult(Generic[T]):
    """Success-or-error wrapper used at every plugin dispatch boundary."""
    is_ok: bool
    value: T | None = None
    code: str | None = None
    plugin_id: str | None = None
    plugin_version: str | None = None
    message: str | None = None
    trace_id: str | None = None

    @classmethod
    def ok(cls, value: T) -> "PluginResult[T]":
        return cls(is_ok=True, value=value)

    @classmethod
    def error(cls, code: str, plugin_id: str, plugin_version: str,
              message: str, trace_id: str) -> "PluginResult[T]":
        return cls(is_ok=False, code=code, plugin_id=plugin_id,
                   plugin_version=plugin_version, message=message, trace_id=trace_id)

    def to_envelope(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "plugin_id": self.plugin_id,
            "plugin_version": self.plugin_version,
            "message": self.message,
            "trace_id": self.trace_id,
        }


# ---------- Plugin protocols ----------

class FormatPlugin(Protocol):
    manifest: FormatManifest

    def detect(self, sample: bytes) -> DetectResult: ...
    def parse(self, source: BinaryIO) -> Union[TabularData, TreeData]: ...
    def emit(self, data: Union[TabularData, TreeData], sink: BinaryIO) -> None: ...


class FilterPlugin(Protocol):
    manifest: FilterManifest

    def apply(self, data: Union[TabularData, TreeData],
              spec: FilterSpec) -> Union[TabularData, TreeData]: ...
    def validate(self, spec: FilterSpec) -> list[ValidationError]: ...
    def explain(self, spec: FilterSpec) -> str: ...


__all__ = [
    "FormatManifest", "FilterManifest",
    "DetectResult", "ColumnFilterSpec", "FilterSpec",
    "ValidationError",
    "PluginResult",
    "FormatPlugin", "FilterPlugin",
]
