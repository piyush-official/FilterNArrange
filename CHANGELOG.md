# Changelog

All notable changes to FilterNArrange are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

## [1.1.1](https://github.com/piyush-official/FilterNArrange/compare/v1.1.0...v1.1.1) (2026-06-08)


### Documentation

* **operations:** per-service deployment guide ([#28](https://github.com/piyush-official/FilterNArrange/issues/28)) ([f94bf68](https://github.com/piyush-official/FilterNArrange/commit/f94bf680bff983f7b7e1a10459c70fdf9388795e))

## [1.1.0](https://github.com/piyush-official/FilterNArrange/compare/v1.0.0...v1.1.0) (2026-06-08)


### Features

* **plan-g:** finish PR-2 — T8 Loki/Tempo/OTel-Collector + T12 tracing + T13 dashboards ([#24](https://github.com/piyush-official/FilterNArrange/issues/24)) ([8b7f55f](https://github.com/piyush-official/FilterNArrange/commit/8b7f55f7bd60abdd2aeed852298871ea9cf922a1))
* **plan-h:** T1 multi-arch GHCR build + T7 tag-triggered deploy ([#20](https://github.com/piyush-official/FilterNArrange/issues/20)) ([240c498](https://github.com/piyush-official/FilterNArrange/commit/240c498a4a9fd8117b54f0e24472f94a1df0269e))


### Bug Fixes

* **compose+health:** unblock 9 latent bugs surfaced by running the stack locally ([#25](https://github.com/piyush-official/FilterNArrange/issues/25)) ([a7ff17d](https://github.com/piyush-official/FilterNArrange/commit/a7ff17dc94a684b5f9744450bea5c464e67143a5))
* **docker:** make gateway + frontend images actually buildable ([#22](https://github.com/piyush-official/FilterNArrange/issues/22)) ([776be2c](https://github.com/piyush-official/FilterNArrange/commit/776be2cda25a734f8d3b806d12e3279bd8fbe5b6))
* **frontend:** drop vite.config.ts/vitest.config.ts from main tsconfig include ([#23](https://github.com/piyush-official/FilterNArrange/issues/23)) ([2a35c8f](https://github.com/piyush-official/FilterNArrange/commit/2a35c8f7e6be3987a9117ceca5feaa393c3200b3))

## 1.0.0 (2026-06-08)


### Features

* Plan A — foundation (apps, compose, contracts, CI, ADRs) ([#1](https://github.com/piyush-official/FilterNArrange/issues/1)) ([8767015](https://github.com/piyush-official/FilterNArrange/commit/8767015412b932a08934b7752e70d394052ff89d))
* Plan B — walking skeleton (gateway↔engine, plugins, frontend, lint contracts) ([#2](https://github.com/piyush-official/FilterNArrange/issues/2)) ([0d49f20](https://github.com/piyush-official/FilterNArrange/commit/0d49f200584b009afc403f56ebf08564e367eb76))
* Plan C — plugin breadth (5 formats, 3 filters, 4 analyses, dispatcher) ([#3](https://github.com/piyush-official/FilterNArrange/issues/3)) ([a5827dc](https://github.com/piyush-official/FilterNArrange/commit/a5827dcaef7915e84642994107a4431f7dd043fa))
* Plan C part 2 — gateway analyze + sheet-pick + OpenAPI 1.1 (T15-T16, T17-T22 wip) ([#4](https://github.com/piyush-official/FilterNArrange/issues/4)) ([0a39f5f](https://github.com/piyush-official/FilterNArrange/commit/0a39f5fa2064725f1f7fd6af83dab9bb4674ac72))
* Plan C T17-T20 — frontend filter modes + Monaco + analysis tab + sheet picker ([#5](https://github.com/piyush-official/FilterNArrange/issues/5)) ([2e76923](https://github.com/piyush-official/FilterNArrange/commit/2e769239e382d96653944ca4b7baea984d162e13))
* Plan D PR-2 — gateway async lane (Job domain + Kafka + idempotency + WebSocket fan-out) ([#7](https://github.com/piyush-official/FilterNArrange/issues/7)) ([b902500](https://github.com/piyush-official/FilterNArrange/commit/b902500cbbba9df3e57f0a93cf6977a68c96a726))
* **plan-d:** foundations — jobs + audit_log migrations, Kafka schemas, kafka-init, MODE switch ([#6](https://github.com/piyush-official/FilterNArrange/issues/6)) ([93ec852](https://github.com/piyush-official/FilterNArrange/commit/93ec8526a5c5161f18d79f95fde85c40c176aadd))
* **plan-d:** T12-T22 worker + frontend + integration tests ([#8](https://github.com/piyush-official/FilterNArrange/issues/8)) ([7487e3c](https://github.com/piyush-official/FilterNArrange/commit/7487e3cf29a773a509e977354da66561c31fcd57))
* **plan-e:** PR-1 — AI foundation, plugins, FastAPI surface ([#9](https://github.com/piyush-official/FilterNArrange/issues/9)) ([4c1af4b](https://github.com/piyush-official/FilterNArrange/commit/4c1af4b756ee994f51202ad26e9faacd72abe8f8))
* **plan-e:** PR-2 — gateway AI pass-through + OpenAPI + ai-anomaly-full job kind ([#10](https://github.com/piyush-official/FilterNArrange/issues/10)) ([f3e0888](https://github.com/piyush-official/FilterNArrange/commit/f3e08881850ab72b2e7e002c0e130614a17b494f))
* **plan-e:** T20-T28 — frontend AI surface + concurrency test + docs ([#11](https://github.com/piyush-official/FilterNArrange/issues/11)) ([3ae8d2e](https://github.com/piyush-official/FilterNArrange/commit/3ae8d2e27a373fd0019a2e2fb0d6c6afbcf36111))
* **plan-f:** PR-1 — tier domain + auth filters + 4 migrations ([#12](https://github.com/piyush-official/FilterNArrange/issues/12)) ([ba19982](https://github.com/piyush-official/FilterNArrange/commit/ba1998246cf545f1fd1235e31550daf427d64db3))
* **plan-f:** PR-2 — recipes + format-requests + jobs topic split + billing ([#13](https://github.com/piyush-official/FilterNArrange/issues/13)) ([9b34cc5](https://github.com/piyush-official/FilterNArrange/commit/9b34cc5d4493f5d0c066bd81a3e6418fac967135))
* **plan-f:** PR-3 — audit-on-reject + retention worker + frontend + e2e ([#14](https://github.com/piyush-official/FilterNArrange/issues/14)) ([2bbe05e](https://github.com/piyush-official/FilterNArrange/commit/2bbe05ef0d959ea5bd1967eda23f31ed01f4a587))
* **plan-g:** PR-1 — Keycloak compose + V10 external_id migration ([#15](https://github.com/piyush-official/FilterNArrange/issues/15)) ([413adf8](https://github.com/piyush-official/FilterNArrange/commit/413adf8c57116c72a3b8ad57d62ad9f6db3752e7))
* **plan-g:** PR-2 — Prometheus + Grafana + Gateway Micrometer ([#16](https://github.com/piyush-official/FilterNArrange/issues/16)) ([f3f41c2](https://github.com/piyush-official/FilterNArrange/commit/f3f41c2fa5df317fe22deb130e9439c67de9b90a))
* **plan-g:** PR-3 — backup container + migration policy + runbooks ([#17](https://github.com/piyush-official/FilterNArrange/issues/17)) ([c58f38f](https://github.com/piyush-official/FilterNArrange/commit/c58f38f685ee204f1df7e3e41b8d0f7863690e79))
* **plan-h:** public deploy — prod compose + Caddy + bootstrap + smoke + docs ([#18](https://github.com/piyush-official/FilterNArrange/issues/18)) ([f87d8d6](https://github.com/piyush-official/FilterNArrange/commit/f87d8d6bfdc4292b230e11296bed67f8002f22d0))


### Documentation

* add consolidated design spec, run guide, and dev-tooling cost catalog ([32bad8a](https://github.com/piyush-official/FilterNArrange/commit/32bad8aec31434b5076d1510252c62d9b53401ff))
* **plans:** add 8 implementation plans (A-H) from empty repo to v1.0.0 ([3cd59e5](https://github.com/piyush-official/FilterNArrange/commit/3cd59e5393c7f11407ad29139d3183af783fbe88))


### Chores

* bootstrap project scaffold and design docs ([685b4b6](https://github.com/piyush-official/FilterNArrange/commit/685b4b6f00091bd16af631daa3d485fbeeda62b8))
* track merged Plan A/B branches pending deletion ([ce7e14b](https://github.com/piyush-official/FilterNArrange/commit/ce7e14b40f64e3be75e040748f0527c457e7c881))
* track merged Plan C branch in MERGED_BRANCHES.md ([6c8abe0](https://github.com/piyush-official/FilterNArrange/commit/6c8abe0916f57c0ecb648045f5cdbf45864fc28f))
* track merged Plan C frontend branch in MERGED_BRANCHES.md ([4e093c2](https://github.com/piyush-official/FilterNArrange/commit/4e093c2ae1c569b93d3b0475c1614c598c4a432c))
* track merged Plan C part 2 branch in MERGED_BRANCHES.md ([d94c97a](https://github.com/piyush-official/FilterNArrange/commit/d94c97a899ffd3a474b094b989535df122d45768))
* track merged Plan D PR-1 foundations branch ([5381066](https://github.com/piyush-official/FilterNArrange/commit/53810664d9fa3fda1e6be01bb8a0d749291f1cd6))
* track merged Plan D PR-2 gateway-async branch ([dac641a](https://github.com/piyush-official/FilterNArrange/commit/dac641af18d15e398bd6527a6e9a2ed129d3284b))
* track merged Plan D PR-3 worker+frontend+integration branch ([022f1cf](https://github.com/piyush-official/FilterNArrange/commit/022f1cf56999a21ea71c5b2554e34f635a8bdab8))
* track merged Plan E PR-1 ai-foundation branch ([0cdece4](https://github.com/piyush-official/FilterNArrange/commit/0cdece45fb86cd5a0d895b24ed5b1d7039ec6468))
* track merged Plan E PR-2 gateway-ai branch ([ea78b9c](https://github.com/piyush-official/FilterNArrange/commit/ea78b9c38e10ff7d83d573e9935ca775746a5e18))
* track merged Plan E PR-3 frontend-ai branch ([daaace2](https://github.com/piyush-official/FilterNArrange/commit/daaace2f2ce8db583da6d61250a4f069e1b17b74))
* track merged Plan F PR-1 + PR-2 branches ([a034e20](https://github.com/piyush-official/FilterNArrange/commit/a034e20aa9c43398f3990a389bfbda1bde7203cc))
* track merged Plan F PR-3 frontend branch ([cc5ef84](https://github.com/piyush-official/FilterNArrange/commit/cc5ef84a5bab1b0cbb30161d1403ba9dd334607d))
* track merged Plan G PR-1 auth branch ([0c69ee7](https://github.com/piyush-official/FilterNArrange/commit/0c69ee7c3060e04c5544af6ab75b343300f04350))
* track merged Plan G PR-2 observability branch ([be86d00](https://github.com/piyush-official/FilterNArrange/commit/be86d00af35430851556662c04c5d499e2602bfb))
* track merged Plan G PR-3 hardening branch ([2232adb](https://github.com/piyush-official/FilterNArrange/commit/2232adb2601dc2fd96069e33e375999e4f15b6b4))
* track merged Plan H public-deploy branch ([cfbc0f9](https://github.com/piyush-official/FilterNArrange/commit/cfbc0f998c57777b0677d1cd9c68a41300d10d3f))

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
