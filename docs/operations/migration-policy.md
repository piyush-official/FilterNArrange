# DB migration policy

Plan G §T22 — how we change the Postgres schema without breaking running
clients. Read this before opening any PR that adds, removes, or alters a
column / table / index.

## Pattern: expand-contract

Every schema change is staged into TWO migrations across TWO releases:

1. **Expand** — add the new thing as optional. Old code keeps working
   because nothing requires it yet. Backfill in a follow-up that doesn't
   block traffic (background job or maintenance window).
2. **Contract** — once every running instance has been on the expanded
   schema for the agreed soak period (≥ 7 days), a follow-up migration
   removes the old column / drops the unused index / promotes a nullable
   column to NOT NULL.

This pattern is the only way to safely roll back any single deploy: at
no point does main carry both code and schema that require each other to
exist on the same revision.

## Rules

- **New columns**: always start nullable. Add a NOT NULL constraint only
  in a follow-up after backfill is complete.
- **Renames**: never use `ALTER ... RENAME COLUMN`. Add the new column,
  dual-write from app code for one release, switch reads, drop the old
  column in a later release.
- **Dropping a column / table**: must be preceded by ≥ 1 release where
  no code references it. Verify with grep.
- **Adding an index on a big table**: use `CREATE INDEX CONCURRENTLY`
  outside a transaction (Flyway needs a callback or sql-style migration
  with `executeInTransaction=false`).
- **Constraints**: add as `NOT VALID` first, then `VALIDATE CONSTRAINT`
  in a follow-up; avoids holding ACCESS EXCLUSIVE during validation.
- **Triggers**: must be idempotent. Re-running a migration that creates
  a trigger must not error — use `CREATE OR REPLACE` + `DROP TRIGGER
  IF EXISTS`.

## Checklist for migration PRs

- [ ] Migration file name follows `VN__what.sql` and `N` is greater than
      every existing file
- [ ] Migration is reversible OR the PR description explains why not and
      links the rollback plan
- [ ] Indexes are created `CONCURRENTLY` for any table > 100k rows
- [ ] No `ALTER TABLE ... DROP COLUMN` without an accompanying release
      note that lists the prior release that stopped reading it
- [ ] No `NOT NULL` added without a backfill commit in the same PR
- [ ] `MigrationTest` (Testcontainers) covers the new shape (column
      existence, constraint behavior)

## Out of scope (Plan H)

- Zero-downtime tooling like `pg-osc` for huge column rewrites.
- Schema lints in CI beyond the existing Flyway migration test.
