# apps/data-engine

FastAPI service for format detection, parsing/emitting, filtering, analysis, and AI orchestration. Owns its Redis cache slice (per spec §5).

## Layout (hexagonal — see spec §6)

- `src/filternarrange_engine/api` — FastAPI routers
- `src/filternarrange_engine/application` — orchestrators per use case
- `src/filternarrange_engine/core` — canonical model (`TabularData`, `TreeData`) + ports
- `src/filternarrange_engine/adapters` — `plugin_registry/`, `storage/`, `kafka/`, `llm/`
- `src/filternarrange_engine/platform` — logging, errors, config

## Local run

```bash
uv run uvicorn filternarrange_engine.api.main:app --reload
```

## Tests

```bash
uv run pytest
```
