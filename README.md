# FilterNArrange

A dynamic web service for **filtering, format conversion, and analysis** of arbitrary user-provided data — with AI assistance — built entirely on open-source tooling.

> **Status:** brainstorming / design phase. No implementation yet.

## Goals

- Accept data via file upload or paste.
- Auto-detect format (CSV, JSON, JSONL, XML, YAML, XLSX at launch; pluggable for more).
- Filter with four modes — column projection, row conditions, expression / SQL-like, regex.
- Convert any supported input format to any supported output format (canonical intermediate model).
- Analyze — summary statistics, group-by, charts, schema inference.
- AI assistance — natural-language → filter, smart summary, chart suggestion, anomaly detection.
- Tiered model (free / paid) with self-hosting always free; paid hosted tier funds maintenance.

## Tech (open-source only)

Spring Boot · React + TypeScript · Python + FastAPI · PostgreSQL (with JSONB) · Redis · Redpanda · MinIO · Keycloak · Ollama · Docker Compose

See [docs/cost-tracking.md](docs/cost-tracking.md) for the full cost breakdown and upgrade paths for every component.

## Documents

- Design spec (in progress): `docs/superpowers/specs/`
- Cost tracking: [docs/cost-tracking.md](docs/cost-tracking.md)
- Architecture decisions: [docs/decisions/](docs/decisions/)
- Changelog: [CHANGELOG.md](CHANGELOG.md)

## License

A formal license has not yet been chosen. See [NOTICE](NOTICE) and [ADR-0001](docs/decisions/ADR-0001-initial-stack-and-principles.md). All rights reserved until a `LICENSE` file is committed (planned: AGPL-3.0 or Apache-2.0).
