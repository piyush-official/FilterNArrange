"""CSV plugin entry-point object."""
from __future__ import annotations
from typing import BinaryIO

from filternarrange_engine.core.canonical import TabularData, TreeData
from filternarrange_engine.core.plugin_api import DetectResult, FormatManifest

from .detect import detect_csv
from .parse import parse_csv
from .emit import emit_csv


class _CsvPlugin:
    manifest = FormatManifest(
        id="csv",
        display_name="CSV",
        version="1.0.0",
        license="Apache-2.0",
        author="FilterNArrange Core",
        mime_types=["text/csv"],
        extensions=[".csv"],
        shape="tabular",
        parse=True, emit=True, streaming=True,
    )

    def detect(self, sample: bytes) -> DetectResult:
        return detect_csv(sample)

    def parse(self, source: BinaryIO) -> TabularData:
        return parse_csv(source)

    def emit(self, data: TabularData | TreeData, sink: BinaryIO) -> None:
        if not isinstance(data, TabularData):
            raise ValueError("csv emit requires TabularData")
        emit_csv(data, sink)


plugin = _CsvPlugin()
