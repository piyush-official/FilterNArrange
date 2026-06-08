#!/usr/bin/env bash
# Plan H §T7 guard — asserts deploy.yml is wired for tag-triggered prod
# deploys with rollback. Cheap to run; doesn't actually invoke ssh-action.

set -euo pipefail
F=.github/workflows/deploy.yml
test -f "$F" || { echo "FAIL: missing $F"; exit 1; }

check() {
  local what="$1" pattern="$2"
  grep -q -- "$pattern" "$F" || { echo "FAIL: $what (pattern: $pattern)"; exit 1; }
}

check "tag trigger declared"        'tags:'
check "vX.Y.Z tag glob"              'v\*.\*.\*'
check "ssh-action import"            'appleboy/ssh-action'
check "Oracle VM host secret"        'ORACLE_VM_HOST'
check "Oracle VM ssh key secret"     'ORACLE_VM_SSH_KEY'
check "last-good-tag handling"       'last-good-tag'
check "smoke.sh runner"              'smoke.sh'
check "rollback step gated on smoke" 'steps.smoke.outcome == .failure.'
check "reuses release.yml builds"    'uses: ./.github/workflows/release.yml'

echo OK
