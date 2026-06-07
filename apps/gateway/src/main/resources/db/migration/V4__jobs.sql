-- V4__jobs.sql — async job tracking (Plan D, spec §5)

CREATE TABLE jobs (
  id           UUID PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES users(id),
  kind         TEXT NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('queued','running','completed','failed','cancelled')),
  params       JSONB NOT NULL,
  result_ref   TEXT,
  error        JSONB,
  priority     INT  NOT NULL DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at   TIMESTAMPTZ,
  finished_at  TIMESTAMPTZ
);

CREATE INDEX jobs_user_recent
  ON jobs(user_id, created_at DESC);

CREATE INDEX jobs_status_open
  ON jobs(status)
  WHERE status IN ('queued','running');
