"""XLSX plugin entry-point — exposes list_sheets alongside detect/parse/emit."""
from __future__ import annotations
from typing import BinaryIO, Optional

from filternarrange_engine.core.canonical import TabularData, TreeData
from filternarrange_engine.core.plugin_protocols import DetectResult, FormatManifest, load_manifest

from .detect import detect as _detect
from .emit import emit as _emit
from .parse import list_sheets as _list_sheets, parse as _parse


class _XlsxPlugin:
    manifest: FormatManifest = load_manifest(__file__, "../../manifest.toml")  # type: ignore[assignment]

    def detect(self, sample: bytes) -> DetectResult:
        return _detect(sample)

    def list_sheets(self, source: BinaryIO) -> list[str]:
        return _list_sheets(source)

    def parse(self, source: BinaryIO, sheet_name: Optional[str] = None) -> TabularData:
        return _parse(source, sheet_name=sheet_name)

    def emit(self, data: TabularData | TreeData, sink: BinaryIO) -> None:
        if not isinstance(data, TabularData):
            raise ValueError("xlsx emit requires TabularData")
        _emit(data, sink)


plugin = _XlsxPlugin()
