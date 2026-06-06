# Plan H — Public Deploy on Oracle Always-Free Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lift the production-credible Plan G stack to a publicly reachable Oracle Cloud Always-Free Ampere A1 instance, cut v1.0.0, and flip the repo public.

**Architecture:** Multi-arch (linux/arm64 + linux/amd64) GHCR images built and signed in CI; a production Compose overlay pulls those images on an Oracle Always-Free Ubuntu 22.04 ARM VM (4 vCPU / 24 GB RAM); Caddy 2 (with the rate-limit module) terminates TLS via Let's Encrypt; a tag-triggered deploy workflow SSHes into the VM, rolls images forward, runs a smoke suite, and rolls back on failure.

**Tech Stack:** GitHub Actions, Docker Buildx, GHCR, Cosign (Plan G), Caddy 2 + xcaddy + `mholt/caddy-ratelimit`, Cloudflare DNS, Oracle Cloud Infrastructure (OCI) Always-Free, Ubuntu 22.04 ARM, UFW, systemd, appleboy/ssh-action, Playwright + curl smoke, release-please.

---

## File Structure

**Created or modified:**

- `.github/workflows/release.yml` (modify) — multi-arch matrix + `:latest`-on-main + adds `caddy` build target.
- `.github/workflows/deploy.yml` (create) — tag-triggered deploy + smoke + rollback.
- `infra/docker-compose/docker-compose.prod.yml` (create) — production overlay.
- `infra/caddy/Caddyfile.prod` (create) — TLS, HSTS, CSP, rate-limit.
- `infra/caddy/Dockerfile` (create) — xcaddy build including the rate-limit module.
- `infra/deploy/bootstrap.sh` (create) — host bootstrap.
- `infra/deploy/filternarrange.service` (create) — systemd unit.
- `infra/deploy/logrotate.conf` (create) — log rotation.
- `infra/deploy/prod.env.example` (create) — example secret env.
- `apps/gateway/src/main/java/io/filternarrange/gateway/cli/SeedProdAdminCommand.java` (create) — first-boot admin CLI.
- `apps/gateway/src/main/resources/bin/seed-prod-admin` (create) — wrapper script.
- `apps/gateway/src/test/java/io/filternarrange/gateway/cli/SeedProdAdminCommandTest.java` (create).
- `tests/smoke/{package.json,playwright.config.ts,smoke-health.sh,smoke-signup-login.spec.ts,smoke-upload-detect-filter.spec.ts,smoke-ai-nl.spec.ts,smoke-job.spec.ts,fixtures/sample.csv}` (create).
- `docs/deploy/oracle-always-free.md` (create) — provisioning runbook + manual rehearsal checklist.
- `docs/deploy/secrets.md` (create) — what to put in GitHub Action secrets.
- `docs/deploy/post-launch.md` (create) — 24 h watch + scale-down + graceful-offline.
- `docs/decisions/ADR-0006-public-release.md` (create).
- `docs/release-notes/v1.0.0.md` (create).
- `README.md` (modify) — live URL + badges.

**Deliberately untouched:** `docs/cost-tracking.md`, `CHANGELOG.md`, any code outside the list above.

**Conventions:** `io.filternarrange.gateway`, `filternarrange_engine`, Conventional Commits, error envelope `{code, plugin_id, message, trace_id}`, image namespace `ghcr.io/piyush-official/filternarrange/<app>`, domain placeholder `filternarrange.example.com` (replaced at deploy time via `prod.env`).

---

## Task 1: Multi-arch GHCR build in release workflow

**Files:** Modify `.github/workflows/release.yml`; create `.github/workflows/release.test.sh`.

- [ ] **Step 1: Inspect existing workflow**

Run: `cat .github/workflows/release.yml`
Expected: Plan A/G workflow with single-arch matrix.

- [ ] **Step 2: Write the failing CI guard**

Create `.github/workflows/release.test.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
F=.github/workflows/release.yml
grep -q 'platforms: linux/arm64,linux/amd64' "$F" || { echo "missing multi-arch"; exit 1; }
grep -q 'docker/setup-qemu-action'     "$F" || { echo "missing QEMU"; exit 1; }
grep -q 'docker/setup-buildx-action'   "$F" || { echo "missing buildx"; exit 1; }
grep -q ':latest'                      "$F" || { echo "missing :latest tag"; exit 1; }
grep -q 'caddy'                        "$F" || { echo "missing caddy target"; exit 1; }
echo OK
```

Run: `bash .github/workflows/release.test.sh` — expected FAIL.

- [ ] **Step 3: Replace the build-and-push job**

Keep the surrounding release-please / Cosign / SBOM jobs from Plan A/G. Replace the build/push job with:

```yaml
  build-and-push:
    runs-on: ubuntu-22.04
    strategy:
      matrix:
        app: [gateway, data-engine, frontend, retention-worker, caddy]
    permissions:
      contents: read
      packages: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-qemu-action@v3
        with: { platforms: arm64,amd64 }
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Resolve build context
        id: ctx
        run: |
          if [[ "${{ matrix.app }}" == "caddy" ]]; then
            echo "path=./infra/caddy" >> "$GITHUB_OUTPUT"
          else
            echo "path=./apps/${{ matrix.app }}" >> "$GITHUB_OUTPUT"
          fi
      - name: Compute tags
        id: tags
        run: |
          IMAGE=ghcr.io/piyush-official/filternarrange/${{ matrix.app }}
          if [[ "${GITHUB_REF}" == refs/tags/v* ]]; then
            VERSION="${GITHUB_REF#refs/tags/}"
            TAGS="${IMAGE}:${VERSION}"
          else
            VERSION="$(git rev-parse --short HEAD)"
            TAGS="${IMAGE}:sha-${VERSION}"
          fi
          if [[ "${GITHUB_REF}" == "refs/heads/main" ]]; then
            TAGS="${TAGS},${IMAGE}:latest"
          fi
          echo "tags=${TAGS}" >> "$GITHUB_OUTPUT"
      - name: Build and push (multi-arch)
        id: build
        uses: docker/build-push-action@v5
        with:
          context: ${{ steps.ctx.outputs.path }}
          platforms: linux/arm64,linux/amd64
          push: true
          tags: ${{ steps.tags.outputs.tags }}
          provenance: true
          sbom: true
          cache-from: type=gha,scope=${{ matrix.app }}
          cache-to: type=gha,scope=${{ matrix.app }},mode=max
```

The existing Cosign signing job (Plan G) already consumes `steps.build.outputs.digest` per matrix entry — leave it untouched.

- [ ] **Step 4: Re-run the guard**

Run: `bash .github/workflows/release.test.sh` — expected `OK`.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/release.yml .github/workflows/release.test.sh
git commit -m "feat(ci): build multi-arch (arm64+amd64) images for Oracle Always-Free deploy"
```

Cross-arch verification (`docker pull --platform linux/arm64` on Oracle, `linux/amd64` on dev box) is the first step of Task 14's manual rehearsal.

---

## Task 2: Production Compose overlay

**Files:** Create `infra/docker-compose/docker-compose.prod.yml`, `infra/deploy/prod.env.example`, `infra/docker-compose/docker-compose.prod.test.sh`.

- [ ] **Step 1: Write the failing validation**

Create `infra/docker-compose/docker-compose.prod.test.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
F=infra/docker-compose/docker-compose.prod.yml
test -f "$F" || { echo "missing $F"; exit 1; }
docker compose -f infra/docker-compose/docker-compose.yml -f "$F" config --quiet
grep -E '^\s+build:' "$F" && { echo "prod must not build"; exit 1; } || true
grep -E '"5173:'     "$F" && { echo "Vite port leaked"; exit 1; } || true
echo OK
```

Run: `bash infra/docker-compose/docker-compose.prod.test.sh` — expected FAIL.

- [ ] **Step 2: Create the overlay**

Create `infra/docker-compose/docker-compose.prod.yml`:

```yaml
# Production overlay for Oracle Always-Free (4 vCPU ARM Ampere / 24 GB).
# Use:
#   docker compose \
#     -f infra/docker-compose/docker-compose.yml \
#     -f infra/docker-compose/docker-compose.prod.yml \
#     --env-file /etc/filternarrange/prod.env \
#     up -d
name: filternarrange

services:
  gateway:
    image: ghcr.io/piyush-official/filternarrange/gateway:${FNA_VERSION:?must set FNA_VERSION}
    build: !reset null
    environment:
      SPRING_PROFILES_ACTIVE: prod
      AUTH_PROVIDER: ${AUTH_PROVIDER:-spring-jwt}     # spring-jwt saves ~1 GB vs keycloak
      JWT_SECRET: ${JWT_SECRET:?}
      POSTGRES_URL: jdbc:postgresql://postgres:5432/filternarrange
      POSTGRES_USER: ${POSTGRES_USER:?}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?}
      REDIS_URL: redis://redis:6379
      KAFKA_BOOTSTRAP: redpanda:9092
      MINIO_ENDPOINT: http://minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY:?}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY:?}
      PUBLIC_BASE_URL: https://${PUBLIC_HOST:?}
      JAVA_TOOL_OPTIONS: -XX:MaxRAMPercentage=70
    ports: !reset []
    expose: ["8080"]
    deploy: { resources: { limits: { memory: 1500m, cpus: "1.0" } } }
    restart: unless-stopped

  data-engine:
    image: ghcr.io/piyush-official/filternarrange/data-engine:${FNA_VERSION:?}
    build: !reset null
    environment:
      MODE: full
      NL2FILTER_MODEL: ${NL2FILTER_MODEL:-qwen2.5:3b}
      SUMMARY_MODEL: ${SUMMARY_MODEL:-llama3.1:8b}
      OLLAMA_URL: http://ollama:11434
      POSTGRES_URL: postgresql://postgres:5432/filternarrange
      REDIS_URL: redis://redis:6379
      KAFKA_BOOTSTRAP: redpanda:9092
      MINIO_ENDPOINT: http://minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY:?}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY:?}
    ports: !reset []
    expose: ["8000"]
    deploy: { resources: { limits: { memory: 2g, cpus: "1.0" } } }
    restart: unless-stopped

  retention-worker:
    image: ghcr.io/piyush-official/filternarrange/retention-worker:${FNA_VERSION:?}
    build: !reset null
    environment:
      MODE: worker
      POSTGRES_URL: postgresql://postgres:5432/filternarrange
      MINIO_ENDPOINT: http://minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY:?}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY:?}
    deploy: { resources: { limits: { memory: 512m, cpus: "0.5" } } }
    restart: unless-stopped

  frontend:
    image: ghcr.io/piyush-official/filternarrange/frontend:${FNA_VERSION:?}
    build: !reset null
    environment:
      VITE_API_BASE: https://${PUBLIC_HOST:?}/api/v1
    ports: !reset []
    expose: ["80"]
    deploy: { resources: { limits: { memory: 128m, cpus: "0.25" } } }
    restart: unless-stopped

  caddy:
    image: ghcr.io/piyush-official/filternarrange/caddy:${FNA_VERSION:?}
    build: !reset null
    environment:
      PUBLIC_HOST: ${PUBLIC_HOST:?}
      ACME_EMAIL: ${ACME_EMAIL:?}
    ports: ["80:80", "443:443"]
    volumes:
      - /var/lib/filternarrange/caddy-data:/data
      - /var/lib/filternarrange/caddy-config:/config
      - ../caddy/Caddyfile.prod:/etc/caddy/Caddyfile:ro
    deploy: { resources: { limits: { memory: 256m, cpus: "0.25" } } }
    restart: unless-stopped

  ollama:
    environment:
      OLLAMA_KEEP_ALIVE: 5m
      OLLAMA_MAX_LOADED_MODELS: "1"
    ports: !reset []
    expose: ["11434"]
    volumes: [/var/lib/filternarrange/ollama:/root/.ollama]
    deploy: { resources: { limits: { memory: 8g, cpus: "2.0" } } }
    restart: unless-stopped

  postgres:
    ports: !reset []
    volumes: [/var/lib/filternarrange/postgres:/var/lib/postgresql/data]
    deploy: { resources: { limits: { memory: 2g, cpus: "1.0" } } }
    restart: unless-stopped

  redis:
    ports: !reset []
    volumes: [/var/lib/filternarrange/redis:/data]
    deploy: { resources: { limits: { memory: 512m, cpus: "0.25" } } }
    restart: unless-stopped

  redpanda:
    ports: !reset []
    volumes: [/var/lib/filternarrange/redpanda:/var/lib/redpanda/data]
    deploy: { resources: { limits: { memory: 1500m, cpus: "0.5" } } }
    restart: unless-stopped

  minio:
    ports: !reset []
    expose: ["9000", "9001"]
    volumes: [/var/lib/filternarrange/minio:/data]
    deploy: { resources: { limits: { memory: 512m, cpus: "0.25" } } }
    restart: unless-stopped

  # Keycloak omitted: AUTH_PROVIDER=spring-jwt is the prod default.
  # Re-enable by copying the keycloak service block from docker-compose.yml here.
```

Memory budget (24 GB Ampere A1): gateway 1.5 + data-engine 2 + retention 0.5 + frontend 0.1 + caddy 0.25 + ollama 8 + postgres 2 + redis 0.5 + redpanda 1.5 + minio 0.5 = **~16.85 GB**; ~7 GB OS/buffer.

- [ ] **Step 3: Example env**

Create `infra/deploy/prod.env.example`:

```bash
# /etc/filternarrange/prod.env — copy, edit, chmod 600, never commit
FNA_VERSION=v1.0.0
PUBLIC_HOST=filternarrange.example.com
ACME_EMAIL=ops@example.com
AUTH_PROVIDER=spring-jwt
JWT_SECRET=replace-with-openssl-rand-base64-48
POSTGRES_USER=filternarrange
POSTGRES_PASSWORD=replace-with-openssl-rand-base64-32
MINIO_ACCESS_KEY=replace-with-openssl-rand-base64-24
MINIO_SECRET_KEY=replace-with-openssl-rand-base64-48
NL2FILTER_MODEL=qwen2.5:3b
SUMMARY_MODEL=llama3.1:8b
```

- [ ] **Step 4: Verify**

Run: `bash infra/docker-compose/docker-compose.prod.test.sh` — expected `OK`.

- [ ] **Step 5: Commit**

```bash
git add infra/docker-compose/docker-compose.prod.yml \
        infra/docker-compose/docker-compose.prod.test.sh \
        infra/deploy/prod.env.example
git commit -m "feat(infra): production Compose overlay sized for Oracle Always-Free 24 GB"
```

---

## Task 3: Caddy custom image with rate-limit module

**Files:** Create `infra/caddy/Dockerfile`, `infra/caddy/Caddyfile.prod`, `infra/caddy/Caddyfile.test.sh`.

- [ ] **Step 1: Write the failing validation**

Create `infra/caddy/Caddyfile.test.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
F=infra/caddy/Caddyfile.prod
test -f "$F" || { echo "missing $F"; exit 1; }
for k in rate_limit Strict-Transport-Security Content-Security-Policy X-Frame-Options X-Content-Type-Options Referrer-Policy; do
  grep -q "$k" "$F" || { echo "missing $k"; exit 1; }
done
echo OK
```

Run: `bash infra/caddy/Caddyfile.test.sh` — expected FAIL.

- [ ] **Step 2: xcaddy Dockerfile**

Create `infra/caddy/Dockerfile`:

```dockerfile
FROM caddy:2-builder AS builder
RUN xcaddy build --with github.com/mholt/caddy-ratelimit

FROM caddy:2
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
LABEL org.opencontainers.image.source="https://github.com/piyush-official/FilterNArrange"
LABEL org.opencontainers.image.title="filternarrange-caddy"
LABEL org.opencontainers.image.description="Caddy 2 with mholt/caddy-ratelimit"
```

- [ ] **Step 3: Caddyfile**

Create `infra/caddy/Caddyfile.prod`:

```caddyfile
{
    email {$ACME_EMAIL}
    admin off
    servers { protocols h1 h2 h3 }
    order rate_limit before basicauth
}

http://{$PUBLIC_HOST} {
    redir https://{$PUBLIC_HOST}{uri} permanent
}

https://{$PUBLIC_HOST} {
    encode zstd gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Frame-Options "DENY"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "geolocation=(), microphone=(), camera=()"
        Content-Security-Policy "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' wss://{$PUBLIC_HOST}; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        -Server
    }

    @auth path /api/v1/auth/*
    rate_limit @auth {
        zone auth_zone {
            key    {http.request.remote.host}
            events 10
            window 1m
        }
    }

    @ws {
        path /ws/*
        header Connection *Upgrade*
        header Upgrade websocket
    }
    reverse_proxy @ws gateway:8080

    handle /api/* {
        reverse_proxy gateway:8080 {
            header_up X-Forwarded-Proto https
            header_up X-Real-IP {http.request.remote.host}
        }
    }

    handle {
        reverse_proxy frontend:80
    }

    log {
        output file /var/log/caddy/access.log {
            roll_size 10mb
            roll_keep 7
            roll_keep_for 168h
        }
        format json
    }
}
```

- [ ] **Step 4: Verify**

Run: `bash infra/caddy/Caddyfile.test.sh` — expected `OK`.

- [ ] **Step 5: Commit**

```bash
git add infra/caddy/Dockerfile infra/caddy/Caddyfile.prod infra/caddy/Caddyfile.test.sh
git commit -m "feat(infra): Caddy 2 prod config with TLS, HSTS, CSP, and auth rate-limit"
```

---

## Task 4: Host bootstrap + systemd + logrotate

**Files:** Create `infra/deploy/bootstrap.sh`, `infra/deploy/filternarrange.service`, `infra/deploy/logrotate.conf`.

- [ ] **Step 1: Failing shellcheck**

Run: `shellcheck infra/deploy/bootstrap.sh` — expected FAIL (file missing).

- [ ] **Step 2: bootstrap.sh**

Create `infra/deploy/bootstrap.sh`:

```bash
#!/usr/bin/env bash
# Bootstrap Oracle Always-Free Ampere A1 Ubuntu 22.04 for FilterNArrange. Idempotent.
set -euo pipefail
[[ "$(id -u)" -eq 0 ]] || { echo "run as root"; exit 1; }

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get -y upgrade
apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg ufw jq logrotate unattended-upgrades

# Docker Engine + Compose v2
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -qq
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable --now docker

# UFW (host-level firewall on top of OCI security list)
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp  comment 'SSH'
ufw allow 80/tcp  comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable

# Volume dirs
install -d -m 0755 /etc/filternarrange
install -d -m 0755 /var/lib/filternarrange
for d in postgres redis redpanda minio ollama caddy-data caddy-config; do
  install -d -m 0755 "/var/lib/filternarrange/${d}"
done
touch /var/lib/filternarrange/last-good-tag

# systemd + logrotate
install -m 0644 /opt/filternarrange/infra/deploy/filternarrange.service \
  /etc/systemd/system/filternarrange.service
systemctl daemon-reload
systemctl enable filternarrange.service
install -m 0644 /opt/filternarrange/infra/deploy/logrotate.conf \
  /etc/logrotate.d/filternarrange

dpkg-reconfigure --priority=low unattended-upgrades
echo "done. next: edit /etc/filternarrange/prod.env, then 'systemctl start filternarrange'"
```

`chmod +x infra/deploy/bootstrap.sh`.

- [ ] **Step 3: systemd unit**

Create `infra/deploy/filternarrange.service`:

```ini
[Unit]
Description=FilterNArrange production stack (Docker Compose)
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/filternarrange
EnvironmentFile=/etc/filternarrange/prod.env
ExecStartPre=/usr/bin/docker compose -f infra/docker-compose/docker-compose.yml -f infra/docker-compose/docker-compose.prod.yml pull
ExecStart=/usr/bin/docker compose -f infra/docker-compose/docker-compose.yml -f infra/docker-compose/docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f infra/docker-compose/docker-compose.yml -f infra/docker-compose/docker-compose.prod.yml down
TimeoutStartSec=600

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 4: logrotate**

Create `infra/deploy/logrotate.conf`:

```
/var/lib/docker/containers/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    copytruncate
    notifempty
}

/var/lib/filternarrange/caddy-data/caddy/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
}
```

- [ ] **Step 5: Verify**

Run: `shellcheck infra/deploy/bootstrap.sh` — expected pass.

- [ ] **Step 6: Commit**

```bash
git add infra/deploy/bootstrap.sh infra/deploy/filternarrange.service infra/deploy/logrotate.conf
git commit -m "feat(deploy): host bootstrap, systemd unit, and log rotation for Oracle Always-Free"
```

---

## Task 5: Gateway `seed-prod-admin` CLI

**Files:** Create `apps/gateway/src/main/java/io/filternarrange/gateway/cli/SeedProdAdminCommand.java`, `apps/gateway/src/main/resources/bin/seed-prod-admin`, `apps/gateway/src/test/java/io/filternarrange/gateway/cli/SeedProdAdminCommandTest.java`.

- [ ] **Step 1: Failing test**

Create `apps/gateway/src/test/java/io/filternarrange/gateway/cli/SeedProdAdminCommandTest.java`:

```java
package io.filternarrange.gateway.cli;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
class SeedProdAdminCommandTest {
    @Autowired SeedProdAdminCommand command;

    @Test
    void seedsAdminUserWhenAbsent() {
        var r = command.run("admin@example.com", "Initial Admin");
        assertThat(r.userId()).isNotNull();
        assertThat(r.created()).isTrue();
        assertThat(r.role()).isEqualTo("admin");
    }

    @Test
    void isIdempotentOnSecondInvocation() {
        command.run("admin@example.com", "Initial Admin");
        var r2 = command.run("admin@example.com", "Initial Admin");
        assertThat(r2.created()).isFalse();
        assertThat(r2.role()).isEqualTo("admin");
    }
}
```

Run: `cd apps/gateway && ./gradlew test --tests SeedProdAdminCommandTest` — expected FAIL.

- [ ] **Step 2: Implementation**

Create `apps/gateway/src/main/java/io/filternarrange/gateway/cli/SeedProdAdminCommand.java`:

```java
package io.filternarrange.gateway.cli;

import io.filternarrange.gateway.domain.users.User;
import io.filternarrange.gateway.domain.users.UserRepository;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

import java.security.SecureRandom;
import java.util.Base64;
import java.util.UUID;

/**
 * Seeds the first admin on a fresh production deploy. Idempotent.
 *
 * <p>Invoked via {@code docker compose exec gateway ./bin/seed-prod-admin <email> "<name>"}.
 */
@Component
@Profile("prod | test")
public class SeedProdAdminCommand implements ApplicationRunner {
    private final UserRepository users;

    public SeedProdAdminCommand(UserRepository users) { this.users = users; }

    @Override
    public void run(ApplicationArguments args) {
        if (!args.containsOption("seed-prod-admin")) return;
        var nonOpt = args.getNonOptionArgs();
        if (nonOpt.size() < 2) {
            throw new IllegalArgumentException("usage: seed-prod-admin <email> <display-name>");
        }
        var r = run(nonOpt.get(0), nonOpt.get(1));
        System.out.println("seed-prod-admin: user_id=" + r.userId()
                + " created=" + r.created() + " role=" + r.role());
        if (r.tempPassword() != null) {
            System.out.println("seed-prod-admin: temp_password=" + r.tempPassword()
                    + " (rotate immediately on first login)");
        }
    }

    public Result run(String email, String displayName) {
        var existing = users.findByEmail(email);
        if (existing.isPresent()) {
            var u = existing.get();
            u.grantRole("admin");
            users.save(u);
            return new Result(u.id(), false, "admin", null);
        }
        var temp = randomPassword();
        var u = User.create(UUID.randomUUID(), email, displayName, temp);
        u.grantRole("admin");
        users.save(u);
        return new Result(u.id(), true, "admin", temp);
    }

    private String randomPassword() {
        var b = new byte[24];
        new SecureRandom().nextBytes(b);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(b);
    }

    public record Result(UUID userId, boolean created, String role, String tempPassword) {}
}
```

- [ ] **Step 3: Wrapper script**

Create `apps/gateway/src/main/resources/bin/seed-prod-admin`:

```bash
#!/usr/bin/env sh
# Thin wrapper that re-invokes the Spring Boot JAR with the seed flag.
exec java ${JAVA_TOOL_OPTIONS:-} -jar /app/gateway.jar --seed-prod-admin "$@"
```

`chmod +x apps/gateway/src/main/resources/bin/seed-prod-admin`. The gateway Dockerfile (Plan A) already COPYs `src/main/resources/bin/` into `/app/bin/`.

- [ ] **Step 4: Run tests**

Run: `cd apps/gateway && ./gradlew test --tests SeedProdAdminCommandTest` — expected PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/cli/SeedProdAdminCommand.java \
        apps/gateway/src/main/resources/bin/seed-prod-admin \
        apps/gateway/src/test/java/io/filternarrange/gateway/cli/SeedProdAdminCommandTest.java
git commit -m "feat(gateway): idempotent seed-prod-admin CLI for first-boot admin"
```

---

## Task 6: Smoke test suite

**Files:** Create `tests/smoke/{package.json,playwright.config.ts,smoke-health.sh,smoke-signup-login.spec.ts,smoke-upload-detect-filter.spec.ts,smoke-ai-nl.spec.ts,smoke-job.spec.ts,fixtures/sample.csv}`.

- [ ] **Step 1: package.json + playwright config**

Create `tests/smoke/package.json`:

```json
{
  "name": "@filternarrange/smoke",
  "private": true,
  "version": "1.0.0",
  "scripts": {
    "smoke:health": "bash smoke-health.sh",
    "smoke:e2e": "playwright test",
    "smoke:all": "npm run smoke:health && npm run smoke:e2e"
  },
  "devDependencies": {
    "@playwright/test": "^1.45.0",
    "typescript": "^5.5.0",
    "ws": "^8.18.0"
  }
}
```

Create `tests/smoke/playwright.config.ts`:

```ts
import { defineConfig } from '@playwright/test';
const baseURL = process.env.SMOKE_BASE_URL ?? 'http://localhost:8080';
export default defineConfig({
    testDir: '.',
    timeout: 30_000,
    expect: { timeout: 10_000 },
    retries: 0,
    workers: 1,
    use: { baseURL, ignoreHTTPSErrors: false, trace: 'retain-on-failure' },
    reporter: [['list'], ['junit', { outputFile: 'smoke-results.xml' }]],
});
```

- [ ] **Step 2: Health smoke**

Create `tests/smoke/smoke-health.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${SMOKE_BASE_URL:?SMOKE_BASE_URL must be set}"
fail=0
for ep in /api/v1/health /api/v1/ready; do
  url="${SMOKE_BASE_URL}${ep}"
  code=$(curl -s -o /tmp/body.$$ -w "%{http_code}" --max-time 10 "$url")
  if [[ "$code" != "200" ]]; then
    echo "FAIL $ep -> $code"; cat /tmp/body.$$ || true; fail=1
  else
    s=$(jq -r '.status // empty' /tmp/body.$$ 2>/dev/null || echo "")
    if [[ -n "$s" && "$s" != "UP" ]]; then
      echo "FAIL $ep -> status=$s"; fail=1
    else
      echo "OK   $ep -> 200"
    fi
  fi
  rm -f /tmp/body.$$
done
exit $fail
```

`chmod +x tests/smoke/smoke-health.sh`.

- [ ] **Step 3: Fixture + signup/login spec**

Create `tests/smoke/fixtures/sample.csv`:

```csv
id,name,age,country
1,Asha,29,IN
2,Ben,17,US
3,Cora,42,UK
4,Dev,33,IN
5,Eli,15,US
```

Create `tests/smoke/smoke-signup-login.spec.ts`:

```ts
import { test, expect, request } from '@playwright/test';
import { randomBytes } from 'crypto';

test('fresh user can sign up and log in', async ({ baseURL }) => {
    const api = await request.newContext({ baseURL });
    const email = `smoke+${randomBytes(6).toString('hex')}@filternarrange.test`;
    const password = randomBytes(24).toString('base64url');
    const signup = await api.post('/api/v1/auth/signup', {
        data: { email, password, displayName: 'Smoke' },
    });
    expect(signup.status(), await signup.text()).toBe(201);
    const login = await api.post('/api/v1/auth/login', { data: { email, password } });
    expect(login.status()).toBe(200);
    const { accessToken } = await login.json();
    expect(accessToken).toBeTruthy();
    const me = await api.get('/api/v1/me', { headers: { Authorization: `Bearer ${accessToken}` } });
    expect(me.status()).toBe(200);
    expect((await me.json()).email).toBe(email);
});
```

- [ ] **Step 4: Upload/detect/filter spec**

Create `tests/smoke/smoke-upload-detect-filter.spec.ts`:

```ts
import { test, expect, request } from '@playwright/test';
import { readFileSync } from 'fs';
import { randomBytes } from 'crypto';
import path from 'path';

test('upload -> detect -> filter round-trip', async ({ baseURL }) => {
    const api = await request.newContext({ baseURL });
    const email = `smoke+${randomBytes(6).toString('hex')}@filternarrange.test`;
    const password = randomBytes(24).toString('base64url');
    await api.post('/api/v1/auth/signup', { data: { email, password, displayName: 'S' } });
    const tok = (await (await api.post('/api/v1/auth/login', { data: { email, password } })).json()).accessToken;
    const auth = { Authorization: `Bearer ${tok}` };

    const sample = readFileSync(path.join(__dirname, 'fixtures', 'sample.csv'));
    const up = await api.post('/api/v1/uploads', {
        headers: auth,
        multipart: { file: { name: 'sample.csv', mimeType: 'text/csv', buffer: sample } },
    });
    expect(up.status()).toBe(201);
    const { uploadId } = await up.json();

    const det = await api.post('/api/v1/detect', { headers: auth, data: { uploadId } });
    expect(det.status()).toBe(200);
    const d = await det.json();
    expect(d.format).toBe('csv');
    expect(d.confidence).toBeGreaterThan(0.8);

    const filt = await api.post('/api/v1/filter/preview', {
        headers: auth,
        data: { uploadId, spec: { kind: 'row', predicate: "age >= 18 AND country = 'IN'" } },
    });
    expect(filt.status()).toBe(200);
    const rows = (await filt.json()).rows as Array<Record<string, unknown>>;
    expect(rows).toHaveLength(2);
    expect(rows.every((r) => r.country === 'IN')).toBe(true);
});
```

- [ ] **Step 5: AI NL spec**

Create `tests/smoke/smoke-ai-nl.spec.ts`:

```ts
import { test, expect, request } from '@playwright/test';
import { readFileSync } from 'fs';
import { randomBytes } from 'crypto';
import path from 'path';

test('AI NL->filter returns structured FilterSpec within 10s', async ({ baseURL }) => {
    const api = await request.newContext({ baseURL });
    const email = `smoke+${randomBytes(6).toString('hex')}@filternarrange.test`;
    const password = randomBytes(24).toString('base64url');
    await api.post('/api/v1/auth/signup', { data: { email, password, displayName: 'S' } });
    const tok = (await (await api.post('/api/v1/auth/login', { data: { email, password } })).json()).accessToken;
    const auth = { Authorization: `Bearer ${tok}` };

    const sample = readFileSync(path.join(__dirname, 'fixtures', 'sample.csv'));
    const up = await api.post('/api/v1/uploads', {
        headers: auth,
        multipart: { file: { name: 'sample.csv', mimeType: 'text/csv', buffer: sample } },
    });
    const { uploadId } = await up.json();

    const t0 = Date.now();
    const nl = await api.post('/api/v1/ai/nl-to-filter', {
        headers: auth,
        data: { uploadId, prompt: 'adults from India' },
    });
    const dt = Date.now() - t0;
    expect(nl.status()).toBe(200);
    expect(dt).toBeLessThan(10_000);
    const body = await nl.json();
    expect(body.spec).toBeTruthy();
    expect(['row', 'expression', 'column', 'regex']).toContain(body.spec.kind);
});
```

- [ ] **Step 6: Job spec**

Create `tests/smoke/smoke-job.spec.ts`:

```ts
import { test, expect, request } from '@playwright/test';
import { readFileSync } from 'fs';
import { randomBytes } from 'crypto';
import path from 'path';
import WebSocket from 'ws';

test('tiny batch job reaches completed via WebSocket', async ({ baseURL }) => {
    const api = await request.newContext({ baseURL });
    const email = `smoke+${randomBytes(6).toString('hex')}@filternarrange.test`;
    const password = randomBytes(24).toString('base64url');
    await api.post('/api/v1/auth/signup', { data: { email, password, displayName: 'S' } });
    const tok = (await (await api.post('/api/v1/auth/login', { data: { email, password } })).json()).accessToken;
    const auth = { Authorization: `Bearer ${tok}` };

    const sample = readFileSync(path.join(__dirname, 'fixtures', 'sample.csv'));
    const up = await api.post('/api/v1/uploads', {
        headers: auth,
        multipart: { file: { name: 'sample.csv', mimeType: 'text/csv', buffer: sample } },
    });
    const { uploadId } = await up.json();

    const job = await api.post('/api/v1/jobs', {
        headers: auth,
        data: { kind: 'convert', params: { input: { uploadId }, operations: [{ kind: 'convert', to: 'json' }] } },
    });
    expect(job.status()).toBe(202);
    const { jobId } = await job.json();

    const wsUrl = (baseURL ?? '').replace(/^http/, 'ws') + `/ws/jobs/${jobId}?token=${tok}`;
    const ws = new WebSocket(wsUrl);
    const finalStatus: string = await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('timeout')), 25_000);
        ws.on('message', (raw) => {
            const m = JSON.parse(raw.toString());
            if (m.status === 'completed' || m.status === 'failed') {
                clearTimeout(timer); ws.close(); resolve(m.status);
            }
        });
        ws.on('error', (e) => { clearTimeout(timer); reject(e); });
    });
    expect(finalStatus).toBe('completed');
});
```

- [ ] **Step 7: Local dry-run**

Run:

```bash
cd tests/smoke && npm install
SMOKE_BASE_URL=http://localhost:8080 npm run smoke:all
```

Expected: against a `docker compose up -d` prod-overlay stack on localhost, all 5 checks pass.

- [ ] **Step 8: Commit**

```bash
git add tests/smoke
git commit -m "test(smoke): health + signup + upload + AI + job smoke suite (Playwright)"
```

---

## Task 7: Tag-triggered deploy workflow with rollback

**Files:** Create `.github/workflows/deploy.yml`, `.github/workflows/deploy.test.sh`.

- [ ] **Step 1: Failing guard**

Create `.github/workflows/deploy.test.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
F=.github/workflows/deploy.yml
test -f "$F" || { echo "missing $F"; exit 1; }
for k in 'tags:' 'v\*.\*.\*' 'appleboy/ssh-action' ORACLE_VM_HOST ORACLE_VM_SSH_KEY last-good-tag smoke-health.sh; do
  grep -q "$k" "$F" || { echo "missing $k"; exit 1; }
done
echo OK
```

Run: `bash .github/workflows/deploy.test.sh` — expected FAIL.

- [ ] **Step 2: Workflow**

Create `.github/workflows/deploy.yml`:

```yaml
name: deploy
on:
  push:
    tags: ["v*.*.*"]

concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: false

jobs:
  build-and-push:
    uses: ./.github/workflows/release.yml
    secrets: inherit

  deploy:
    needs: build-and-push
    runs-on: ubuntu-22.04
    environment:
      name: production
      url: https://${{ vars.PUBLIC_HOST }}
    steps:
      - uses: actions/checkout@v4
      - name: Compute version
        id: v
        run: echo "version=${GITHUB_REF#refs/tags/}" >> "$GITHUB_OUTPUT"

      - name: Sync repo to VM
        uses: appleboy/scp-action@v0.1.7
        with:
          host:     ${{ secrets.ORACLE_VM_HOST }}
          username: ${{ secrets.ORACLE_VM_USER }}
          key:      ${{ secrets.ORACLE_VM_SSH_KEY }}
          source:   "infra/,apps/gateway/src/main/resources/bin/"
          target:   "/opt/filternarrange/"
          strip_components: 0

      - name: Pull, restart, verify
        uses: appleboy/ssh-action@v1.0.3
        with:
          host:     ${{ secrets.ORACLE_VM_HOST }}
          username: ${{ secrets.ORACLE_VM_USER }}
          key:      ${{ secrets.ORACLE_VM_SSH_KEY }}
          script: |
            set -euo pipefail
            NEW_TAG="${{ steps.v.outputs.version }}"
            sudo sed -i "s|^FNA_VERSION=.*|FNA_VERSION=${NEW_TAG}|" /etc/filternarrange/prod.env
            sudo systemctl restart filternarrange
            for i in $(seq 1 30); do
              if sudo docker compose -f /opt/filternarrange/infra/docker-compose/docker-compose.yml \
                                     -f /opt/filternarrange/infra/docker-compose/docker-compose.prod.yml \
                                     ps --format json | jq -e 'all(.Health == "healthy" or .Health == "")' >/dev/null; then
                echo "healthy after $((i*3))s"; break
              fi
              sleep 3
            done

      - name: Install smoke deps
        run: |
          cd tests/smoke
          npm ci
          npx playwright install --with-deps chromium

      - name: Run smoke tests against live URL
        id: smoke
        env:
          SMOKE_BASE_URL: https://${{ vars.PUBLIC_HOST }}
        run: cd tests/smoke && npm run smoke:all

      - name: Record new last-good tag
        if: steps.smoke.outcome == 'success'
        uses: appleboy/ssh-action@v1.0.3
        with:
          host:     ${{ secrets.ORACLE_VM_HOST }}
          username: ${{ secrets.ORACLE_VM_USER }}
          key:      ${{ secrets.ORACLE_VM_SSH_KEY }}
          script: |
            echo "${{ steps.v.outputs.version }}" | sudo tee /var/lib/filternarrange/last-good-tag

      - name: Rollback on smoke failure
        if: failure() && steps.smoke.outcome == 'failure'
        uses: appleboy/ssh-action@v1.0.3
        with:
          host:     ${{ secrets.ORACLE_VM_HOST }}
          username: ${{ secrets.ORACLE_VM_USER }}
          key:      ${{ secrets.ORACLE_VM_SSH_KEY }}
          script: |
            set -euo pipefail
            PREV_TAG="$(cat /var/lib/filternarrange/last-good-tag 2>/dev/null || echo '')"
            [[ -n "$PREV_TAG" ]] || { echo "no previous good tag — manual fix"; exit 1; }
            echo "rolling back to ${PREV_TAG}"
            sudo sed -i "s|^FNA_VERSION=.*|FNA_VERSION=${PREV_TAG}|" /etc/filternarrange/prod.env
            sudo systemctl restart filternarrange

      - name: Upload smoke artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: smoke-results-${{ steps.v.outputs.version }}
          path: |
            tests/smoke/smoke-results.xml
            tests/smoke/test-results/
          if-no-files-found: ignore
```

- [ ] **Step 3: Verify**

Run: `bash .github/workflows/deploy.test.sh` — expected `OK`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/deploy.yml .github/workflows/deploy.test.sh
git commit -m "feat(ci): tag-triggered deploy to Oracle Always-Free with smoke + rollback"
```

---

## Task 8: Oracle provisioning runbook

**Files:** Create `docs/deploy/oracle-always-free.md`.

- [ ] **Step 1: Write the runbook**

Create `docs/deploy/oracle-always-free.md`:

````markdown
# Deploying FilterNArrange on Oracle Cloud Always-Free

Shape: **VM.Standard.A1.Flex** — 4 OCPU ARM Ampere, 24 GB RAM, 200 GB boot volume, Ubuntu 22.04 ARM. Cost: **$0/month**.

After v1.0.0, re-deploys are automated by `.github/workflows/deploy.yml`. This document covers first-time provisioning only.

## 0. Manual rehearsal checklist (do once before tagging v1.0.0)

Tick each box only after executing the step against a real Oracle VM. Do not tag v1.0.0 until every box is checked.

- [ ] §1: Always-Free shape provisioned, public IP allocated
- [ ] §2: Security list inbound rules verified
- [ ] §3: DNS record resolves globally (`dig +short` from two networks)
- [ ] §4: `bootstrap.sh` ran cleanly; `ufw status` shows three allow rules
- [ ] §5: `/etc/filternarrange/prod.env` populated; mode 0600
- [ ] §6: `systemctl start filternarrange` brought the stack up healthy
- [ ] §7: Both Ollama models pulled (`ollama list` shows `qwen2.5:3b` and `llama3.1:8b`)
- [ ] §8: `seed-prod-admin` succeeded; admin can log in via public URL
- [ ] §9: `curl https://<host>/api/v1/health` returns `{"status":"UP"}` over real TLS
- [ ] §10: Smoke suite from laptop against the live URL passes all 5 checks
- [ ] §11: Rollback rehearsal: edit FNA_VERSION to earlier tag, restart, confirm older images, restore
- [ ] Cross-arch image rehearsal: `docker pull --platform linux/arm64 ghcr.io/.../gateway:latest` on Oracle + `linux/amd64` on dev box both succeed and `--version` works

## 1. OCI account & shape

1. Sign up at <https://www.oracle.com/cloud/free/>. Always-Free A1 quota is up to 4 OCPUs / 24 GB across A1 instances — use it all in one VM.
2. Compute → Instances → Create instance:
   - Name: `filternarrange-prod`
   - Image: Canonical Ubuntu 22.04 (ARM)
   - Shape: VM.Standard.A1.Flex → 4 OCPUs, 24 GB
   - Assign a public IPv4
   - Paste your SSH public key
   - Boot volume: 200 GB
3. Wait ~2 min for **Running**; note the public IP.

## 2. Inbound security list

VCN → Security Lists → Default → Add Ingress Rules:

| Source        | Protocol | Port | Comment |
|---------------|----------|------|---------|
| `<your-ip>/32` | TCP     | 22   | SSH (your IP only) |
| `0.0.0.0/0`   | TCP      | 80   | HTTP (ACME + redirect) |
| `0.0.0.0/0`   | TCP      | 443  | HTTPS |

Delete the default `0.0.0.0/0 → 22` rule. UFW (Task 4) is the second layer.

## 3. DNS (Cloudflare free)

Add an A record `filternarrange.<your-domain>` → OCI public IP. **Proxy: DNS only (grey cloud)** — orange proxy breaks the ACME HTTP-01 challenge. Verify: `dig +short filternarrange.<your-domain>`.

## 4. Host bootstrap

```bash
ssh ubuntu@<oracle-ip>
sudo mkdir -p /opt/filternarrange && sudo chown ubuntu:ubuntu /opt/filternarrange
# from laptop:
rsync -a infra/ ubuntu@<oracle-ip>:/opt/filternarrange/infra/
# on VM:
sudo bash /opt/filternarrange/infra/deploy/bootstrap.sh
```

Verify: `docker compose version` (≥ v2.20), `sudo ufw status` (22/80/443 allow), `systemctl is-enabled filternarrange` (enabled).

## 5. Production env

```bash
sudo cp /opt/filternarrange/infra/deploy/prod.env.example /etc/filternarrange/prod.env
sudo chmod 600 /etc/filternarrange/prod.env
sudo nano /etc/filternarrange/prod.env
```

Replace secrets with `openssl rand -base64 <N>`. Set `PUBLIC_HOST`, `ACME_EMAIL`. Keep `FNA_VERSION=v1.0.0`.

## 6. Start the stack

```bash
sudo systemctl start filternarrange
sudo journalctl -u filternarrange -f       # in one shell while images pull (~5–10 min)
sudo docker compose -f /opt/filternarrange/infra/docker-compose/docker-compose.yml \
                    -f /opt/filternarrange/infra/docker-compose/docker-compose.prod.yml ps
```

All services should reach `running (healthy)` within 5 min after pulls.

## 7. Pull Ollama models

```bash
COMPOSE='sudo docker compose -f /opt/filternarrange/infra/docker-compose/docker-compose.yml -f /opt/filternarrange/infra/docker-compose/docker-compose.prod.yml'
$COMPOSE exec ollama ollama pull qwen2.5:3b
$COMPOSE exec ollama ollama pull llama3.1:8b
```

## 8. Seed the first admin

```bash
$COMPOSE exec gateway ./bin/seed-prod-admin you@example.com "Site Admin"
```

Capture the printed temp password. Log in at `https://filternarrange.<your-domain>` and rotate immediately.

## 9. First-boot smoke

```bash
curl -fsSL https://filternarrange.<your-domain>/api/v1/health | jq .
# {"status":"UP"}
```

From laptop:

```bash
cd tests/smoke
SMOKE_BASE_URL=https://filternarrange.<your-domain> npm run smoke:all
```

## 10. Hand off to automation

```bash
git tag -a v1.0.1 -m "patch"
git push origin v1.0.1
```

`deploy.yml` builds multi-arch images, SSHes in, restarts, runs smoke, rolls back on failure.

## 11. Rollback rehearsal

```bash
ssh ubuntu@<oracle-ip>
echo "v0.9.0" | sudo tee /var/lib/filternarrange/last-good-tag
sudo sed -i 's|^FNA_VERSION=.*|FNA_VERSION=v0.9.0|' /etc/filternarrange/prod.env
sudo systemctl restart filternarrange
# confirm older images running, then restore FNA_VERSION=v1.0.0 and restart
```
````

- [ ] **Step 2: Commit**

```bash
git add docs/deploy/oracle-always-free.md
git commit -m "docs(deploy): Oracle Always-Free provisioning runbook + manual rehearsal checklist"
```

---

## Task 9: Secrets documentation

**Files:** Create `docs/deploy/secrets.md`.

- [ ] **Step 1: Write**

Create `docs/deploy/secrets.md`:

```markdown
# Deploy Secrets

Secrets live only in GitHub Actions repo settings and in `/etc/filternarrange/prod.env` on the VM. Never committed, never echoed, never logged.

## Repository secrets (Settings → Secrets and variables → Actions → Secrets)

| Name | Purpose | How to obtain |
|------|---------|---------------|
| `ORACLE_VM_HOST` | Public IP or DNS of the Oracle VM | OCI console |
| `ORACLE_VM_USER` | SSH user | `ubuntu` for Canonical images |
| `ORACLE_VM_SSH_KEY` | Private key with access to the VM | `ssh-keygen -t ed25519 -f deploy_key`; add `.pub` to `~ubuntu/.ssh/authorized_keys` |

## Repository variables (non-secret)

| Name | Example | Purpose |
|------|---------|---------|
| `PUBLIC_HOST` | `filternarrange.example.com` | FQDN used by deploy workflow as `SMOKE_BASE_URL` host and environment URL |

## On-VM (`/etc/filternarrange/prod.env`, mode 0600)

| Variable | Purpose |
|----------|---------|
| `FNA_VERSION` | Currently deployed tag; updated by the deploy workflow |
| `PUBLIC_HOST` | Same as the GitHub variable; consumed by Caddy + frontend |
| `ACME_EMAIL` | Let's Encrypt notifications |
| `JWT_SECRET` | HMAC secret for spring-jwt |
| `POSTGRES_USER`, `POSTGRES_PASSWORD` | Database credentials |
| `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` | Object-store credentials |
| `NL2FILTER_MODEL`, `SUMMARY_MODEL` | Ollama model selection |

## Rotation

- **JWT_SECRET:** rotation invalidates active sessions; coordinate via post-launch runbook.
- **POSTGRES_PASSWORD:** `ALTER USER` → update `prod.env` → `systemctl restart filternarrange`.
- **MINIO keys:** mint via MinIO console → update `prod.env` → restart.
- **SSH key:** generate new pair, append public, remove old, update GitHub secret.

## Anti-patterns

- Do not write secrets to environment in workflow YAML.
- Do not `cat /etc/filternarrange/prod.env` in any script that might end up in CI logs.
- Do not commit `prod.env` or any derived file.
- Do not store these in repo-root `.env` (which is for dev only and gitignored).
```

- [ ] **Step 2: Commit**

```bash
git add docs/deploy/secrets.md
git commit -m "docs(deploy): document GitHub Action and on-VM secrets, rotation, anti-patterns"
```

---

## Task 10: Post-launch monitoring runbook

**Files:** Create `docs/deploy/post-launch.md`.

- [ ] **Step 1: Write**

Create `docs/deploy/post-launch.md`:

````markdown
# Post-Launch Runbook (First 24 h)

Assumes the Plan G observability stack (Grafana + Prometheus + Loki + Alertmanager) is on the same VM.

## Dashboards to keep open

1. Stack overview — container CPU, memory, restarts
2. Gateway API latency — p50/p95/p99 per route
3. Async job queue — Redpanda lag, worker concurrency, job-state breakdown
4. Ollama — request rate, queue depth, p95 latency
5. Postgres — connections, slow queries, autovacuum
6. Disk + memory — `/var/lib/filternarrange/*` growth, swap usage

## What "normal" looks like

| Metric | Normal | Alert at |
|--------|--------|----------|
| Host CPU | < 15 % | > 70 % sustained 5 m |
| Host memory | 14–18 GB used | > 22 GB used |
| Host swap | 0 | any non-zero |
| Caddy 5xx rate | 0 | > 1 % over 5 m |
| Gateway p95 `/api/v1/detect` | < 500 ms | > 1 s |
| Gateway p95 `/api/v1/filter/preview` | < 1 s | > 2 s |
| AI NL→filter p95 | < 3 s | > 8 s |
| Ollama queue depth | < 2 | > 5 sustained |
| Postgres connections | < 30 | > 70 |
| Redpanda lag | < 100 | > 1000 sustained 5 m |
| Disk used `/var/lib/filternarrange` | < 60 % | > 80 % |

## Scale-down playbook (RAM pressure)

If host memory crosses 22 GB used or swap > 0:

```bash
ssh ubuntu@<oracle-ip>
sudo sed -i 's|^SUMMARY_MODEL=.*|SUMMARY_MODEL=qwen2.5:3b|' /etc/filternarrange/prod.env
sudo systemctl restart filternarrange
sudo docker compose -f /opt/filternarrange/infra/docker-compose/docker-compose.yml \
                    -f /opt/filternarrange/infra/docker-compose/docker-compose.prod.yml \
                    exec ollama ollama ps
# only qwen2.5:3b should be loaded
```

If still tight, stop retention-worker temporarily:

```bash
sudo docker compose [...] stop retention-worker
```

Log every change in the Incident Log below — never silently mutate config.

## Graceful offline

To take the site offline cleanly while keeping data services up:

```bash
sudo docker compose [...] stop frontend gateway
```

Caddy serves 502; to serve a maintenance page instead, drop a static `maintenance.html` into the caddy volume and add a `handle_errors` block. Bring back: `sudo docker compose [...] start gateway frontend`.

## Incident log

Append entries here as on-call deals with anything non-trivial.

```
### YYYY-MM-DD HH:MM UTC — short title
- Trigger:
- Action:
- Outcome:
- Follow-up issue:
```
````

- [ ] **Step 2: Commit**

```bash
git add docs/deploy/post-launch.md
git commit -m "docs(deploy): post-launch watch list, scale-down playbook, and graceful-offline"
```

---

## Task 11: ADR-0006 — Public release

**Files:** Create `docs/decisions/ADR-0006-public-release.md`.

- [ ] **Step 1: Write**

Create `docs/decisions/ADR-0006-public-release.md`:

```markdown
# ADR-0006 — Public release of FilterNArrange at v1.0.0

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06-07 |
| **Deciders** | piyush-official |
| **Supersedes** | — |
| **Related** | ADR-0001, ADR-0002 (license: Apache-2.0), ADR-0003, ADR-0004, ADR-0005 (tier model) |

## Context

Initial development happened in a private repo. The design spec flagged repo-flip-to-public once a license was chosen; ADR-0002 chose Apache-2.0. Plans A–G delivered the feature set + observability + supply-chain hardening. Plan H lifts the stack onto Oracle Always-Free with a real public URL.

## Decision

1. Cut release **v1.0.0**.
2. Flip the GitHub repository from private to public:
   ```bash
   gh repo edit piyush-official/FilterNArrange \
     --visibility public \
     --accept-visibility-change-consequences
   ```
3. License: Apache-2.0 (LICENSE already at repo root from ADR-0002).
4. First public URL: `https://filternarrange.<your-domain>` (actual host stays in `prod.env`, not committed).
5. SemVer (spec §7.3) applies strictly from v1.0.0 onward.

## Consequences

**Positive:** project becomes forkable and contributable under Apache-2.0; multi-arch GHCR images enable self-hosting on both x86 servers and ARM hobby boxes; Oracle Always-Free deploy gives the project a $0/month live demo.

**Negative / risks:** public-tier abuse is now possible. Mitigations: Caddy rate-limit on `/api/v1/auth/*`, per-user quotas in the gateway, UFW on the host, OCI security list narrowed for SSH.

**Follow-ups:** ADR-0007 will record first paid signup + any Stripe wiring. ADR-0008 will record any move off Oracle Always-Free.

## Execution checklist

- [ ] Plan H Task 14 manual rehearsal complete
- [ ] release-please PR for v1.0.0 reviewed and merged
- [ ] Tag `v1.0.0` exists; `deploy.yml` green
- [ ] Smoke suite passed against live URL
- [ ] `gh repo edit ... --visibility public ...` executed
- [ ] `docs/release-notes/v1.0.0.md` posted as GitHub Release body
- [ ] README updated with live URL + badge
```

- [ ] **Step 2: Commit**

```bash
git add docs/decisions/ADR-0006-public-release.md
git commit -m "docs(adr): ADR-0006 — public release at v1.0.0 under Apache-2.0"
```

---

## Task 12: v1.0.0 release notes

**Files:** Create `docs/release-notes/v1.0.0.md`.

- [ ] **Step 1: Write**

Create `docs/release-notes/v1.0.0.md`:

```markdown
# FilterNArrange v1.0.0 — Public Release

**Tag:** `v1.0.0` · **Date:** 2026-06-07 · **License:** Apache-2.0

FilterNArrange is an open-source web service for filtering, format conversion, and analysis of arbitrary user-provided data, with AI assistance powered by local open-weight models. This is the first public release.

Live demo: <https://filternarrange.example.com> *(replace with your actual host after deploy)*

## What v1.0.0 includes

**Ingestion:** file upload + direct paste. Auto-detection of CSV, TSV, JSON, JSONL, XML, YAML, XLSX with confidence + fallback flow.

**Filter modes:** column projection, row conditions, expression / SQL-like, regex search.

**Conversion:** any-to-any across all 7 launch formats via canonical TabularData / TreeData. Streaming where the format allows.

**Analysis:** summary statistics, group-by aggregations, auto-suggested charts (Vega-Lite specs), schema/structure inference.

**AI (local Ollama):** NL→filter (`qwen2.5:3b` on Always-Free, `qwen2.5:7b` on 32 GB hosts), auto summary (`llama3.1:8b`), chart suggest, anomaly detection.

**Tier system:** free vs paid levers — file-size, daily ops, recipe storage, advanced features. Stripe wiring deferred until first paid signup.

**Async batch:** Redpanda + per-tier consumer groups so free traffic cannot starve paid.

**Auth:** Spring Security + JWT default; Keycloak available as a Compose profile.

**Operations:** multi-arch (amd64 + arm64) GHCR images; Cosign signing + SBOM (Plan G); tag-triggered deploy with smoke gating and automatic rollback; Grafana / Prometheus / Loki observability; nightly Postgres backups (14-day retention).

## Breaking changes

None. First public release.

## Migration notes

None. First public release.

## Performance snapshot (k6, Oracle Always-Free 4 vCPU / 24 GB)

| Operation | p95 budget | p95 observed |
|-----------|-----------|--------------|
| `/api/v1/detect` | 500 ms | (fill in at tag time) |
| `/api/v1/filter/preview` (100k rows) | 1 s | (fill in at tag time) |
| `/api/v1/ai/nl-to-filter` | 3 s | (fill in at tag time) |

## Plugin compatibility

Plugin API version **v1**. All 7 launch format plugins, 4 filter operators, 4 analysis modules, and the Ollama LLM provider target v1. No quarantined plugins.

## Contributors

- @piyush-official — design, architecture, implementation

Future contributors will land here automatically via release-please.

## Links

- Repo: <https://github.com/piyush-official/FilterNArrange>
- Design spec: [docs/superpowers/specs/2026-06-07-filternarrange-design.md](../superpowers/specs/2026-06-07-filternarrange-design.md)
- ADRs: [docs/decisions/](../decisions/)
- Deploy runbook: [docs/deploy/oracle-always-free.md](../deploy/oracle-always-free.md)
- Post-launch runbook: [docs/deploy/post-launch.md](../deploy/post-launch.md)
```

- [ ] **Step 2: Commit**

```bash
git add docs/release-notes/v1.0.0.md
git commit -m "docs(release): v1.0.0 announcement"
```

---

## Task 13: README badges + live URL

**Files:** Modify `README.md`.

- [ ] **Step 1: Inspect existing README**

Run: `cat README.md | head -40`
Expected: a README created in Plan A with badges row + project description.

- [ ] **Step 2: Add badges and live URL block**

Use `Edit` to insert the following directly under the existing badges row (do not rewrite the file):

```markdown
[![Release](https://img.shields.io/github/v/release/piyush-official/FilterNArrange?style=flat-square)](https://github.com/piyush-official/FilterNArrange/releases)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=flat-square)](LICENSE)
[![Deploy](https://img.shields.io/badge/deploy-Oracle%20Always--Free-orange?style=flat-square)](docs/deploy/oracle-always-free.md)
[![Live](https://img.shields.io/website?url=https%3A%2F%2Ffilternarrange.example.com%2Fapi%2Fv1%2Fhealth&style=flat-square&label=live)](https://filternarrange.example.com)

**Live demo:** <https://filternarrange.example.com> *(replace with your actual host)*
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add release/license/deploy/live badges and live URL pointer"
```

---

## Task 14: End-to-end deploy rehearsal against a real Oracle VM

No code produced; this exercises every prior task against a live VM and ticks `oracle-always-free.md` §0.

- [ ] **Step 1:** Provision the VM per §1–§3 of the runbook.
- [ ] **Step 2:** Run `bootstrap.sh`; tick §4.
- [ ] **Step 3:** Populate `/etc/filternarrange/prod.env`; tick §5 (`stat -c %a` → `600`).
- [ ] **Step 4:** `sudo systemctl start filternarrange`; tick §6 (all services healthy in 5 min).
- [ ] **Step 5:** Pull models, run `seed-prod-admin`, run smoke suite from laptop; tick §7–§10.
- [ ] **Step 6:** Rollback rehearsal per §11.
- [ ] **Step 7:** Cross-arch image pull rehearsal:

```bash
# On x86 dev box:
docker pull --platform linux/amd64 ghcr.io/piyush-official/filternarrange/gateway:latest
docker run --rm --platform linux/amd64 ghcr.io/piyush-official/filternarrange/gateway:latest --version
# On Oracle Ampere:
docker pull --platform linux/arm64 ghcr.io/piyush-official/filternarrange/gateway:latest
docker run --rm --platform linux/arm64 ghcr.io/piyush-official/filternarrange/gateway:latest --version
```

Both must succeed.

- [ ] **Step 8:** Tick all boxes in `docs/deploy/oracle-always-free.md` §0 and commit:

```bash
git add docs/deploy/oracle-always-free.md
git commit -m "docs(deploy): mark Oracle Always-Free rehearsal checklist complete"
```

---

## Task 15: Tag v1.0.0 (orchestrator action — not executed by the agent)

The agent prepares; the human merges the release PR and flips visibility.

- [ ] **Step 1:** Verify every required check on `main` is green; confirm release-please PR exists and bumps to v1.0.0.
- [ ] **Step 2:** Merge the Release PR. release-please creates tag `v1.0.0` and a GitHub Release; `release.yml` pushes multi-arch images; `deploy.yml` SSHes into Oracle, rolls forward, runs smoke, stays-or-rolls-back.
- [ ] **Step 3:** Replace the auto-generated Release body with `docs/release-notes/v1.0.0.md` content; fill in real k6 p95 numbers.
- [ ] **Step 4:** Flip the repo public:

```bash
gh repo edit piyush-official/FilterNArrange \
  --visibility public \
  --accept-visibility-change-consequences
```

- [ ] **Step 5:** Announce in the channels of your choosing using the release notes as canonical text.
- [ ] **Step 6:** Stand the 24 h watch per `docs/deploy/post-launch.md`. Log incidents in its Incident Log.

---

## Self-Review

**1. Spec coverage:**
- Multi-arch images & GHCR → Task 1.
- Production compose overlay (no builds, no dev ports, sized for 24 GB) → Task 2.
- Caddy prod with rate-limit + headers + xcaddy image → Task 3.
- Oracle runbook (account, security list, DNS, bootstrap, seed, smoke) → Task 8 (+ Task 14 rehearsal).
- Deploy CI with rollback → Task 7.
- Smoke suite (health, signup/login, upload/detect/filter, AI NL, job) → Task 6.
- Repo flip + v1.0.0 + release notes + README → Tasks 11, 12, 13, 15.
- Post-launch monitoring → Task 10.
- Secrets doc → Task 9.
- Manual rehearsal checklist → embedded in Task 8 doc, exercised in Task 14.

**2. Placeholder scan:** No `TBD`/`TODO` in plan steps. "(fill in at tag time)" inside release notes is an artifact-content marker the human fills in with k6 numbers — by design. `filternarrange.example.com` is explicitly flagged "replace with your actual host," consistent with the spec's instruction to keep the actual host out of the repo. `<your-domain>` / `<oracle-ip>` are operator-supplied parameters, documented as such.

**3. Type / name consistency:**
- `FNA_VERSION` identical across `prod.env.example`, Compose overlay, deploy workflow, rollback path.
- `PUBLIC_HOST` identical across `prod.env.example`, Caddyfile, frontend env, GitHub repo variable.
- `seed-prod-admin` wrapper path (`/app/bin/seed-prod-admin`) matches source location (`apps/gateway/src/main/resources/bin/seed-prod-admin`).
- Compose matrix `[gateway, data-engine, frontend, retention-worker, caddy]` identical to the release.yml matrix after Task 1 Step 3.
- Image namespace `ghcr.io/piyush-official/filternarrange/<app>` identical across release.yml, compose overlay, runbook, secrets doc.
- The `$COMPOSE` shorthand in the runbook expands to the same two `-f` paths as the systemd unit, the deploy workflow, and the smoke pre-flight.

**4. Intentional spec deltas:**
- Spec §2 listed Keycloak as default; Plan H defaults `AUTH_PROVIDER=spring-jwt` to save ~1 GB on a 24 GB host, with Keycloak re-enablement documented inline.
- Spec §10 referenced `docs/deploy-free-tier.md`; this plan delivers the more specific `docs/deploy/oracle-always-free.md` — identical intent, better filename.

No further fixes needed.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-07-H-public-deploy.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
