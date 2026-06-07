"""XML detection — `<?xml` declaration or structural sniff via lxml."""
from __future__ import annotations

from lxml import etree

from filternarrange_engine.core.plugin_protocols import DetectResult


def detect(sample: bytes) -> DetectResult:
    head = sample[:8192]
    stripped = head.lstrip()
    if stripped.startswith(b"<?xml"):
        return DetectResult(format="xml", confidence=0.99)
    if not stripped.startswith(b"<"):
        return DetectResult(format="xml", confidence=0.0)
    try:
        etree.fromstring(head, etree.XMLParser(recover=False, resolve_entities=False))
        return DetectResult(format="xml", confidence=0.85)
    except etree.XMLSyntaxError:
        return DetectResult(format="xml", confidence=0.05)


__all__ = ["detect"]
