"""AI capability registry (Plan E §6).

Capabilities are pip-installable plugins that advertise themselves under the
``filternarrange.ai_capabilities`` entry-point group. The registry discovers
them at startup, honors a per-deploy disabled set, and dispatches by name.
"""
from __future__ import annotations

from importlib.metadata import entry_points
from typing import Iterable

from filternarrange_engine.core.llm import AICapability


GROUP = "filternarrange.ai_capabilities"


class CapabilityNotFoundError(LookupError):
    """Raised when a capability is missing or disabled."""


class AiCapabilityRegistry:
    def __init__(self, capabilities: dict[str, AICapability]) -> None:
        self._caps = capabilities

    @classmethod
    def load(cls, *, disabled: frozenset[str]) -> "AiCapabilityRegistry":
        eps: Iterable = entry_points(group=GROUP)  # type: ignore[arg-type]
        loaded: dict[str, AICapability] = {}
        for ep in eps:
            if ep.name in disabled:
                continue
            obj = ep.load()
            cap = obj() if callable(obj) and not hasattr(obj, "name") else obj
            loaded[cap.name] = cap
        return cls(loaded)

    def names(self) -> list[str]:
        return sorted(self._caps.keys())

    def is_enabled(self, name: str) -> bool:
        return name in self._caps

    def get(self, name: str) -> AICapability:
        try:
            return self._caps[name]
        except KeyError as exc:
            raise CapabilityNotFoundError(name) from exc


__all__ = ["AiCapabilityRegistry", "CapabilityNotFoundError", "GROUP"]
