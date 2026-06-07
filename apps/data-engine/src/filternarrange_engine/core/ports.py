"""Adapter-facing ports the data-engine core depends on."""
from __future__ import annotations
from typing import BinaryIO, Protocol


class ObjectStorePort(Protocol):
    def get(self, ref: str) -> BinaryIO: ...
    def put(self, ref: str, data: BinaryIO, size: int, content_type: str) -> None: ...


__all__ = ["ObjectStorePort"]
