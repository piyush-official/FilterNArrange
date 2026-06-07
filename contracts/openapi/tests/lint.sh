#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npx --yes @stoplight/spectral-cli@6 lint gateway-public.v1.yaml --ruleset .spectral.yaml --fail-severity=warn
npx --yes @stoplight/spectral-cli@6 lint gateway-internal.v1.yaml --ruleset .spectral.yaml --fail-severity=warn
echo "OK"
