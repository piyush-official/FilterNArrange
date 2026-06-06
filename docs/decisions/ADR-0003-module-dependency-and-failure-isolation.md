# ADR-0003: Module dependency direction & failure isolation

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** piyush-official
- **Codifies:** spec §6 (Module Organization, Dependency Order & Failure Isolation)

## Context

Spec §6 lays out hexagonal per-app structure, dependency direction rules, a "public surface = single file" rule, and eight failure-isolation patterns. These are enforced by automated tooling, not just code review — so they need to be locked in as a decision, not a guideline.

## Decision

### Dependency direction (CI-enforced)

```
api  →  application  →  domain
                          ▲
                          │ implements
                  infrastructure
```

1. Domain depends on nothing — pure types + ports.
2. Application depends only on domain.
3. Infrastructure depends on domain (to implement ports), never the other way.
4. API depends on application + domain, never directly on infrastructure.
5. Features (frontend) never import other features — cross-feature traffic goes through `shared/`.
6. Plugins depend only on the published plugin API, never on app internals.

### Enforcement

| Layer | Linter |
|---|---|
| Java | ArchUnit tests in CI |
| Python | `import-linter` (declarative rules in `.importlinter`) |
| TypeScript | `eslint-plugin-boundaries` + `eslint-plugin-import` |

Violation = merge blocked.

### Public surface rule

A module's public surface = exactly one file:

- Python: `__init__.py` with `__all__`
- TypeScript: `index.ts` (barrel)
- Java: top-level package types; everything under `internal/` is package-private

If a name isn't in the surface, importing it from outside the module is a lint error.

### Code-level failure isolation patterns

1. Error envelopes at every cross-module boundary (`Result<T,E>` in Java/TS, `PluginResult` in Python).
2. Single structured wire-error model: `{ code, plugin_id?, message, trace_id }`. `plugin_id` is optional because not every error originates in a plugin.
3. Bulkheading via separate pools per concern (`web-io`, `db-io`, `kafka-producer` in Java; `data-cpu`, `ai-async`, `plugin-async` in Python).
4. Timeouts at every boundary (gateway→python 5s sync / 30s AI; postgres 3s; redis 250ms; kafka produce 10s; minio 60s; python→ollama 30s).
5. Circuit breakers between services (Resilience4j; open after 5 consecutive failures in 10s; half-open after 30s).
6. Idempotency keys for all async writes — `Idempotency-Key` header → Redis 24h.
7. No shared mutable state across modules — configuration injected, never globals.
8. Plugin failure quarantine (3 failures in 5 min → 10-min cooldown).

## Consequences

- Plan A wires the enforcement tooling (Spectral for contracts, commitlint for messages); ArchUnit / import-linter / eslint-plugin-boundaries land as the apps grow real code (Plan B+).
- Refactors that cross module boundaries become loud — by design.
- New contributors pay a one-time onboarding cost for the layering rules, balanced against fewer "where does this go?" debates later.

## Follow-ups

- Add ArchUnit dependency + first rule set when Plan B's gateway code lands.
- Add `.importlinter` + first rule set when Plan B's Python code lands.
- Add `eslint-plugin-boundaries` config when Plan B's frontend code lands.
