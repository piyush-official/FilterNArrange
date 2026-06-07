-- V9__plugin_registry.sql
-- Plan F §5 — open-core tier gating. Seeded with the current plugin set.

CREATE TABLE plugin_registry (
  plugin_id     TEXT NOT NULL,
  kind          TEXT NOT NULL
                CHECK (kind IN ('format','filter','analysis','ai-provider','feature')),
  version       TEXT NOT NULL,
  status        TEXT NOT NULL CHECK (status IN ('enabled','disabled','deprecated')),
  required_tier TEXT CHECK (required_tier IN ('free','paid')),
  installed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (plugin_id, version)
);

CREATE INDEX plugin_registry_required_tier
  ON plugin_registry(required_tier) WHERE status = 'enabled';

INSERT INTO plugin_registry (plugin_id, kind, version, status, required_tier) VALUES
  ('format-csv',   'format', '1.0.0', 'enabled', 'free'),
  ('format-tsv',   'format', '1.0.0', 'enabled', 'free'),
  ('format-json',  'format', '1.0.0', 'enabled', 'free'),
  ('format-jsonl', 'format', '1.0.0', 'enabled', 'free'),
  ('format-xml',   'format', '1.0.0', 'enabled', 'free'),
  ('format-yaml',  'format', '1.0.0', 'enabled', 'free'),
  ('format-xlsx',  'format', '1.0.0', 'enabled', 'free');

INSERT INTO plugin_registry (plugin_id, kind, version, status, required_tier) VALUES
  ('filter-column',     'filter', '1.0.0', 'enabled', 'free'),
  ('filter-row',        'filter', '1.0.0', 'enabled', 'free'),
  ('filter-expression', 'filter', '1.0.0', 'enabled', 'free'),
  ('filter-regex',      'filter', '1.0.0', 'enabled', 'free');

INSERT INTO plugin_registry (plugin_id, kind, version, status, required_tier) VALUES
  ('analysis-summary-stats',  'analysis', '1.0.0', 'enabled', 'free'),
  ('analysis-group-by',       'analysis', '1.0.0', 'enabled', 'free'),
  ('analysis-chart-suggest',  'analysis', '1.0.0', 'enabled', 'free'),
  ('analysis-schema-infer',   'analysis', '1.0.0', 'enabled', 'free');

INSERT INTO plugin_registry (plugin_id, kind, version, status, required_tier) VALUES
  ('ai-nl-to-filter',   'ai-provider', '1.0.0', 'enabled', 'paid'),
  ('ai-auto-summary',   'ai-provider', '1.0.0', 'enabled', 'paid'),
  ('ai-chart-suggest',  'ai-provider', '1.0.0', 'enabled', 'paid'),
  ('ai-anomaly-detect', 'ai-provider', '1.0.0', 'enabled', 'paid');

-- Synthetic 'feature' entries — the FeatureGateFilter reads from the same table.
INSERT INTO plugin_registry (plugin_id, kind, version, status, required_tier) VALUES
  ('recipe-crud',           'feature', '1.0.0', 'enabled', 'paid'),
  ('job-batch-filter',      'feature', '1.0.0', 'enabled', 'paid'),
  ('format-request-submit', 'feature', '1.0.0', 'enabled', 'paid');
