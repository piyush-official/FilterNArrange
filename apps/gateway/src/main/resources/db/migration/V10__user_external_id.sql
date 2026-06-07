-- V10__user_external_id.sql
-- Plan G §T2 — Keycloak subject mapping. Expand step: add ``external_id`` as
-- nullable so the migration is reversible; backfill happens on first
-- Keycloak login (Plan G §T3). spring-jwt users keep NULL.

ALTER TABLE users ADD COLUMN IF NOT EXISTS external_id TEXT;

-- Partial unique index so multiple NULLs are allowed while non-null subjects
-- remain globally unique.
CREATE UNIQUE INDEX IF NOT EXISTS users_external_id_uq
  ON users(external_id)
  WHERE external_id IS NOT NULL;

COMMENT ON COLUMN users.external_id IS
  'Identity-provider subject (Keycloak ''sub'' claim). NULL for users created via the spring-jwt path.';
