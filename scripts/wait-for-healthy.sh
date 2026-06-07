#!/usr/bin/env bash
# Polls the /health endpoint of each FilterNArrange app service until every
# one reports {"status":"UP"} (or until the per-service timeout elapses).
#
# Exit codes:
#   0  all services healthy
#   1  one or more services failed to become healthy
#
# Intended usage:
#   ./scripts/wait-for-healthy.sh                          # default endpoints
#   TIMEOUT_SECONDS=600 ./scripts/wait-for-healthy.sh      # longer timeout
#
# CI uses this script after `docker compose up -d` to gate downstream stages.

set -euo pipefail

TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-3}"

# Service name → health URL.
declare -a SERVICES=(
  "gateway|http://localhost:8080/health"
  "data-engine|http://localhost:8000/health"
  "frontend|http://localhost:8081/health"   # frontend container :80 published via compose override; adjust if mapping differs
  "caddy|https://localhost:8443/health"
)

log() { printf '[wait-for-healthy] %s\n' "$*"; }

curl_ok() {
  # -k accepts the Caddy self-signed cert on :8443.
  local url="$1"
  local body
  body="$(curl -fsSk --max-time 5 "${url}" || return 1)"
  printf '%s' "${body}" | grep -q '"status"[[:space:]]*:[[:space:]]*"UP"'
}

wait_for() {
  local name="$1" url="$2" elapsed=0
  log "waiting for ${name} at ${url}"
  while (( elapsed < TIMEOUT_SECONDS )); do
    if curl_ok "${url}"; then
      log "${name} is UP after ${elapsed}s"
      return 0
    fi
    sleep "${POLL_INTERVAL_SECONDS}"
    elapsed=$(( elapsed + POLL_INTERVAL_SECONDS ))
  done
  log "ERROR: ${name} did not become healthy within ${TIMEOUT_SECONDS}s"
  return 1
}

failures=0
for entry in "${SERVICES[@]}"; do
  name="${entry%%|*}"
  url="${entry#*|}"
  if ! wait_for "${name}" "${url}"; then
    failures=$(( failures + 1 ))
  fi
done

if (( failures > 0 )); then
  log "FAILED: ${failures} service(s) not healthy"
  exit 1
fi

log "All services healthy."
