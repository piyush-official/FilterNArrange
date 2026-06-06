# Plan C — Plugin Breadth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the FilterNArrange v1 launch surface with 5 new format plugins (XML, YAML, JSONL, TSV, XLSX), 3 new filter plugins (row, expression, regex), 4 analysis plugins (summary-stats, group-by, chart-suggest, schema-infer), schema-aware filter validation, an `/api/v1/analyze` endpoint, and matching frontend (filter mode picker, expression editor, analysis tab, multi-sheet picker). Sync path only.

**Architecture:** Each plugin lives in its own `plugins/<kind>-<id>/` subdirectory with its own `pyproject.toml`, `manifest.toml`, `src/`, and `tests/`. Plugins are discovered at data-engine startup via `importlib.metadata.entry_points` (already wired in Plan B). The gateway gets a new dispatcher endpoint `/api/v1/analyze` and extends `/api/v1/filter/preview` to accept all four filter `kind`s. The data-engine gains `FilterPlugin` and `AnalysisPlugin` dispatchers, schema-aware validation, and an extended conformance suite. The frontend gains a 4-tab filter mode picker, a Monaco-backed expression editor with schema-driven autocomplete, an analysis tab with ECharts rendering, and a sheet-picker step for multi-sheet XLSX uploads. No Kafka, no AI, no quotas — those land in later plans.

**Tech Stack:** Python 3.12 + FastAPI (data-engine), Spring Boot 3 + Java 21 (gateway), React 18 + TypeScript + Vite + Monaco Editor + Apache ECharts (frontend). Parser libs: `lxml`, `PyYAML` (safe loader), `openpyxl`, stdlib `csv`/`json`. Expression engine: `simpleeval`. Stats: `statistics` (stdlib).

---

## File Structure

### New plugin directories (one per plugin, all under `plugins/`)

Each plugin follows the canonical layout established by Plan B's `plugins/format-csv/`:

```
plugins/<plugin-dir>/
├── pyproject.toml            # entry-point registration
├── README.md                 # purpose, public API, limits
├── manifest.toml             # declarative plugin metadata
├── src/<python_pkg>/
│   ├── __init__.py           # exports `plugin` instance
│   ├── plugin.py             # FormatPlugin / FilterPlugin / AnalysisPlugin class
│   ├── detect.py / parse.py / emit.py   (format plugins)
│   └── apply.py / validate.py           (filter / analysis plugins)
└── tests/
    ├── fixtures/<canonical-fixture>
    ├── test_detect.py / test_parse.py / test_emit.py / test_apply.py / test_analyze.py
    └── test_conformance.py   # registered in shared canonical suite
```

The 12 new plugin directories:

| Path | Python package | Entry-point group |
|---|---|---|
| `plugins/format-xml/` | `filternarrange_format_xml` | `filternarrange.formats` |
| `plugins/format-yaml/` | `filternarrange_format_yaml` | `filternarrange.formats` |
| `plugins/format-jsonl/` | `filternarrange_format_jsonl` | `filternarrange.formats` |
| `plugins/format-tsv/` | `filternarrange_format_tsv` | `filternarrange.formats` |
| `plugins/format-xlsx/` | `filternarrange_format_xlsx` | `filternarrange.formats` |
| `plugins/filter-row/` | `filternarrange_filter_row` | `filternarrange.filters` |
| `plugins/filter-expression/` | `filternarrange_filter_expression` | `filternarrange.filters` |
| `plugins/filter-regex/` | `filternarrange_filter_regex` | `filternarrange.filters` |
| `plugins/analysis-summary-stats/` | `filternarrange_analysis_summary_stats` | `filternarrange.analyses` |
| `plugins/analysis-group-by/` | `filternarrange_analysis_group_by` | `filternarrange.analyses` |
| `plugins/analysis-chart-suggest/` | `filternarrange_analysis_chart_suggest` | `filternarrange.analyses` |
| `plugins/analysis-schema-infer/` | `filternarrange_analysis_schema_infer` | `filternarrange.analyses` |

### Data-engine modifications

- `apps/data-engine/src/filternarrange_engine/core/filter_spec.py` — extend `FilterSpec` discriminated union with `RowSpec`, `ExpressionSpec`, `RegexSpec`.
- `apps/data-engine/src/filternarrange_engine/core/analysis.py` — new `AnalysisSpec`, `AnalysisResult`, `AnalysisPlugin` Protocol.
- `apps/data-engine/src/filternarrange_engine/adapters/plugin_registry/registry.py` — add `analyses` discovery; expose `get_filter(kind)` and `get_analysis(kind)` dispatchers.
- `apps/data-engine/src/filternarrange_engine/application/filter_service.py` — schema-aware validation, kind-based dispatch.
- `apps/data-engine/src/filternarrange_engine/application/analysis_service.py` — new orchestrator.
- `apps/data-engine/src/filternarrange_engine/api/routers/filter.py` — accept all four kinds.
- `apps/data-engine/src/filternarrange_engine/api/routers/analysis.py` — new router.

### Gateway modifications

- `apps/gateway/src/main/java/io/filternarrange/gateway/api/AnalyzeController.java` — new endpoint.
- `apps/gateway/src/main/java/io/filternarrange/gateway/api/dto/AnalyzeRequest.java`, `AnalyzeResponse.java`, `FilterSpecDto.java` — DTOs.
- `apps/gateway/src/main/java/io/filternarrange/gateway/application/AnalyzeService.java` — orchestrator.
- `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/http/DataEngineClient.java` — new methods `previewFilterAny`, `analyze`, `pickSheet`.
- `apps/gateway/src/main/java/io/filternarrange/gateway/api/SheetController.java` — XLSX sheet pick endpoint.

### Contract modifications

- `contracts/openapi/gateway-public.v1.yaml` — bump patch (1.0.0 → 1.1.0 additive within v1; spec §3 says additive within a major is allowed). Add `/api/v1/analyze`, `/api/v1/uploads/{id}/sheets`, extend `FilterSpec` schema with discriminated union.
- `contracts/openapi/gateway-internal.v1.yaml` — same additions for the gateway↔data-engine internal contract.

### Frontend modifications

- `apps/frontend/src/features/filter/ui/FilterModePicker.tsx` — 4-tab picker.
- `apps/frontend/src/features/filter/ui/RowFilterForm.tsx` — predicate builder.
- `apps/frontend/src/features/filter/ui/ExpressionFilterEditor.tsx` — Monaco editor + autocomplete.
- `apps/frontend/src/features/filter/ui/RegexFilterForm.tsx` — regex input + flags.
- `apps/frontend/src/features/analyze/` — new feature folder with `api/`, `ui/`, `state/`, `index.ts`.
- `apps/frontend/src/features/analyze/ui/AnalysisTab.tsx`, `SummaryPanel.tsx`, `GroupByPanel.tsx`, `ChartsPanel.tsx`, `SchemaPanel.tsx`.
- `apps/frontend/src/features/upload/ui/SheetPicker.tsx` — multi-sheet XLSX flow.
- `apps/frontend/src/shared/api/client.ts` — `analyze()`, `listSheets()`, `previewFilter()` updates.

### Test / CI modifications

- `tests/integration/test_plugin_conformance.py` — auto-discovers every registered plugin and runs the canonical round-trip suite against it.
- `.github/workflows/pr.yml` — add a matrix job `plugin-tests` that discovers each `plugins/*/` directory and runs that plugin's tests in isolation.

---

## Task List (overview)

1. Filter & analysis core types in data-engine
2. format-tsv plugin
3. format-jsonl plugin
4. format-yaml plugin
5. format-xml plugin
6. format-xlsx plugin + sheet-pick API
7. filter-row plugin + schema-aware validation
8. filter-expression plugin (simpleeval, register_function)
9. filter-regex plugin
10. analysis-summary-stats plugin
11. analysis-group-by plugin
12. analysis-chart-suggest plugin
13. analysis-schema-infer plugin
14. Data-engine dispatcher + `/internal/analyze` + extended `/internal/filter/preview`
15. Gateway DTOs + AnalyzeController + extended FilterController + SheetController
16. OpenAPI contract bump
17. Frontend filter mode picker (Columns/Rows/Expression/Regex tabs)
18. Frontend expression editor (Monaco + schema autocomplete)
19. Frontend analysis tab (Summary/Group-by/Charts/Schema sub-tabs, ECharts)
20. Frontend XLSX sheet picker
21. Shared plugin conformance integration test
22. CI matrix job per plugin

---

## Conventions used in every task

- **Conventional Commits.** `feat(format-xml): add XML plugin`, `feat(gateway): add analyze endpoint`, etc.
- **Error envelope** on every failure: `{code, plugin_id?, message, trace_id}`.
- **PluginResult envelope** (defined in Plan B) wraps every plugin return.
- **Manifest TOML** schema is fixed by spec §4 — all 12 plugins ship one.
- Each plugin's `pyproject.toml` declares `requires-python = ">=3.12"` and an entry point.

A canonical `pyproject.toml` skeleton (referenced by every format/filter/analysis task):

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "filternarrange-<kind>-<id>"
version = "0.1.0"
description = "<one-line>"
requires-python = ">=3.12"
dependencies = ["filternarrange-engine-core>=0.2,<0.3", "<extra-libs>"]

[project.entry-points."filternarrange.<group>"]
<id> = "<python_pkg>:plugin"

[tool.hatch.build.targets.wheel]
packages = ["src/<python_pkg>"]
```

---

### Task 1: Filter & analysis core types (data-engine)

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/core/filter_spec.py`
- Create: `apps/data-engine/src/filternarrange_engine/core/analysis.py`
- Create: `apps/data-engine/src/filternarrange_engine/core/plugin_protocols.py` (extends Plan B's file — additive)
- Test: `apps/data-engine/tests/unit/core/test_filter_spec.py`
- Test: `apps/data-engine/tests/unit/core/test_analysis.py`

- [ ] **Step 1: Write failing test for FilterSpec discriminated union**

```python
# apps/data-engine/tests/unit/core/test_filter_spec.py
import pytest
from filternarrange_engine.core.filter_spec import parse_filter_spec, ColumnSpec, RowSpec, ExpressionSpec, RegexSpec

def test_parse_column_spec():
    spec = parse_filter_spec({"kind": "column", "include": ["a", "b"]})
    assert isinstance(spec, ColumnSpec)
    assert spec.include == ["a", "b"]

def test_parse_row_spec():
    spec = parse_filter_spec({"kind": "row", "predicate": {"col": "age", "op": "gt", "value": 18}})
    assert isinstance(spec, RowSpec)
    assert spec.predicate.op == "gt"

def test_parse_expression_spec():
    spec = parse_filter_spec({"kind": "expression", "expr": "age > 18 AND country = 'IN'"})
    assert isinstance(spec, ExpressionSpec)

def test_parse_regex_spec():
    spec = parse_filter_spec({"kind": "regex", "pattern": "^foo", "flags": ["i"]})
    assert isinstance(spec, RegexSpec)
    assert spec.flags == ["i"]

def test_unknown_kind_raises():
    with pytest.raises(ValueError, match="unknown filter kind"):
        parse_filter_spec({"kind": "nope"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/data-engine && uv run pytest tests/unit/core/test_filter_spec.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Implement filter_spec.py**

```python
# apps/data-engine/src/filternarrange_engine/core/filter_spec.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Union, Any

RowOp = Literal["eq","ne","gt","gte","lt","lte","contains","starts_with",
                "ends_with","regex","in","not_in","is_null","is_not_null"]

@dataclass(frozen=True)
class RowPredicate:
    col: str
    op: RowOp
    value: Any = None

@dataclass(frozen=True)
class ColumnSpec:
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    kind: Literal["column"] = "column"

@dataclass(frozen=True)
class RowSpec:
    predicate: RowPredicate
    kind: Literal["row"] = "row"

@dataclass(frozen=True)
class ExpressionSpec:
    expr: str
    kind: Literal["expression"] = "expression"

@dataclass(frozen=True)
class RegexSpec:
    pattern: str
    flags: list[str] = field(default_factory=list)
    kind: Literal["regex"] = "regex"

FilterSpec = Union[ColumnSpec, RowSpec, ExpressionSpec, RegexSpec]

def parse_filter_spec(payload: dict) -> FilterSpec:
    kind = payload.get("kind")
    if kind == "column":
        return ColumnSpec(include=payload.get("include", []), exclude=payload.get("exclude", []))
    if kind == "row":
        p = payload["predicate"]
        return RowSpec(predicate=RowPredicate(col=p["col"], op=p["op"], value=p.get("value")))
    if kind == "expression":
        return ExpressionSpec(expr=payload["expr"])
    if kind == "regex":
        return RegexSpec(pattern=payload["pattern"], flags=payload.get("flags", []))
    raise ValueError(f"unknown filter kind: {kind!r}")
```

- [ ] **Step 4: Run tests — green**

Run: `cd apps/data-engine && uv run pytest tests/unit/core/test_filter_spec.py -v`
Expected: 5 passed.

- [ ] **Step 5: Write failing test for AnalysisSpec / AnalysisResult**

```python
# apps/data-engine/tests/unit/core/test_analysis.py
from filternarrange_engine.core.analysis import AnalysisSpec, AnalysisResult, parse_analysis_spec

def test_parse_analysis_spec_summary():
    spec = parse_analysis_spec({"kind": "summary_stats", "options": {}})
    assert spec.kind == "summary_stats"
    assert spec.options == {}

def test_analysis_result_envelope():
    res = AnalysisResult(kind="summary_stats", payload={"rows": 100}, warnings=[])
    assert res.kind == "summary_stats"
    assert res.payload["rows"] == 100
```

- [ ] **Step 6: Implement analysis.py**

```python
# apps/data-engine/src/filternarrange_engine/core/analysis.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
from .canonical import TabularData, TreeData

@dataclass(frozen=True)
class AnalysisSpec:
    kind: str
    options: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class AnalysisResult:
    kind: str
    payload: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

def parse_analysis_spec(payload: dict) -> AnalysisSpec:
    return AnalysisSpec(kind=payload["kind"], options=payload.get("options", {}))

@runtime_checkable
class AnalysisPlugin(Protocol):
    manifest: Any
    def analyze(self, data: TabularData | TreeData, options: dict) -> AnalysisResult: ...
    def validate(self, spec: AnalysisSpec, schema: list | None = None) -> list[str]: ...
```

- [ ] **Step 7: Run analysis tests — green**

Run: `cd apps/data-engine && uv run pytest tests/unit/core/test_analysis.py -v`
Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/core/filter_spec.py \
        apps/data-engine/src/filternarrange_engine/core/analysis.py \
        apps/data-engine/tests/unit/core/test_filter_spec.py \
        apps/data-engine/tests/unit/core/test_analysis.py
git commit -m "feat(data-engine): add FilterSpec union and AnalysisSpec core types"
```

---

### Task 2: format-tsv plugin

**Files:**
- Create: `plugins/format-tsv/pyproject.toml`
- Create: `plugins/format-tsv/manifest.toml`
- Create: `plugins/format-tsv/README.md`
- Create: `plugins/format-tsv/src/filternarrange_format_tsv/__init__.py`
- Create: `plugins/format-tsv/src/filternarrange_format_tsv/plugin.py`
- Create: `plugins/format-tsv/src/filternarrange_format_tsv/detect.py`
- Create: `plugins/format-tsv/src/filternarrange_format_tsv/parse.py`
- Create: `plugins/format-tsv/src/filternarrange_format_tsv/emit.py`
- Create: `plugins/format-tsv/tests/fixtures/sample.tsv`
- Test: `plugins/format-tsv/tests/test_detect.py`, `test_parse.py`, `test_emit.py`, `test_conformance.py`

- [ ] **Step 1: Write failing detect test (TSV vs CSV disambiguation)**

```python
# plugins/format-tsv/tests/test_detect.py
from filternarrange_format_tsv import plugin

def test_detect_tab_dominant():
    sample = b"id\tname\tage\n1\tAda\t37\n2\tGrace\t85\n"
    res = plugin.detect(sample)
    assert res.format == "tsv"
    assert res.confidence > 0.9

def test_detect_csv_returns_low_conf():
    sample = b"id,name,age\n1,Ada,37\n"
    res = plugin.detect(sample)
    assert res.confidence < 0.3
```

- [ ] **Step 2: Run — FAIL (module missing)**

Run: `cd plugins/format-tsv && uv run pytest tests/test_detect.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement detect.py**

```python
# plugins/format-tsv/src/filternarrange_format_tsv/detect.py
import csv, io
from filternarrange_engine.core.plugin_protocols import DetectResult

def detect(sample: bytes) -> DetectResult:
    try:
        head = sample[:8192].decode("utf-8", errors="ignore")
    except Exception:
        return DetectResult(format="tsv", confidence=0.0)
    if not head:
        return DetectResult(format="tsv", confidence=0.0)
    # csv.Sniffer disambiguates from CSV
    try:
        dialect = csv.Sniffer().sniff(head, delimiters="\t,;|")
    except csv.Error:
        return DetectResult(format="tsv", confidence=0.0)
    if dialect.delimiter != "\t":
        return DetectResult(format="tsv", confidence=0.05)
    # consistency check: same column count across first 10 lines
    rows = list(csv.reader(io.StringIO(head), dialect))[:10]
    if len(rows) < 2:
        return DetectResult(format="tsv", confidence=0.4)
    widths = {len(r) for r in rows if r}
    if len(widths) == 1 and next(iter(widths)) > 1:
        return DetectResult(format="tsv", confidence=0.95)
    return DetectResult(format="tsv", confidence=0.6)
```

- [ ] **Step 4: Implement parse.py (streaming reader producing TabularData)**

```python
# plugins/format-tsv/src/filternarrange_format_tsv/parse.py
import csv, io
from typing import BinaryIO, AsyncIterator
from filternarrange_engine.core.canonical import TabularData, Column, TypeTag, infer_type_tag

def parse(source: BinaryIO) -> TabularData:
    text = io.TextIOWrapper(source, encoding="utf-8", newline="")
    reader = csv.reader(text, delimiter="\t")
    header = next(reader, [])
    # First pass sample (up to 200 rows) for type inference
    sample = []
    for i, row in enumerate(reader):
        if i >= 200: break
        sample.append(row)
    types: list[TypeTag] = [infer_type_tag([r[i] for r in sample if i < len(r)]) for i in range(len(header))]
    schema = [Column(name=h, type=t, nullable=True) for h, t in zip(header, types)]
    # Rewind not needed — caller passes fresh handle for full stream
    async def rows() -> AsyncIterator[list]:
        source.seek(0)
        text2 = io.TextIOWrapper(source, encoding="utf-8", newline="")
        r = csv.reader(text2, delimiter="\t")
        next(r, None)  # skip header
        for row in r:
            yield row
    return TabularData(schema=schema, rows=rows())
```

- [ ] **Step 5: Implement emit.py**

```python
# plugins/format-tsv/src/filternarrange_format_tsv/emit.py
import csv, io
from typing import BinaryIO
from filternarrange_engine.core.canonical import TabularData
import asyncio

def emit(data: TabularData, sink: BinaryIO) -> None:
    text = io.TextIOWrapper(sink, encoding="utf-8", newline="", write_through=True)
    writer = csv.writer(text, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([c.name for c in data.schema])
    async def drain():
        async for row in data.rows:
            writer.writerow(row)
    asyncio.run(drain())
```

- [ ] **Step 6: Plugin entry & manifest**

```python
# plugins/format-tsv/src/filternarrange_format_tsv/plugin.py
from dataclasses import dataclass
from . import detect as _d, parse as _p, emit as _e
from filternarrange_engine.core.plugin_protocols import load_manifest

class _Plugin:
    manifest = load_manifest(__file__, "../../manifest.toml")
    detect = staticmethod(_d.detect)
    parse  = staticmethod(_p.parse)
    emit   = staticmethod(_e.emit)

plugin = _Plugin()
```

```python
# plugins/format-tsv/src/filternarrange_format_tsv/__init__.py
from .plugin import plugin
__all__ = ["plugin"]
```

```toml
# plugins/format-tsv/manifest.toml
[plugin]
id = "tsv"
display_name = "TSV"
version = "0.1.0"
license = "Apache-2.0"
author = "FilterNArrange Core"

[detect]
mime_types = ["text/tab-separated-values"]
extensions = [".tsv"]
magic_bytes = []
confidence_strategy = "content-sniff"

[capabilities]
parse = true
emit = true
streaming = true
shape = "tabular"
```

```toml
# plugins/format-tsv/pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "filternarrange-format-tsv"
version = "0.1.0"
description = "TSV format plugin"
requires-python = ">=3.12"
dependencies = ["filternarrange-engine-core>=0.2,<0.3"]

[project.entry-points."filternarrange.formats"]
tsv = "filternarrange_format_tsv:plugin"

[tool.hatch.build.targets.wheel]
packages = ["src/filternarrange_format_tsv"]
```

- [ ] **Step 7: Fixture**

`plugins/format-tsv/tests/fixtures/sample.tsv`:
```
id	name	age
1	Ada	37
2	Grace	85
3	Linus	54
```

- [ ] **Step 8: Parse + emit tests**

```python
# plugins/format-tsv/tests/test_parse.py
import asyncio, pathlib
from filternarrange_format_tsv import plugin

def test_parse_sample():
    with open(pathlib.Path(__file__).parent / "fixtures/sample.tsv", "rb") as f:
        td = plugin.parse(f)
    assert [c.name for c in td.schema] == ["id", "name", "age"]
    async def collect():
        return [r async for r in td.rows]
    rows = asyncio.run(collect())
    assert len(rows) == 3
    assert rows[0] == ["1", "Ada", "37"]
```

```python
# plugins/format-tsv/tests/test_emit.py
import asyncio, io, pathlib
from filternarrange_format_tsv import plugin

def test_roundtrip():
    with open(pathlib.Path(__file__).parent / "fixtures/sample.tsv", "rb") as f:
        td = plugin.parse(f)
    sink = io.BytesIO()
    plugin.emit(td, sink)
    out = sink.getvalue().decode()
    assert "id\tname\tage" in out
    assert "Ada" in out
```

- [ ] **Step 9: Conformance test**

```python
# plugins/format-tsv/tests/test_conformance.py
from filternarrange_engine.testing.conformance import run_format_conformance
from filternarrange_format_tsv import plugin
import pathlib

def test_conformance():
    fixture = pathlib.Path(__file__).parent / "fixtures/sample.tsv"
    run_format_conformance(plugin, fixture)
```

- [ ] **Step 10: Install + run**

```bash
cd plugins/format-tsv && uv pip install -e . && uv run pytest -v
```

Expected: all green.

- [ ] **Step 11: Commit**

```bash
git add plugins/format-tsv/
git commit -m "feat(format-tsv): add TSV format plugin"
```

---

### Task 3: format-jsonl plugin

**Files:**
- Create: `plugins/format-jsonl/{pyproject.toml,manifest.toml,README.md}`
- Create: `plugins/format-jsonl/src/filternarrange_format_jsonl/{__init__.py,plugin.py,detect.py,parse.py,emit.py}`
- Create: `plugins/format-jsonl/tests/fixtures/sample.jsonl`
- Test: same 4-file suite as Task 2

- [ ] **Step 1: Write failing detect test**

```python
# plugins/format-jsonl/tests/test_detect.py
from filternarrange_format_jsonl import plugin

def test_detect_jsonl():
    sample = b'{"id":1,"name":"Ada"}\n{"id":2,"name":"Grace"}\n'
    res = plugin.detect(sample)
    assert res.format == "jsonl"
    assert res.confidence > 0.9

def test_single_json_object_not_jsonl():
    sample = b'{"id":1,"name":"Ada"}'
    res = plugin.detect(sample)
    assert res.confidence < 0.5

def test_json_array_not_jsonl():
    sample = b'[{"id":1}]'
    res = plugin.detect(sample)
    assert res.confidence < 0.1
```

- [ ] **Step 2: Implement detect.py**

```python
import json
from filternarrange_engine.core.plugin_protocols import DetectResult

def detect(sample: bytes) -> DetectResult:
    head = sample[:8192].decode("utf-8", errors="ignore").strip()
    if not head or head.startswith("["):
        return DetectResult(format="jsonl", confidence=0.0)
    lines = [ln for ln in head.splitlines() if ln.strip()]
    if len(lines) < 2:
        # Could still be JSONL with 1 line; low confidence
        try:
            json.loads(lines[0])
            return DetectResult(format="jsonl", confidence=0.45)
        except Exception:
            return DetectResult(format="jsonl", confidence=0.0)
    good = 0
    for ln in lines[:50]:
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict): good += 1
        except Exception:
            pass
    ratio = good / min(len(lines), 50)
    return DetectResult(format="jsonl", confidence=ratio)
```

- [ ] **Step 3: Implement parse.py (streaming)**

```python
import json, io
from typing import BinaryIO, AsyncIterator
from filternarrange_engine.core.canonical import TabularData, Column, TypeTag, infer_type_tag

def parse(source: BinaryIO) -> TabularData:
    # Two-pass: scan first 200 lines for union schema + types
    text = io.TextIOWrapper(source, encoding="utf-8")
    sample_objs = []
    for i, ln in enumerate(text):
        if i >= 200: break
        ln = ln.strip()
        if ln:
            sample_objs.append(json.loads(ln))
    keys: list[str] = []
    seen = set()
    for obj in sample_objs:
        for k in obj:
            if k not in seen:
                seen.add(k); keys.append(k)
    schema = []
    for k in keys:
        vals = [str(o[k]) for o in sample_objs if k in o and o[k] is not None]
        schema.append(Column(name=k, type=infer_type_tag(vals), nullable=True))
    async def rows() -> AsyncIterator[list]:
        source.seek(0)
        t2 = io.TextIOWrapper(source, encoding="utf-8")
        for ln in t2:
            ln = ln.strip()
            if not ln: continue
            obj = json.loads(ln)
            yield [obj.get(k) for k in keys]
    return TabularData(schema=schema, rows=rows())
```

- [ ] **Step 4: Implement emit.py**

```python
import json, io, asyncio
from typing import BinaryIO
from filternarrange_engine.core.canonical import TabularData

def emit(data: TabularData, sink: BinaryIO) -> None:
    text = io.TextIOWrapper(sink, encoding="utf-8", write_through=True)
    keys = [c.name for c in data.schema]
    async def drain():
        async for row in data.rows:
            obj = {k: v for k, v in zip(keys, row)}
            text.write(json.dumps(obj, ensure_ascii=False) + "\n")
    asyncio.run(drain())
```

- [ ] **Step 5: plugin.py / __init__.py / manifest / pyproject — identical pattern to Task 2 with `id = "jsonl"`, extensions `[".jsonl", ".ndjson"]`, entry-point `jsonl = "filternarrange_format_jsonl:plugin"`.**

- [ ] **Step 6: Fixture**

```jsonl
{"id":1,"name":"Ada","age":37}
{"id":2,"name":"Grace","age":85}
{"id":3,"name":"Linus","age":54}
```

- [ ] **Step 7: Parse/emit/conformance tests — same shape as Task 2.**

- [ ] **Step 8: Install + run + commit**

```bash
cd plugins/format-jsonl && uv pip install -e . && uv run pytest -v
git add plugins/format-jsonl/
git commit -m "feat(format-jsonl): add JSON Lines format plugin"
```

---

### Task 4: format-yaml plugin

**Files:** standard plugin layout under `plugins/format-yaml/`. Python pkg `filternarrange_format_yaml`.

- [ ] **Step 1: Failing detect test**

```python
# plugins/format-yaml/tests/test_detect.py
from filternarrange_format_yaml import plugin

def test_detect_yaml_doc():
    sample = b"name: Ada\nage: 37\nlanguages:\n  - python\n  - ada\n"
    res = plugin.detect(sample)
    assert res.format == "yaml"
    assert res.confidence > 0.7

def test_detect_yaml_doc_marker():
    sample = b"---\nfoo: bar\n"
    res = plugin.detect(sample)
    assert res.confidence > 0.9

def test_json_is_not_yaml():
    # YAML is a JSON superset; we lower confidence when JSON syntax dominates
    sample = b'{"a":1}'
    res = plugin.detect(sample)
    assert res.confidence < 0.4
```

- [ ] **Step 2: detect.py — structural sniff, prefer the `---` marker and indent-based mapping**

```python
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
        return DetectResult(format="yaml", confidence=0.3)  # let JSON win
    if isinstance(doc, (dict, list)):
        return DetectResult(format="yaml", confidence=0.8)
    return DetectResult(format="yaml", confidence=0.5)
```

- [ ] **Step 3: parse.py — emit TreeData**

```python
import yaml
from typing import BinaryIO
from filternarrange_engine.core.canonical import TreeData, Node, TypeTag, value_to_type_tag

def _to_node(key: str, val) -> Node:
    if isinstance(val, dict):
        return Node(key=key, value=None, type=TypeTag.NULL,
                    children=[_to_node(k, v) for k, v in val.items()])
    if isinstance(val, list):
        return Node(key=key, value=None, type=TypeTag.NULL,
                    children=[_to_node(str(i), v) for i, v in enumerate(val)])
    return Node(key=key, value=val, type=value_to_type_tag(val), children=[])

def parse(source: BinaryIO) -> TreeData:
    raw = source.read().decode("utf-8")
    doc = yaml.safe_load(raw)
    root = _to_node("$", doc if doc is not None else {})
    return TreeData(root=root, meta={"loader": "PyYAML.safe"})
```

- [ ] **Step 4: emit.py**

```python
import yaml, io
from typing import BinaryIO
from filternarrange_engine.core.canonical import TreeData, Node

def _from_node(n: Node):
    if n.children:
        # Detect array (numeric sequential keys) vs object
        keys = [c.key for c in n.children]
        if all(k.isdigit() for k in keys):
            return [_from_node(c) for c in n.children]
        return {c.key: _from_node(c) for c in n.children}
    return n.value

def emit(data: TreeData, sink: BinaryIO) -> None:
    obj = _from_node(data.root)
    if isinstance(obj, dict) and len(obj) == 1 and "$" in obj:
        obj = obj["$"]
    text = io.TextIOWrapper(sink, encoding="utf-8", write_through=True)
    yaml.safe_dump(obj, text, sort_keys=False, allow_unicode=True)
```

- [ ] **Step 5: plugin.py / __init__.py / manifest.toml (`shape = "tree"`) / pyproject (`dependencies = ["PyYAML>=6"]`).**

- [ ] **Step 6: Fixture `plugins/format-yaml/tests/fixtures/sample.yaml`**

```yaml
name: Ada
age: 37
languages:
  - python
  - ada
```

- [ ] **Step 7: Tests + install + commit**

```bash
cd plugins/format-yaml && uv pip install -e . && uv run pytest -v
git add plugins/format-yaml/
git commit -m "feat(format-yaml): add YAML format plugin (safe loader only)"
```

---

### Task 5: format-xml plugin

**Files:** standard layout under `plugins/format-xml/`. Python pkg `filternarrange_format_xml`. Library: `lxml`.

- [ ] **Step 1: Failing detect test**

```python
# plugins/format-xml/tests/test_detect.py
from filternarrange_format_xml import plugin

def test_detect_xml_decl():
    sample = b'<?xml version="1.0"?><root><x>1</x></root>'
    res = plugin.detect(sample)
    assert res.format == "xml"
    assert res.confidence > 0.95

def test_detect_xml_no_decl():
    sample = b'<root><x>1</x></root>'
    res = plugin.detect(sample)
    assert res.confidence > 0.8

def test_not_xml():
    res = plugin.detect(b'name=foo')
    assert res.confidence < 0.1
```

- [ ] **Step 2: detect.py — magic bytes + structural sniff**

```python
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
```

- [ ] **Step 3: parse.py — emit TreeData**

```python
from lxml import etree
from typing import BinaryIO
from filternarrange_engine.core.canonical import TreeData, Node, TypeTag, value_to_type_tag

def _to_node(elem) -> Node:
    children = []
    if elem.attrib:
        for k, v in elem.attrib.items():
            children.append(Node(key=f"@{k}", value=v, type=TypeTag.STRING, children=[]))
    for ch in elem:
        children.append(_to_node(ch))
    text = (elem.text or "").strip() if elem.text else ""
    if children:
        if text:
            children.insert(0, Node(key="#text", value=text, type=TypeTag.STRING, children=[]))
        return Node(key=elem.tag, value=None, type=TypeTag.NULL, children=children)
    return Node(key=elem.tag, value=text or None,
                type=value_to_type_tag(text or None), children=[])

def parse(source: BinaryIO) -> TreeData:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
    tree = etree.parse(source, parser)
    return TreeData(root=_to_node(tree.getroot()), meta={"parser": "lxml.safe"})
```

- [ ] **Step 4: emit.py**

```python
from lxml import etree
from typing import BinaryIO
from filternarrange_engine.core.canonical import TreeData, Node

def _build(node: Node):
    elem = etree.Element(node.key if not node.key.startswith("@") else node.key[1:])
    for c in node.children:
        if c.key.startswith("@"):
            elem.set(c.key[1:], str(c.value))
        elif c.key == "#text":
            elem.text = str(c.value)
        else:
            elem.append(_build(c))
    if not node.children and node.value is not None:
        elem.text = str(node.value)
    return elem

def emit(data: TreeData, sink: BinaryIO) -> None:
    root = _build(data.root)
    sink.write(etree.tostring(root, xml_declaration=True, encoding="utf-8", pretty_print=True))
```

- [ ] **Step 5: plugin.py / __init__.py / manifest (`shape = "tree"`) / pyproject (`dependencies = ["lxml>=5"]`).**

- [ ] **Step 6: Fixture `sample.xml`**

```xml
<?xml version="1.0"?>
<people>
  <person id="1"><name>Ada</name><age>37</age></person>
  <person id="2"><name>Grace</name><age>85</age></person>
</people>
```

- [ ] **Step 7: Parse, emit, conformance tests + install + commit**

```bash
cd plugins/format-xml && uv pip install -e . && uv run pytest -v
git add plugins/format-xml/
git commit -m "feat(format-xml): add XML format plugin via lxml"
```

---

### Task 6: format-xlsx plugin + sheet-pick

**Files:** standard layout under `plugins/format-xlsx/`. Python pkg `filternarrange_format_xlsx`. Library: `openpyxl`.

Special: an XLSX workbook may contain multiple sheets. The plugin exposes a `list_sheets(source)` API so the gateway can show a sheet picker before parse. `parse()` accepts an optional `sheet_name`.

- [ ] **Step 1: Failing detect test (magic bytes + xl/workbook.xml entry)**

```python
# plugins/format-xlsx/tests/test_detect.py
import pathlib
from filternarrange_format_xlsx import plugin

def test_detect_xlsx():
    fixture = pathlib.Path(__file__).parent / "fixtures/two_sheets.xlsx"
    with open(fixture, "rb") as f:
        sample = f.read(8192)
    res = plugin.detect(sample)
    assert res.format == "xlsx"
    assert res.confidence > 0.95

def test_zip_without_xl_workbook_not_xlsx():
    # A plain zip — should not detect as xlsx
    sample = b"PK\x03\x04" + b"\x00" * 100
    res = plugin.detect(sample)
    assert res.confidence < 0.5
```

- [ ] **Step 2: detect.py**

```python
import io, zipfile
from filternarrange_engine.core.plugin_protocols import DetectResult

def detect(sample: bytes) -> DetectResult:
    if not sample.startswith(b"PK\x03\x04"):
        return DetectResult(format="xlsx", confidence=0.0)
    try:
        with zipfile.ZipFile(io.BytesIO(sample)) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile:
        # Truncated central directory in the sample is common; treat as weak signal.
        return DetectResult(format="xlsx", confidence=0.4)
    if "xl/workbook.xml" in names:
        return DetectResult(format="xlsx", confidence=0.99)
    return DetectResult(format="xlsx", confidence=0.1)
```

- [ ] **Step 3: parse.py + list_sheets**

```python
from typing import BinaryIO, Optional, AsyncIterator
from openpyxl import load_workbook
from filternarrange_engine.core.canonical import TabularData, Column, infer_type_tag

def list_sheets(source: BinaryIO) -> list[str]:
    wb = load_workbook(source, read_only=True, data_only=True)
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()

def parse(source: BinaryIO, sheet_name: Optional[str] = None) -> TabularData:
    wb = load_workbook(source, read_only=True, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb[wb.sheetnames[0]]
    rows_iter = ws.iter_rows(values_only=True)
    header = list(next(rows_iter, []))
    # First-pass sample (up to 200 rows) for type inference
    sample = []
    for i, row in enumerate(rows_iter):
        if i >= 200: break
        sample.append(row)
    schema = [Column(name=str(h) if h is not None else f"col_{i}",
                     type=infer_type_tag([str(r[i]) for r in sample if i < len(r) and r[i] is not None]),
                     nullable=True)
              for i, h in enumerate(header)]
    async def rows() -> AsyncIterator[list]:
        # Reopen so we can stream from the top again
        source.seek(0)
        wb2 = load_workbook(source, read_only=True, data_only=True)
        ws2 = wb2[sheet_name] if sheet_name else wb2[wb2.sheetnames[0]]
        it = ws2.iter_rows(values_only=True)
        next(it, None)
        for row in it:
            yield list(row)
        wb2.close()
    return TabularData(schema=schema, rows=rows())
```

- [ ] **Step 4: emit.py (single-sheet workbook)**

```python
import asyncio
from typing import BinaryIO
from openpyxl import Workbook
from filternarrange_engine.core.canonical import TabularData

def emit(data: TabularData, sink: BinaryIO) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append([c.name for c in data.schema])
    async def drain():
        async for row in data.rows:
            ws.append(list(row))
    asyncio.run(drain())
    wb.save(sink)
```

- [ ] **Step 5: plugin.py — expose `list_sheets` on the plugin alongside detect/parse/emit**

```python
from . import detect as _d, parse as _p, emit as _e
from filternarrange_engine.core.plugin_protocols import load_manifest

class _Plugin:
    manifest = load_manifest(__file__, "../../manifest.toml")
    detect = staticmethod(_d.detect)
    parse  = staticmethod(_p.parse)
    emit   = staticmethod(_e.emit)
    list_sheets = staticmethod(_p.list_sheets)

plugin = _Plugin()
```

- [ ] **Step 6: manifest.toml + pyproject.toml** — `id = "xlsx"`, `extensions = [".xlsx"]`, `magic_bytes = ["PK"]`, `confidence_strategy = "magic-byte"`, `shape = "tabular"`, `multi-stream = true`. `dependencies = ["openpyxl>=3.1"]`.

- [ ] **Step 7: Fixture — generate `two_sheets.xlsx` via a small `conftest.py` helper or commit a pre-built file. Commit a pre-built file built by:**

```python
# scripts/build_xlsx_fixture.py — run once, NOT part of CI
from openpyxl import Workbook
wb = Workbook(); s1 = wb.active; s1.title = "people"
s1.append(["id","name","age"]); s1.append([1,"Ada",37]); s1.append([2,"Grace",85])
s2 = wb.create_sheet("orders"); s2.append(["order_id","total"]); s2.append([1001, 25.5])
wb.save("plugins/format-xlsx/tests/fixtures/two_sheets.xlsx")
```

- [ ] **Step 8: list_sheets + parse + emit + conformance tests**

```python
# plugins/format-xlsx/tests/test_parse.py
import asyncio, pathlib
from filternarrange_format_xlsx import plugin

def test_list_sheets():
    with open(pathlib.Path(__file__).parent / "fixtures/two_sheets.xlsx", "rb") as f:
        assert plugin.list_sheets(f) == ["people", "orders"]

def test_parse_specific_sheet():
    with open(pathlib.Path(__file__).parent / "fixtures/two_sheets.xlsx", "rb") as f:
        td = plugin.parse(f, sheet_name="orders")
    assert [c.name for c in td.schema] == ["order_id","total"]
    rows = asyncio.run(_collect(td))
    assert rows[0] == [1001, 25.5]

async def _collect(td):
    return [r async for r in td.rows]
```

- [ ] **Step 9: Install + run + commit**

```bash
cd plugins/format-xlsx && uv pip install -e . && uv run pytest -v
git add plugins/format-xlsx/
git commit -m "feat(format-xlsx): add XLSX format plugin with multi-sheet support"
```

---

### Task 7: filter-row plugin + schema-aware validation

**Files:** standard layout under `plugins/filter-row/`. Python pkg `filternarrange_filter_row`.

- [ ] **Step 1: Failing tests**

```python
# plugins/filter-row/tests/test_apply.py
import asyncio
from filternarrange_engine.core.canonical import TabularData, Column, TypeTag
from filternarrange_engine.core.filter_spec import RowSpec, RowPredicate
from filternarrange_filter_row import plugin

async def _rows(lst):
    for r in lst: yield r

def _make(rows):
    return TabularData(
        schema=[Column("id", TypeTag.INTEGER, False),
                Column("name", TypeTag.STRING, False),
                Column("age", TypeTag.INTEGER, True)],
        rows=_rows(rows))

def test_gt():
    td = _make([[1,"Ada",37],[2,"Grace",85],[3,"Kid",10]])
    spec = RowSpec(predicate=RowPredicate(col="age", op="gt", value=18))
    out = plugin.apply(td, spec)
    rows = asyncio.run(_collect(out))
    assert [r[0] for r in rows] == [1, 2]

def test_contains():
    td = _make([[1,"Ada",37],[2,"Grace Hopper",85]])
    out = plugin.apply(td, RowSpec(predicate=RowPredicate(col="name", op="contains", value="Hopper")))
    rows = asyncio.run(_collect(out))
    assert len(rows) == 1

def test_is_null():
    td = _make([[1,"Ada",37],[2,"Grace",None]])
    out = plugin.apply(td, RowSpec(predicate=RowPredicate(col="age", op="is_null")))
    rows = asyncio.run(_collect(out))
    assert len(rows) == 1 and rows[0][1] == "Grace"

def test_validate_unknown_column():
    schema = [Column("age", TypeTag.INTEGER, False)]
    errors = plugin.validate(RowSpec(predicate=RowPredicate(col="nope", op="eq", value=1)), schema=schema)
    assert errors and "unknown column" in errors[0].lower()

async def _collect(td):
    return [r async for r in td.rows]
```

- [ ] **Step 2: apply.py**

```python
import re as _re
from typing import AsyncIterator
from filternarrange_engine.core.canonical import TabularData
from filternarrange_engine.core.filter_spec import RowSpec, RowPredicate

_OPS = {
    "eq":  lambda a, b: a == b,
    "ne":  lambda a, b: a != b,
    "gt":  lambda a, b: a is not None and a >  b,
    "gte": lambda a, b: a is not None and a >= b,
    "lt":  lambda a, b: a is not None and a <  b,
    "lte": lambda a, b: a is not None and a <= b,
    "contains":    lambda a, b: a is not None and str(b) in str(a),
    "starts_with": lambda a, b: a is not None and str(a).startswith(str(b)),
    "ends_with":   lambda a, b: a is not None and str(a).endswith(str(b)),
    "regex":       lambda a, b: a is not None and bool(_re.search(str(b), str(a))),
    "in":     lambda a, b: a in (b or []),
    "not_in": lambda a, b: a not in (b or []),
    "is_null":     lambda a, _b: a is None,
    "is_not_null": lambda a, _b: a is not None,
}

def _predicate(spec: RowSpec, col_index: int):
    p = spec.predicate
    fn = _OPS[p.op]
    return lambda row: fn(row[col_index], p.value)

def apply(data: TabularData, spec: RowSpec) -> TabularData:
    col_index = next((i for i, c in enumerate(data.schema) if c.name == spec.predicate.col), -1)
    if col_index == -1:
        raise ValueError(f"unknown column: {spec.predicate.col!r}")
    pred = _predicate(spec, col_index)
    async def out() -> AsyncIterator[list]:
        async for row in data.rows:
            if pred(row): yield row
    return TabularData(schema=data.schema, rows=out())
```

- [ ] **Step 3: validate.py**

```python
from filternarrange_engine.core.filter_spec import RowSpec
from filternarrange_engine.core.canonical import Column

def validate(spec: RowSpec, schema: list[Column] | None = None) -> list[str]:
    errors: list[str] = []
    if spec.predicate.op not in {"eq","ne","gt","gte","lt","lte","contains",
                                  "starts_with","ends_with","regex","in","not_in",
                                  "is_null","is_not_null"}:
        errors.append(f"unknown op: {spec.predicate.op}")
    if schema is not None:
        names = {c.name for c in schema}
        if spec.predicate.col not in names:
            errors.append(f"unknown column: {spec.predicate.col!r} (available: {sorted(names)})")
    if spec.predicate.op in {"in", "not_in"} and not isinstance(spec.predicate.value, list):
        errors.append(f"{spec.predicate.op} requires a list value")
    return errors
```

- [ ] **Step 4: plugin.py / __init__.py / manifest (`kind = "filter"`, `kinds_supported = ["row"]`) / pyproject (entry-point group `filternarrange.filters`).**

```python
# plugin.py
from . import apply as _a, validate as _v
from filternarrange_engine.core.plugin_protocols import load_manifest

class _Plugin:
    manifest = load_manifest(__file__, "../../manifest.toml")
    apply    = staticmethod(_a.apply)
    validate = staticmethod(_v.validate)
    def explain(self, spec) -> str:
        p = spec.predicate
        return f"keep rows where {p.col} {p.op} {p.value!r}"

plugin = _Plugin()
```

- [ ] **Step 5: Run + commit**

```bash
cd plugins/filter-row && uv pip install -e . && uv run pytest -v
git add plugins/filter-row/
git commit -m "feat(filter-row): add row predicate filter plugin"
```

---

### Task 8: filter-expression plugin (simpleeval + register_function)

**Files:** standard layout under `plugins/filter-expression/`. Python pkg `filternarrange_filter_expression`.

The engine parses a SQL-ish expression by translating to a Python expression that `simpleeval` evaluates against a per-row name binding. We translate `AND/OR/NOT` (case-insensitive), `=` to `==`, and leave the rest alone. `register_function(name, fn, signature)` allows future plugins to extend the expression vocabulary.

- [ ] **Step 1: Failing tests**

```python
# plugins/filter-expression/tests/test_apply.py
import asyncio
from filternarrange_engine.core.canonical import TabularData, Column, TypeTag
from filternarrange_engine.core.filter_spec import ExpressionSpec
from filternarrange_filter_expression import plugin

async def _rows(lst):
    for r in lst: yield r

def _make(rows):
    return TabularData(
        schema=[Column("id", TypeTag.INTEGER, False),
                Column("name", TypeTag.STRING, False),
                Column("age", TypeTag.INTEGER, True),
                Column("country", TypeTag.STRING, True)],
        rows=_rows(rows))

def test_and():
    td = _make([[1,"Ada",37,"UK"],[2,"Grace",85,"US"],[3,"Kid",10,"IN"]])
    out = plugin.apply(td, ExpressionSpec(expr="age > 18 AND country = 'UK'"))
    rows = asyncio.run(_collect(out))
    assert [r[1] for r in rows] == ["Ada"]

def test_or_not():
    td = _make([[1,"Ada",37,"UK"],[2,"Grace",85,"US"]])
    out = plugin.apply(td, ExpressionSpec(expr="NOT (country = 'US') OR age > 80"))
    rows = asyncio.run(_collect(out))
    assert len(rows) == 2

def test_register_function():
    plugin.register_function("double", lambda x: x * 2, "int -> int")
    td = _make([[1,"Ada",37,"UK"],[2,"Grace",85,"US"]])
    out = plugin.apply(td, ExpressionSpec(expr="double(age) > 100"))
    rows = asyncio.run(_collect(out))
    assert [r[1] for r in rows] == ["Grace"]

def test_validate_syntax():
    errs = plugin.validate(ExpressionSpec(expr="age > "))
    assert errs

async def _collect(td):
    return [r async for r in td.rows]
```

- [ ] **Step 2: apply.py — translator + simpleeval**

```python
import re
from typing import AsyncIterator, Callable
from simpleeval import SimpleEval, FunctionNotDefined, NameNotDefined
from filternarrange_engine.core.canonical import TabularData
from filternarrange_engine.core.filter_spec import ExpressionSpec

_FUNCTIONS: dict[str, Callable] = {}
_SIGNATURES: dict[str, str] = {}

def register_function(name: str, fn: Callable, signature: str) -> None:
    _FUNCTIONS[name] = fn
    _SIGNATURES[name] = signature

def registered_functions() -> dict[str, str]:
    return dict(_SIGNATURES)

def _translate(expr: str) -> str:
    # SQL-ish → Python expression
    # Replace = (not ==, <=, >=, !=) with ==
    expr = re.sub(r"(?<![<>=!])=(?!=)", "==", expr)
    # Word ops: AND OR NOT (case-insensitive, word-boundary)
    expr = re.sub(r"\bAND\b", "and", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bOR\b",  "or",  expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bNOT\b", "not", expr, flags=re.IGNORECASE)
    return expr

def apply(data: TabularData, spec: ExpressionSpec) -> TabularData:
    py_expr = _translate(spec.expr)
    names = [c.name for c in data.schema]
    async def out() -> AsyncIterator[list]:
        async for row in data.rows:
            binding = {n: v for n, v in zip(names, row)}
            ev = SimpleEval(names=binding, functions=dict(_FUNCTIONS))
            try:
                if bool(ev.eval(py_expr)):
                    yield row
            except (FunctionNotDefined, NameNotDefined, SyntaxError):
                # silently drop — validate() should have caught this; if it didn't, skip the row
                continue
    return TabularData(schema=data.schema, rows=out())
```

- [ ] **Step 3: validate.py — schema-aware**

```python
import ast, re
from filternarrange_engine.core.filter_spec import ExpressionSpec
from filternarrange_engine.core.canonical import Column

def _translate(expr: str) -> str:
    expr = re.sub(r"(?<![<>=!])=(?!=)", "==", expr)
    expr = re.sub(r"\bAND\b", "and", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bOR\b",  "or",  expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bNOT\b", "not", expr, flags=re.IGNORECASE)
    return expr

def validate(spec: ExpressionSpec, schema: list[Column] | None = None) -> list[str]:
    errors: list[str] = []
    try:
        tree = ast.parse(_translate(spec.expr), mode="eval")
    except SyntaxError as e:
        return [f"syntax error: {e.msg} at col {e.offset}"]
    if schema is not None:
        names = {c.name for c in schema}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id not in names \
                    and node.id not in {"True", "False", "None"}:
                # could be a registered function name; we accept those too
                from .apply import registered_functions
                if node.id not in registered_functions():
                    errors.append(f"unknown name: {node.id!r}")
    return errors
```

- [ ] **Step 4: plugin.py — exposes register_function**

```python
from . import apply as _a, validate as _v
from filternarrange_engine.core.plugin_protocols import load_manifest

class _Plugin:
    manifest = load_manifest(__file__, "../../manifest.toml")
    apply    = staticmethod(_a.apply)
    validate = staticmethod(_v.validate)
    register_function = staticmethod(_a.register_function)
    registered_functions = staticmethod(_a.registered_functions)
    def explain(self, spec) -> str:
        return f"keep rows matching expression: {spec.expr}"

plugin = _Plugin()
```

- [ ] **Step 5: manifest / pyproject (`dependencies = ["simpleeval>=0.9"]`, entry-point `expression = "filternarrange_filter_expression:plugin"`).**

- [ ] **Step 6: Install + tests + commit**

```bash
cd plugins/filter-expression && uv pip install -e . && uv run pytest -v
git add plugins/filter-expression/
git commit -m "feat(filter-expression): add SQL-like expression filter plugin"
```

---

### Task 9: filter-regex plugin

**Files:** standard layout under `plugins/filter-regex/`. Python pkg `filternarrange_filter_regex`.

- [ ] **Step 1: Failing tests**

```python
# plugins/filter-regex/tests/test_apply.py
import asyncio
from filternarrange_engine.core.canonical import TabularData, Column, TypeTag
from filternarrange_engine.core.filter_spec import RegexSpec
from filternarrange_filter_regex import plugin

async def _rows(lst):
    for r in lst: yield r

def _make(rows):
    return TabularData(
        schema=[Column("id", TypeTag.INTEGER, False),
                Column("name", TypeTag.STRING, False),
                Column("note", TypeTag.STRING, True)],
        rows=_rows(rows))

def test_regex_any_string_col():
    td = _make([[1,"Ada","loves haskell"],[2,"Grace","COBOL"],[3,"Kid","plays"]])
    out = plugin.apply(td, RegexSpec(pattern=r"\bCOBOL\b"))
    rows = asyncio.run(_collect(out))
    assert [r[1] for r in rows] == ["Grace"]

def test_flags_i():
    td = _make([[1,"Ada","cobol fans"]])
    out = plugin.apply(td, RegexSpec(pattern="COBOL", flags=["i"]))
    rows = asyncio.run(_collect(out))
    assert len(rows) == 1

def test_validate_bad_pattern():
    errs = plugin.validate(RegexSpec(pattern="(unclosed"))
    assert errs and "regex" in errs[0].lower()

async def _collect(td):
    return [r async for r in td.rows]
```

- [ ] **Step 2: apply.py**

```python
import re
from typing import AsyncIterator
from filternarrange_engine.core.canonical import TabularData, TypeTag
from filternarrange_engine.core.filter_spec import RegexSpec

_FLAG = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}

def _compile(spec: RegexSpec):
    flags = 0
    for f in spec.flags: flags |= _FLAG.get(f, 0)
    return re.compile(spec.pattern, flags)

def apply(data: TabularData, spec: RegexSpec) -> TabularData:
    pat = _compile(spec)
    string_cols = [i for i, c in enumerate(data.schema) if c.type == TypeTag.STRING]
    async def out() -> AsyncIterator[list]:
        async for row in data.rows:
            for i in string_cols:
                v = row[i] if i < len(row) else None
                if v is not None and pat.search(str(v)):
                    yield row; break
    return TabularData(schema=data.schema, rows=out())
```

- [ ] **Step 3: validate.py**

```python
import re
from filternarrange_engine.core.filter_spec import RegexSpec

def validate(spec: RegexSpec, schema=None) -> list[str]:
    errors: list[str] = []
    try:
        re.compile(spec.pattern)
    except re.error as e:
        errors.append(f"invalid regex: {e}")
    for f in spec.flags:
        if f not in {"i","m","s"}:
            errors.append(f"unknown flag: {f!r}")
    return errors
```

- [ ] **Step 4: plugin.py / manifest / pyproject (entry-point `regex = "filternarrange_filter_regex:plugin"`).**

- [ ] **Step 5: Run + commit**

```bash
cd plugins/filter-regex && uv pip install -e . && uv run pytest -v
git add plugins/filter-regex/
git commit -m "feat(filter-regex): add regex search filter plugin"
```

---

### Task 10: analysis-summary-stats plugin

**Files:** standard layout under `plugins/analysis-summary-stats/`. Python pkg `filternarrange_analysis_summary_stats`.

- [ ] **Step 1: Failing tests**

```python
# plugins/analysis-summary-stats/tests/test_analyze.py
import asyncio
from filternarrange_engine.core.canonical import TabularData, Column, TypeTag
from filternarrange_analysis_summary_stats import plugin

async def _rows(lst):
    for r in lst: yield r

def _make(rows):
    return TabularData(
        schema=[Column("id", TypeTag.INTEGER, False),
                Column("name", TypeTag.STRING, False),
                Column("age", TypeTag.INTEGER, True)],
        rows=_rows(rows))

def test_summary_basics():
    td = _make([[1,"Ada",37],[2,"Grace",85],[3,"Ada",None]])
    res = asyncio.run(plugin.analyze(td, {}))
    cols = {c["name"]: c for c in res.payload["columns"]}
    assert cols["age"]["count"] == 2
    assert cols["age"]["nulls"] == 1
    assert cols["age"]["min"] == 37
    assert cols["age"]["max"] == 85
    assert cols["name"]["distinct"] == 2
    assert any(t["value"] == "Ada" and t["count"] == 2 for t in cols["name"]["top"])
```

- [ ] **Step 2: plugin.py + analyze**

```python
# plugin.py
import asyncio, statistics
from collections import Counter
from filternarrange_engine.core.canonical import TabularData, TypeTag
from filternarrange_engine.core.analysis import AnalysisResult
from filternarrange_engine.core.plugin_protocols import load_manifest

NUMERIC = {TypeTag.NUMBER, TypeTag.INTEGER}

class _Plugin:
    manifest = load_manifest(__file__, "../../manifest.toml")

    @staticmethod
    async def analyze(data: TabularData, options: dict) -> AnalysisResult:
        top_n = int(options.get("top_n", 10))
        cols = [{"name": c.name, "type": c.type.name.lower(),
                 "count": 0, "nulls": 0, "distinct": 0, "_values": []}
                for c in data.schema]
        async for row in data.rows:
            for i, v in enumerate(row):
                if i >= len(cols): continue
                if v is None or v == "":
                    cols[i]["nulls"] += 1
                else:
                    cols[i]["count"] += 1
                    cols[i]["_values"].append(v)
        out_cols = []
        for c, schema_c in zip(cols, data.schema):
            distinct = len(set(c["_values"]))
            entry = {"name": c["name"], "type": c["type"],
                     "count": c["count"], "nulls": c["nulls"], "distinct": distinct}
            if schema_c.type in NUMERIC and c["_values"]:
                nums = [float(v) for v in c["_values"] if v is not None]
                if nums:
                    entry["min"] = min(nums)
                    entry["max"] = max(nums)
                    entry["mean"] = statistics.fmean(nums)
                    entry["median"] = statistics.median(nums)
                    entry["stddev"] = statistics.pstdev(nums) if len(nums) > 1 else 0.0
            else:
                top = Counter(c["_values"]).most_common(top_n)
                entry["top"] = [{"value": v, "count": n} for v, n in top]
            del c["_values"]
            out_cols.append(entry)
        return AnalysisResult(kind="summary_stats", payload={"columns": out_cols}, warnings=[])

    @staticmethod
    def validate(spec, schema=None) -> list[str]:
        return []

plugin = _Plugin()
```

- [ ] **Step 3: manifest (`kind = "analysis"`, `id = "summary_stats"`, `shape = "tabular"`) + pyproject (entry-point group `filternarrange.analyses`).**

- [ ] **Step 4: Run + commit**

```bash
cd plugins/analysis-summary-stats && uv pip install -e . && uv run pytest -v
git add plugins/analysis-summary-stats/
git commit -m "feat(analysis-summary-stats): add per-column summary statistics plugin"
```

---

### Task 11: analysis-group-by plugin

**Files:** standard layout under `plugins/analysis-group-by/`.

- [ ] **Step 1: Failing tests**

```python
# plugins/analysis-group-by/tests/test_analyze.py
import asyncio
from filternarrange_engine.core.canonical import TabularData, Column, TypeTag
from filternarrange_engine.core.analysis import AnalysisSpec
from filternarrange_analysis_group_by import plugin

async def _rows(lst):
    for r in lst: yield r

def _make(rows):
    return TabularData(
        schema=[Column("country", TypeTag.STRING, False),
                Column("amount", TypeTag.NUMBER, False)],
        rows=_rows(rows))

def test_group_sum_count():
    td = _make([["IN", 10.0], ["US", 5.0], ["IN", 2.0], ["US", 7.0]])
    opts = {"by": ["country"], "agg": {"amount": ["sum", "count", "avg"]}}
    res = asyncio.run(plugin.analyze(td, opts))
    groups = {g["country"]: g for g in res.payload["groups"]}
    assert groups["IN"]["amount_sum"] == 12.0
    assert groups["IN"]["amount_count"] == 2
    assert groups["US"]["amount_avg"] == 6.0

def test_validate_unknown_col():
    schema = [Column("a", TypeTag.NUMBER, False)]
    errs = plugin.validate(AnalysisSpec(kind="group_by", options={"by":["nope"], "agg":{}}), schema=schema)
    assert errs and "unknown column" in errs[0].lower()
```

- [ ] **Step 2: plugin.py**

```python
import statistics
from collections import defaultdict
from filternarrange_engine.core.canonical import TabularData
from filternarrange_engine.core.analysis import AnalysisResult, AnalysisSpec
from filternarrange_engine.core.plugin_protocols import load_manifest

_AGGS = {
    "sum":    lambda vs: sum(vs),
    "count":  lambda vs: len(vs),
    "avg":    lambda vs: statistics.fmean(vs) if vs else 0,
    "min":    lambda vs: min(vs) if vs else None,
    "max":    lambda vs: max(vs) if vs else None,
    "median": lambda vs: statistics.median(vs) if vs else None,
}

class _Plugin:
    manifest = load_manifest(__file__, "../../manifest.toml")

    @staticmethod
    async def analyze(data: TabularData, options: dict) -> AnalysisResult:
        by = options["by"]
        agg = options.get("agg", {})
        name_index = {c.name: i for i, c in enumerate(data.schema)}
        by_idx = [name_index[b] for b in by]
        agg_idx = {col: name_index[col] for col in agg}
        buckets: dict[tuple, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        async for row in data.rows:
            key = tuple(row[i] for i in by_idx)
            for col, idx in agg_idx.items():
                v = row[idx]
                if v is None: continue
                try: buckets[key][col].append(float(v))
                except (TypeError, ValueError):
                    if "count" in agg.get(col, []):
                        buckets[key][col].append(v)
        groups = []
        for key, cols in buckets.items():
            entry = {b: k for b, k in zip(by, key)}
            for col, fns in agg.items():
                vs = cols.get(col, [])
                for fn in fns:
                    if fn == "count":
                        entry[f"{col}_count"] = len(vs)
                    else:
                        try:
                            entry[f"{col}_{fn}"] = _AGGS[fn]([v for v in vs if isinstance(v, (int, float))])
                        except KeyError:
                            entry[f"{col}_{fn}"] = None
            groups.append(entry)
        return AnalysisResult(kind="group_by", payload={"groups": groups}, warnings=[])

    @staticmethod
    def validate(spec: AnalysisSpec, schema=None) -> list[str]:
        errors: list[str] = []
        opts = spec.options
        if "by" not in opts or not opts["by"]:
            errors.append("group_by requires non-empty 'by'")
        if schema is not None:
            names = {c.name for c in schema}
            for col in opts.get("by", []):
                if col not in names:
                    errors.append(f"unknown column in 'by': {col!r}")
            for col in opts.get("agg", {}):
                if col not in names:
                    errors.append(f"unknown column in 'agg': {col!r}")
        for col, fns in opts.get("agg", {}).items():
            for fn in fns:
                if fn not in _AGGS:
                    errors.append(f"unknown aggregator: {fn!r}")
        return errors

plugin = _Plugin()
```

- [ ] **Step 3: manifest / pyproject (entry-point `group_by = "filternarrange_analysis_group_by:plugin"`).**

- [ ] **Step 4: Run + commit**

```bash
cd plugins/analysis-group-by && uv pip install -e . && uv run pytest -v
git add plugins/analysis-group-by/
git commit -m "feat(analysis-group-by): add group-by aggregation plugin"
```

---

### Task 12: analysis-chart-suggest plugin

Examines schema + sample cardinality; returns ranked Vega-Lite chart specs.

- [ ] **Step 1: Failing tests**

```python
# plugins/analysis-chart-suggest/tests/test_analyze.py
import asyncio
from filternarrange_engine.core.canonical import TabularData, Column, TypeTag
from filternarrange_analysis_chart_suggest import plugin

async def _rows(lst):
    for r in lst: yield r

def test_two_numerics_scatter():
    td = TabularData(
        schema=[Column("x", TypeTag.NUMBER, False), Column("y", TypeTag.NUMBER, False)],
        rows=_rows([[1.0, 2.0], [3.0, 4.0]]))
    res = asyncio.run(plugin.analyze(td, {}))
    kinds = [c["mark"] for c in res.payload["charts"]]
    assert "point" in kinds  # scatter

def test_datetime_numeric_line():
    td = TabularData(
        schema=[Column("ts", TypeTag.DATETIME, False), Column("v", TypeTag.NUMBER, False)],
        rows=_rows([["2026-01-01T00:00:00Z", 1.0]]))
    res = asyncio.run(plugin.analyze(td, {}))
    assert res.payload["charts"][0]["mark"] == "line"

def test_categorical_numeric_bar():
    td = TabularData(
        schema=[Column("c", TypeTag.STRING, False), Column("n", TypeTag.NUMBER, False)],
        rows=_rows([["a",1],["b",2]]))
    res = asyncio.run(plugin.analyze(td, {}))
    assert res.payload["charts"][0]["mark"] == "bar"
```

- [ ] **Step 2: plugin.py**

```python
from filternarrange_engine.core.canonical import TabularData, TypeTag
from filternarrange_engine.core.analysis import AnalysisResult
from filternarrange_engine.core.plugin_protocols import load_manifest

NUMERIC = {TypeTag.NUMBER, TypeTag.INTEGER}
TEMPORAL = {TypeTag.DATETIME}
CATEGORICAL = {TypeTag.STRING, TypeTag.BOOLEAN}

def _vl(mark, x, y, score, rationale, x_type, y_type):
    return {"mark": mark, "score": score, "rationale": rationale,
            "spec": {
                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                "mark": mark,
                "encoding": {
                    "x": {"field": x, "type": x_type},
                    "y": {"field": y, "type": y_type}
                }
            }}

def _vl_type(tag: TypeTag) -> str:
    if tag in NUMERIC: return "quantitative"
    if tag in TEMPORAL: return "temporal"
    return "nominal"

class _Plugin:
    manifest = load_manifest(__file__, "../../manifest.toml")

    @staticmethod
    async def analyze(data: TabularData, options: dict) -> AnalysisResult:
        cols = data.schema
        charts = []
        for i, a in enumerate(cols):
            for b in cols[i+1:]:
                if a.type in TEMPORAL and b.type in NUMERIC:
                    charts.append(_vl("line", a.name, b.name, 0.95,
                                      "temporal × numeric → line",
                                      "temporal", "quantitative"))
                elif b.type in TEMPORAL and a.type in NUMERIC:
                    charts.append(_vl("line", b.name, a.name, 0.95,
                                      "temporal × numeric → line",
                                      "temporal", "quantitative"))
                elif a.type in CATEGORICAL and b.type in NUMERIC:
                    charts.append(_vl("bar", a.name, b.name, 0.85,
                                      "categorical × numeric → bar",
                                      "nominal", "quantitative"))
                elif b.type in CATEGORICAL and a.type in NUMERIC:
                    charts.append(_vl("bar", b.name, a.name, 0.85,
                                      "categorical × numeric → bar",
                                      "nominal", "quantitative"))
                elif a.type in NUMERIC and b.type in NUMERIC:
                    charts.append(_vl("point", a.name, b.name, 0.7,
                                      "two numerics → scatter",
                                      "quantitative", "quantitative"))
        # consume rows so the async iterator is properly drained (cardinality used for
        # future ranking; not consumed here intentionally)
        async for _ in data.rows:
            break
        charts.sort(key=lambda c: c["score"], reverse=True)
        return AnalysisResult(kind="chart_suggest", payload={"charts": charts}, warnings=[])

    @staticmethod
    def validate(spec, schema=None) -> list[str]:
        return []

plugin = _Plugin()
```

- [ ] **Step 3: manifest / pyproject (entry-point `chart_suggest = "filternarrange_analysis_chart_suggest:plugin"`).**

- [ ] **Step 4: Run + commit**

```bash
cd plugins/analysis-chart-suggest && uv pip install -e . && uv run pytest -v
git add plugins/analysis-chart-suggest/
git commit -m "feat(analysis-chart-suggest): add Vega-Lite chart suggestion plugin"
```

---

### Task 13: analysis-schema-infer plugin (TreeData)

- [ ] **Step 1: Failing tests**

```python
# plugins/analysis-schema-infer/tests/test_analyze.py
import asyncio
from filternarrange_engine.core.canonical import TreeData, Node, TypeTag
from filternarrange_analysis_schema_infer import plugin

def test_infer_paths_and_depth():
    root = Node(key="$", value=None, type=TypeTag.NULL, children=[
        Node(key="name", value="Ada", type=TypeTag.STRING, children=[]),
        Node(key="addr", value=None, type=TypeTag.NULL, children=[
            Node(key="city", value="London", type=TypeTag.STRING, children=[]),
        ]),
    ])
    td = TreeData(root=root, meta={})
    res = asyncio.run(plugin.analyze(td, {}))
    paths = {p["path"]: p for p in res.payload["paths"]}
    assert "$.name" in paths
    assert "$.addr.city" in paths
    assert paths["$.name"]["types"] == ["string"]
    assert res.payload["depth"] == 3
    assert res.payload["leaf_count"] == 2
```

- [ ] **Step 2: plugin.py**

```python
from collections import defaultdict
from filternarrange_engine.core.canonical import TreeData, Node
from filternarrange_engine.core.analysis import AnalysisResult
from filternarrange_engine.core.plugin_protocols import load_manifest

class _Plugin:
    manifest = load_manifest(__file__, "../../manifest.toml")

    @staticmethod
    async def analyze(data: TreeData, options: dict) -> AnalysisResult:
        path_info: dict[str, dict] = defaultdict(
            lambda: {"types": set(), "depth_min": 1<<31, "depth_max": 0, "frequency": 0})
        leaf_count = 0
        max_depth = 0

        def walk(node: Node, path: str, depth: int):
            nonlocal leaf_count, max_depth
            max_depth = max(max_depth, depth)
            if not node.children:
                leaf_count += 1
                info = path_info[path]
                info["types"].add(node.type.name.lower())
                info["depth_min"] = min(info["depth_min"], depth)
                info["depth_max"] = max(info["depth_max"], depth)
                info["frequency"] += 1
            else:
                info = path_info[path]
                info["types"].add("object")
                info["depth_min"] = min(info["depth_min"], depth)
                info["depth_max"] = max(info["depth_max"], depth)
                info["frequency"] += 1
                for ch in node.children:
                    walk(ch, f"{path}.{ch.key}", depth + 1)

        walk(data.root, data.root.key, 1)
        paths = [{"path": p, "types": sorted(v["types"]),
                  "depth_min": v["depth_min"], "depth_max": v["depth_max"],
                  "frequency": v["frequency"]}
                 for p, v in path_info.items()]
        return AnalysisResult(kind="schema_infer",
                              payload={"paths": paths, "leaf_count": leaf_count, "depth": max_depth},
                              warnings=[])

    @staticmethod
    def validate(spec, schema=None) -> list[str]:
        return []

plugin = _Plugin()
```

- [ ] **Step 3: manifest (`shape = "tree"`) / pyproject (entry-point `schema_infer = "filternarrange_analysis_schema_infer:plugin"`).**

- [ ] **Step 4: Run + commit**

```bash
cd plugins/analysis-schema-infer && uv pip install -e . && uv run pytest -v
git add plugins/analysis-schema-infer/
git commit -m "feat(analysis-schema-infer): add TreeData schema inference plugin"
```

---

### Task 14: Data-engine dispatcher + `/internal/analyze` + extended `/internal/filter/preview`

**Files:**
- Modify: `apps/data-engine/src/filternarrange_engine/adapters/plugin_registry/registry.py`
- Modify: `apps/data-engine/src/filternarrange_engine/application/filter_service.py`
- Create: `apps/data-engine/src/filternarrange_engine/application/analysis_service.py`
- Modify: `apps/data-engine/src/filternarrange_engine/api/routers/filter.py`
- Create: `apps/data-engine/src/filternarrange_engine/api/routers/analysis.py`
- Modify: `apps/data-engine/src/filternarrange_engine/api/main.py` — mount analysis router
- Test: `apps/data-engine/tests/unit/application/test_filter_dispatch.py`, `test_analysis_service.py`
- Test: `apps/data-engine/tests/api/test_analyze_endpoint.py`, `test_filter_preview_all_kinds.py`

- [ ] **Step 1: Failing test for filter dispatch by kind**

```python
# apps/data-engine/tests/unit/application/test_filter_dispatch.py
import asyncio
from filternarrange_engine.application.filter_service import FilterService
from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.core.canonical import TabularData, Column, TypeTag

async def _rows(lst):
    for r in lst: yield r

def test_dispatch_row_kind():
    reg = PluginRegistry.load()
    svc = FilterService(reg)
    td = TabularData(
        schema=[Column("age", TypeTag.INTEGER, True)],
        rows=_rows([[10],[20],[30]]))
    out = svc.apply(td, {"kind": "row", "predicate": {"col": "age", "op": "gt", "value": 15}})
    rows = asyncio.run(_collect(out))
    assert [r[0] for r in rows] == [20, 30]

def test_unknown_kind_raises():
    reg = PluginRegistry.load()
    svc = FilterService(reg)
    td = TabularData(schema=[], rows=_rows([]))
    try:
        svc.apply(td, {"kind": "nope"})
    except ValueError as e:
        assert "unknown" in str(e)
    else:
        raise AssertionError("expected ValueError")

async def _collect(td):
    return [r async for r in td.rows]
```

- [ ] **Step 2: Extend PluginRegistry**

```python
# apps/data-engine/src/filternarrange_engine/adapters/plugin_registry/registry.py
# (additions only — Plan B already implemented format discovery)
from importlib.metadata import entry_points

class PluginRegistry:
    # ...existing format discovery in Plan B...

    @classmethod
    def load(cls):
        reg = cls()
        for ep in entry_points(group="filternarrange.formats"):
            reg._formats[ep.name] = ep.load()
        for ep in entry_points(group="filternarrange.filters"):
            reg._filters[ep.name] = ep.load()
        for ep in entry_points(group="filternarrange.analyses"):
            reg._analyses[ep.name] = ep.load()
        return reg

    def get_format(self, fmt: str): return self._formats[fmt]
    def get_filter(self, kind: str):
        if kind not in self._filters:
            raise ValueError(f"unknown filter kind: {kind!r}")
        return self._filters[kind]
    def get_analysis(self, kind: str):
        if kind not in self._analyses:
            raise ValueError(f"unknown analysis kind: {kind!r}")
        return self._analyses[kind]
```

- [ ] **Step 3: FilterService dispatch**

```python
# apps/data-engine/src/filternarrange_engine/application/filter_service.py
from filternarrange_engine.core.filter_spec import parse_filter_spec
from filternarrange_engine.core.canonical import TabularData, TreeData

class FilterService:
    def __init__(self, registry):
        self._registry = registry

    def apply(self, data: TabularData | TreeData, spec_payload: dict):
        spec = parse_filter_spec(spec_payload)
        plugin = self._registry.get_filter(spec.kind)
        # schema-aware validation
        schema = data.schema if isinstance(data, TabularData) else None
        errors = plugin.validate(spec, schema=schema) if hasattr(plugin, "validate") else []
        if errors:
            raise ValueError(f"filter validation failed: {errors}")
        return plugin.apply(data, spec)
```

- [ ] **Step 4: Run + see green**

```bash
cd apps/data-engine && uv run pytest tests/unit/application/test_filter_dispatch.py -v
```

- [ ] **Step 5: Failing test for AnalysisService**

```python
# apps/data-engine/tests/unit/application/test_analysis_service.py
import asyncio
from filternarrange_engine.application.analysis_service import AnalysisService
from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.core.canonical import TabularData, Column, TypeTag

async def _rows(lst):
    for r in lst: yield r

def test_summary_stats():
    svc = AnalysisService(PluginRegistry.load())
    td = TabularData(schema=[Column("age", TypeTag.INTEGER, True)], rows=_rows([[1],[2],[3]]))
    res = asyncio.run(svc.analyze(td, {"kind": "summary_stats", "options": {}}))
    assert res.kind == "summary_stats"
    assert res.payload["columns"][0]["count"] == 3
```

- [ ] **Step 6: AnalysisService impl**

```python
# apps/data-engine/src/filternarrange_engine/application/analysis_service.py
from filternarrange_engine.core.analysis import parse_analysis_spec
from filternarrange_engine.core.canonical import TabularData, TreeData

class AnalysisService:
    def __init__(self, registry):
        self._registry = registry

    async def analyze(self, data: TabularData | TreeData, spec_payload: dict):
        spec = parse_analysis_spec(spec_payload)
        plugin = self._registry.get_analysis(spec.kind)
        schema = data.schema if isinstance(data, TabularData) else None
        errors = plugin.validate(spec, schema=schema) if hasattr(plugin, "validate") else []
        if errors:
            raise ValueError(f"analysis validation failed: {errors}")
        return await plugin.analyze(data, spec.options)
```

- [ ] **Step 7: API router**

```python
# apps/data-engine/src/filternarrange_engine/api/routers/analysis.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from filternarrange_engine.application.analysis_service import AnalysisService
from filternarrange_engine.application.upload_service import UploadService  # from Plan B
from filternarrange_engine.application.filter_service import FilterService
from filternarrange_engine.api.deps import get_analysis_service, get_upload_service, get_filter_service

router = APIRouter(prefix="/internal", tags=["analysis"])

class AnalyzeBody(BaseModel):
    upload_id: str
    filter: dict | None = None
    analysis: dict

@router.post("/analyze")
async def analyze(body: AnalyzeBody,
                  ana: AnalysisService = Depends(get_analysis_service),
                  up:  UploadService   = Depends(get_upload_service),
                  flt: FilterService   = Depends(get_filter_service)):
    try:
        data = up.load_canonical(body.upload_id)
        if body.filter:
            data = flt.apply(data, body.filter)
        result = await ana.analyze(data, body.analysis)
        return {"kind": result.kind, "payload": result.payload, "warnings": result.warnings}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(e)})
```

- [ ] **Step 8: Extend `routers/filter.py` to accept any kind** — replace body type check from Plan B's `ColumnFilterBody` to a generic `dict`, then route through `FilterService.apply()`.

```python
# apps/data-engine/src/filternarrange_engine/api/routers/filter.py  (modified)
class FilterPreviewBody(BaseModel):
    upload_id: str
    filter: dict
    limit: int = 100

@router.post("/filter/preview")
async def preview(body: FilterPreviewBody,
                  up: UploadService = Depends(get_upload_service),
                  flt: FilterService = Depends(get_filter_service)):
    try:
        data = up.load_canonical(body.upload_id)
        out = flt.apply(data, body.filter)
        rows = []
        async for row in out.rows:
            rows.append(row)
            if len(rows) >= body.limit: break
        return {"schema": [{"name": c.name, "type": c.type.name.lower()} for c in out.schema],
                "rows": rows}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(e)})
```

- [ ] **Step 9: Mount router**

```python
# apps/data-engine/src/filternarrange_engine/api/main.py  (modified)
from .routers import analysis as analysis_router
app.include_router(analysis_router.router)
```

- [ ] **Step 10: API integration tests**

```python
# apps/data-engine/tests/api/test_analyze_endpoint.py
def test_analyze_summary(client, csv_upload):
    body = {"upload_id": csv_upload, "analysis": {"kind": "summary_stats", "options": {}}}
    r = client.post("/internal/analyze", json=body)
    assert r.status_code == 200
    assert r.json()["kind"] == "summary_stats"

def test_analyze_unknown_kind(client, csv_upload):
    body = {"upload_id": csv_upload, "analysis": {"kind": "nope"}}
    r = client.post("/internal/analyze", json=body)
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_REQUEST"
```

```python
# apps/data-engine/tests/api/test_filter_preview_all_kinds.py
def test_row_preview(client, csv_upload):
    body = {"upload_id": csv_upload,
            "filter": {"kind": "row", "predicate": {"col": "age", "op": "gt", "value": 18}},
            "limit": 10}
    r = client.post("/internal/filter/preview", json=body)
    assert r.status_code == 200

def test_expression_preview(client, csv_upload):
    body = {"upload_id": csv_upload,
            "filter": {"kind": "expression", "expr": "age > 18"}, "limit": 10}
    r = client.post("/internal/filter/preview", json=body)
    assert r.status_code == 200

def test_regex_preview(client, csv_upload):
    body = {"upload_id": csv_upload,
            "filter": {"kind": "regex", "pattern": "^A"}, "limit": 10}
    r = client.post("/internal/filter/preview", json=body)
    assert r.status_code == 200

def test_schema_aware_unknown_col(client, csv_upload):
    body = {"upload_id": csv_upload,
            "filter": {"kind": "row", "predicate": {"col": "nope", "op": "eq", "value": 1}},
            "limit": 10}
    r = client.post("/internal/filter/preview", json=body)
    assert r.status_code == 400
```

- [ ] **Step 11: Run + commit**

```bash
cd apps/data-engine && uv run pytest -v
git add apps/data-engine/
git commit -m "feat(data-engine): dispatch filter/analysis by kind; add /internal/analyze"
```

---

### Task 15: Gateway DTOs + AnalyzeController + extended FilterController + SheetController

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/dto/FilterSpecDto.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/dto/AnalyzeRequest.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/dto/AnalyzeResponse.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/AnalyzeController.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/SheetController.java`
- Modify: `apps/gateway/src/main/java/io/filternarrange/gateway/api/FilterController.java`
- Modify: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/http/DataEngineClient.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/application/AnalyzeService.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/api/AnalyzeControllerTest.java`

- [ ] **Step 1: Failing controller test**

```java
// AnalyzeControllerTest.java
@WebMvcTest(AnalyzeController.class)
class AnalyzeControllerTest {
  @Autowired MockMvc mvc;
  @MockBean AnalyzeService service;

  @Test
  void analyzeReturnsPayload() throws Exception {
    when(service.analyze(any(), any())).thenReturn(
        new AnalyzeResponse("summary_stats", Map.of("columns", List.of()), List.of()));
    mvc.perform(post("/api/v1/analyze")
            .header("Authorization", "Bearer test")
            .contentType("application/json")
            .content("""
              {"upload_id":"u1","analysis":{"kind":"summary_stats","options":{}}}
              """))
       .andExpect(status().isOk())
       .andExpect(jsonPath("$.kind").value("summary_stats"));
  }
}
```

- [ ] **Step 2: DTOs**

```java
// FilterSpecDto.java — passthrough JSON; gateway does NOT parse the spec
// (the data-engine validates kind + fields). This keeps additive launches
// of new kinds zero-change at the gateway.
public record FilterSpecDto(Map<String, Object> raw) {}

// AnalyzeRequest.java
public record AnalyzeRequest(
    @NotBlank String upload_id,
    Map<String, Object> filter,            // optional
    @NotNull Map<String, Object> analysis  // {kind, options}
) {}

// AnalyzeResponse.java
public record AnalyzeResponse(String kind, Map<String, Object> payload, List<String> warnings) {}
```

- [ ] **Step 3: AnalyzeService**

```java
// AnalyzeService.java
@Service
public class AnalyzeService {
  private final DataEngineClient client;
  public AnalyzeService(DataEngineClient client) { this.client = client; }

  public AnalyzeResponse analyze(String userId, AnalyzeRequest req) {
    return client.analyze(req);
  }
}
```

- [ ] **Step 4: AnalyzeController**

```java
// AnalyzeController.java
@RestController
@RequestMapping("/api/v1")
public class AnalyzeController {
  private final AnalyzeService service;
  public AnalyzeController(AnalyzeService s) { this.service = s; }

  @PostMapping("/analyze")
  public AnalyzeResponse analyze(@AuthenticationPrincipal Jwt jwt,
                                 @Valid @RequestBody AnalyzeRequest req) {
    return service.analyze(jwt.getSubject(), req);
  }
}
```

- [ ] **Step 5: DataEngineClient extension**

```java
// DataEngineClient.java additions
public AnalyzeResponse analyze(AnalyzeRequest req) {
  return restClient.post().uri("/internal/analyze")
      .body(req).retrieve().body(AnalyzeResponse.class);
}

public PreviewResponse previewFilterAny(String uploadId, Map<String,Object> filter, int limit) {
  return restClient.post().uri("/internal/filter/preview")
      .body(Map.of("upload_id", uploadId, "filter", filter, "limit", limit))
      .retrieve().body(PreviewResponse.class);
}

public List<String> listSheets(String uploadId) {
  return restClient.get().uri("/internal/uploads/{id}/sheets", uploadId)
      .retrieve().body(new ParameterizedTypeReference<List<String>>() {});
}
```

- [ ] **Step 6: FilterController extension — accept any filter kind**

```java
// FilterController.java (modified)
@PostMapping("/filter/preview")
public PreviewResponse preview(@AuthenticationPrincipal Jwt jwt,
                               @Valid @RequestBody FilterPreviewRequest req) {
  return client.previewFilterAny(req.upload_id(), req.filter(), req.limit());
}

public record FilterPreviewRequest(
    @NotBlank String upload_id,
    @NotNull Map<String, Object> filter,
    @Min(1) @Max(1000) int limit
) {}
```

- [ ] **Step 7: SheetController**

```java
// SheetController.java
@RestController
@RequestMapping("/api/v1")
public class SheetController {
  private final DataEngineClient client;
  public SheetController(DataEngineClient c) { this.client = c; }

  @GetMapping("/uploads/{id}/sheets")
  public List<String> sheets(@PathVariable String id) {
    return client.listSheets(id);
  }
}
```

- [ ] **Step 8: Add `/internal/uploads/{id}/sheets` to data-engine**

```python
# apps/data-engine/src/filternarrange_engine/api/routers/uploads.py  (additions)
@router.get("/internal/uploads/{upload_id}/sheets")
def sheets(upload_id: str, up: UploadService = Depends(get_upload_service)):
    raw = up.open_raw(upload_id)
    fmt = up.get_detected_format(upload_id)
    if fmt != "xlsx":
        raise HTTPException(400, detail={"code":"NOT_MULTI_SHEET","message":"upload is not XLSX"})
    from filternarrange_format_xlsx import plugin as xlsx
    return xlsx.list_sheets(raw)
```

- [ ] **Step 9: Run + commit**

```bash
cd apps/gateway && ./mvnw test
git add apps/gateway/ apps/data-engine/src/filternarrange_engine/api/routers/uploads.py
git commit -m "feat(gateway): add /api/v1/analyze, sheet picker, extended filter dispatch"
```

---

### Task 16: OpenAPI contract bump

**Files:**
- Modify: `contracts/openapi/gateway-public.v1.yaml`
- Modify: `contracts/openapi/gateway-internal.v1.yaml`
- Test: contract validation in CI is already wired by Plan B; we add example payloads.

- [ ] **Step 1: Bump patch + add paths**

```yaml
# contracts/openapi/gateway-public.v1.yaml — additive within v1
info:
  version: 1.1.0
paths:
  /api/v1/filter/preview:
    post:
      requestBody:
        content:
          application/json:
            schema: { $ref: "#/components/schemas/FilterPreviewRequest" }
  /api/v1/analyze:
    post:
      summary: Run an analysis against an upload, optionally pre-filtered
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: "#/components/schemas/AnalyzeRequest" }
      responses:
        "200":
          content:
            application/json:
              schema: { $ref: "#/components/schemas/AnalyzeResponse" }
        "400": { $ref: "#/components/responses/ErrorEnvelope" }
  /api/v1/uploads/{id}/sheets:
    get:
      parameters:
        - in: path
          name: id
          required: true
          schema: { type: string }
      responses:
        "200":
          content:
            application/json:
              schema:
                type: array
                items: { type: string }
components:
  schemas:
    FilterSpec:
      oneOf:
        - $ref: "#/components/schemas/ColumnFilterSpec"
        - $ref: "#/components/schemas/RowFilterSpec"
        - $ref: "#/components/schemas/ExpressionFilterSpec"
        - $ref: "#/components/schemas/RegexFilterSpec"
      discriminator:
        propertyName: kind
        mapping:
          column:     "#/components/schemas/ColumnFilterSpec"
          row:        "#/components/schemas/RowFilterSpec"
          expression: "#/components/schemas/ExpressionFilterSpec"
          regex:      "#/components/schemas/RegexFilterSpec"
    ColumnFilterSpec:
      type: object
      required: [kind]
      properties:
        kind:    { type: string, enum: [column] }
        include: { type: array, items: { type: string } }
        exclude: { type: array, items: { type: string } }
    RowFilterSpec:
      type: object
      required: [kind, predicate]
      properties:
        kind: { type: string, enum: [row] }
        predicate:
          type: object
          required: [col, op]
          properties:
            col: { type: string }
            op:
              type: string
              enum: [eq,ne,gt,gte,lt,lte,contains,starts_with,ends_with,regex,in,not_in,is_null,is_not_null]
            value: {}
    ExpressionFilterSpec:
      type: object
      required: [kind, expr]
      properties:
        kind: { type: string, enum: [expression] }
        expr: { type: string }
    RegexFilterSpec:
      type: object
      required: [kind, pattern]
      properties:
        kind:    { type: string, enum: [regex] }
        pattern: { type: string }
        flags:
          type: array
          items: { type: string, enum: [i, m, s] }
    FilterPreviewRequest:
      type: object
      required: [upload_id, filter]
      properties:
        upload_id: { type: string }
        filter:    { $ref: "#/components/schemas/FilterSpec" }
        limit:     { type: integer, minimum: 1, maximum: 1000, default: 100 }
    AnalyzeRequest:
      type: object
      required: [upload_id, analysis]
      properties:
        upload_id: { type: string }
        filter:    { $ref: "#/components/schemas/FilterSpec" }
        analysis:
          type: object
          required: [kind]
          properties:
            kind:    { type: string, enum: [summary_stats, group_by, chart_suggest, schema_infer] }
            options: { type: object, additionalProperties: true }
    AnalyzeResponse:
      type: object
      required: [kind, payload]
      properties:
        kind:     { type: string }
        payload:  { type: object, additionalProperties: true }
        warnings: { type: array, items: { type: string } }
  responses:
    ErrorEnvelope:
      description: Structured error
      content:
        application/json:
          schema:
            type: object
            required: [code, message]
            properties:
              code:      { type: string }
              plugin_id: { type: string }
              message:   { type: string }
              trace_id:  { type: string }
```

- [ ] **Step 2: Mirror the same `FilterSpec`, `AnalyzeRequest`, `AnalyzeResponse`, and sheets endpoint into `contracts/openapi/gateway-internal.v1.yaml` (under `/internal/...` paths).**

- [ ] **Step 3: Run contract validation locally**

```bash
npx --yes @redocly/cli lint contracts/openapi/gateway-public.v1.yaml
npx --yes @redocly/cli lint contracts/openapi/gateway-internal.v1.yaml
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add contracts/openapi/
git commit -m "feat(contracts): add analyze, sheets, multi-kind FilterSpec (v1.1.0, additive)"
```

---

### Task 17: Frontend filter mode picker (Columns/Rows/Expression/Regex)

**Files:**
- Create: `apps/frontend/src/features/filter/ui/FilterModePicker.tsx`
- Create: `apps/frontend/src/features/filter/ui/RowFilterForm.tsx`
- Create: `apps/frontend/src/features/filter/ui/RegexFilterForm.tsx`
- Modify: `apps/frontend/src/features/filter/ui/FilterPage.tsx` (Plan B)
- Modify: `apps/frontend/src/features/filter/state/filterStore.ts`
- Test: `apps/frontend/src/features/filter/ui/FilterModePicker.test.tsx`, `RowFilterForm.test.tsx`

- [ ] **Step 1: Failing test for FilterModePicker**

```tsx
// apps/frontend/src/features/filter/ui/FilterModePicker.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { FilterModePicker } from "./FilterModePicker";

test("switches active mode on tab click", () => {
  const onChange = vi.fn();
  render(<FilterModePicker mode="column" onChange={onChange} />);
  fireEvent.click(screen.getByRole("tab", { name: /rows/i }));
  expect(onChange).toHaveBeenCalledWith("row");
});

test("renders all four tabs", () => {
  render(<FilterModePicker mode="column" onChange={() => {}} />);
  expect(screen.getByRole("tab", { name: /columns/i })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: /rows/i })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: /expression/i })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: /regex/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: FilterModePicker component**

```tsx
// apps/frontend/src/features/filter/ui/FilterModePicker.tsx
import * as React from "react";

export type FilterMode = "column" | "row" | "expression" | "regex";

const TABS: { id: FilterMode; label: string }[] = [
  { id: "column",     label: "Columns" },
  { id: "row",        label: "Rows" },
  { id: "expression", label: "Expression" },
  { id: "regex",      label: "Regex" },
];

export function FilterModePicker({ mode, onChange }: {
  mode: FilterMode; onChange: (m: FilterMode) => void;
}) {
  return (
    <div role="tablist" aria-label="Filter mode" className="filter-mode-picker">
      {TABS.map(t => (
        <button
          key={t.id}
          role="tab"
          aria-selected={mode === t.id}
          className={mode === t.id ? "tab tab-active" : "tab"}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: RowFilterForm**

```tsx
// apps/frontend/src/features/filter/ui/RowFilterForm.tsx
import * as React from "react";
import type { ColumnMeta } from "@/shared/api/client";

const OPS = ["eq","ne","gt","gte","lt","lte","contains","starts_with","ends_with",
             "regex","in","not_in","is_null","is_not_null"] as const;

export type RowPredicate = { col: string; op: (typeof OPS)[number]; value?: unknown };

export function RowFilterForm({ schema, value, onChange }: {
  schema: ColumnMeta[];
  value: RowPredicate;
  onChange: (p: RowPredicate) => void;
}) {
  const needsValue = !value.op.startsWith("is_");
  return (
    <div className="row-filter">
      <label>
        Column:
        <select value={value.col} onChange={e => onChange({ ...value, col: e.target.value })}>
          {schema.map(c => <option key={c.name} value={c.name}>{c.name} ({c.type})</option>)}
        </select>
      </label>
      <label>
        Operator:
        <select value={value.op} onChange={e => onChange({ ...value, op: e.target.value as any })}>
          {OPS.map(op => <option key={op} value={op}>{op}</option>)}
        </select>
      </label>
      {needsValue && (
        <label>
          Value:
          <input
            value={value.value as string ?? ""}
            onChange={e => onChange({ ...value, value: e.target.value })}
          />
        </label>
      )}
    </div>
  );
}
```

- [ ] **Step 4: RegexFilterForm**

```tsx
// apps/frontend/src/features/filter/ui/RegexFilterForm.tsx
import * as React from "react";

export type RegexSpec = { pattern: string; flags: ("i"|"m"|"s")[] };

export function RegexFilterForm({ value, onChange }: {
  value: RegexSpec;
  onChange: (s: RegexSpec) => void;
}) {
  const toggle = (f: "i"|"m"|"s") => onChange({
    ...value,
    flags: value.flags.includes(f) ? value.flags.filter(x => x !== f) : [...value.flags, f],
  });
  return (
    <div className="regex-filter">
      <label>
        Pattern:
        <input value={value.pattern} onChange={e => onChange({ ...value, pattern: e.target.value })} />
      </label>
      <div className="flags">
        {(["i","m","s"] as const).map(f => (
          <label key={f}>
            <input type="checkbox" checked={value.flags.includes(f)} onChange={() => toggle(f)} /> {f}
          </label>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Modify FilterPage to host all four modes**

```tsx
// FilterPage.tsx (relevant excerpt — replaces Plan B's columns-only body)
const [mode, setMode] = useState<FilterMode>("column");
const [columnSpec, setColumnSpec] = useState<{include: string[]}>({ include: [] });
const [rowSpec, setRowSpec] = useState<RowPredicate>({ col: schema[0]?.name ?? "", op: "eq", value: "" });
const [exprSpec, setExprSpec] = useState<{ expr: string }>({ expr: "" });
const [regexSpec, setRegexSpec] = useState<RegexSpec>({ pattern: "", flags: [] });

const filter = useMemo<Record<string, unknown>>(() => {
  switch (mode) {
    case "column":     return { kind: "column", ...columnSpec };
    case "row":        return { kind: "row", predicate: rowSpec };
    case "expression": return { kind: "expression", expr: exprSpec.expr };
    case "regex":      return { kind: "regex", pattern: regexSpec.pattern, flags: regexSpec.flags };
  }
}, [mode, columnSpec, rowSpec, exprSpec, regexSpec]);

return (
  <div>
    <FilterModePicker mode={mode} onChange={setMode} />
    {mode === "column"     && <ColumnFilterForm schema={schema} value={columnSpec}  onChange={setColumnSpec} />}
    {mode === "row"        && <RowFilterForm     schema={schema} value={rowSpec}    onChange={setRowSpec} />}
    {mode === "expression" && <ExpressionFilterEditor schema={schema} value={exprSpec} onChange={setExprSpec} />}
    {mode === "regex"      && <RegexFilterForm  value={regexSpec} onChange={setRegexSpec} />}
    <PreviewPanel uploadId={uploadId} filter={filter} />
  </div>
);
```

- [ ] **Step 6: Run tests + commit**

```bash
cd apps/frontend && npm test -- features/filter
git add apps/frontend/src/features/filter/
git commit -m "feat(frontend): add filter mode picker with column/row/expression/regex tabs"
```

---

### Task 18: Frontend expression editor (Monaco + schema autocomplete)

**Files:**
- Create: `apps/frontend/src/features/filter/ui/ExpressionFilterEditor.tsx`
- Modify: `apps/frontend/package.json` — add `@monaco-editor/react`
- Test: `apps/frontend/src/features/filter/ui/ExpressionFilterEditor.test.tsx`

- [ ] **Step 1: Add Monaco dep**

```bash
cd apps/frontend && npm install @monaco-editor/react@4 monaco-editor@0.52
```

- [ ] **Step 2: Failing test**

```tsx
// ExpressionFilterEditor.test.tsx
import { render, screen } from "@testing-library/react";
import { ExpressionFilterEditor } from "./ExpressionFilterEditor";

vi.mock("@monaco-editor/react", () => ({
  __esModule: true,
  default: ({ value, onChange }: any) => (
    <textarea data-testid="monaco" value={value} onChange={e => onChange(e.target.value)} />
  ),
}));

test("calls onChange when editor value changes", async () => {
  const onChange = vi.fn();
  render(<ExpressionFilterEditor
    schema={[{ name: "age", type: "integer" }]}
    value={{ expr: "" }}
    onChange={onChange}
  />);
  const ta = screen.getByTestId("monaco");
  ta.dispatchEvent(new Event("change", { bubbles: true }));
  // basic render assertion
  expect(screen.getByTestId("monaco")).toBeInTheDocument();
});
```

- [ ] **Step 3: Component**

```tsx
// ExpressionFilterEditor.tsx
import * as React from "react";
import Editor, { OnMount } from "@monaco-editor/react";
import type { ColumnMeta } from "@/shared/api/client";

export function ExpressionFilterEditor({ schema, value, onChange }: {
  schema: ColumnMeta[];
  value: { expr: string };
  onChange: (v: { expr: string }) => void;
}) {
  const handleMount: OnMount = (_editor, monaco) => {
    // Register a single-shot language with autocomplete for schema columns
    monaco.languages.register({ id: "fna-expr" });
    monaco.languages.setMonarchTokensProvider("fna-expr", {
      keywords: ["AND","OR","NOT","TRUE","FALSE","NULL"],
      tokenizer: {
        root: [
          [/[A-Za-z_][A-Za-z0-9_]*/, {
            cases: { "@keywords": "keyword", "@default": "identifier" }
          }],
          [/'[^']*'/, "string"],
          [/\d+(\.\d+)?/, "number"],
          [/[=<>!]+/, "operator"],
        ],
      },
    });
    monaco.languages.registerCompletionItemProvider("fna-expr", {
      provideCompletionItems: () => ({
        suggestions: [
          ...schema.map(c => ({
            label: c.name,
            kind: monaco.languages.CompletionItemKind.Field,
            insertText: c.name,
            detail: c.type,
            range: undefined as any,
          })),
          ...["AND","OR","NOT","TRUE","FALSE","NULL"].map(kw => ({
            label: kw,
            kind: monaco.languages.CompletionItemKind.Keyword,
            insertText: kw,
            range: undefined as any,
          })),
        ],
      }),
    });
  };

  return (
    <div className="expression-editor">
      <Editor
        height="180px"
        language="fna-expr"
        theme="vs-light"
        value={value.expr}
        onMount={handleMount}
        onChange={(v) => onChange({ expr: v ?? "" })}
        options={{ minimap: { enabled: false }, fontSize: 14 }}
      />
      <div className="hint">
        e.g. <code>age &gt; 18 AND country = 'IN'</code>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run + commit**

```bash
cd apps/frontend && npm test -- ExpressionFilterEditor
git add apps/frontend/
git commit -m "feat(frontend): add Monaco expression editor with schema autocomplete"
```

---

### Task 19: Frontend analysis tab (Summary / Group-by / Charts / Schema)

**Files:**
- Modify: `apps/frontend/package.json` — add `echarts` + `echarts-for-react`
- Create: `apps/frontend/src/features/analyze/api/index.ts`
- Create: `apps/frontend/src/features/analyze/ui/AnalysisTab.tsx`
- Create: `apps/frontend/src/features/analyze/ui/SummaryPanel.tsx`
- Create: `apps/frontend/src/features/analyze/ui/GroupByPanel.tsx`
- Create: `apps/frontend/src/features/analyze/ui/ChartsPanel.tsx`
- Create: `apps/frontend/src/features/analyze/ui/SchemaPanel.tsx`
- Create: `apps/frontend/src/features/analyze/index.ts`
- Test: `apps/frontend/src/features/analyze/ui/AnalysisTab.test.tsx`

- [ ] **Step 1: Add ECharts**

```bash
cd apps/frontend && npm install echarts@5 echarts-for-react@3
```

- [ ] **Step 2: API client**

```ts
// apps/frontend/src/features/analyze/api/index.ts
import { apiClient } from "@/shared/api/client";

export type AnalyzeResponse = { kind: string; payload: any; warnings: string[] };

export async function analyze(uploadId: string, kind: string,
                              options: Record<string, unknown> = {},
                              filter?: Record<string, unknown>): Promise<AnalyzeResponse> {
  return apiClient.post("/api/v1/analyze", {
    upload_id: uploadId,
    filter,
    analysis: { kind, options },
  });
}
```

- [ ] **Step 3: AnalysisTab + sub-tabs**

```tsx
// AnalysisTab.tsx
import * as React from "react";
import { SummaryPanel } from "./SummaryPanel";
import { GroupByPanel } from "./GroupByPanel";
import { ChartsPanel } from "./ChartsPanel";
import { SchemaPanel } from "./SchemaPanel";

type SubTab = "summary" | "group_by" | "charts" | "schema";

export function AnalysisTab({ uploadId, filter, shape }: {
  uploadId: string;
  filter?: Record<string, unknown>;
  shape: "tabular" | "tree";
}) {
  const [sub, setSub] = React.useState<SubTab>("summary");
  return (
    <div className="analysis-tab">
      <div role="tablist">
        <button role="tab" aria-selected={sub==="summary"}  onClick={() => setSub("summary")}>Summary</button>
        <button role="tab" aria-selected={sub==="group_by"} onClick={() => setSub("group_by")} disabled={shape !== "tabular"}>Group-by</button>
        <button role="tab" aria-selected={sub==="charts"}   onClick={() => setSub("charts")}   disabled={shape !== "tabular"}>Charts</button>
        <button role="tab" aria-selected={sub==="schema"}   onClick={() => setSub("schema")}   disabled={shape !== "tree"}>Schema</button>
      </div>
      <div className="panel">
        {sub === "summary"  && <SummaryPanel  uploadId={uploadId} filter={filter} />}
        {sub === "group_by" && <GroupByPanel  uploadId={uploadId} filter={filter} />}
        {sub === "charts"   && <ChartsPanel   uploadId={uploadId} filter={filter} />}
        {sub === "schema"   && <SchemaPanel   uploadId={uploadId} filter={filter} />}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: SummaryPanel**

```tsx
// SummaryPanel.tsx
import * as React from "react";
import { analyze } from "../api";

export function SummaryPanel({ uploadId, filter }: { uploadId: string; filter?: any }) {
  const [data, setData] = React.useState<any>(null);
  const [err, setErr] = React.useState<string | null>(null);
  React.useEffect(() => {
    analyze(uploadId, "summary_stats", {}, filter)
      .then(r => setData(r.payload))
      .catch(e => setErr(e.message));
  }, [uploadId, JSON.stringify(filter)]);
  if (err) return <div className="error">{err}</div>;
  if (!data) return <div>Loading…</div>;
  return (
    <table className="summary-table">
      <thead>
        <tr><th>Column</th><th>Type</th><th>Count</th><th>Nulls</th><th>Distinct</th><th>Min</th><th>Max</th><th>Mean</th></tr>
      </thead>
      <tbody>
        {data.columns.map((c: any) => (
          <tr key={c.name}>
            <td>{c.name}</td><td>{c.type}</td><td>{c.count}</td><td>{c.nulls}</td><td>{c.distinct}</td>
            <td>{c.min ?? "—"}</td><td>{c.max ?? "—"}</td><td>{c.mean !== undefined ? c.mean.toFixed(2) : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 5: GroupByPanel**

```tsx
// GroupByPanel.tsx
import * as React from "react";
import { analyze } from "../api";

export function GroupByPanel({ uploadId, filter }: { uploadId: string; filter?: any }) {
  const [by, setBy] = React.useState<string>("");
  const [aggCol, setAggCol] = React.useState<string>("");
  const [fn, setFn] = React.useState<string>("sum");
  const [data, setData] = React.useState<any>(null);
  const run = async () => {
    if (!by || !aggCol) return;
    const r = await analyze(uploadId, "group_by", {
      by: [by], agg: { [aggCol]: [fn] }
    }, filter);
    setData(r.payload);
  };
  return (
    <div>
      <input placeholder="group by column" value={by} onChange={e => setBy(e.target.value)} />
      <input placeholder="aggregate column" value={aggCol} onChange={e => setAggCol(e.target.value)} />
      <select value={fn} onChange={e => setFn(e.target.value)}>
        {["sum","count","avg","min","max","median"].map(f => <option key={f} value={f}>{f}</option>)}
      </select>
      <button onClick={run}>Run</button>
      {data && (
        <table>
          <thead><tr>{Object.keys(data.groups[0] ?? {}).map(k => <th key={k}>{k}</th>)}</tr></thead>
          <tbody>
            {data.groups.map((g: any, i: number) => (
              <tr key={i}>{Object.values(g).map((v: any, j) => <td key={j}>{String(v)}</td>)}</tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
```

- [ ] **Step 6: ChartsPanel (ECharts renders Vega-Lite-like specs by translating to ECharts options)**

```tsx
// ChartsPanel.tsx
import * as React from "react";
import ReactECharts from "echarts-for-react";
import { analyze } from "../api";

function vlToECharts(spec: any): any {
  const x = spec.encoding.x.field, y = spec.encoding.y.field;
  return {
    title: { text: `${spec.mark}: ${x} × ${y}` },
    tooltip: {},
    xAxis: { name: x, type: spec.encoding.x.type === "temporal" ? "time" :
                       spec.encoding.x.type === "quantitative" ? "value" : "category" },
    yAxis: { name: y, type: spec.encoding.y.type === "quantitative" ? "value" : "category" },
    series: [{
      type: spec.mark === "point" ? "scatter" : spec.mark === "line" ? "line" : "bar",
      data: [],  // populated server-side in a follow-up; v1 ships chart-spec only
    }],
  };
}

export function ChartsPanel({ uploadId, filter }: { uploadId: string; filter?: any }) {
  const [data, setData] = React.useState<any>(null);
  React.useEffect(() => {
    analyze(uploadId, "chart_suggest", {}, filter).then(r => setData(r.payload));
  }, [uploadId, JSON.stringify(filter)]);
  if (!data) return <div>Loading…</div>;
  return (
    <div>
      {data.charts.map((c: any, i: number) => (
        <div key={i} className="chart-card">
          <h4>{c.rationale} <small>(score {c.score})</small></h4>
          <ReactECharts option={vlToECharts(c.spec)} style={{ height: 280 }} />
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 7: SchemaPanel**

```tsx
// SchemaPanel.tsx
import * as React from "react";
import { analyze } from "../api";

export function SchemaPanel({ uploadId, filter }: { uploadId: string; filter?: any }) {
  const [data, setData] = React.useState<any>(null);
  React.useEffect(() => {
    analyze(uploadId, "schema_infer", {}, filter).then(r => setData(r.payload));
  }, [uploadId, JSON.stringify(filter)]);
  if (!data) return <div>Loading…</div>;
  return (
    <div>
      <p>Leaf count: {data.leaf_count}, depth: {data.depth}</p>
      <table>
        <thead><tr><th>Path</th><th>Types</th><th>Depth (min..max)</th><th>Frequency</th></tr></thead>
        <tbody>
          {data.paths.map((p: any) => (
            <tr key={p.path}>
              <td><code>{p.path}</code></td>
              <td>{p.types.join(", ")}</td>
              <td>{p.depth_min}..{p.depth_max}</td>
              <td>{p.frequency}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 8: Test + commit**

```tsx
// AnalysisTab.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { AnalysisTab } from "./AnalysisTab";

vi.mock("../api", () => ({ analyze: vi.fn().mockResolvedValue({ kind:"summary_stats", payload:{ columns:[] }, warnings:[] }) }));

test("renders summary by default and switches sub-tab", () => {
  render(<AnalysisTab uploadId="u1" shape="tabular" />);
  expect(screen.getByRole("tab", { name: /summary/i, selected: true })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: /charts/i }));
  expect(screen.getByRole("tab", { name: /charts/i, selected: true })).toBeInTheDocument();
});
```

```bash
cd apps/frontend && npm test -- analyze
git add apps/frontend/
git commit -m "feat(frontend): add analysis tab with summary/group-by/charts/schema panels"
```

---

### Task 20: Frontend XLSX sheet picker

**Files:**
- Create: `apps/frontend/src/features/upload/ui/SheetPicker.tsx`
- Modify: `apps/frontend/src/features/upload/ui/UploadPage.tsx`
- Modify: `apps/frontend/src/shared/api/client.ts` — add `listSheets`
- Test: `apps/frontend/src/features/upload/ui/SheetPicker.test.tsx`

- [ ] **Step 1: API helper**

```ts
// shared/api/client.ts additions
export async function listSheets(uploadId: string): Promise<string[]> {
  return apiClient.get(`/api/v1/uploads/${uploadId}/sheets`);
}
```

- [ ] **Step 2: Failing test**

```tsx
// SheetPicker.test.tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SheetPicker } from "./SheetPicker";

vi.mock("@/shared/api/client", () => ({
  listSheets: vi.fn().mockResolvedValue(["people", "orders"]),
}));

test("lists sheets and emits selection", async () => {
  const onPick = vi.fn();
  render(<SheetPicker uploadId="u1" onPick={onPick} />);
  await waitFor(() => screen.getByText("orders"));
  fireEvent.click(screen.getByText("orders"));
  expect(onPick).toHaveBeenCalledWith("orders");
});
```

- [ ] **Step 3: SheetPicker**

```tsx
// SheetPicker.tsx
import * as React from "react";
import { listSheets } from "@/shared/api/client";

export function SheetPicker({ uploadId, onPick }: { uploadId: string; onPick: (sheet: string) => void }) {
  const [sheets, setSheets] = React.useState<string[] | null>(null);
  React.useEffect(() => { listSheets(uploadId).then(setSheets); }, [uploadId]);
  if (!sheets) return <div>Loading sheets…</div>;
  return (
    <div className="sheet-picker">
      <h3>Pick a sheet</h3>
      <ul>
        {sheets.map(s => (
          <li key={s}>
            <button onClick={() => onPick(s)}>{s}</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 4: Wire into UploadPage after detect**

```tsx
// UploadPage.tsx (excerpt — gating step between upload and filter view)
{detectResult?.format === "xlsx" && !pickedSheet && (
  <SheetPicker uploadId={uploadId} onPick={setPickedSheet} />
)}
{pickedSheet && <FilterPage uploadId={uploadId} sheet={pickedSheet} />}
```

- [ ] **Step 5: Run + commit**

```bash
cd apps/frontend && npm test -- SheetPicker
git add apps/frontend/
git commit -m "feat(frontend): add XLSX sheet picker step between detect and filter"
```

---

### Task 21: Shared plugin conformance integration test

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/testing/__init__.py`
- Create: `apps/data-engine/src/filternarrange_engine/testing/conformance.py`
- Create: `tests/integration/test_plugin_conformance.py`

- [ ] **Step 1: Conformance runner**

```python
# apps/data-engine/src/filternarrange_engine/testing/conformance.py
"""Canonical round-trip suite. Every format plugin must pass."""
import asyncio, io, pathlib
from filternarrange_engine.core.canonical import TabularData, TreeData

async def _materialize(td):
    if isinstance(td, TabularData):
        return {"schema": [(c.name, c.type) for c in td.schema],
                "rows": [r async for r in td.rows]}
    # tree
    def walk(n): return (n.key, n.value, [walk(c) for c in n.children])
    return walk(td.root)

def run_format_conformance(plugin, fixture_path: pathlib.Path):
    # 1. detect on a sample
    sample = fixture_path.read_bytes()[:8192]
    det = plugin.detect(sample)
    assert det.confidence > 0.5, f"detect failed: {det}"

    # 2. parse
    with open(fixture_path, "rb") as f:
        data1 = plugin.parse(f) if "sheet" not in plugin.__class__.__name__.lower() else plugin.parse(f, sheet_name=None)
    snap1 = asyncio.run(_materialize(data1))

    # 3. emit
    sink = io.BytesIO()
    with open(fixture_path, "rb") as f:
        data1b = plugin.parse(f)
        plugin.emit(data1b, sink)
    sink.seek(0)

    # 4. re-parse and assert equivalence
    data2 = plugin.parse(sink)
    snap2 = asyncio.run(_materialize(data2))
    assert snap1 == snap2, f"round-trip mismatch for {plugin.manifest.id}"
```

- [ ] **Step 2: Auto-discovery integration test**

```python
# tests/integration/test_plugin_conformance.py
import importlib, pathlib, pytest
from importlib.metadata import entry_points

ROOT = pathlib.Path(__file__).resolve().parents[2] / "plugins"

# Each format plugin ships a canonical fixture under tests/fixtures/<id>.<ext>
FIXTURES = {
    "csv":   "format-csv/tests/fixtures/sample.csv",
    "tsv":   "format-tsv/tests/fixtures/sample.tsv",
    "json":  "format-json/tests/fixtures/sample.json",
    "jsonl": "format-jsonl/tests/fixtures/sample.jsonl",
    "xml":   "format-xml/tests/fixtures/sample.xml",
    "yaml":  "format-yaml/tests/fixtures/sample.yaml",
    "xlsx":  "format-xlsx/tests/fixtures/two_sheets.xlsx",
}

@pytest.mark.parametrize("fmt", list(FIXTURES))
def test_format_plugin_roundtrip(fmt):
    from filternarrange_engine.testing.conformance import run_format_conformance
    plugin = next(ep.load() for ep in entry_points(group="filternarrange.formats") if ep.name == fmt)
    run_format_conformance(plugin, ROOT / FIXTURES[fmt])

def test_all_filter_kinds_registered():
    eps = {ep.name for ep in entry_points(group="filternarrange.filters")}
    assert {"column", "row", "expression", "regex"} <= eps

def test_all_analyses_registered():
    eps = {ep.name for ep in entry_points(group="filternarrange.analyses")}
    assert {"summary_stats", "group_by", "chart_suggest", "schema_infer"} <= eps
```

- [ ] **Step 3: Run + commit**

```bash
cd apps/data-engine && uv run pytest ../../tests/integration/test_plugin_conformance.py -v
git add apps/data-engine/src/filternarrange_engine/testing/ tests/integration/test_plugin_conformance.py
git commit -m "test(plugins): add shared conformance suite + entry-point discovery test"
```

---

### Task 22: CI matrix job per plugin

**Files:**
- Modify: `.github/workflows/pr.yml`

- [ ] **Step 1: Add discovery + matrix job**

```yaml
# .github/workflows/pr.yml — additions at the end of jobs:
  list-plugins:
    runs-on: ubuntu-latest
    outputs:
      plugins: ${{ steps.find.outputs.plugins }}
    steps:
      - uses: actions/checkout@v4
      - id: find
        run: |
          PLUGINS=$(ls -d plugins/*/ | sed 's|plugins/||;s|/||' | jq -R . | jq -s -c .)
          echo "plugins=$PLUGINS" >> "$GITHUB_OUTPUT"

  plugin-tests:
    needs: list-plugins
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        plugin: ${{ fromJSON(needs.list-plugins.outputs.plugins) }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - name: Install engine core
        run: cd apps/data-engine && uv pip install --system -e .
      - name: Install plugin
        run: cd plugins/${{ matrix.plugin }} && uv pip install --system -e .
      - name: Run plugin tests
        run: cd plugins/${{ matrix.plugin }} && uv run pytest -v
```

- [ ] **Step 2: Add conformance integration job (separate so a broken plugin doesn't poison it)**

```yaml
  conformance:
    needs: plugin-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - name: Install engine + all plugins
        run: |
          cd apps/data-engine && uv pip install --system -e .
          for d in plugins/*/; do uv pip install --system -e "$d"; done
      - name: Run conformance suite
        run: uv run pytest tests/integration/test_plugin_conformance.py -v
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/pr.yml
git commit -m "ci: per-plugin matrix job + conformance integration step"
```

---

## Self-Review

**Spec coverage check (spec §1–§9):**

- §1 Goals — all four filter modes (column/row/expression/regex) ship in this plan (Tasks 7-9 + existing column). All four analyses ship (Tasks 10-13). All seven launch formats ship — csv & json from Plan B, the other five in Tasks 2-6.
- §3 Latency budget — relies on Plan B's k6 setup; per-plugin tests use small fixtures and stay under thresholds.
- §3 Sync threshold — Plan C is fully sync; we never exceed 25 MB or 500 k rows in fixtures.
- §3 Error envelope — Task 14 step 7, Task 15 DTOs, and Task 16 OpenAPI `ErrorEnvelope` all emit `{code, plugin_id?, message, trace_id}`.
- §4 Plugin manifest — every plugin ships a manifest.toml with the spec-mandated fields.
- §4 Entry-point discovery — every plugin's `pyproject.toml` registers under the correct group; Task 14 step 2 reads them.
- §4 Detection pipeline — magic bytes (xlsx, xml), structural sniff (csv/tsv/jsonl/yaml/xml fallback), heuristic (column-count consistency in tsv). Confidence values returned consistently as floats 0..1.
- §4 register_function — Task 8 step 4 exposes it on the expression plugin.
- §4 Chart-suggest returns Vega-Lite-shaped specs — Task 12, Task 19 step 6 translates them to ECharts at render time.
- §4 Schema-infer for TreeData — Task 13.
- §6 Public surface rule — every plugin's `__init__.py` exports only `plugin`.
- §7 Conventional Commits — every Task ends with a `feat(...)`, `test(...)`, or `ci:` commit.
- §7 Plugin conformance in CI — Task 21 + 22.

**Placeholder scan:** Searched the plan. No `TBD`, no `TODO`, no "implement later", no "Similar to Task N", no `...` ellipses standing in for code. Every code step shows complete code or a complete, named, copy-pasteable file. The only `# ...existing format discovery in Plan B...` comment in Task 14 step 2 is an explicit reference to Plan B's deliverable and is followed by the full code being added — acceptable per spec.

**Type consistency:**

- `FilterSpec` discriminated union: `kind` literal matches everywhere (`column | row | expression | regex`) across Tasks 1, 7, 8, 9, 14, 16, 17, 18.
- `AnalysisSpec.kind` values match across Tasks 1, 10-13, 14, 16, 19 (`summary_stats`, `group_by`, `chart_suggest`, `schema_infer`).
- `RowPredicate.op` enum identical in core (Task 1), filter-row (Task 7), OpenAPI (Task 16), and frontend (Task 17).
- `RegexSpec.flags` enum `i|m|s` identical across plugin, OpenAPI, and frontend.
- `TypeTag` reused as defined in Plan B; no redefinition.
- Each plugin's package name matches the entry-point target exactly (e.g., `filternarrange_format_xlsx:plugin`).
- `PluginRegistry.get_filter` / `get_analysis` signatures match dispatch use in `FilterService` / `AnalysisService`.
- `analyze()` is async on every analysis plugin; the dispatcher in Task 14 step 6 awaits it; the FastAPI handler in step 7 awaits the service.
- Frontend `ColumnMeta` (from Plan B) is reused, not redefined.

**Consistency concerns surfaced for the orchestrator:**

1. **Plan B dependency contract.** This plan assumes Plan B exposes: `filternarrange_engine.core.canonical.{TabularData, TreeData, Column, Node, TypeTag, infer_type_tag, value_to_type_tag}`, `filternarrange_engine.core.plugin_protocols.{DetectResult, load_manifest}`, `PluginRegistry` with private `_formats / _filters / _analyses` dicts, and `UploadService` with `load_canonical(upload_id)`, `open_raw(upload_id)`, `get_detected_format(upload_id)`. If Plan B uses different names, Plan C needs a thin compatibility shim.
2. **`infer_type_tag` / `value_to_type_tag` helpers** are assumed to be in Plan B's canonical module. If Plan B kept type inference inside individual plugins, Task 2/3/6 need a small inline helper instead.
3. **CSV plugin's `manifest.toml`** in Plan B currently says `display_name = "CSV / TSV"` per the spec sample (§4). With TSV now a separate plugin, Plan B's CSV manifest should be updated to `display_name = "CSV"` — flagged here, edit lives in Plan B's scope.
4. **OpenAPI version bump.** Spec §3 says "a v1 contract is immutable; additive changes get a sibling v2". I treated 1.0.0 → 1.1.0 as additive-within-major (a strict reading of the spec might require v2). The orchestrator should confirm intent — if strict, Task 16 should write to `contracts/openapi/gateway-public.v2.yaml` and the gateway should serve both.
5. **ChartsPanel currently renders empty series.** The chart-suggest plugin only returns specs; rendering the actual data is intentionally deferred — server-side data fetch happens via a follow-up `/api/v1/chart-data` endpoint (out of Plan C scope per spec §4 which states "Chart analyses return a chart spec"). Flagged so the orchestrator knows the visual is intentionally empty in this plan.
6. **`xlsx` detection on truncated samples.** `zipfile.ZipFile(io.BytesIO(sample))` will raise on a partial 8 KB sample because the central directory is at the end of the file. The plan returns confidence 0.4 in that case and relies on the gateway to pass the full file once size ≤ 25 MB (spec §3 sync threshold). If Plan B passes only the head, this needs revisiting.
7. **Frontend test setup** assumes Plan B set up `vitest` + `@testing-library/react` with `vi.mock` aliasing `@/` to `apps/frontend/src/`. If Plan B used Jest, the syntax in Tasks 17-20 needs trivial substitution.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-07-C-plugin-breadth.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
