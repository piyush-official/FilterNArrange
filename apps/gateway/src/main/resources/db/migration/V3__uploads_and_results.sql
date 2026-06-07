CREATE TABLE uploads (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id      UUID NOT NULL REFERENCES users(id),
  ref          TEXT NOT NULL,
  size_bytes   BIGINT NOT NULL,
  content_type TEXT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX uploads_user_id ON uploads(user_id, created_at DESC);

CREATE TABLE results (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id      UUID NOT NULL REFERENCES users(id),
  upload_id    UUID REFERENCES uploads(id),
  ref          TEXT NOT NULL,
  output_format TEXT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX results_user_id ON results(user_id, created_at DESC);
