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
