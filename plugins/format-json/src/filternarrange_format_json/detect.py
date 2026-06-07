"""JSON detection — parse a sample and check for array/object."""
from __future__ import annotations
import json
from filternarrange_engine.core.plugin_api import DetectResult


def detect_json(sample: bytes) -> DetectResult:
    try:
        text = sample.decode("utf-8-sig")
    except UnicodeDecodeError:
        return DetectResult(format="json", confidence=0.0)
    stripped = text.lstrip()
    if not stripped or stripped[0] not in "[{":
        return DetectResult(format="json", confidence=0.0)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return DetectResult(format="json", confidence=0.0)
    if isinstance(parsed, list) and all(isinstance(x, dict) for x in parsed):
        return DetectResult(format="json", confidence=0.98)
    if isinstance(parsed, dict):
        return DetectResult(format="json", confidence=0.95)
    return DetectResult(format="json", confidence=0.7)


__all__ = ["detect_json"]
