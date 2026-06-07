# ADR-0006 — Public release: v1.0.0 deploys to Oracle Always-Free

- **Status:** Accepted
- **Date:** 2026-06-08
- **Supersedes:** —
- **Related:** ADR-0001 (Valkey instead of Redis), ADR-0002–0005 (decisions through Plan G)

## Context

Plan H is the last plan in the original spec. We need to put a public,
free-tier-friendly URL in front of FilterNArrange so users can sign up and
try it. The constraint: zero ongoing hosting cost. The opportunity:
Oracle Cloud Always-Free gives every account one ARM Ampere VM
(4 OCPU / 24 GB / 200 GB block storage) indefinitely.

## Decision

Ship v1.0.0 to a single OCI ARM Ampere A1 VM running the full
docker-compose stack with a production overlay. TLS via Caddy + Let's
Encrypt. Auth defaults to spring-jwt (memory budget); Keycloak remains
available behind the AUTH_PROVIDER switch for installs that want OIDC.

## Consequences

- **Cost stays at $0/month** as long as the OCI free-tier offer holds.
- **Single-VM = single point of failure.** Acceptable for v1.0; Plan H
  follow-up adds the off-VM Backblaze backup so a complete VM loss
  doesn't lose user data.
- **ARM-only host** forces multi-arch images. CI builds linux/arm64 +
  linux/amd64; dev boxes (typically amd64) still work because we publish
  both.
- **Memory budget is tight** (16.85 GB committed of 24 GB total). Ollama
  is the biggest knob; the scale-down playbook in post-launch-monitoring
  documents how to recover headroom under pressure.
- **The deploy workflow is tag-triggered.** Tagging `v1.0.x` on main
  builds + signs + pushes images, then SSHes into the VM and runs
  `docker compose up -d` against the new tag. Rollback is a one-line env
  flip.

## Execution checklist

- [x] All Plan A-G PRs merged
- [x] Plan H PR (this one) merged with overlay + Caddy + bootstrap +
      smoke + docs
- [ ] OCI VM provisioned per ``docs/operations/oracle-provisioning.md``
- [ ] DNS `A` record live on the public host
- [ ] First admin seeded
- [ ] Smoke green
- [ ] Tag `v1.0.0` on main
- [ ] Announcement post drafted (`docs/releases/v1.0.0.md`)
