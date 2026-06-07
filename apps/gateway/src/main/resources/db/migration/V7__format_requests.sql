-- V7__format_requests.sql
-- Plan F §5 — format requests with status lifecycle.

CREATE TABLE format_requests (
  id           UUID PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  sample_ref   TEXT NOT NULL,
  user_label   TEXT,
  status       TEXT NOT NULL DEFAULT 'open'
               CHECK (status IN ('open','triaged','in-progress','shipped','rejected')),
  priority     INT NOT NULL DEFAULT 0,
  github_issue INT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at  TIMESTAMPTZ
);

CREATE INDEX format_requests_status_open
  ON format_requests(status) WHERE status IN ('open', 'triaged', 'in-progress');

CREATE INDEX format_requests_user_recent
  ON format_requests(user_id, created_at DESC);
