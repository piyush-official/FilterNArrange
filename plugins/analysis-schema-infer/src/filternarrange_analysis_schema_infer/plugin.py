"""schema_infer analysis plugin — walks a TreeData document."""
from __future__ import annotations
from collections import defaultdict
from typing import Optional

from filternarrange_engine.core.analysis import AnalysisResult, AnalysisSpec
from filternarrange_engine.core.canonical import Column, Node, TreeData
from filternarrange_engine.core.plugin_protocols import FilterManifest, load_manifest


class _SchemaInferPlugin:
    manifest: FilterManifest = load_manifest(__file__, "../../manifest.toml")  # type: ignore[assignment]

    async def analyze(self, data: TreeData, options: dict) -> AnalysisResult:
        path_info: dict[str, dict] = defaultdict(
            lambda: {"types": set(), "depth_min": 1 << 31, "depth_max": 0, "frequency": 0}
        )
        leaf_count = 0
        max_depth = 0

        def walk(node: Node, path: str, depth: int) -> None:
            nonlocal leaf_count, max_depth
            max_depth = max(max_depth, depth)
            info = path_info[path]
            info["depth_min"] = min(info["depth_min"], depth)
            info["depth_max"] = max(info["depth_max"], depth)
            info["frequency"] += 1
            if not node.children:
                leaf_count += 1
                info["types"].add(node.type.name.lower())
            else:
                info["types"].add("object")
                for ch in node.children:
                    walk(ch, f"{path}.{ch.key}", depth + 1)

        walk(data.root, data.root.key, 1)
        paths = [
            {
                "path": p,
                "types": sorted(v["types"]),
                "depth_min": v["depth_min"],
                "depth_max": v["depth_max"],
                "frequency": v["frequency"],
            }
            for p, v in path_info.items()
        ]
        return AnalysisResult(
            kind="schema_infer",
            payload={"paths": paths, "leaf_count": leaf_count, "depth": max_depth},
            warnings=[],
        )

    def validate(self, spec: AnalysisSpec, schema: Optional[list[Column]] = None) -> list[str]:
        return []


plugin = _SchemaInferPlugin()
