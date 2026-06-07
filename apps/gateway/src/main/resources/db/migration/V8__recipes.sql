-- V8__recipes.sql
-- Plan F §5 — paid feature; per-user named pipelines stored as JSONB.

CREATE TABLE recipes (
  id           UUID PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name         TEXT NOT NULL,
  recipe       JSONB NOT NULL,
  is_shared    BOOLEAN NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, name)
);

CREATE INDEX recipes_user_updated
  ON recipes(user_id, updated_at DESC);

CREATE OR REPLACE FUNCTION recipes_touch_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER recipes_touch_updated_at_trg
  BEFORE UPDATE ON recipes
  FOR EACH ROW EXECUTE FUNCTION recipes_touch_updated_at();
