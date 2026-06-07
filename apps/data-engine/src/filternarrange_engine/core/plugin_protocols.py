"""Plan C compatibility surface.

Re-exports Plan B's plugin protocol types under the location Plan C tasks
import from, and adds two helpers Plan C plugins call:

- `load_manifest(file, relpath)` — reads a sibling manifest.toml and returns
  a `FormatManifest` (for format plugins) or `FilterManifest` (for filter
  plugins) populated from the TOML.
"""
from __future__ import annotations
import pathlib
import sys
from typing import Literal

from .plugin_api import (
    DetectResult,
    FilterManifest,
    FilterPlugin,
    FormatManifest,
    FormatPlugin,
    PluginResult,
    ValidationError,
)
from .analysis import AnalysisPlugin, AnalysisResult, AnalysisSpec

if sys.version_info >= (3, 11):
    import tomllib as _toml
else:  # pragma: no cover — repo pins 3.12
    import tomli as _toml  # type: ignore[no-redef]


def load_manifest(file: str, relpath: str) -> FormatManifest | FilterManifest:
    """Load `manifest.toml` next to a plugin and build the right dataclass.

    `file` is the importing module's `__file__`; `relpath` is the relative
    path to manifest.toml from that file's directory (e.g. `../../manifest.toml`).
    """
    here = pathlib.Path(file).resolve().parent
    path = (here / relpath).resolve()
    with path.open("rb") as f:
        raw = _toml.load(f)

    p = raw["plugin"]
    caps = raw.get("capabilities", {})
    det = raw.get("detect", {})

    common = dict(
        id=p["id"],
        display_name=p["display_name"],
        version=p["version"],
        license=p["license"],
        author=p["author"],
    )

    # Filter manifest if the TOML declares filter `kinds`, else format manifest.
    if "kinds" in caps:
        return FilterManifest(**common, kinds=list(caps["kinds"]))

    shape: Literal["tabular", "tree"] = caps.get("shape", "tabular")
    return FormatManifest(
        **common,
        mime_types=list(det.get("mime_types", [])),
        extensions=list(det.get("extensions", [])),
        shape=shape,
        parse=bool(caps.get("parse", True)),
        emit=bool(caps.get("emit", True)),
        streaming=bool(caps.get("streaming", False)),
        magic_bytes=[bytes(b, "utf-8") if isinstance(b, str) else b for b in det.get("magic_bytes", [])],
        confidence_strategy=det.get("confidence_strategy", "content-sniff"),
        required_tier=p.get("required_tier", "free"),
    )


__all__ = [
    "DetectResult",
    "FilterManifest", "FilterPlugin",
    "FormatManifest", "FormatPlugin",
    "AnalysisPlugin", "AnalysisResult", "AnalysisSpec",
    "PluginResult", "ValidationError",
    "load_manifest",
]
