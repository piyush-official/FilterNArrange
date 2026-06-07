"""Plugin registry.

Discovers plugins via importlib entry-points and offers explicit register()
for tests. Honors the FILTERNARRANGE_DISABLED_PLUGINS env var.
"""
from __future__ import annotations
import os
from importlib.metadata import entry_points

from filternarrange_engine.core.analysis import AnalysisPlugin
from filternarrange_engine.core.plugin_api import FilterPlugin, FormatPlugin


class PluginRegistry:

    FORMAT_GROUP = "filternarrange.formats"
    FILTER_GROUP = "filternarrange.filters"
    ANALYSIS_GROUP = "filternarrange.analyses"

    def __init__(self) -> None:
        self._formats: dict[str, FormatPlugin] = {}
        self._filters: dict[str, FilterPlugin] = {}
        self._analyses: dict[str, AnalysisPlugin] = {}
        self._disabled = self._read_disabled()

    @staticmethod
    def _read_disabled() -> set[str]:
        raw = os.environ.get("FILTERNARRANGE_DISABLED_PLUGINS", "")
        return {p.strip() for p in raw.split(",") if p.strip()}

    def is_disabled(self, plugin_id: str) -> bool:
        return plugin_id in self._disabled

    # explicit registration (used by tests + plugins that fail entry-point load)
    def register_format(self, plugin: FormatPlugin) -> None:
        if self.is_disabled(plugin.manifest.id):
            return
        self._formats[plugin.manifest.id] = plugin

    def register_filter(self, plugin: FilterPlugin) -> None:
        if self.is_disabled(plugin.manifest.id):
            return
        for k in plugin.manifest.kinds:
            self._filters[k] = plugin

    def register_analysis(self, plugin: AnalysisPlugin) -> None:
        if self.is_disabled(plugin.manifest.id):
            return
        # Analysis plugins follow the same `kinds` shape as FilterManifest.
        for k in getattr(plugin.manifest, "kinds", []):
            self._analyses[k] = plugin

    def discover(self) -> None:
        for ep in entry_points(group=self.FORMAT_GROUP):
            plugin = ep.load()
            if hasattr(plugin, "manifest"):
                self.register_format(plugin)
        for ep in entry_points(group=self.FILTER_GROUP):
            plugin = ep.load()
            if hasattr(plugin, "manifest"):
                self.register_filter(plugin)
        for ep in entry_points(group=self.ANALYSIS_GROUP):
            plugin = ep.load()
            if hasattr(plugin, "manifest"):
                self.register_analysis(plugin)

    def get_format(self, fid: str) -> FormatPlugin:
        if fid not in self._formats:
            raise KeyError(fid)
        return self._formats[fid]

    def get_filter(self, kind: str) -> FilterPlugin:
        if kind not in self._filters:
            raise KeyError(kind)
        return self._filters[kind]

    def get_analysis(self, kind: str) -> AnalysisPlugin:
        if kind not in self._analyses:
            raise KeyError(kind)
        return self._analyses[kind]

    def list_formats(self) -> list[str]:
        return sorted(self._formats.keys())

    def list_filters(self) -> list[str]:
        return sorted(self._filters.keys())

    def list_analyses(self) -> list[str]:
        return sorted(self._analyses.keys())

    def detect_format(self, sample: bytes) -> tuple[str, float] | None:
        best: tuple[str, float] | None = None
        for fid, plugin in self._formats.items():
            try:
                res = plugin.detect(sample)
            except Exception:
                continue
            if res.confidence > (best[1] if best else 0.0):
                best = (res.format, res.confidence)
        return best


__all__ = ["PluginRegistry"]
