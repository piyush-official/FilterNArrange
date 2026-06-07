#!/usr/bin/env bash
# Creates the four v1 Kafka topics on the Redpanda broker. Idempotent — re-runs
# are no-ops because `rpk topic create` returns non-zero on "already exists"
# which we tolerate.
set -euo pipefail

BROKER="${REDPANDA_BROKERS:-redpanda:9092}"

create() {
  local name="$1" partitions="$2" retention_ms="$3"
  echo "==> ensuring topic ${name} (partitions=${partitions}, retention=${retention_ms}ms)"
  rpk topic create "${name}" \
      --brokers "${BROKER}" \
      --partitions "${partitions}" \
      --replicas 1 \
      --config "retention.ms=${retention_ms}" \
      || true   # ignore "already exists"
}

# Spec §5 — Kafka topics table
create "topic.v1.jobs"            6 $((7 * 24 * 60 * 60 * 1000))
# Plan F §T17 — tier-routed jobs topics. Same retention as the parent.
create "topic.v1.jobs.paid"       6 $((7 * 24 * 60 * 60 * 1000))
create "topic.v1.jobs.free"       6 $((7 * 24 * 60 * 60 * 1000))
create "topic.v1.job-results"     6 $((24 * 60 * 60 * 1000))
create "topic.v1.audit-events"    3 $((7 * 24 * 60 * 60 * 1000))
create "topic.v1.format-requests" 3 $((30 * 24 * 60 * 60 * 1000))

echo "==> topics provisioned"
