"""Engine-side error envelope."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class EngineError(Exception):
    code: str
    message: str
    http_status: int = 500
    plugin_id: str | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


__all__ = ["EngineError"]
