# contracts/

The single source of truth for every cross-service interface. Per spec §3:

- `openapi/` — Gateway REST surfaces (consumed by React; consumed by data-engine when gateway calls it)
- `kafka/` — JSON-Schema definitions of every Kafka payload

## Versioning rules (locked)

1. **Contracts are versioned independently of code.** Filename includes the major version: `gateway-public.v1.yaml`, `topic.v1.jobs.schema.json`.
2. **A v1 contract is immutable** once shipped on `main`. No edits — additions go in a sibling v2.
3. **Additive changes get a new major version**, not a mutation of the existing one. CI fails if a v1 file changes in any way other than whitespace/comments. Practical rule: if the change is purely additive *and* introduced as v2, both files can co-exist while consumers migrate.
4. **Both sides validate against the same schema.** Spring Boot generates DTOs from `openapi/*.yaml` at build; Python generates pydantic models from the same files; Kafka producers + consumers validate every payload against the relevant JSON schema.
5. **No service imports another service's source code.** Only the schemas in this directory.
6. **CI fails if a contract changes without bumping a version.** Enforced by the contract-validation stage in `pr.yml`.

## Adding a new contract

1. Pick the next major version (always `vN` where `N` ≥ 1 in filenames).
2. Write the OpenAPI / JSON-Schema file with `info.version` matching the filename.
3. Run `npx @stoplight/spectral-cli lint contracts/openapi/<file>.yaml` locally before pushing.
4. Open a PR. The contract-validation CI stage lints + diffs against the previous version on `main`.

## Current contracts

| File | Owner | Consumers | Status |
|---|---|---|---|
| `openapi/gateway-public.v1.yaml` | gateway | frontend | placeholder (Plan A) — only `/health` |
| `openapi/gateway-internal.v1.yaml` | gateway | data-engine | placeholder (Plan A) — only `/health` |
| `kafka/topic.v1.jobs.schema.json` | gateway → data-engine | placeholder | Plan A skeleton; Plan D fleshes out |
| `kafka/topic.v1.job-results.schema.json` | data-engine → gateway | placeholder | Plan A skeleton; Plan D fleshes out |
| `kafka/topic.v1.format-requests.schema.json` | gateway → admin notifier | placeholder | Plan A skeleton |
| `kafka/topic.v1.audit-events.schema.json` | any → audit-writer | placeholder | Plan A skeleton |
