"""TSV plugin entry-point."""
from __future__ import annotations
from typing import BinaryIO

from filternarrange_engine.core.canonical import TabularData, TreeData
from filternarrange_engine.core.plugin_protocols import DetectResult, FormatManifest, load_manifest

from .detect import detect as _detect
from .parse import parse as _parse
from .emit import emit as _emit


class _TsvPlugin:
    manifest: FormatManifest = load_manifest(__file__, "../../manifest.toml")  # type: ignore[assignment]

    def detect(self, sample: bytes) -> DetectResult:
        return _detect(sample)

    def parse(self, source: BinaryIO) -> TabularData:
        return _parse(source)

    def emit(self, data: TabularData | TreeData, sink: BinaryIO) -> None:
        if not isinstance(data, TabularData):
            raise ValueError("tsv emit requires TabularData")
        _emit(data, sink)


plugin = _TsvPlugin()
