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
