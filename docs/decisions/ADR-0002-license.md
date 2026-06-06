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
