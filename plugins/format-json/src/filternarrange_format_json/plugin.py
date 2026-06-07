"""JSON plugin entry-point."""
from __future__ import annotations
from typing import BinaryIO

from filternarrange_engine.core.canonical import TabularData, TreeData
from filternarrange_engine.core.plugin_api import DetectResult, FormatManifest

from .detect import detect_json
from .parse import parse_json
from .emit import emit_json


class _JsonPlugin:
    manifest = FormatManifest(
        id="json",
        display_name="JSON",
        version="1.0.0",
        license="Apache-2.0",
        author="FilterNArrange Core",
        mime_types=["application/json"],
        extensions=[".json"],
        shape="tabular",  # default — tree if structure dictates
        parse=True, emit=True, streaming=False,
    )

    def detect(self, sample: bytes) -> DetectResult:
        return detect_json(sample)

    def parse(self, source: BinaryIO) -> TabularData | TreeData:
        return parse_json(source)

    def emit(self, data: TabularData | TreeData, sink: BinaryIO) -> None:
        emit_json(data, sink)


plugin = _JsonPlugin()
