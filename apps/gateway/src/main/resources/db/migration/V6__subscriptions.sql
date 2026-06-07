-- V6__subscriptions.sql
-- Plan F §5 — subscriptions table with one-active-sub-per-user invariant.

CREATE TABLE subscriptions (
  id           UUID PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tier         TEXT NOT NULL CHECK (tier IN ('free', 'paid')),
  status       TEXT NOT NULL CHECK (status IN ('active', 'cancelled', 'expired')),
  started_at   TIMESTAMPTZ NOT NULL,
  expires_at   TIMESTAMPTZ,
  external_ref TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX one_active_sub_per_user
  ON subscriptions(user_id) WHERE status = 'active';

CREATE INDEX subscriptions_user_recent
  ON subscriptions(user_id, created_at DESC);

-- Backfill: every existing user gets a free active subscription.
INSERT INTO subscriptions (id, user_id, tier, status, started_at)
SELECT gen_random_uuid(), id, 'free', 'active', now()
FROM users
WHERE NOT EXISTS (
  SELECT 1 FROM subscriptions s
  WHERE s.user_id = users.id AND s.status = 'active'
);
