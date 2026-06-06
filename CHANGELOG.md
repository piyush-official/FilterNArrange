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
