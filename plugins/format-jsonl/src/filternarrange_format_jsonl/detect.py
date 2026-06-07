"""JSONL detection — each non-blank line must be a JSON object."""
from __future__ import annotations
import json

from filternarrange_engine.core.plugin_protocols import DetectResult


def detect(sample: bytes) -> DetectResult:
    head = sample[:8192].decode("utf-8", errors="ignore").strip()
    if not head or head.startswith("["):
        return DetectResult(format="jsonl", confidence=0.0)
    lines = [ln for ln in head.splitlines() if ln.strip()]
    if len(lines) < 2:
        try:
            json.loads(lines[0])
        except Exception:
            return DetectResult(format="jsonl", confidence=0.0)
        return DetectResult(format="jsonl", confidence=0.45)
    good = 0
    for ln in lines[:50]:
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                good += 1
        except Exception:
            pass
    ratio = good / min(len(lines), 50)
    return DetectResult(format="jsonl", confidence=ratio)


__all__ = ["detect"]
