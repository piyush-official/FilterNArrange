#!/usr/bin/env bash
# Plan H §T1 guard — asserts release.yml builds multi-arch GHCR images for the
# Oracle Always-Free deploy target. Intentionally cheap so CI can run it on
# every PR alongside the heavier workflow execution.

set -euo pipefail
F=.github/workflows/release.yml

check() {
  local what="$1" pattern="$2"
  grep -q -- "$pattern" "$F" || { echo "FAIL: $what (pattern: $pattern)"; exit 1; }
}

check "multi-arch platform list"   'platforms: linux/arm64,linux/amd64'
check "QEMU setup action"          'docker/setup-qemu-action'
check "buildx setup action"        'docker/setup-buildx-action'
check ":latest tag pattern"        ':latest'
check "caddy app in matrix"        'caddy'
check "ghcr image namespace"       'ghcr.io/piyush-official/filternarrange'
check "workflow_call trigger"      'workflow_call:'

echo OK
