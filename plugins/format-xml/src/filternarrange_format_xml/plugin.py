"""XML plugin entry-point."""
from __future__ import annotations
from typing import BinaryIO

from filternarrange_engine.core.canonical import TabularData, TreeData
from filternarrange_engine.core.plugin_protocols import DetectResult, FormatManifest, load_manifest

from .detect import detect as _detect
from .emit import emit as _emit
from .parse import parse as _parse


class _XmlPlugin:
    manifest: FormatManifest = load_manifest(__file__, "../../manifest.toml")  # type: ignore[assignment]

    def detect(self, sample: bytes) -> DetectResult:
        return _detect(sample)

    def parse(self, source: BinaryIO) -> TreeData:
        return _parse(source)

    def emit(self, data: TabularData | TreeData, sink: BinaryIO) -> None:
        if not isinstance(data, TreeData):
            raise ValueError("xml emit requires TreeData")
        _emit(data, sink)


plugin = _XmlPlugin()
