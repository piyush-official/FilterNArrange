"""XLSX detection — `PK` zip magic + `xl/workbook.xml` entry."""
from __future__ import annotations
import io
import zipfile

from filternarrange_engine.core.plugin_protocols import DetectResult


def detect(sample: bytes) -> DetectResult:
    if not sample.startswith(b"PK\x03\x04"):
        return DetectResult(format="xlsx", confidence=0.0)
    try:
        with zipfile.ZipFile(io.BytesIO(sample)) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile:
        return DetectResult(format="xlsx", confidence=0.4)
    if "xl/workbook.xml" in names:
        return DetectResult(format="xlsx", confidence=0.99)
    return DetectResult(format="xlsx", confidence=0.1)


__all__ = ["detect"]
