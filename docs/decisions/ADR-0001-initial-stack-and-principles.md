# ADR-0001: Initial stack and architectural principles

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** Project owner (piyush-official)
- **Context:** Brainstorming session establishing the foundation for FilterNArrange.

## Decision

FilterNArrange will be built as an **open-source web service** under one of {AGPL-3.0, Apache-2.0} (final license TBD) using a polyglot, plugin-driven, loosely-coupled architecture on entirely open-source tooling.

### Stack

| Layer | Choice |
|---|---|
| Frontend | React + TypeScript, Vite build, Nginx serve |
| API gateway | Spring Boot 3.x (Java/OpenJDK 21) — auth, tier/quota, routing, tickets, WebSocket push |
| Data + AI service | Python 3.12 + FastAPI — format detection/parse/emit, filtering, analysis, AI orchestration |
| LLM runtime | Ollama with open-weight models (Llama 3.1 8B, Qwen2.5 7B, Mistral 7B) |
| Relational DB | PostgreSQL 16 (with JSONB for nested data) |
| Cache / rate limits | Redis (OSS edition or Valkey fork) |
| Messaging | Redpanda OSS (Kafka-API-compatible, single binary, no ZooKeeper) |
| Object storage | MinIO (S3-compatible) |
| Identity | Keycloak (or Spring Security + self-managed JWT fallback) |
| Reverse proxy / TLS | Caddy (auto Let's Encrypt) |
| Observability | Prometheus + Grafana + Loki + Tempo (all self-hosted) |
| CI | GitHub Actions on public repo |
| Container registry | GHCR (ghcr.io) |
| Orchestration | Docker Compose for v1; k3s as upgrade path |

### Architectural principles

1. **Loose coupling.** All cross-service communication via versioned contracts in a top-level `contracts/` directory. No service imports another's source. No service writes to another's datastore.
2. **Plugin-first.** Formats, filters, analyses, AI providers, and storage backends are all plugins discovered via entry-points. Core never grows when one is added.
3. **Canonical intermediate model.** Every format parses into one of two canonical shapes (Tabular / Tree); every filter and analysis operates on canonical; every emitter writes from canonical. Eliminates O(N²) converters.
4. **Mode flag for the Python service.** Same image, runtime mode (`full | data | ai | worker`) chosen by env var, so splitting into separate services later is a Compose-file edit, not a rewrite.
5. **Cost-aware: free first.** Every dependency tracked in `docs/cost-tracking.md` with upgrade paths and scaling cost. No paid SaaS without explicit decision.
6. **OSS-friendly licensing.** MongoDB rejected (SSPL not OSI-approved). Redpanda chosen over Apache Kafka for free-tier RAM footprint, with swap-back path documented.
7. **Failure isolation.** Plugin errors caught at dispatch boundary; one plugin failure cannot affect others.

### Out of scope for v1

DB/URL ingestion, real-time collaboration, multi-tenant orgs, mobile apps, SSO with enterprise IdPs, Stripe (deferred until first paid customer), Kubernetes.

## Consequences

- Setup complexity sits in Docker Compose, not in code — clear separation of concerns.
- Polyglot raises onboarding bar (contributors need Java + Python + React familiarity at minimum) — mitigated by per-component CONTRIBUTING guides.
- Plugin discovery via `entry_points` requires plugins to be installed Python packages — adds packaging overhead per plugin, paid back by zero-config registration.
- Postgres JSONB instead of MongoDB simplifies ops at the cost of slightly less native nested-query ergonomics — acceptable.

## Follow-ups

- Choose license (ADR-0002).
- Define module-dependency ordering and failure-isolation rules (ADR-0003 — to follow §5/§6 of design).
- Define ticketing & versioning workflow (ADR-0004 — to follow §7).
- Establish required system configuration for local dev (`docs/run-guide.md`).
