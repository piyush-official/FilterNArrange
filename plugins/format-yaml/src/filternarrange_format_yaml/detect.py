"""YAML detection — prefer doc-marker, de-prioritise JSON-shaped inputs."""
from __future__ import annotations

import yaml

from filternarrange_engine.core.plugin_protocols import DetectResult


def detect(sample: bytes) -> DetectResult:
    head = sample[:16384].decode("utf-8", errors="ignore")
    if not head.strip():
        return DetectResult(format="yaml", confidence=0.0)
    stripped = head.lstrip()
    json_like = stripped.startswith("{") or stripped.startswith("[")
    has_marker = stripped.startswith("---")
    try:
        doc = yaml.safe_load(head)
    except yaml.YAMLError:
        return DetectResult(format="yaml", confidence=0.0)
    if doc is None:
        return DetectResult(format="yaml", confidence=0.1)
    if has_marker:
        return DetectResult(format="yaml", confidence=0.95)
    if json_like:
        return DetectResult(format="yaml", confidence=0.3)
    if isinstance(doc, (dict, list)):
        return DetectResult(format="yaml", confidence=0.8)
    return DetectResult(format="yaml", confidence=0.5)


__all__ = ["detect"]
