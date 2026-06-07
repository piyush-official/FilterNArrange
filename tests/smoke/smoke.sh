#!/usr/bin/env bash
# Plan H §T6 — post-deploy smoke. Designed to run from the deploy workflow
# OR by hand from any host that can reach the public URL.
#
# Usage:
#   PUBLIC_URL=https://filternarrange.example.com tests/smoke/smoke.sh

set -euo pipefail

URL="${PUBLIC_URL:-http://localhost}"
echo "==> smoking ${URL}"

ok() {
    local what="$1"
    local cmd="$2"
    if eval "$cmd" >/dev/null 2>&1; then
        echo "    OK   $what"
    else
        echo "    FAIL $what"
        exit 1
    fi
}

# 1. TLS / 200 on root
ok "frontend root returns 200" \
   "curl -fsSL --max-time 5 '${URL}/'"

# 2. Health endpoints
ok "gateway /health returns 200" \
   "curl -fsSL --max-time 5 '${URL}/health'"

# 3. Public API is reachable + auth gate fires
ok "GET /api/v1/auth/me without token returns 401" \
   "test \$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 '${URL}/api/v1/auth/me') = 401"

# 4. Security headers are present
ok "Strict-Transport-Security header is set" \
   "curl -sI --max-time 5 '${URL}/' | grep -qi 'strict-transport-security'"

ok "X-Frame-Options DENY is set" \
   "curl -sI --max-time 5 '${URL}/' | grep -qi 'x-frame-options: DENY'"

# 5. Actuator prometheus is exposed for in-cluster scrape only.
# When hit from outside, Caddy's path rules should NOT route it.
ok "external /actuator/prometheus is not exposed publicly" \
   "test \$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 '${URL}/actuator/prometheus') != 200"

echo "==> smoke OK"
