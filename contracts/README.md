# contracts/

Versioned cross-service API contracts. **Source of truth** for both sides of every cross-service call (per spec §3).

- `openapi/` — REST contracts (gateway public + gateway↔data-engine internal).
- `kafka/` — JSON Schemas for Kafka topic payloads.

In Plan A this directory is scaffolded with placeholders. Plan A Task 11 (Contracts scaffold) lands the v1 schemas; subsequent plans extend them additively per the versioning rules below.

## Versioning rules (locked by spec §3)

1. A v1 contract is immutable once published. Additive changes ship as a sibling v2.
2. Both sides validate against the same schema file. Gateway generates DTOs from OpenAPI at build; data-engine uses `pydantic` models generated from the same files.
3. No service imports another service's source code — only schemas.
4. CI fails if a contract changes without bumping its version.

Detailed schemas appear here as Plan A Task 11 lands.
