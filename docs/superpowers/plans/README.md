# FilterNArrange — Implementation Plans

This directory contains the implementation plans that take FilterNArrange from an empty repository to a publicly-deployed v1.0.0. Each plan delivers **working, testable software** on its own — execute end-to-end before starting the next.

All plans were written on 2026-06-07 alongside the [design spec](../specs/2026-06-07-filternarrange-design.md) and follow the [writing-plans skill format](https://github.com/anthropics/claude-skills): bite-sized TDD steps (each 2–5 minutes), complete code in every step, exact commands with expected output, Conventional Commit messages.

## Plans in dependency order

| # | Plan | Ships | Tag | Status |
|---|------|-------|-----|--------|
| **A** | [Foundation](2026-06-07-A-foundation.md) — monorepo, Docker Compose, CI pipeline, ADRs 0002–0004, license (Apache-2.0) | Bootable empty stack with green `/health` endpoints; full CI baseline | `v0.1.0` | Drafted — not executed |
| **B** | [Walking skeleton](2026-06-07-B-walking-skeleton.md) — gateway with JWT auth + upload/detect/filter/convert/download; data-engine with canonical model + CSV + JSON; column-projection filter; frontend with login/upload/filter/download | First end-to-end user flow works | `v0.2.0` | Drafted — not executed |
| **C** | [Plugin breadth](2026-06-07-C-plugin-breadth.md) — XML/YAML/JSONL/TSV/XLSX format plugins; row/expression/regex filter modes; all 4 analyses (stats, group-by, charts, schema-infer) | Full sync feature set across the 7 launch formats | `v0.3.0` | Drafted — not executed |
| **D** | [Async path](2026-06-07-D-async-path.md) — Redpanda topics, worker mode, WebSocket push, idempotency keys, circuit breaker, bulkheading | Batch / long-running jobs no longer block the request thread | `v0.4.0` | Drafted — not executed |
| **E** | [AI integration](2026-06-07-E-ai-integration.md) — Ollama provider, 4 AI capabilities as plugins (NL→filter, summary, chart-suggest, anomaly-detect) | NL filter prompts work; AI insights render in UI | `v0.5.0` | Drafted — not executed |
| **F** | [Tiers & format requests](2026-06-07-F-tiers-and-format-requests.md) — subscriptions table, tier middleware, Redis quotas, retention worker, recipes (paid), format-request workflow (paid-prioritized + community-PR), ADR-0005 | Free vs paid behaves correctly; format-not-detected UX correct per tier | `v0.6.0` | Drafted — not executed |
| **G** | [Production hardening](2026-06-07-G-production-hardening.md) — Keycloak integration, full observability (Prometheus/Grafana/Loki/Tempo), backup/DR, k6 perf gates, supply-chain security (Trivy, Syft, Cosign, OWASP ZAP) | Production-credible deployment | `v0.7.0` | Drafted — not executed |
| **H** | [Public deploy](2026-06-07-H-public-deploy.md) — multi-arch images, prod compose profile, Caddy + Let's Encrypt, Oracle Always-Free runbook, deploy.yml with rollback, smoke suite, ADR-0006, **flip repo public**, tag v1.0.0 | First public URL with the v1 feature set | `v1.0.0` | Drafted — not executed |

**Dependencies:** A → B → (C ∥ D ∥ E) → F → G → H. After Plan B ships, C, D, E can be developed in any order or in parallel.

## ADR numbering across plans

| ADR | Topic | Plan |
|---|---|---|
| ADR-0001 | Initial stack & principles | (already accepted before any plan) |
| ADR-0002 | License (Apache-2.0) | A |
| ADR-0003 | Module dependency & failure isolation | A |
| ADR-0004 | Ticketing & versioning workflow | A |
| ADR-0005 | Tier system & format-request workflow | F |
| ADR-0006 | Public release at v1.0.0 | H |

## Cross-plan reconciliation notes

These items surfaced during plan review and need to be honored at execution time. They are not blockers; they are dependencies between plans that the executor must respect.

### Type & symbol names locked across plans
- Java: `io.filternarrange.gateway.platform.security.AuthenticatedUser`, `io.filternarrange.gateway.platform.audit.AuditEmitter`, `io.filternarrange.gateway.platform.error.ErrorEnvelope` (JSON field name `pluginId`).
- Python: `filternarrange_engine.core.PluginResult`, `filternarrange_engine.core.{TabularData,TreeData,Column,TypeTag,Node}`, `filternarrange_engine.application.pipeline.run`.
- All filter modes share a discriminated union `FilterSpec` with `kind: column | row | expression | regex` (Plan B ships `column`; Plan C extends).

### `/health` vs `/ready`
Spec §3 mentions only `/health` but the run guide §7 lists both. Plan A ships `/health` only. Plan B should add `/ready` (Spring Boot Actuator `/actuator/health/readiness` + FastAPI `/ready`) — readiness gates on Postgres + Redis + MinIO reachability.

### Detection-strategy terminology
Spec §4 uses both "content-sniff" and "structural sniff" for the same concept. Plans treat them as synonyms; recommend the spec be tightened in a future revision to use "content-sniff" everywhere.

### Redis daily counter key
`gw:rate:user:{user_id}:ops:{date}` — `{date}` is `YYYY-MM-DD` in **UTC**. Plan F establishes this; earlier plans should follow.

### OpenAPI version bumping (additive within v1)
Spec §3 says "a v1 contract is immutable". Plan C bumps `gateway-public.v1.yaml` `info.version` `1.0.0 → 1.1.0` as additive. The spec rule applies to **paths** being immutable once v1 is published; additive `info.version` patches signaling backward-compatible additions are fine. Breaking changes get a sibling `gateway-public.v2.yaml`.

### CSV vs TSV plugin split
Plan B ships `format-csv` with manifest `display_name = "CSV / TSV"`. Plan C splits TSV into its own `plugins/format-tsv/`. When Plan C lands, Plan B's CSV manifest must be edited to `display_name = "CSV"` and its sniffer must reject tab-delimited files (let `format-tsv` win for `.tsv`).

### Test-harness endpoint
Plan F integration tests reference `POST /api/v1/test/_promote_paid` to promote a test user to paid tier. Plan B should ship this endpoint guarded by `AUTH_DEV_MODE=true` (off in production). Plan G's perf workflow expects the same flag for `/api/v1/auth/dev-token`.

### AI capability tier assignments
Plan E ships all four AI capabilities with `required_tier = "free"` in their manifests as a sensible default. Plan F's `V8__plugin_registry.sql` flips capabilities to `paid` per the open-core model (all four AI capabilities → paid, per spec §1). Plan E does not need to be edited — Plan F's seed data is the source of truth at runtime.

### Auth provider default for production
Plan H defaults `AUTH_PROVIDER=spring-jwt` on the Oracle Always-Free deploy to save ~1 GB RAM (Keycloak's footprint vs. the host's 24 GB total ceiling). The spec already calls spring-jwt a supported "RAM-saving fallback"; ADR-0006 records this trade-off. Re-enabling Keycloak post-launch is a one-env-var change.

### Plan length vs writing-plans skill rules
All 8 plans exceed the per-plan length guidance given to the writers. This was a deliberate choice: the writing-plans skill explicitly forbids placeholders ("TBD", "fill in details", "implement appropriate error handling", "similar to Task N without showing code"). Polyglot full-stack plans with TDD-step granularity and complete code in every step run long. Total plan content: ~32 300 lines across 194 tasks.

## Execution recommendation

Execute one plan at a time:

1. **Open a GitHub issue** for each task in the plan (helps the writing-plans `Closes #N` references resolve to real issues).
2. **Branch from `main`**: `git checkout -b feat/plan-a-task-N`.
3. **Follow each step verbatim** — failing test → run + observe failure → minimal implementation → run + observe pass → commit with Conventional Commit message.
4. **Open a PR per task** (or per logical task cluster). PR template enforces impact assessment, regression risk, test coverage.
5. **Merge with squash-merge**; tag the milestone release with release-please after the plan's final PR lands.

For agentic execution: use **superpowers:subagent-driven-development** (one task → one fresh subagent → reviewed → merged → next subagent). Plans were written assuming this pattern.

## What's deferred beyond v1 (post-Plan-H)

Captured in spec §9 "Future work": Stripe billing wiring, additional formats (Parquet/Avro/Markdown-tables/fixed-width), API access tier for paid users, optional SaaS-managed dependencies (Neon/Upstash/etc.), additional AI capabilities, GPU-backed inference path, enterprise SSO support via Keycloak.
