# Changelog

All notable changes to FilterNArrange are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

## [Unreleased]

### Added
- Initial project scaffold (README, CHANGELOG, .gitignore, docs directory).
- Cost-tracking document covering every chosen tool, tier (Free / Cost-effective / Paid / Deferred), and horizontal+vertical scaling paths.
- ADR-0001 capturing the initial stack and architecture decisions made during brainstorming.
- Consolidated design specification (`docs/superpowers/specs/2026-06-07-filternarrange-design.md`) covering §1 purpose & scope, §2 architecture & loose-coupling, §3 data flow & contracts, §4 plugin & extensibility model, §5 storage & data model, §6 module organization & failure isolation, §7 engineering workflow (ticketing, versioning, CI/CD, testing), §8 run-guide pointer, §9 roadmap, §10 open questions, §11 references.
- Run guide (`docs/run-guide.md`) with hardware tiers, host-software prerequisites, ports map, first-run sequence, daily dev loop, configuration matrix, health checks, troubleshooting playbook, cleanup, and free-tier deploy preview.
- Cost-tracking §20 — full catalog of OSS development & testing tooling (commitlint, git-cliff, release-please, ArchUnit, import-linter, schemathesis, testcontainers, Playwright, k6, Codecov, PIT, mutmut, OWASP ZAP, Trivy, gitleaks, Syft, Cosign, Dependabot).
- Cost-tracking §12a — source code hosting (GitHub private repo, free).
- Eight implementation plans in `docs/superpowers/plans/` covering the path from empty repo to v1.0.0 public deploy:
  - Plan A — Foundation (monorepo, Docker Compose, CI, ADRs 0002–0004, Apache-2.0 license).
  - Plan B — Walking skeleton (gateway + data-engine + frontend with first end-to-end flow).
  - Plan C — Plugin breadth (5 format plugins, 3 filter modes, 4 analyses).
  - Plan D — Async path (Kafka topics, worker mode, WebSocket push, circuit breakers).
  - Plan E — AI integration (Ollama provider, 4 AI capabilities as plugins).
  - Plan F — Tiers & format-request workflow (quotas, retention, recipes, paid-prioritized format requests, ADR-0005).
  - Plan G — Production hardening (Keycloak, observability stack, backup/DR, k6 perf gates, supply-chain security).
  - Plan H — Public deploy on Oracle Always-Free (multi-arch images, Caddy + LE, deploy.yml with rollback, ADR-0006, repo flip to public, v1.0.0 tag).
- Plans index and cross-plan reconciliation notes at `docs/superpowers/plans/README.md`.
- **Plan A — Foundation** executed (branch `feat/plan-a-foundation`):
  - Monorepo skeleton: `apps/{gateway,data-engine,frontend}/`, `plugins/`, `contracts/{openapi,kafka}/`, `infra/{docker-compose,caddy,observability}/`, `scripts/`, `tests/integration/`, `.github/{workflows,ISSUE_TEMPLATE}/`. Each app has its own README documenting the hexagonal/feature-sliced layout. `.gitattributes` enforces LF line endings.
  - **LICENSE**: Apache-2.0 adopted (full canonical text). `NOTICE` placeholder removed.
  - **ADRs**: ADR-0002 (license — Apache-2.0), ADR-0003 (module dependency direction & 8 failure-isolation patterns), ADR-0004 (ticketing + versioning + CI workflow), `docs/decisions/README.md` index.
  - **Gateway hello-world**: Spring Boot 3.2.5 + OpenJDK 21 (Gradle toolchain auto-provisioned via Foojay) with `/health` endpoint, JUnit 5 test, multi-stage Dockerfile (Eclipse Temurin), Gradle wrapper committed.
  - **Data-engine hello-world**: FastAPI 0.111.0 on Python 3.12 (managed via `uv`) with `/health` endpoint, pytest contract test, multi-stage Dockerfile, `pyproject.toml` with ruff + mypy + pytest configs, `uv.lock`.
  - **Frontend hello-world**: Vite 5 + React 18 + TypeScript 5.4 + Vitest, "FilterNArrange — running" banner, Testing-Library test, nginx-served multi-stage Dockerfile.
  - **`.env.example`**: full configuration matrix from spec §8.6 (auth, Postgres, Redis, Redpanda, MinIO, Ollama, tiers, retention, observability, plugins, frontend).
  - **Caddy reverse-proxy**: `infra/caddy/Caddyfile` routes `:8443` to gateway (API/WS/health) + frontend (everything else) with auto self-signed local certs.
  - **Docker Compose stack**: `infra/docker-compose/docker-compose.yml` with 10 services (postgres:16, valkey:7, redpanda KRaft, minio, ollama + ollama-init one-shot, gateway, data-engine, frontend, caddy), healthchecks on every service, named volumes, single bridge network.
  - **Scripts**: `scripts/wait-for-healthy.sh` polls `/health` endpoints with timeout; `scripts/seed-dev` placeholder for Plan B's user-table seeding.
  - **Contracts scaffold**: `contracts/README.md` with versioning rules (immutable v1, additive v2); placeholder `gateway-public.v1.yaml` + `gateway-internal.v1.yaml` (OpenAPI 3.1 with `/health`); placeholder JSON Schemas for the four Kafka topics (jobs, job-results, format-requests, audit-events).
  - **GitHub repo plumbing**: `.github/CODEOWNERS`, `.github/pull_request_template.md` (PR template enforced by CI), 5 issue templates (`bug`, `feature`, `format-request`, `plugin`, `chore`), `.github/ISSUE_TEMPLATE/config.yml` disabling blank issues and linking security advisories.
  - **commitlint + husky**: root `package.json`, `commitlint.config.js` extending `@commitlint/config-conventional`, `.husky/commit-msg` hook validating Conventional Commit messages locally.
  - **release-please**: `release-please-config.json` (simple release type, changelog sections per Conventional Commit) and `.release-please-manifest.json` starting at `0.0.0`.
  - **CI workflows**: `.github/workflows/pr.yml` with all 9 stages from spec §7.5 (lint, unit-tests, architecture-tests, contract-validation with Spectral + ajv, plugin-conformance, integration-tests, e2e, performance-gates, pr-template-guard); `.github/workflows/release.yml` wiring `release-please-action`.
