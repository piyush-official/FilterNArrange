"""CSV detection via csv.Sniffer + heuristics."""
from __future__ import annotations
import csv
import io

from filternarrange_engine.core.plugin_api import DetectResult


def detect_csv(sample: bytes) -> DetectResult:
    text = _safe_decode(sample)
    if not text or "\x00" in text:
        return DetectResult(format="csv", confidence=0.0)

    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(text[:4096], delimiters=",\t;|")
    except csv.Error:
        return DetectResult(format="csv", confidence=0.0)

    reader = csv.reader(io.StringIO(text), dialect=dialect)
    rows = []
    for i, row in enumerate(reader):
        if i >= 50:
            break
        rows.append(row)
    if not rows or len(rows) < 2:
        return DetectResult(format="csv", confidence=0.0)

    header_len = len(rows[0])
    if header_len == 0:
        return DetectResult(format="csv", confidence=0.0)
    consistent = sum(1 for r in rows[1:] if len(r) == header_len)
    confidence = consistent / max(len(rows) - 1, 1)
    confidence = min(confidence + (0.1 if dialect.delimiter == "," else 0.0), 1.0)
    return DetectResult(format="csv", confidence=round(confidence, 3))


def _safe_decode(b: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return ""


__all__ = ["detect_csv"]
