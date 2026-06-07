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
