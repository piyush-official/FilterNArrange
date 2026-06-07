"""TSV detection — `csv.Sniffer` with tab delimiter + width consistency."""
from __future__ import annotations
import csv
import io

from filternarrange_engine.core.plugin_protocols import DetectResult


def detect(sample: bytes) -> DetectResult:
    try:
        head = sample[:8192].decode("utf-8", errors="ignore")
    except Exception:
        return DetectResult(format="tsv", confidence=0.0)
    if not head:
        return DetectResult(format="tsv", confidence=0.0)
    try:
        dialect = csv.Sniffer().sniff(head, delimiters="\t,;|")
    except csv.Error:
        return DetectResult(format="tsv", confidence=0.0)
    if dialect.delimiter != "\t":
        return DetectResult(format="tsv", confidence=0.05)
    rows = list(csv.reader(io.StringIO(head), dialect=dialect))[:10]
    if len(rows) < 2:
        return DetectResult(format="tsv", confidence=0.4)
    widths = {len(r) for r in rows if r}
    if len(widths) == 1 and next(iter(widths)) > 1:
        return DetectResult(format="tsv", confidence=0.95)
    return DetectResult(format="tsv", confidence=0.6)


__all__ = ["detect"]
