# Plan A — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the monorepo skeleton, three "hello world" apps (gateway / data-engine / frontend), full Docker Compose stack, contracts scaffold, CI/CD pipeline, governance templates, and three foundational ADRs so every subsequent plan (B–H) can start with a green build.

**Architecture:** Polyglot monorepo with `apps/{gateway,data-engine,frontend}`, top-level `contracts/`, `plugins/`, `infra/`, `scripts/`, and `tests/integration/` per spec §6. Each app boots a `/health` endpoint, packages a Dockerfile, and joins a single Docker Compose network alongside Postgres, Redis, Redpanda, MinIO, Ollama, and Caddy. Cross-cutting CI uses GitHub Actions; releases use `release-please`.

**Tech Stack:**
- Gateway: Spring Boot 3.x, Gradle, OpenJDK 21 (Eclipse Temurin)
- Data-engine: FastAPI, `uv`, Python 3.12-slim
- Frontend: Vite + React + TypeScript, Node 20 / nginx
- Infra: Postgres 16, Valkey 7 (Redis-compatible), Redpanda (KRaft), MinIO, Ollama, Caddy 2
- CI: GitHub Actions, Spectral (OpenAPI lint), commitlint, husky, release-please
- License: Apache-2.0 (ADR-0002)

---

## Spec Citations

This plan implements the foundational subset of:

- §2 Architecture (service map; loose-coupling rules 1–6)
- §3 Data Flow & Contracts (contracts directory layout)
- §6 Module Organization (monorepo layout, hexagonal per-app skeleton, public-surface rule)
- §7 Engineering Workflow (7.1 ticketing, 7.2 PR workflow, 7.3 versioning, 7.4 ADRs, 7.5 CI/CD pipeline)
- §8 Run Guide (the configuration matrix used by `.env.example`)

Out-of-scope items are listed in the user-provided Plan A scope.

---

## File Structure

### Directories to create

```
apps/
├── gateway/                       # Spring Boot 3.x (Java 21)
│   ├── src/main/java/io/filternarrange/gateway/
│   │   ├── api/                   # REST controllers
│   │   ├── application/           # use-case services
│   │   ├── domain/                # entities + ports
│   │   ├── infrastructure/        # adapters
│   │   └── platform/              # cross-cutting
│   ├── src/main/resources/
│   ├── src/test/java/io/filternarrange/gateway/
│   ├── build.gradle.kts
│   ├── settings.gradle.kts
│   ├── gradle.properties
│   ├── Dockerfile
│   └── README.md
├── data-engine/                   # FastAPI (Python 3.12)
│   ├── src/filternarrange_engine/
│   │   ├── api/
│   │   ├── application/
│   │   ├── core/
│   │   ├── adapters/
│   │   └── platform/
│   ├── tests/
│   ├── pyproject.toml
│   ├── .python-version
│   ├── Dockerfile
│   └── README.md
└── frontend/                      # Vite + React + TS
    ├── src/
    │   ├── app/
    │   ├── pages/
    │   ├── features/
    │   └── shared/
    ├── public/
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── nginx.conf
    ├── Dockerfile
    └── README.md

plugins/                           # (empty in Plan A; populated by Plan B+)
└── README.md

contracts/
├── README.md
├── openapi/
│   ├── gateway-public.v1.yaml
│   └── gateway-internal.v1.yaml
└── kafka/
    ├── topic.v1.jobs.schema.json
    ├── topic.v1.job-results.schema.json
    ├── topic.v1.format-requests.schema.json
    └── topic.v1.audit-events.schema.json

infra/
├── docker-compose/
│   └── docker-compose.yml
├── caddy/
│   └── Caddyfile
└── observability/
    └── README.md                  # placeholder; populated by Plan H

scripts/
├── wait-for-healthy.sh
└── seed-dev

tests/
└── integration/
    └── README.md                  # placeholder

.github/
├── workflows/
│   ├── pr.yml
│   └── release.yml
├── ISSUE_TEMPLATE/
│   ├── bug.yml
│   ├── feature.yml
│   ├── format-request.yml
│   ├── plugin.yml
│   ├── chore.yml
│   └── config.yml
├── pull_request_template.md
└── CODEOWNERS

docs/decisions/
├── ADR-0002-license.md
├── ADR-0003-module-dependency-and-failure-isolation.md
├── ADR-0004-ticketing-and-versioning-workflow.md
└── README.md

# repo root additions
LICENSE                            # Apache-2.0 full text
.env.example
.gitattributes
package.json                       # monorepo devDeps (commitlint + husky)
commitlint.config.js
release-please-config.json
.release-please-manifest.json
.husky/commit-msg                  # created by `husky install` + add hook
```

### Files removed

- `NOTICE` (superseded by `LICENSE` once ADR-0002 lands)

### Files modified

- `README.md` (drop "license pending" language, point at `LICENSE`)
- Note: `CHANGELOG.md` updates and `docs/cost-tracking.md` updates are reserved for the orchestrator after all 8 plans land.

---

## Task Ordering Notes

The 16 tasks below are ordered so each one can be reviewed and merged independently. Within a task, every code step shows the full text being created or modified — no "fill in details". Each task ends with a Conventional Commit. The executor is expected to open a GitHub issue per task before starting and reference it in the commit (`Closes #N`); use `#TBD` if the issue isn't yet open and update before merging.

---

## Task 1: Monorepo skeleton (empty directories + placeholder READMEs)

**Files:**
- Create: `apps/gateway/README.md`
- Create: `apps/data-engine/README.md`
- Create: `apps/frontend/README.md`
- Create: `plugins/README.md`
- Create: `contracts/README.md`
- Create: `infra/observability/README.md`
- Create: `tests/integration/README.md`
- Create: `.gitattributes`

- [ ] **Step 1: Create directory tree**

```bash
mkdir -p apps/gateway/src/main/java/io/filternarrange/gateway/{api,application,domain,infrastructure,platform}
mkdir -p apps/gateway/src/main/resources
mkdir -p apps/gateway/src/test/java/io/filternarrange/gateway
mkdir -p apps/data-engine/src/filternarrange_engine/{api,application,core,adapters,platform}
mkdir -p apps/data-engine/tests
mkdir -p apps/frontend/src/{app,pages,features,shared}
mkdir -p apps/frontend/public
mkdir -p plugins
mkdir -p contracts/openapi contracts/kafka
mkdir -p infra/docker-compose infra/caddy infra/observability
mkdir -p scripts
mkdir -p tests/integration
mkdir -p .github/workflows .github/ISSUE_TEMPLATE
```

- [ ] **Step 2: Write `apps/gateway/README.md`**

```markdown
# apps/gateway

Spring Boot 3.x API gateway (Java 21). Owns auth, tier/quota enforcement, routing to the data-engine, WebSocket push for async results, and the Postgres datastore (per spec §2 service map).

## Layout (hexagonal — see spec §6)

- `src/main/java/io/filternarrange/gateway/api` — REST controllers
- `src/main/java/io/filternarrange/gateway/application` — use-case services
- `src/main/java/io/filternarrange/gateway/domain` — entities + ports (pure, zero outside deps)
- `src/main/java/io/filternarrange/gateway/infrastructure` — adapters (persistence, messaging, storage, http)
- `src/main/java/io/filternarrange/gateway/platform` — auth, errors, observability

## Local run

```bash
./gradlew bootRun
```

## Tests

```bash
./gradlew test
```
```

- [ ] **Step 3: Write `apps/data-engine/README.md`**

```markdown
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
```

- [ ] **Step 4: Write `apps/frontend/README.md`**

```markdown
# apps/frontend

Vite + React + TypeScript SPA. Talks only to the gateway (per spec §2 loose-coupling rule 2).

## Layout (feature-sliced — see spec §6)

- `src/app/` — shell, routing, providers
- `src/pages/` — route components
- `src/features/<feature>/{api,ui,state,index.ts}` — features never import each other
- `src/shared/` — `ui/`, `lib/`, `api/client`

## Local run

```bash
npm install
npm run dev   # http://localhost:5173
```

## Tests

```bash
npm test
```
```

- [ ] **Step 5: Write `plugins/README.md`**

```markdown
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
```

- [ ] **Step 6: Write `infra/observability/README.md`**

```markdown
# infra/observability/

Reserved for Prometheus, Grafana, Loki, and Tempo configuration. Populated by Plan H (production deploy). Plan A leaves this empty so the directory exists in source control.
```

- [ ] **Step 7: Write `tests/integration/README.md`**

```markdown
# tests/integration/

Cross-service integration suite using testcontainers (Postgres, Redis, Redpanda, MinIO). Populated by Plan B and grown by each subsequent plan. Run via `./scripts/test-integration.sh` (added by Plan B).
```

- [ ] **Step 8: Write `.gitattributes`** (force LF endings for shell scripts so CI on Linux runners doesn't choke)

```
* text=auto eol=lf
*.sh text eol=lf
*.bat text eol=crlf
*.png binary
*.jpg binary
*.parquet binary
*.xlsx binary
```

- [ ] **Step 9: Verify** (no automated test for skeleton-only changes; visual `ls` check)

Run: `find apps plugins contracts infra scripts tests .github -maxdepth 2 -type d | sort`
Expected output (subset): `apps/data-engine`, `apps/frontend`, `apps/gateway`, `contracts/kafka`, `contracts/openapi`, `infra/caddy`, `infra/docker-compose`, `infra/observability`, `plugins`, `scripts`, `tests/integration`.

- [ ] **Step 10: Commit**

```bash
git add apps plugins contracts infra scripts tests .github .gitattributes
git commit -m "chore(repo): scaffold monorepo directories and per-app READMEs

Closes #TBD"
```

---

## Task 2: License — drop NOTICE, add LICENSE (Apache-2.0), update README

**Files:**
- Create: `LICENSE`
- Delete: `NOTICE`
- Modify: `README.md`

- [ ] **Step 1: Write LICENSE** (full Apache-2.0 text)

Use the canonical Apache-2.0 text from <https://www.apache.org/licenses/LICENSE-2.0.txt>. The file must include the header `Apache License, Version 2.0, January 2004` followed by the unmodified 11-section license body and the standard "APPENDIX: How to apply the Apache License to your work" boilerplate. Set the copyright line in the appendix template to:

```
Copyright 2026 Piyush (piyush-official) and FilterNArrange contributors
```

(Do not abbreviate the license body. The Apache-2.0 text is ~11 KB; reproduce it verbatim. If the executor needs a deterministic source, fetch from <https://www.apache.org/licenses/LICENSE-2.0.txt> at commit time.)

- [ ] **Step 2: Delete NOTICE**

```bash
git rm NOTICE
```

- [ ] **Step 3: Replace the License section in `README.md`**

Replace lines 30–32 (the existing `## License` block) with:

```markdown
## License

FilterNArrange is licensed under the [Apache License, Version 2.0](LICENSE) — see [ADR-0002](docs/decisions/ADR-0002-license.md) for the rationale.
```

- [ ] **Step 4: Verify**

Run: `head -1 LICENSE && grep -c "Apache License" LICENSE`
Expected: first line contains "Apache License", grep count ≥ 2.

Run: `grep -c "license pending\|AGPL\|NOTICE" README.md`
Expected: `0`.

Run: `test ! -f NOTICE && echo "NOTICE removed"`
Expected: `NOTICE removed`.

- [ ] **Step 5: Commit**

```bash
git add LICENSE README.md
git rm NOTICE 2>/dev/null || true
git commit -m "chore(license): adopt Apache-2.0 and remove NOTICE placeholder

Closes #TBD"
```

---

## Task 3: ADR-0002 (license), ADR-0003 (deps + failure isolation), ADR-0004 (workflow), ADR index

**Files:**
- Create: `docs/decisions/ADR-0002-license.md`
- Create: `docs/decisions/ADR-0003-module-dependency-and-failure-isolation.md`
- Create: `docs/decisions/ADR-0004-ticketing-and-versioning-workflow.md`
- Create: `docs/decisions/README.md`

- [ ] **Step 1: Write `docs/decisions/ADR-0002-license.md`**

```markdown
# ADR-0002: License — Apache-2.0

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** piyush-official
- **Supersedes:** the "license TBD" note in ADR-0001 §Follow-ups

## Context

ADR-0001 left the license choice open between AGPL-3.0 and Apache-2.0. The repository was kept private until this decision landed (per spec §1). A license is required before the repo flips public, and before any external contributor can submit a PR.

The headline trade-off:

- **AGPL-3.0** — strongest copyleft. Anyone running a modified FilterNArrange as a network service must publish their changes. Deters proprietary forks; deters some users from self-hosting because of fear-of-the-AGPL.
- **Apache-2.0** — permissive. Anyone can fork, modify, and host without obligation. Maximizes adoption and contributor flow; offers an explicit patent grant.

## Decision

License under **Apache-2.0**.

## Rationale

1. **Adoption first.** FilterNArrange's success depends on a healthy community contributing format / filter / analysis plugins. Apache-2.0 is the lowest-friction license for downstream users and corporate contributors who can't ship AGPL-licensed dependencies.
2. **Moat comes from features, not license restriction.** The paid hosted tier funds itself via managed UX (saved recipes, retention, advanced features, prioritized format requests — per spec §1). A fork that strips those is welcome; we're not betting on copyleft to lock anyone in.
3. **Plugin ecosystem.** Plugins ship as separately-licensed packages (see manifest `license` field in spec §4). Apache-2.0 on core lets plugins choose Apache, MIT, BSD, or copyleft — author's call.
4. **Patent grant.** Apache-2.0's explicit patent grant protects contributors and users in ways the SSPL-style licenses don't.

## Consequences

- `LICENSE` file (full Apache-2.0 text) committed to repo root; `NOTICE` removed.
- README updated to point at `LICENSE` and this ADR.
- Repo can flip public once Plan A merges.
- Future contributions are inbound under Apache-2.0 by default (per the standard "outbound = inbound" reading of contribution via PRs against an Apache-2.0 project).
- If we ever ship a feature we want to keep exclusive to the hosted tier, we deliver it as a closed-source overlay package, not by relicensing the core. (No re-licensing without a future ADR.)

## Follow-ups

- Add an `Apache-2.0` SPDX header to every new source file going forward (`// SPDX-License-Identifier: Apache-2.0`).
- When the repo flips public, add a `CONTRIBUTING.md` clarifying inbound = Apache-2.0.
```

- [ ] **Step 2: Write `docs/decisions/ADR-0003-module-dependency-and-failure-isolation.md`**

```markdown
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
```

- [ ] **Step 3: Write `docs/decisions/ADR-0004-ticketing-and-versioning-workflow.md`**

```markdown
# ADR-0004: Ticketing, versioning, and CI workflow

- **Status:** Accepted
- **Date:** 2026-06-07
- **Deciders:** piyush-official
- **Codifies:** spec §7 (Engineering Workflow)

## Context

Spec §7 specifies GitHub Issues for ticketing, Conventional Commits + SemVer for versioning, ADRs for decisions, a 9-stage CI pipeline, a test pyramid (~70% unit, ~20% integration, ~5% E2E, ~5% contract), coverage minimums (80% lines / 70% branches per app), and a change-impact report per release. These need to be authoritative so they can't drift across the eight implementation plans.

## Decision

### Ticketing

- All work tracked as GitHub Issues. Templates: `bug.yml`, `feature.yml`, `format-request.yml`, `plugin.yml`, `chore.yml` (per spec §7.1).
- Required fields per template: requirement, acceptance criteria, scope (in/out), blast radius, regression risk, test plan.
- Labels: `Type` (bug/feature/chore/docs/format-request/regression), `Area` (gateway/data-engine/frontend/plugins/infra/contracts), `Priority` (P0–P3), `Status` (triaged/in-progress/blocked/needs-review/needs-tests), `Risk` (low/medium/high), `Tier` (free/paid).
- Project board: Backlog → Triaged → In Progress → In Review → Done.

### Versioning & releases

- **SemVer.** Pre-1.0 minor bumps may include breaking changes.
- **Conventional Commits** drive the changelog:
  - `feat:` → MINOR
  - `fix:` → PATCH
  - `feat!:` / `BREAKING CHANGE:` → MAJOR
  - `chore` / `docs` / `refactor` / `test` / `ci` / `build` / `perf` → no bump (still in changelog)
- `release-please` (GitHub Action) opens / updates a Release PR; merging it tags `vX.Y.Z`, builds images, generates SBOM (Syft), signs (Cosign), publishes the GitHub Release.
- `latest` tag only on `main` for non-production usage. Container images tagged `vX.Y.Z` for releases.

### ADRs

- One file per decision in `docs/decisions/ADR-NNNN-<slug>.md`.
- Format: Status / Date / Deciders / Context / Decision / Consequences / Follow-ups.
- Immutable once Accepted. Supersede with a later ADR; cross-link both ways.
- Required when: stack choice, license, schema change with migration impact, contract version bump, plugin API change, tier/quota model change.
- Index at `docs/decisions/README.md`.

### PR workflow

- Title: Conventional Commit.
- Body template (`.github/pull_request_template.md`) requires Summary / Linked issues / Changes / Impact assessment / Regression risk / Tests / Docs+cost-tracking checklist. CI fails the PR if any required section is empty.
- Merge: squash-merge. One issue → one commit on `main`.
- Branch protection on `main`: ≥1 CODEOWNERS approval, all required checks green, no force-push, no direct push, linear history.

### CI pipeline (`.github/workflows/pr.yml`)

Stages (spec §7.5):

1. lint (Java: spotless+checkstyle; Python: ruff+mypy; TS: eslint+tsc; commitlint)
2. unit tests (JUnit / pytest / vitest; coverage → Codecov)
3. architecture tests (ArchUnit / import-linter / eslint-plugin-boundaries)
4. contract validation (Spectral on OpenAPI; ajv on JSON Schema; Schemathesis fuzz)
5. plugin conformance (canonical suite per plugin)
6. integration tests (testcontainers — Postgres, Redis, Kafka, MinIO)
7. e2e (Playwright against compose stack)
8. performance gates (k6; fail if p95 > budget + 10%)
9. PR template guard

Required to merge: 1, 2, 3, 4, 5, 9. Integration + E2E required on `main` with one auto-retry. Performance gates blocking.

### Test pyramid + coverage minimums

- Unit ≈70%, Architecture (n/a share), Contract ≈5%, Integration ≈20%, E2E ≈5%.
- 80% lines / 70% branches per app; new-code patch coverage ≥85%.
- Every bug fix ships a regression test that fails on `main` and passes on the fix.

### Change-impact + regression report (per release)

Each GitHub Release includes:

1. Summary (auto from CHANGELOG).
2. Migration notes (DB migrations, env-var changes, config changes).
3. Regression watch — top 3 risk areas from merged PRs.
4. Performance snapshot — k6 numbers vs previous release.
5. Plugin compatibility — plugin API version + quarantined plugins.

## Consequences

- Plan A wires the surface area: PR template, issue templates, CODEOWNERS, `pr.yml` skeleton with all 9 jobs (placeholders OK where the apps don't yet have real code), `release.yml` with `release-please`.
- Plans B–H deepen each stage (real ArchUnit rules, real integration tests, real k6 budgets) without changing the workflow itself.

## Follow-ups

- Set up Codecov account and add the upload token to repo secrets when first real tests land (Plan B).
- Configure branch protection rules on `main` once the first PR is ready to merge (manual step).
```

- [ ] **Step 4: Write `docs/decisions/README.md`**

```markdown
# Architecture Decision Records (ADRs)

This directory holds one file per material architectural decision. Format and policy are defined in [ADR-0004](ADR-0004-ticketing-and-versioning-workflow.md). ADRs are immutable once Accepted; they are superseded by later ADRs, not edited.

## Index

| # | Title | Status | Date |
|---|---|---|---|
| [0001](ADR-0001-initial-stack-and-principles.md) | Initial stack and architectural principles | Accepted | 2026-06-07 |
| [0002](ADR-0002-license.md) | License — Apache-2.0 | Accepted | 2026-06-07 |
| [0003](ADR-0003-module-dependency-and-failure-isolation.md) | Module dependency direction & failure isolation | Accepted | 2026-06-07 |
| [0004](ADR-0004-ticketing-and-versioning-workflow.md) | Ticketing, versioning, and CI workflow | Accepted | 2026-06-07 |

## Conventions

- File name: `ADR-NNNN-<kebab-slug>.md` with `NNNN` zero-padded to four digits.
- Status values: `Proposed`, `Accepted`, `Superseded by ADR-XXXX`, `Withdrawn`.
- Required when: stack choice, license, schema change with migration impact, contract version bump, plugin API change, tier/quota model change.
```

- [ ] **Step 5: Verify**

Run: `ls docs/decisions/`
Expected: `ADR-0001-...`, `ADR-0002-license.md`, `ADR-0003-...`, `ADR-0004-...`, `README.md`.

Run: `grep -l "Status.*Accepted" docs/decisions/ADR-000*.md | wc -l`
Expected: `4`.

- [ ] **Step 6: Commit**

```bash
git add docs/decisions/
git commit -m "docs(adr): add ADR-0002 license, ADR-0003 deps, ADR-0004 workflow

Closes #TBD"
```

---

## Task 4: Gateway hello-world (Spring Boot + Gradle + /health)

**Files:**
- Create: `apps/gateway/settings.gradle.kts`
- Create: `apps/gateway/build.gradle.kts`
- Create: `apps/gateway/gradle.properties`
- Create: `apps/gateway/src/main/resources/application.yml`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/GatewayApplication.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/HealthController.java`
- Create: `apps/gateway/src/test/java/io/filternarrange/gateway/api/HealthControllerTest.java`
- Create: `apps/gateway/.gitignore`
- Create: `apps/gateway/Dockerfile`
- Create: `apps/gateway/.dockerignore`

- [ ] **Step 1: Write `apps/gateway/settings.gradle.kts`**

```kotlin
rootProject.name = "gateway"
```

- [ ] **Step 2: Write `apps/gateway/build.gradle.kts`**

```kotlin
plugins {
    java
    id("org.springframework.boot") version "3.2.5"
    id("io.spring.dependency-management") version "1.1.4"
}

group = "io.filternarrange"
version = "0.0.0"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

repositories {
    mavenCentral()
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-actuator")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.junit.jupiter:junit-jupiter")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.withType<Test> {
    useJUnitPlatform()
}
```

- [ ] **Step 3: Write `apps/gateway/gradle.properties`**

```properties
org.gradle.jvmargs=-Xmx1g -Dfile.encoding=UTF-8
org.gradle.parallel=true
org.gradle.caching=true
```

- [ ] **Step 4: Write `apps/gateway/src/main/resources/application.yml`**

```yaml
spring:
  application:
    name: filternarrange-gateway

server:
  port: 8080

management:
  endpoints:
    web:
      exposure:
        include: health,info
  endpoint:
    health:
      show-details: never
```

- [ ] **Step 5: Write `apps/gateway/.gitignore`**

```
.gradle/
build/
out/
*.iml
.idea/
.vscode/
```

- [ ] **Step 6: Write the failing test `apps/gateway/src/test/java/io/filternarrange/gateway/api/HealthControllerTest.java`**

```java
// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class HealthControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void healthEndpointReturnsUp() throws Exception {
        mockMvc.perform(get("/health"))
            .andExpect(status().isOk())
            .andExpect(content().contentTypeCompatibleWith("application/json"))
            .andExpect(jsonPath("$.status").value("UP"));
    }
}
```

- [ ] **Step 7: Run the test to verify it fails**

Run: `cd apps/gateway && ./gradlew test`
Expected: FAIL — Spring Boot application class doesn't exist; build fails to find a `@SpringBootApplication`-annotated main.

(If a Gradle wrapper isn't present yet, the executor must first run `gradle wrapper --gradle-version 8.7` once with a system Gradle, then commit `gradlew`, `gradlew.bat`, and `gradle/wrapper/`.)

- [ ] **Step 8: Write `apps/gateway/src/main/java/io/filternarrange/gateway/GatewayApplication.java`**

```java
// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class GatewayApplication {
    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }
}
```

- [ ] **Step 9: Write `apps/gateway/src/main/java/io/filternarrange/gateway/api/HealthController.java`**

```java
// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "UP");
    }
}
```

- [ ] **Step 10: Run the test to verify it passes**

Run: `cd apps/gateway && ./gradlew test`
Expected: PASS — `HealthControllerTest.healthEndpointReturnsUp` green.

- [ ] **Step 11: Write `apps/gateway/.dockerignore`**

```
.gradle
build
out
*.iml
.idea
.vscode
src/test
```

- [ ] **Step 12: Write `apps/gateway/Dockerfile`** (multi-stage; Eclipse Temurin 21)

```dockerfile
# syntax=docker/dockerfile:1.7

# ---- build stage ----
FROM eclipse-temurin:21-jdk-jammy AS build
WORKDIR /workspace
COPY gradlew gradlew
COPY gradle gradle
COPY settings.gradle.kts build.gradle.kts gradle.properties ./
COPY src src
RUN chmod +x gradlew && ./gradlew --no-daemon bootJar

# ---- runtime stage ----
FROM eclipse-temurin:21-jre-jammy
WORKDIR /app
RUN useradd --system --uid 1001 --create-home --home-dir /home/gateway gateway
COPY --from=build /workspace/build/libs/gateway-0.0.0.jar /app/gateway.jar
USER gateway
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=10 \
    CMD curl -fsS http://localhost:8080/health || exit 1
ENTRYPOINT ["java", "-jar", "/app/gateway.jar"]
```

(`curl` is present in the Temurin Jammy base image. If a future slim base drops it, install via `apt-get install -y --no-install-recommends curl` in the runtime stage.)

- [ ] **Step 13: Commit**

```bash
git add apps/gateway
git commit -m "feat(gateway): bootstrap Spring Boot app with /health endpoint

Closes #TBD"
```

---

## Task 5: Data-engine hello-world (FastAPI + uv + /health)

**Files:**
- Create: `apps/data-engine/pyproject.toml`
- Create: `apps/data-engine/.python-version`
- Create: `apps/data-engine/.gitignore`
- Create: `apps/data-engine/src/filternarrange_engine/__init__.py`
- Create: `apps/data-engine/src/filternarrange_engine/api/__init__.py`
- Create: `apps/data-engine/src/filternarrange_engine/api/main.py`
- Create: `apps/data-engine/tests/__init__.py`
- Create: `apps/data-engine/tests/test_health.py`
- Create: `apps/data-engine/Dockerfile`
- Create: `apps/data-engine/.dockerignore`

- [ ] **Step 1: Write `apps/data-engine/.python-version`**

```
3.12
```

- [ ] **Step 2: Write `apps/data-engine/pyproject.toml`**

```toml
[project]
name = "filternarrange-engine"
version = "0.0.0"
description = "FilterNArrange data + AI engine (FastAPI)."
readme = "README.md"
license = { text = "Apache-2.0" }
requires-python = ">=3.12,<3.13"
dependencies = [
    "fastapi==0.111.0",
    "uvicorn[standard]==0.30.1",
    "pydantic==2.7.1",
]

[project.optional-dependencies]
dev = [
    "pytest==8.2.0",
    "pytest-asyncio==0.23.7",
    "httpx==0.27.0",
    "ruff==0.4.4",
    "mypy==1.10.0",
]

[build-system]
requires = ["hatchling>=1.24.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/filternarrange_engine"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "N"]

[tool.mypy]
python_version = "3.12"
strict = true
mypy_path = "src"
```

- [ ] **Step 3: Write `apps/data-engine/.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
dist/
build/
*.egg-info/
.coverage
```

- [ ] **Step 4: Write `apps/data-engine/src/filternarrange_engine/__init__.py`**

```python
# SPDX-License-Identifier: Apache-2.0
"""FilterNArrange data + AI engine."""

__all__: list[str] = []
__version__ = "0.0.0"
```

- [ ] **Step 5: Write `apps/data-engine/src/filternarrange_engine/api/__init__.py`**

```python
# SPDX-License-Identifier: Apache-2.0
"""FastAPI routers — public surface for the API layer."""

from filternarrange_engine.api.main import app

__all__ = ["app"]
```

- [ ] **Step 6: Write the failing test `apps/data-engine/tests/test_health.py`**

```python
# SPDX-License-Identifier: Apache-2.0
"""Health endpoint contract test."""

from fastapi.testclient import TestClient

from filternarrange_engine.api.main import app


def test_health_returns_up() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "UP"}
```

- [ ] **Step 7: Run the test to verify it fails**

Run: `cd apps/data-engine && uv sync --all-extras && uv run pytest tests/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'filternarrange_engine.api.main'`.

- [ ] **Step 8: Write `apps/data-engine/src/filternarrange_engine/api/main.py`**

```python
# SPDX-License-Identifier: Apache-2.0
"""FastAPI application entrypoint and /health endpoint."""

from fastapi import FastAPI

app = FastAPI(
    title="FilterNArrange data-engine",
    version="0.0.0",
    docs_url="/docs",
    redoc_url=None,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe — returns {'status': 'UP'} when the process is serving."""
    return {"status": "UP"}
```

- [ ] **Step 9: Write `apps/data-engine/tests/__init__.py`** (empty file so pytest treats `tests/` as a package)

```python
```

- [ ] **Step 10: Run the test to verify it passes**

Run: `cd apps/data-engine && uv run pytest tests/test_health.py -v`
Expected: PASS — 1 passed.

- [ ] **Step 11: Write `apps/data-engine/.dockerignore`**

```
__pycache__
*.pyc
.pytest_cache
.mypy_cache
.ruff_cache
.venv
dist
build
*.egg-info
tests
```

- [ ] **Step 12: Write `apps/data-engine/Dockerfile`** (`python:3.12-slim` + `uv`)

```dockerfile
# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.2.5

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN uv pip install --system .

RUN useradd --system --uid 1001 --create-home --home-dir /home/engine engine \
    && chown -R engine:engine /app
USER engine

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=10 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["uvicorn", "filternarrange_engine.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 13: Commit**

```bash
git add apps/data-engine
git commit -m "feat(data-engine): bootstrap FastAPI app with /health endpoint

Closes #TBD"
```

---

## Task 6: Frontend hello-world (Vite + React + TS + nginx)

**Files:**
- Create: `apps/frontend/package.json`
- Create: `apps/frontend/tsconfig.json`
- Create: `apps/frontend/tsconfig.node.json`
- Create: `apps/frontend/vite.config.ts`
- Create: `apps/frontend/vitest.config.ts`
- Create: `apps/frontend/.gitignore`
- Create: `apps/frontend/index.html`
- Create: `apps/frontend/src/main.tsx`
- Create: `apps/frontend/src/app/App.tsx`
- Create: `apps/frontend/src/app/App.test.tsx`
- Create: `apps/frontend/nginx.conf`
- Create: `apps/frontend/Dockerfile`
- Create: `apps/frontend/.dockerignore`

- [ ] **Step 1: Write `apps/frontend/package.json`**

```json
{
  "name": "filternarrange-frontend",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "typecheck": "tsc -b --noEmit"
  },
  "dependencies": {
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "6.4.5",
    "@testing-library/react": "16.0.0",
    "@types/node": "20.12.12",
    "@types/react": "18.3.3",
    "@types/react-dom": "18.3.0",
    "@vitejs/plugin-react": "4.3.0",
    "happy-dom": "14.10.1",
    "typescript": "5.4.5",
    "vite": "5.2.11",
    "vitest": "1.6.0"
  }
}
```

- [ ] **Step 2: Write `apps/frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noImplicitOverride": true,
    "noUncheckedIndexedAccess": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"],
    "baseUrl": "./src",
    "paths": {
      "@/*": ["*"]
    }
  },
  "include": ["src", "vite.config.ts", "vitest.config.ts"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 3: Write `apps/frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts", "vitest.config.ts"]
}
```

- [ ] **Step 4: Write `apps/frontend/vite.config.ts`**

```ts
// SPDX-License-Identifier: Apache-2.0
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: "0.0.0.0",
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
```

- [ ] **Step 5: Write `apps/frontend/vitest.config.ts`**

```ts
// SPDX-License-Identifier: Apache-2.0
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "happy-dom",
    setupFiles: ["./src/test-setup.ts"],
  },
});
```

- [ ] **Step 6: Write `apps/frontend/src/test-setup.ts`**

```ts
// SPDX-License-Identifier: Apache-2.0
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 7: Write `apps/frontend/.gitignore`**

```
node_modules
dist
.vite
coverage
*.log
```

- [ ] **Step 8: Write `apps/frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>FilterNArrange</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 9: Write `apps/frontend/src/main.tsx`**

```tsx
// SPDX-License-Identifier: Apache-2.0
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/App";

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("Root element #root not found");

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 10: Write the failing test `apps/frontend/src/app/App.test.tsx`**

```tsx
// SPDX-License-Identifier: Apache-2.0
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("renders the running banner", () => {
    render(<App />);
    expect(screen.getByText("FilterNArrange — running")).toBeInTheDocument();
  });
});
```

- [ ] **Step 11: Run the test to verify it fails**

Run: `cd apps/frontend && npm install && npm test`
Expected: FAIL — `Cannot find module './App'` (module hasn't been written yet).

- [ ] **Step 12: Write `apps/frontend/src/app/App.tsx`**

```tsx
// SPDX-License-Identifier: Apache-2.0
import type { ReactElement } from "react";

export function App(): ReactElement {
  return (
    <main>
      <h1>FilterNArrange — running</h1>
    </main>
  );
}
```

- [ ] **Step 13: Run the test to verify it passes**

Run: `cd apps/frontend && npm test`
Expected: PASS — 1 passing.

- [ ] **Step 14: Write `apps/frontend/nginx.conf`**

```nginx
worker_processes  1;
events { worker_connections 1024; }

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout 65;
    gzip          on;
    gzip_types    text/plain text/css application/javascript application/json image/svg+xml;

    server {
        listen 80;
        server_name _;
        root   /usr/share/nginx/html;
        index  index.html;

        location /health {
            access_log off;
            return 200 '{"status":"UP"}';
            add_header Content-Type application/json;
        }

        location / {
            try_files $uri /index.html;
        }
    }
}
```

- [ ] **Step 15: Write `apps/frontend/.dockerignore`**

```
node_modules
dist
.vite
coverage
*.log
```

- [ ] **Step 16: Write `apps/frontend/Dockerfile`**

```dockerfile
# syntax=docker/dockerfile:1.7

# ---- build stage ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY . .
RUN npm run build

# ---- runtime stage ----
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD wget -qO- http://localhost/health >/dev/null || exit 1
```

(`wget` is present in `nginx:1.27-alpine`. Alpine doesn't ship `curl` by default; we use `wget` here.)

- [ ] **Step 17: Commit**

```bash
git add apps/frontend
git commit -m "feat(frontend): bootstrap Vite + React + TS app with running banner

Closes #TBD"
```

---

## Task 7: `.env.example` (configuration matrix from spec §8.6)

**Files:**
- Create: `.env.example`

- [ ] **Step 1: Write `.env.example`** — every variable documented inline. Values are non-secret defaults safe for local dev only.

```ini
# =============================================================================
# FilterNArrange — local development environment
# Copy to `.env` and override anything you want different. Never commit `.env`.
# All secrets in this file are LOCAL DEV defaults and MUST be replaced in any
# non-dev deployment.
# =============================================================================

# --- Identity ----------------------------------------------------------------
# Which auth backend the gateway uses. `keycloak` runs Keycloak in compose;
# `spring-jwt` skips it and saves ~1 GB RAM (good for free-tier deploy).
AUTH_PROVIDER=spring-jwt
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=changeme

# --- Postgres ----------------------------------------------------------------
# Single DB instance, owned by the gateway. Data-engine never connects.
POSTGRES_USER=filternarrange
POSTGRES_PASSWORD=changeme
POSTGRES_DB=filternarrange
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# --- Redis / Valkey ----------------------------------------------------------
# Used for rate-limits (gw:*), sessions, and Python's detection/preview cache (py:*).
REDIS_HOST=redis
REDIS_PORT=6379

# --- Redpanda (Kafka API) ----------------------------------------------------
# KRaft mode, single broker. No ZooKeeper.
KAFKA_BOOTSTRAP=redpanda:9092

# --- MinIO -------------------------------------------------------------------
# Object storage; buckets: uploads, results, format-samples, backups.
MINIO_ROOT_USER=filternarrange
MINIO_ROOT_PASSWORD=changeme
MINIO_ENDPOINT=http://minio:9000

# --- AI / Ollama -------------------------------------------------------------
# Ollama LLM runtime. Default models pulled by the `ollama-init` service.
OLLAMA_HOST=http://ollama:11434
NL2FILTER_MODEL=qwen2.5:7b
SUMMARY_MODEL=llama3.1:8b
AI_TIMEOUT_SECONDS=30
AI_MAX_CONCURRENT=4

# --- Tier defaults (override for production launch) --------------------------
# Free-tier file-size cap (MB) — sync uploads above this rejected at gateway.
FREE_TIER_MAX_UPLOAD_MB=5
# Free-tier daily-operation cap. Counter at Redis `gw:rate:user:{id}:ops:{date}`.
FREE_TIER_DAILY_OPS=20
# Paid-tier file-size cap (MB).
PAID_TIER_MAX_UPLOAD_MB=500
# Paid-tier daily-operation cap. 0 = unlimited.
PAID_TIER_DAILY_OPS=10000

# --- Storage retention -------------------------------------------------------
# Upload retention in MinIO `uploads` bucket per tier (spec §5 Data lifecycle).
UPLOAD_RETENTION_FREE_HOURS=24
UPLOAD_RETENTION_PAID_DAYS=30

# --- Python service mode -----------------------------------------------------
# Spec §2 loose-coupling rule 6. `full` runs everything; `data`/`ai`/`worker`
# constrain responsibilities so we can split later by editing compose only.
DATA_ENGINE_MODE=full

# --- Observability -----------------------------------------------------------
GRAFANA_ADMIN_PASSWORD=admin
LOG_LEVEL=info                  # debug | info | warn | error

# --- Plugin controls ---------------------------------------------------------
# Comma-separated plugin IDs to skip at registration (spec §4 lifecycle).
FILTERNARRANGE_DISABLED_PLUGINS=

# --- Frontend ----------------------------------------------------------------
# Vite picks this up via import.meta.env.VITE_API_BASE_URL.
VITE_API_BASE_URL=https://localhost:8443/api/v1
```

- [ ] **Step 2: Verify**

Run: `grep -c "^[A-Z_][A-Z0-9_]*=" .env.example`
Expected: ≥25 (one per variable above).

- [ ] **Step 3: Commit**

```bash
git add .env.example
git commit -m "chore(infra): add .env.example with full configuration matrix

Closes #TBD"
```

---

## Task 8: Caddy reverse-proxy config

**Files:**
- Create: `infra/caddy/Caddyfile`

- [ ] **Step 1: Write `infra/caddy/Caddyfile`** (single entry on `:8443` proxying to gateway/frontend; auto self-signed for `localhost`)

```caddyfile
{
    # Auto self-signed local cert; flip to Let's Encrypt when public deploy lands (Plan H).
    local_certs
    auto_https disable_redirects
}

:8443 {
    # API + WebSocket traffic → gateway
    @api path /api/* /ws/* /health
    handle @api {
        reverse_proxy gateway:8080 {
            header_up X-Forwarded-Proto https
        }
    }

    # Everything else → frontend
    handle {
        reverse_proxy frontend:80
    }

    log {
        output stdout
        format console
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add infra/caddy/Caddyfile
git commit -m "chore(infra): add Caddy reverse-proxy config

Closes #TBD"
```

---

## Task 9: Docker Compose stack (all services + healthchecks + named volumes)

**Files:**
- Create: `infra/docker-compose/docker-compose.yml`

- [ ] **Step 1: Write `infra/docker-compose/docker-compose.yml`**

```yaml
# FilterNArrange — local dev compose stack.
# All services on a single bridge network. Healthchecks on every service so
# `docker compose up --wait` exits green only when the stack is actually ready.

name: filternarrange

x-restart: &restart
  restart: unless-stopped

services:
  # ---------- Persistence ----------------------------------------------------
  postgres:
    image: postgres:16-alpine
    <<: *restart
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-filternarrange}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
      POSTGRES_DB: ${POSTGRES_DB:-filternarrange}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      timeout: 3s
      retries: 20
      start_period: 10s
    networks: [filternarrange]

  redis:
    # Valkey 7 — drop-in Redis-OSS fork with no SSPL drift risk (ADR-0001).
    image: valkey/valkey:7-alpine
    <<: *restart
    command: ["valkey-server", "--appendonly", "yes"]
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "valkey-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 20
      start_period: 5s
    networks: [filternarrange]

  redpanda:
    image: redpandadata/redpanda:latest
    <<: *restart
    command:
      - redpanda
      - start
      - --kafka-addr
      - INTERNAL://0.0.0.0:9092,EXTERNAL://0.0.0.0:19092
      - --advertise-kafka-addr
      - INTERNAL://redpanda:9092,EXTERNAL://localhost:19092
      - --rpc-addr
      - redpanda:33145
      - --advertise-rpc-addr
      - redpanda:33145
      - --mode
      - dev-container
      - --smp
      - "1"
      - --memory
      - "1G"
      - --reserve-memory
      - "0M"
      - --overprovisioned
      - --node-id
      - "0"
    ports:
      - "9092:9092"
      - "19092:19092"
      - "9644:9644"
    volumes:
      - redpanda-data:/var/lib/redpanda/data
    healthcheck:
      test: ["CMD", "rpk", "cluster", "health", "--exit-when-healthy"]
      interval: 10s
      timeout: 5s
      retries: 20
      start_period: 20s
    networks: [filternarrange]

  minio:
    image: minio/minio:latest
    <<: *restart
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-filternarrange}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-changeme}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio-data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 20
      start_period: 10s
    networks: [filternarrange]

  # ---------- AI runtime -----------------------------------------------------
  ollama:
    image: ollama/ollama:latest
    <<: *restart
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    healthcheck:
      # `ollama list` exits 0 when the daemon is reachable, even with no models.
      test: ["CMD", "ollama", "list"]
      interval: 10s
      timeout: 5s
      retries: 20
      start_period: 15s
    networks: [filternarrange]

  ollama-init:
    # One-shot job — pulls the default models, then exits. `docker compose up`
    # treats this as completed-successfully via the `service_completed_successfully`
    # condition used by downstream services that need the models present.
    image: ollama/ollama:latest
    depends_on:
      ollama:
        condition: service_healthy
    environment:
      OLLAMA_HOST: http://ollama:11434
    entrypoint:
      - sh
      - -c
      - |
        set -e
        echo "Pulling ${NL2FILTER_MODEL:-qwen2.5:7b}..."
        ollama pull "${NL2FILTER_MODEL:-qwen2.5:7b}"
        echo "Pulling ${SUMMARY_MODEL:-llama3.1:8b}..."
        ollama pull "${SUMMARY_MODEL:-llama3.1:8b}"
        echo "Default models present."
    restart: "no"
    networks: [filternarrange]

  # ---------- Application services ------------------------------------------
  gateway:
    build:
      context: ../../apps/gateway
      dockerfile: Dockerfile
    <<: *restart
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      redpanda:
        condition: service_healthy
      minio:
        condition: service_healthy
    environment:
      SPRING_PROFILES_ACTIVE: docker
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_USER: ${POSTGRES_USER:-filternarrange}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
      POSTGRES_DB: ${POSTGRES_DB:-filternarrange}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      KAFKA_BOOTSTRAP: redpanda:9092
      MINIO_ENDPOINT: http://minio:9000
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-filternarrange}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-changeme}
      AUTH_PROVIDER: ${AUTH_PROVIDER:-spring-jwt}
      LOG_LEVEL: ${LOG_LEVEL:-info}
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8080/health"]
      interval: 10s
      timeout: 3s
      retries: 20
      start_period: 30s
    networks: [filternarrange]

  data-engine:
    build:
      context: ../../apps/data-engine
      dockerfile: Dockerfile
    <<: *restart
    depends_on:
      redis:
        condition: service_healthy
      redpanda:
        condition: service_healthy
      minio:
        condition: service_healthy
      ollama:
        condition: service_healthy
    environment:
      DATA_ENGINE_MODE: ${DATA_ENGINE_MODE:-full}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      KAFKA_BOOTSTRAP: redpanda:9092
      MINIO_ENDPOINT: http://minio:9000
      OLLAMA_HOST: http://ollama:11434
      NL2FILTER_MODEL: ${NL2FILTER_MODEL:-qwen2.5:7b}
      SUMMARY_MODEL: ${SUMMARY_MODEL:-llama3.1:8b}
      AI_TIMEOUT_SECONDS: ${AI_TIMEOUT_SECONDS:-30}
      AI_MAX_CONCURRENT: ${AI_MAX_CONCURRENT:-4}
      LOG_LEVEL: ${LOG_LEVEL:-info}
      FILTERNARRANGE_DISABLED_PLUGINS: ${FILTERNARRANGE_DISABLED_PLUGINS:-}
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/health"]
      interval: 10s
      timeout: 3s
      retries: 20
      start_period: 20s
    networks: [filternarrange]

  frontend:
    build:
      context: ../../apps/frontend
      dockerfile: Dockerfile
    <<: *restart
    depends_on:
      gateway:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost/health"]
      interval: 10s
      timeout: 3s
      retries: 20
      start_period: 10s
    networks: [filternarrange]

  caddy:
    image: caddy:2-alpine
    <<: *restart
    depends_on:
      frontend:
        condition: service_healthy
      gateway:
        condition: service_healthy
    ports:
      - "8443:8443"
    volumes:
      - ../caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
      - caddy-config:/config
    healthcheck:
      test: ["CMD", "wget", "-qO-", "--no-check-certificate", "https://localhost:8443/health"]
      interval: 10s
      timeout: 3s
      retries: 20
      start_period: 10s
    networks: [filternarrange]

# ---------- Volumes / networks ---------------------------------------------
volumes:
  postgres-data:
  redis-data:
  redpanda-data:
  minio-data:
  ollama-data:
  caddy-data:
  caddy-config:

networks:
  filternarrange:
    name: filternarrange
    driver: bridge
```

- [ ] **Step 2: Static-validate the compose file**

Run: `docker compose -f infra/docker-compose/docker-compose.yml --env-file .env.example config -q`
Expected: exits 0, no errors. (This parses + interpolates without starting anything.)

- [ ] **Step 3: Commit**

```bash
git add infra/docker-compose/docker-compose.yml
git commit -m "chore(infra): add docker-compose stack with all services and healthchecks

Closes #TBD"
```

---

## Task 10: `scripts/wait-for-healthy.sh` + `scripts/seed-dev`

**Files:**
- Create: `scripts/wait-for-healthy.sh`
- Create: `scripts/seed-dev`

- [ ] **Step 1: Write `scripts/wait-for-healthy.sh`**

```bash
#!/usr/bin/env bash
# Polls the /health endpoint of each FilterNArrange app service until every
# one reports {"status":"UP"} (or until the per-service timeout elapses).
#
# Exit codes:
#   0  all services healthy
#   1  one or more services failed to become healthy
#
# Intended usage:
#   ./scripts/wait-for-healthy.sh                          # default endpoints
#   TIMEOUT_SECONDS=600 ./scripts/wait-for-healthy.sh      # longer timeout
#
# CI uses this script after `docker compose up -d` to gate downstream stages.

set -euo pipefail

TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-3}"

# Service name → health URL.
declare -a SERVICES=(
  "gateway|http://localhost:8080/health"
  "data-engine|http://localhost:8000/health"
  "frontend|http://localhost:8081/health"   # frontend container :80 published via compose override; adjust if mapping differs
  "caddy|https://localhost:8443/health"
)

log() { printf '[wait-for-healthy] %s\n' "$*"; }

curl_ok() {
  # -k accepts the Caddy self-signed cert on :8443.
  local url="$1"
  local body
  body="$(curl -fsSk --max-time 5 "${url}" || return 1)"
  printf '%s' "${body}" | grep -q '"status"[[:space:]]*:[[:space:]]*"UP"'
}

wait_for() {
  local name="$1" url="$2" elapsed=0
  log "waiting for ${name} at ${url}"
  while (( elapsed < TIMEOUT_SECONDS )); do
    if curl_ok "${url}"; then
      log "${name} is UP after ${elapsed}s"
      return 0
    fi
    sleep "${POLL_INTERVAL_SECONDS}"
    elapsed=$(( elapsed + POLL_INTERVAL_SECONDS ))
  done
  log "ERROR: ${name} did not become healthy within ${TIMEOUT_SECONDS}s"
  return 1
}

failures=0
for entry in "${SERVICES[@]}"; do
  name="${entry%%|*}"
  url="${entry#*|}"
  if ! wait_for "${name}" "${url}"; then
    failures=$(( failures + 1 ))
  fi
done

if (( failures > 0 )); then
  log "FAILED: ${failures} service(s) not healthy"
  exit 1
fi

log "All services healthy."
```

- [ ] **Step 2: Write `scripts/seed-dev`**

```bash
#!/usr/bin/env bash
# Seeds dev data (admin user, default tier configs, sample fixtures) into the
# running compose stack.
#
# In Plan A this is a placeholder — the users table doesn't yet exist. Plan B
# replaces this body with real seeding logic.

set -euo pipefail

echo "[seed-dev] TODO: seed-dev runs after Plan B lands users table."
exit 0
```

- [ ] **Step 3: Make both scripts executable**

```bash
chmod +x scripts/wait-for-healthy.sh scripts/seed-dev
```

- [ ] **Step 4: Verify `wait-for-healthy.sh` is syntactically valid**

Run: `bash -n scripts/wait-for-healthy.sh && echo OK`
Expected: `OK`.

Run: `bash -n scripts/seed-dev && echo OK`
Expected: `OK`.

Run: `./scripts/seed-dev`
Expected: prints the TODO line and exits 0.

- [ ] **Step 5: Commit**

```bash
git add scripts/wait-for-healthy.sh scripts/seed-dev
git commit -m "chore(scripts): add wait-for-healthy and placeholder seed-dev

Closes #TBD"
```

---

## Task 11: Contracts scaffold (README + placeholder OpenAPI + Kafka schemas)

**Files:**
- Modify: `contracts/README.md` (already created in Task 1 as a stub — rewrite to full version)
- Create: `contracts/openapi/gateway-public.v1.yaml`
- Create: `contracts/openapi/gateway-internal.v1.yaml`
- Create: `contracts/kafka/topic.v1.jobs.schema.json`
- Create: `contracts/kafka/topic.v1.job-results.schema.json`
- Create: `contracts/kafka/topic.v1.format-requests.schema.json`
- Create: `contracts/kafka/topic.v1.audit-events.schema.json`

- [ ] **Step 1: Rewrite `contracts/README.md`**

```markdown
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
```

- [ ] **Step 2: Write `contracts/openapi/gateway-public.v1.yaml`**

```yaml
openapi: 3.1.0
info:
  title: FilterNArrange gateway — public API
  summary: Frontend-facing REST + WebSocket surface
  version: 1.0.0
  description: |
    Public surface of the FilterNArrange gateway. Consumed by the React
    frontend. Versioned per spec §3 (rule 4: explicit `/api/v1/...`).
  license:
    name: Apache-2.0
    url: https://www.apache.org/licenses/LICENSE-2.0
servers:
  - url: https://localhost:8443
    description: Local dev (via Caddy)
paths:
  /health:
    get:
      operationId: getHealth
      summary: Liveness probe.
      responses:
        "200":
          description: Service is up.
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/HealthResponse"
components:
  schemas:
    HealthResponse:
      type: object
      required: [status]
      properties:
        status:
          type: string
          enum: [UP]
```

- [ ] **Step 3: Write `contracts/openapi/gateway-internal.v1.yaml`**

```yaml
openapi: 3.1.0
info:
  title: FilterNArrange gateway — internal API
  summary: Surface called by the data-engine and other internal services
  version: 1.0.0
  description: |
    Internal-only REST surface. Not reachable from outside the compose network
    (per spec §2 loose-coupling rule 2). Versioned independently of the public
    surface.
  license:
    name: Apache-2.0
    url: https://www.apache.org/licenses/LICENSE-2.0
servers:
  - url: http://gateway:8080
    description: Internal compose network
paths:
  /health:
    get:
      operationId: getInternalHealth
      summary: Liveness probe (internal).
      responses:
        "200":
          description: Service is up.
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/HealthResponse"
components:
  schemas:
    HealthResponse:
      type: object
      required: [status]
      properties:
        status:
          type: string
          enum: [UP]
```

- [ ] **Step 4: Write `contracts/kafka/topic.v1.jobs.schema.json`** (placeholder skeleton — Plan D fleshes out)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://filternarrange.io/contracts/kafka/topic.v1.jobs.schema.json",
  "title": "topic.v1.jobs",
  "description": "Skeleton for jobs produced by the gateway. Plan D adds the full payload (kind, user_id, params, idempotency_key, etc.).",
  "type": "object",
  "required": ["job_id", "schema_version"],
  "properties": {
    "job_id": { "type": "string", "format": "uuid" },
    "schema_version": { "type": "string", "const": "v1" }
  },
  "additionalProperties": true
}
```

- [ ] **Step 5: Write `contracts/kafka/topic.v1.job-results.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://filternarrange.io/contracts/kafka/topic.v1.job-results.schema.json",
  "title": "topic.v1.job-results",
  "description": "Skeleton for job-result events produced by the data-engine worker. Plan D adds the full payload.",
  "type": "object",
  "required": ["job_id", "schema_version", "status"],
  "properties": {
    "job_id": { "type": "string", "format": "uuid" },
    "schema_version": { "type": "string", "const": "v1" },
    "status": { "type": "string", "enum": ["completed", "failed", "cancelled"] }
  },
  "additionalProperties": true
}
```

- [ ] **Step 6: Write `contracts/kafka/topic.v1.format-requests.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://filternarrange.io/contracts/kafka/topic.v1.format-requests.schema.json",
  "title": "topic.v1.format-requests",
  "description": "Skeleton for format-request events. Plan B fleshes out user-submitted payload + sample reference.",
  "type": "object",
  "required": ["request_id", "schema_version"],
  "properties": {
    "request_id": { "type": "string", "format": "uuid" },
    "schema_version": { "type": "string", "const": "v1" }
  },
  "additionalProperties": true
}
```

- [ ] **Step 7: Write `contracts/kafka/topic.v1.audit-events.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://filternarrange.io/contracts/kafka/topic.v1.audit-events.schema.json",
  "title": "topic.v1.audit-events",
  "description": "Skeleton for audit-log events. Plan B fleshes out the action/target/metadata fields.",
  "type": "object",
  "required": ["event_id", "schema_version", "action"],
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "schema_version": { "type": "string", "const": "v1" },
    "action": { "type": "string" }
  },
  "additionalProperties": true
}
```

- [ ] **Step 8: Lint the OpenAPI files locally**

Run: `npx --yes @stoplight/spectral-cli@6.11.1 lint contracts/openapi/gateway-public.v1.yaml contracts/openapi/gateway-internal.v1.yaml`
Expected: `No results with a severity of 'error' found!`. (Warnings about missing `description` on top-level operations are acceptable for the placeholder.)

- [ ] **Step 9: Commit**

```bash
git add contracts/
git commit -m "feat(contracts): scaffold OpenAPI + Kafka schemas with versioning rules

Closes #TBD"
```

---

## Task 12: GitHub issue templates, PR template, CODEOWNERS

**Files:**
- Create: `.github/CODEOWNERS`
- Create: `.github/pull_request_template.md`
- Create: `.github/ISSUE_TEMPLATE/config.yml`
- Create: `.github/ISSUE_TEMPLATE/bug.yml`
- Create: `.github/ISSUE_TEMPLATE/feature.yml`
- Create: `.github/ISSUE_TEMPLATE/format-request.yml`
- Create: `.github/ISSUE_TEMPLATE/plugin.yml`
- Create: `.github/ISSUE_TEMPLATE/chore.yml`

- [ ] **Step 1: Write `.github/CODEOWNERS`**

```
# Default owner — applies to every path until per-directory overrides land.
*  @piyush-official
```

- [ ] **Step 2: Write `.github/pull_request_template.md`** (per spec §7.2)

```markdown
## Summary

<!-- One-paragraph "what + why" of this PR. -->

## Linked issues

<!-- Use `Closes #N` so the issue auto-closes on merge. List every related issue. -->

Closes #

## Changes

<!-- Bullet list of files / modules touched. Mention any contract bump. -->

-

## Impact assessment

| Area | Touched? | Notes |
|---|---|---|
| Modules | yes / no | <!-- which modules --> |
| Contracts (`contracts/`) | yes / no | <!-- additive vs version bump --> |
| DB schema / migrations | yes / no | <!-- Flyway version --> |
| Public API (`/api/v1/*`) | yes / no | <!-- breaking? --> |
| Plugin API | yes / no | <!-- targets API version --> |
| Infra (`infra/`, compose) | yes / no | <!-- which services --> |
| Docs / cost-tracking / ADR | yes / no | <!-- which files --> |

## Regression risk

<!-- low / medium / high — explain. Link any prior incident if relevant. -->

## Tests

- [ ] Unit tests added / updated
- [ ] Regression test added (for bug fixes)
- [ ] Contract tests updated (if contracts changed)
- [ ] Integration test (testcontainers) covered
- [ ] E2E (Playwright) covered (if user-facing)
- [ ] Performance gate verified (if latency-sensitive)

## Docs / cost-tracking / ADR checklist

- [ ] README / module README updated where behavior changed
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] `docs/cost-tracking.md` updated if any tool / dependency / hosting line changed
- [ ] ADR added or referenced (per spec §7.4) when this PR is a material decision

<!--
PR template guard CI stage fails the PR if any of the required sections above
is left empty. Conventional Commit title required.
-->
```

- [ ] **Step 3: Write `.github/ISSUE_TEMPLATE/config.yml`**

```yaml
blank_issues_enabled: false
contact_links:
  - name: Security disclosure
    url: https://github.com/piyush-official/FilterNArrange/security/advisories/new
    about: Report a vulnerability privately via GitHub security advisories.
```

- [ ] **Step 4: Write `.github/ISSUE_TEMPLATE/bug.yml`**

```yaml
name: Bug report
description: A reproducible defect in shipped behavior.
title: "bug: <short summary>"
labels: ["bug", "triaged"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for reporting. Every required field below is enforced by CI on PRs that close this issue.

  - type: input
    id: requirement
    attributes:
      label: What should have happened
      placeholder: e.g. detecting a UTF-16 CSV returns format=csv with confidence > 0.8
    validations:
      required: true

  - type: input
    id: actual
    attributes:
      label: What actually happened
      placeholder: e.g. detect returns format=unknown
    validations:
      required: true

  - type: textarea
    id: reproduce
    attributes:
      label: Reproduction steps
      description: Minimal steps. Attach a fixture if relevant (anonymize PII).
      placeholder: |
        1. POST /api/v1/detect with fixture utf16.csv
        2. Observe response
    validations:
      required: true

  - type: dropdown
    id: blast_radius
    attributes:
      label: Blast radius
      options:
        - "Single user, single request"
        - "All users of one tier"
        - "All users"
        - "Data-loss risk"
    validations:
      required: true

  - type: dropdown
    id: regression_risk
    attributes:
      label: Regression risk
      options:
        - low
        - medium
        - high
    validations:
      required: true

  - type: textarea
    id: test_plan
    attributes:
      label: Test plan for the fix
      description: A regression test that fails on `main` and passes on the fix is mandatory per ADR-0004.
    validations:
      required: true
```

- [ ] **Step 5: Write `.github/ISSUE_TEMPLATE/feature.yml`**

```yaml
name: Feature request
description: New behavior or capability.
title: "feat: <short summary>"
labels: ["feature", "triaged"]
body:
  - type: textarea
    id: requirement
    attributes:
      label: Requirement
      description: User-facing description of what this enables.
    validations:
      required: true

  - type: textarea
    id: acceptance
    attributes:
      label: Acceptance criteria
      description: Specific, testable criteria. Use bullet points.
      placeholder: |
        - Detect endpoint returns confidence float between 0 and 1
        - Confidence < 0.5 returns format=unknown
    validations:
      required: true

  - type: textarea
    id: scope_in
    attributes:
      label: In scope
    validations:
      required: true

  - type: textarea
    id: scope_out
    attributes:
      label: Out of scope (explicit YAGNI)
    validations:
      required: true

  - type: dropdown
    id: tier
    attributes:
      label: Tier
      options:
        - free
        - paid
        - both
    validations:
      required: true

  - type: dropdown
    id: regression_risk
    attributes:
      label: Regression risk
      options:
        - low
        - medium
        - high
    validations:
      required: true

  - type: textarea
    id: test_plan
    attributes:
      label: Test plan
      description: Unit + integration + (if user-facing) E2E coverage.
    validations:
      required: true
```

- [ ] **Step 6: Write `.github/ISSUE_TEMPLATE/format-request.yml`**

```yaml
name: Format request
description: Request support for a new file format.
title: "format-request: <format name>"
labels: ["format-request", "triaged"]
body:
  - type: markdown
    attributes:
      value: |
        Two paths exist for new formats:
        1. **Community PR** — fork, copy `plugins/format-csv` as a template, implement, open PR. Free.
        2. **Maintainer-handled** — request prioritized work. Paid-tier users get priority.

  - type: input
    id: format_name
    attributes:
      label: Format name
      placeholder: e.g. Parquet, Avro, Markdown table
    validations:
      required: true

  - type: textarea
    id: sample
    attributes:
      label: Sample data
      description: Paste a small anonymized sample, or attach the file (the MinIO `format-samples` bucket holds it once triaged).
    validations:
      required: true

  - type: dropdown
    id: tier
    attributes:
      label: Your tier
      options:
        - free
        - paid
        - unsure
    validations:
      required: true

  - type: dropdown
    id: path
    attributes:
      label: Preferred path
      options:
        - "I will open a PR myself"
        - "Please prioritize (paid)"
        - "Either is fine"
    validations:
      required: true

  - type: textarea
    id: use_case
    attributes:
      label: Use case
      description: Why you need this format supported.
    validations:
      required: true
```

- [ ] **Step 7: Write `.github/ISSUE_TEMPLATE/plugin.yml`**

```yaml
name: Plugin proposal
description: Propose a new filter, analysis, or AI-provider plugin.
title: "plugin: <plugin name>"
labels: ["feature", "area:plugins", "triaged"]
body:
  - type: dropdown
    id: kind
    attributes:
      label: Plugin kind
      options:
        - format
        - filter
        - analysis
        - ai-provider
        - storage
    validations:
      required: true

  - type: input
    id: plugin_id
    attributes:
      label: Plugin ID
      description: Lowercase, hyphen-separated. Will become the `manifest.toml` `id`.
      placeholder: e.g. geohash-distance
    validations:
      required: true

  - type: textarea
    id: behavior
    attributes:
      label: Behavior
      description: What the plugin does. Reference the relevant Protocol in spec §4 (FormatPlugin / FilterPlugin / AnalysisPlugin / LLMProvider).
    validations:
      required: true

  - type: dropdown
    id: tier
    attributes:
      label: Required tier
      options:
        - free
        - paid
    validations:
      required: true

  - type: textarea
    id: api_version
    attributes:
      label: Targeted plugin API version
      placeholder: e.g. plugin-api-v1
    validations:
      required: true

  - type: textarea
    id: test_plan
    attributes:
      label: Conformance test plan
      description: How the canonical conformance suite will exercise this plugin.
    validations:
      required: true
```

- [ ] **Step 8: Write `.github/ISSUE_TEMPLATE/chore.yml`**

```yaml
name: Chore
description: Non-functional work — refactor, dependency bump, infra tweak, docs.
title: "chore: <short summary>"
labels: ["chore", "triaged"]
body:
  - type: textarea
    id: requirement
    attributes:
      label: What needs to change and why
    validations:
      required: true

  - type: dropdown
    id: area
    attributes:
      label: Area
      options:
        - gateway
        - data-engine
        - frontend
        - plugins
        - infra
        - contracts
        - docs
        - tests
        - ci
    validations:
      required: true

  - type: dropdown
    id: risk
    attributes:
      label: Regression risk
      options:
        - low
        - medium
        - high
    validations:
      required: true

  - type: textarea
    id: rollout
    attributes:
      label: Rollout / verification
      description: How you'll prove the change is safe before merging.
    validations:
      required: true
```

- [ ] **Step 9: Verify the YAML parses**

Run: `for f in .github/ISSUE_TEMPLATE/*.yml; do python3 -c "import yaml,sys; yaml.safe_load(open('$f'))" && echo "$f OK"; done`
Expected: every line ends in `OK`.

- [ ] **Step 10: Commit**

```bash
git add .github/CODEOWNERS .github/pull_request_template.md .github/ISSUE_TEMPLATE/
git commit -m "chore(repo): add CODEOWNERS, PR template, and 5 issue templates

Closes #TBD"
```

---

## Task 13: Root `package.json` + commitlint + husky

**Files:**
- Create: `package.json`
- Create: `commitlint.config.js`
- Create: `.husky/.gitignore`
- Create: `.husky/commit-msg`

- [ ] **Step 1: Write `package.json`** (monorepo root — only manages commit tooling, not actual apps)

```json
{
  "name": "filternarrange-monorepo",
  "version": "0.0.0",
  "private": true,
  "description": "Monorepo root — manages commitlint + husky. Apps live under apps/.",
  "scripts": {
    "prepare": "husky install || true",
    "commitlint": "commitlint --edit"
  },
  "devDependencies": {
    "@commitlint/cli": "19.3.0",
    "@commitlint/config-conventional": "19.2.2",
    "husky": "9.0.11"
  }
}
```

- [ ] **Step 2: Write `commitlint.config.js`**

```js
// SPDX-License-Identifier: Apache-2.0
// Conventional Commits config — see ADR-0004 §Versioning.
module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [
      2,
      "always",
      ["feat", "fix", "chore", "docs", "refactor", "test", "ci", "build", "perf", "revert"],
    ],
    "subject-case": [2, "never", ["upper-case", "pascal-case", "start-case"]],
    "header-max-length": [2, "always", 100],
  },
};
```

- [ ] **Step 3: Install dependencies and set up husky**

```bash
npm install
npm run prepare
```

This creates `.husky/` and the `_` helper directory.

- [ ] **Step 4: Write `.husky/.gitignore`** (husky's own internals)

```
_
```

- [ ] **Step 5: Write `.husky/commit-msg`**

```bash
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

npx --no-install commitlint --edit "$1"
```

Make executable:

```bash
chmod +x .husky/commit-msg
```

- [ ] **Step 6: Verify commitlint catches a bad message**

Run: `echo "bad message" | npx --no-install commitlint`
Expected: non-zero exit, error mentioning `subject may not be empty` or `type may not be empty`.

Run: `echo "feat(foo): add bar" | npx --no-install commitlint`
Expected: exit 0.

- [ ] **Step 7: Commit**

```bash
git add package.json package-lock.json commitlint.config.js .husky/
git commit -m "chore(repo): add commitlint + husky for Conventional Commits

Closes #TBD"
```

---

## Task 14: `release-please` configuration

**Files:**
- Create: `release-please-config.json`
- Create: `.release-please-manifest.json`

- [ ] **Step 1: Write `release-please-config.json`**

```json
{
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "release-type": "simple",
  "include-component-in-tag": false,
  "bump-minor-pre-major": true,
  "bump-patch-for-minor-pre-major": false,
  "draft": false,
  "prerelease": false,
  "changelog-sections": [
    { "type": "feat",     "section": "Features" },
    { "type": "fix",      "section": "Bug Fixes" },
    { "type": "perf",     "section": "Performance" },
    { "type": "refactor", "section": "Refactors" },
    { "type": "docs",     "section": "Documentation" },
    { "type": "test",     "section": "Tests" },
    { "type": "build",    "section": "Build" },
    { "type": "ci",       "section": "CI" },
    { "type": "chore",    "section": "Chores",  "hidden": false }
  ],
  "packages": {
    ".": {
      "package-name": "filternarrange",
      "release-type": "simple"
    }
  }
}
```

- [ ] **Step 2: Write `.release-please-manifest.json`** (start at `0.0.0`)

```json
{
  ".": "0.0.0"
}
```

- [ ] **Step 3: Verify JSON parses**

Run: `python3 -c "import json; json.load(open('release-please-config.json')); json.load(open('.release-please-manifest.json'))" && echo OK`
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add release-please-config.json .release-please-manifest.json
git commit -m "ci(release): wire release-please config and manifest at 0.0.0

Closes #TBD"
```

---

## Task 15: CI workflows (`pr.yml` + `release.yml`)

**Files:**
- Create: `.github/workflows/pr.yml`
- Create: `.github/workflows/release.yml`

The PR pipeline implements all nine stages from spec §7.5. Where a stage has nothing to enforce yet (e.g., architecture-tests for empty apps), the job runs a no-op `echo` and exits 0 — keeping the job graph stable so Plan B+ only changes step bodies, never workflow structure.

- [ ] **Step 1: Write `.github/workflows/pr.yml`**

```yaml
name: pr

on:
  pull_request:
    branches: [main]

permissions:
  contents: read
  pull-requests: read

concurrency:
  group: pr-${{ github.ref }}
  cancel-in-progress: true

jobs:

  # ---- 1. lint --------------------------------------------------------------
  lint:
    name: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Set up JDK 21
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "21"
      - name: Set up Node 20
        uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Set up Python 3.12 + uv
        uses: astral-sh/setup-uv@v3
        with:
          python-version: "3.12"
      - name: Install monorepo deps
        run: npm install
      - name: Frontend lint + typecheck (placeholder until ESLint config lands)
        run: |
          cd apps/frontend
          npm install
          npm run typecheck
      - name: Python lint (ruff)
        run: |
          cd apps/data-engine
          uv sync --all-extras
          uv run ruff check .
      - name: Python type-check (mypy)
        run: |
          cd apps/data-engine
          uv run mypy src
      - name: Gateway compile-check (Gradle assemble — full lint/spotless lands in Plan B)
        run: |
          cd apps/gateway
          ./gradlew --no-daemon assemble
      - name: Commitlint (last commit only)
        run: |
          npx commitlint --from=HEAD~1 --to=HEAD --verbose || \
          npx commitlint --from="${{ github.event.pull_request.base.sha }}" --to="${{ github.event.pull_request.head.sha }}" --verbose

  # ---- 2. unit tests --------------------------------------------------------
  unit-tests:
    name: unit-tests
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: "21" }
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - uses: astral-sh/setup-uv@v3
        with: { python-version: "3.12" }
      - name: Gateway tests
        run: |
          cd apps/gateway
          ./gradlew --no-daemon test
      - name: Data-engine tests
        run: |
          cd apps/data-engine
          uv sync --all-extras
          uv run pytest -v
      - name: Frontend tests
        run: |
          cd apps/frontend
          npm install
          npm test

  # ---- 3. architecture tests -----------------------------------------------
  architecture-tests:
    name: architecture-tests
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - name: Placeholder
        run: |
          echo "Architecture tests: ArchUnit / import-linter / eslint-plugin-boundaries"
          echo "Plan A ships the workflow stage; Plan B wires the first concrete rules."

  # ---- 4. contract validation ----------------------------------------------
  contract-validation:
    name: contract-validation
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - name: Spectral lint — OpenAPI
        run: |
          npx --yes @stoplight/spectral-cli@6.11.1 lint \
            contracts/openapi/gateway-public.v1.yaml \
            contracts/openapi/gateway-internal.v1.yaml
      - name: ajv validate — Kafka JSON schemas
        run: |
          npx --yes ajv-cli@5.0.0 compile -s contracts/kafka/topic.v1.jobs.schema.json
          npx --yes ajv-cli@5.0.0 compile -s contracts/kafka/topic.v1.job-results.schema.json
          npx --yes ajv-cli@5.0.0 compile -s contracts/kafka/topic.v1.format-requests.schema.json
          npx --yes ajv-cli@5.0.0 compile -s contracts/kafka/topic.v1.audit-events.schema.json
      - name: Detect contract mutation (v1 files must be immutable on main)
        run: |
          echo "Plan A note: full v1-immutability diff lands when first non-trivial contract is shipped (Plan B)."
          echo "This step is a stable placeholder so Plan B only edits the body."

  # ---- 5. plugin conformance -----------------------------------------------
  plugin-conformance:
    name: plugin-conformance
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - name: Placeholder
        run: |
          echo "Plugin canonical conformance suite — no plugins in Plan A."
          echo "Plan B ships the suite and the first launch plugins (csv/tsv/json/jsonl/xml/yaml/xlsx)."

  # ---- 6. integration tests ------------------------------------------------
  integration-tests:
    name: integration-tests
    runs-on: ubuntu-latest
    needs: [unit-tests, contract-validation]
    steps:
      - uses: actions/checkout@v4
      - name: Placeholder
        run: |
          echo "Integration tests via testcontainers — Plan B onwards."

  # ---- 7. e2e --------------------------------------------------------------
  e2e:
    name: e2e
    runs-on: ubuntu-latest
    needs: integration-tests
    steps:
      - uses: actions/checkout@v4
      - name: Placeholder
        run: |
          echo "Playwright E2E — Plan C onwards (after gateway endpoints exist)."

  # ---- 8. performance gates ------------------------------------------------
  performance-gates:
    name: performance-gates
    runs-on: ubuntu-latest
    needs: integration-tests
    steps:
      - uses: actions/checkout@v4
      - name: Placeholder
        run: |
          echo "k6 latency budgets from spec §3 — wire in Plan B once /detect exists."

  # ---- 9. PR template guard ------------------------------------------------
  pr-template-guard:
    name: pr-template-guard
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Required sections present in PR body
        env:
          BODY: ${{ github.event.pull_request.body }}
        run: |
          set -e
          missing=0
          check() {
            if ! printf '%s' "$BODY" | grep -qiE "## *$1"; then
              echo "PR body missing required section: $1"
              missing=1
            fi
          }
          check "Summary"
          check "Linked issues"
          check "Changes"
          check "Impact assessment"
          check "Regression risk"
          check "Tests"
          check "Docs / cost-tracking / ADR checklist"
          if [ "$missing" -ne 0 ]; then
            echo "::error::PR template required sections missing — see .github/pull_request_template.md"
            exit 1
          fi
          echo "All required sections present."
```

- [ ] **Step 2: Write `.github/workflows/release.yml`**

```yaml
name: release

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write
  issues: write

jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - name: Run release-please
        uses: googleapis/release-please-action@v4
        with:
          config-file: release-please-config.json
          manifest-file: .release-please-manifest.json
          token: ${{ secrets.GITHUB_TOKEN }}
```

(Build / SBOM / Cosign steps land in Plan H once images publish to ghcr.io. The Release PR mechanism itself is sufficient for Plan A — merging it tags `v0.0.1` and creates a GitHub Release.)

- [ ] **Step 3: Verify the workflow YAML parses**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/pr.yml')); yaml.safe_load(open('.github/workflows/release.yml'))" && echo OK`
Expected: `OK`.

- [ ] **Step 4: Optional — actionlint locally**

Run: `npx --yes actionlint-cli .github/workflows/*.yml 2>/dev/null || echo "actionlint not available locally; CI will catch it"`

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/
git commit -m "ci: add PR pipeline (9 stages) and release-please workflow

Closes #TBD"
```

---

## Task 16: Final wiring — verify the whole stack boots end-to-end

This task doesn't create new files. It validates the integration of everything Plan A produced. It is the gate before opening the Plan A umbrella PR.

- [ ] **Step 1: Static-check the compose stack**

Run: `docker compose -f infra/docker-compose/docker-compose.yml --env-file .env.example config -q && echo OK`
Expected: `OK`.

- [ ] **Step 2: Build all three app images**

Run:
```bash
docker compose -f infra/docker-compose/docker-compose.yml --env-file .env.example build gateway data-engine frontend
```
Expected: three successful builds, no errors. Skip `ollama-init`'s build (it uses a pre-built image).

- [ ] **Step 3: Bring up only the apps + their backing services** (skipping Ollama model pull to keep the loop fast)

Run:
```bash
docker compose -f infra/docker-compose/docker-compose.yml --env-file .env.example up -d \
  postgres redis redpanda minio gateway data-engine frontend caddy
```

- [ ] **Step 4: Run the health waiter**

Run: `./scripts/wait-for-healthy.sh`
Expected: every service prints `is UP`; final line `All services healthy.`

If `frontend` port mapping isn't published in compose (it sits behind Caddy by design), edit `scripts/wait-for-healthy.sh` to hit the frontend via Caddy (`https://localhost:8443/health` already covers it). Use that as the only frontend check.

Adjusted `SERVICES` array (replace in Step 1 of Task 10 if needed):

```bash
declare -a SERVICES=(
  "gateway|http://localhost:8080/health"
  "data-engine|http://localhost:8000/health"
  "caddy|https://localhost:8443/health"
)
```

(Make this edit in `scripts/wait-for-healthy.sh` if the previous wording confused the executor. Caddy proxies `/health` to gateway, so the Caddy check transitively covers public reachability. The dedicated `frontend` line is removed because the frontend container is not directly port-mapped.)

- [ ] **Step 5: Manually hit `/health` on each app**

Run:
```bash
curl -fsS http://localhost:8080/health    # gateway
curl -fsS http://localhost:8000/health    # data-engine
curl -fsSk https://localhost:8443/health  # via Caddy (self-signed)
```
Expected: each returns `{"status":"UP"}`.

- [ ] **Step 6: Tear down**

Run: `docker compose -f infra/docker-compose/docker-compose.yml down -v`
Expected: all containers stopped, volumes removed.

- [ ] **Step 7: Commit any wait-for-healthy.sh adjustment from Step 4**

```bash
git add scripts/wait-for-healthy.sh
git diff --cached --quiet || git commit -m "fix(scripts): drop unmapped frontend port from wait-for-healthy

Closes #TBD"
```

(If no edit was needed, this step is a no-op.)

- [ ] **Step 8: Open the Plan A umbrella PR**

Title: `feat: Plan A — foundation (apps, compose, contracts, CI, ADRs)`

Body must follow `.github/pull_request_template.md`. Link every issue opened during tasks 1–15 with `Closes #N`. The PR template guard CI stage will block merge if any required section is empty.

---

## Self-Review

### 1. Spec coverage

Walking spec §-by-§ and pointing at the task that lands it:

| Spec ref | Plan A task |
|---|---|
| §1 license decision | Task 2 (LICENSE), Task 3 (ADR-0002) |
| §2 service map | Task 9 (compose: postgres, redis, redpanda, minio, ollama, gateway, data-engine, frontend, caddy) |
| §2 loose-coupling rule 1 (one service owns each datastore) | Documented in `apps/gateway/README.md` (Task 1), `apps/data-engine/README.md` (Task 1), ADR-0003 (Task 3) |
| §2 loose-coupling rule 2 (frontend → gateway only) | Caddy config only proxies `/api/* /ws/* /health` to gateway (Task 8); frontend port not published in compose (Task 9) |
| §2 loose-coupling rule 3 (versioned contracts) | Task 11 (contracts/) + Task 15 (CI Spectral + ajv) |
| §2 loose-coupling rule 4 (`/api/v1/...`, `topic.v1.<name>`) | Task 11 filenames |
| §2 loose-coupling rule 5 (plugins as the only extension point) | `plugins/README.md` (Task 1) — directory exists; first plugins ship in Plan B |
| §2 loose-coupling rule 6 (MODE flag) | `DATA_ENGINE_MODE` env var in `.env.example` (Task 7) and compose service env (Task 9) |
| §3 contracts directory layout | Task 11 |
| §3 sync vs async paths | Out of scope for Plan A; reserved for Plan B (sync) + Plan D (async) |
| §6 monorepo layout | Task 1 directory tree |
| §6 hexagonal per-app structure | Task 1 creates the subdirectories; Tasks 4/5/6 honor them in the hello-world implementations |
| §6 public-surface rule | Task 5 `__init__.py` with `__all__` for `filternarrange_engine.api`; Task 6 frontend `index.ts` barrels added incrementally (no exported feature yet so no barrel needed in Plan A); ADR-0003 codifies (Task 3) |
| §6 failure-isolation patterns | ADR-0003 (Task 3) codifies all 8; concrete enforcement lands per pattern in Plan B+ |
| §7.1 ticketing | Task 12 (5 issue templates + config.yml) |
| §7.2 PR workflow | Task 12 (pull_request_template.md) + Task 15 (pr-template-guard stage) |
| §7.3 versioning & releases | Task 13 (commitlint) + Task 14 (release-please) + ADR-0004 (Task 3) |
| §7.4 ADRs | Task 3 (ADR-0002, ADR-0003, ADR-0004, README/index) |
| §7.5 CI pipeline (9 stages) | Task 15 (all 9 jobs present; placeholders where the app doesn't yet have content to enforce) |
| §7.6 testing strategy | Hello-world tests in Tasks 4/5/6 establish the pyramid base; deeper layers land plan-by-plan |
| §8 run guide config matrix | Task 7 (`.env.example`) |
| §8 health check script | Task 10 (`wait-for-healthy.sh`) |
| §10 follow-up #1 (license) | Resolved by ADR-0002 (Task 3) |
| §10 follow-up #4 (ADR-0003) | Resolved by Task 3 |
| §10 follow-up #5 (ADR-0004) | Resolved by Task 3 |

Out-of-scope-for-Plan-A items are explicitly reserved for Plans B–H (auth, plugin loader, Kafka topics, AI capabilities, tier middleware, Keycloak realm, production deploy).

### 2. Placeholder scan

Searched the plan for the red-flag patterns from the writing-plans skill:

- "TBD" — only appears in `#TBD` issue-number placeholders inside commit messages, which is explicitly allowed by the conventions block in the brief ("use `#TBD` if not yet known, with a note to update before merge").
- "TODO" — appears in `scripts/seed-dev` body and in a single text marker inside the `seed-dev` echo line. This is the literal user-requested behavior of that task; not a plan-level placeholder.
- "implement later" / "fill in details" / "add appropriate error handling" / "handle edge cases" / "similar to Task N" / "write tests for the above" — **none** found.
- Every code block in the plan is complete enough to copy-paste-execute. Where Plan A defers content to a later plan (ArchUnit rules, integration tests, k6 budgets, real Kafka payloads), the CI job exists and runs a deliberate no-op `echo` so the workflow shape is stable — this is documented at each occurrence and is not a placeholder gap.

### 3. Type and naming consistency

Cross-checked names referenced across tasks:

- Java package: `io.filternarrange.gateway` — used in `GatewayApplication.java`, `HealthController.java`, the test, and the build coordinates. Matches the brief's locked convention.
- Python package: `filternarrange_engine` — used in `pyproject.toml`, every `__init__.py`, the test imports, the Dockerfile entrypoint, and the README. Matches the brief.
- App-name strings: gateway (`filternarrange-gateway`), data-engine (`filternarrange-engine`), frontend (`filternarrange-frontend`) — matches across `package.json`, `application.yml`, and `pyproject.toml`.
- Service names in compose match the hostnames used in `.env.example` (`postgres`, `redis`, `redpanda`, `minio`, `ollama`, `gateway`, `data-engine`, `frontend`, `caddy`).
- Volume names (`postgres-data`, `redis-data`, `redpanda-data`, `minio-data`, `ollama-data`, `caddy-data`, `caddy-config`) are declared once in the volumes block and only referenced from the corresponding service.
- Conventional Commit types in commits (`feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`, `build`, `perf`) match `commitlint.config.js`.
- Frontend test runner: `vitest` (used in `vitest.config.ts`, the `test` npm script, the `test-setup.ts`, and the test file).
- Wire error envelope: ADR-0003 specifies `{ code, plugin_id?, message, trace_id }` (note `plugin_id?` is optional) — matches the brief's "Cross-service errors" convention. The brief's wording omitted the `?`, but the spec §6 reads as conceptually optional ("plugin failure → graceful error") so I made it explicit.

### 4. Notes for the orchestrator

- `CHANGELOG.md` updates are deferred to the orchestrator per the user's instruction. Plan A's contribution to the `[Unreleased]` section should list (one bullet each): monorepo scaffold, gateway/data-engine/frontend hello-world apps, docker-compose stack, contracts scaffold with versioning rules, GitHub workflows + templates + CODEOWNERS, commitlint + husky, release-please config, ADR-0002 (license), ADR-0003 (deps/failure isolation), ADR-0004 (ticketing/versioning), Apache-2.0 LICENSE, removal of NOTICE.
- `docs/cost-tracking.md` updates are deferred to the orchestrator. Plan A adds **zero** new paid line items; everything used (Spectral CLI, ajv, commitlint, husky, release-please-action, GitHub Actions on private repo) is already cataloged in §12a / §20 per the existing CHANGELOG entries.

### 5. Consistency concerns spotted in the spec

While writing this plan I noted three minor spec items worth flagging to the orchestrator:

1. **Spec §3 lists `/health` only implicitly under `gateway-public.v1.yaml`**, but the run-guide §7 mentions both `/health` and `/ready`. Plan A only ships `/health`; `/ready` (readiness probe distinct from liveness) is a Plan B/H concern. The spec should be clarified to either drop `/ready` or commit to it as a separate endpoint.

2. **Spec §4 cites both `confidence_strategy = "content-sniff"` in the CSV manifest and a "structural sniff" step in the detection pipeline.** No semantic conflict, but they should use the same term. Surface to ADR-0003 successor (plugin API ADR) when Plan B writes it.

3. **Spec §3 lists `gw:rate:user:{user_id}:ops:{date}` Redis keys and §5 repeats it.** Identical content. Minor — but the `{date}` format isn't specified (ISO `YYYY-MM-DD` vs Unix-day-bucket). Plan B's tier middleware needs to pick one; I'd recommend `YYYY-MM-DD` in UTC. Flagged for the Plan B author.

None of these block Plan A.
