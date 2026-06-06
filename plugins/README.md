# plugins/

Per-spec §4: every format adapter, filter operator, analysis module, AI provider, and storage backend lives here as an independent installable Python package discovered via entry-points.

In Plan A this directory is empty. Plan B lands the launch format set (`csv`, `tsv`, `json`, `jsonl`, `xml`, `yaml`, `xlsx`) and the canonical conformance suite.

## Per-plugin layout (locked by spec §4)

```
plugins/format-<name>/
├── pyproject.toml
├── README.md
├── manifest.toml
├── src/filternarrange_format_<name>/
│   ├── plugin.py
│   ├── detect.py
│   ├── parse.py
│   └── emit.py
└── tests/
```
