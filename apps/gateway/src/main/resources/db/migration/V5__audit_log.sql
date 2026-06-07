-- V5__audit_log.sql — partitioned audit trail (Plan D, spec §5)

CREATE TABLE audit_log (
  id           BIGSERIAL,
  user_id      UUID,
  action       TEXT NOT NULL,
  target       TEXT,
  metadata     JSONB,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Current-month partition. The bounds are computed at migration time so the
-- shipped artifact is deterministic across re-runs; Flyway's checksum will
-- match because the SQL text is fixed and the date_trunc result is taken at
-- run time inside an anonymous block.
DO $$
DECLARE
    start_ts timestamptz := date_trunc('month', now());
    end_ts   timestamptz := start_ts + interval '1 month';
    pname    text := 'audit_log_' || to_char(start_ts, 'YYYY_MM');
BEGIN
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF audit_log FOR VALUES FROM (%L) TO (%L)',
        pname, start_ts, end_ts);
END
$$;

CREATE TABLE IF NOT EXISTS audit_log_default
    PARTITION OF audit_log DEFAULT;

CREATE INDEX audit_log_user_recent
    ON audit_log (user_id, created_at DESC);
