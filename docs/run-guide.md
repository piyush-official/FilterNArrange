# FilterNArrange — Run Guide

> The practical "how do I run this on my machine" doc. A fresh contributor should be able to follow this end-to-end and be running in under an hour.

## 1. Hardware tiers

| Tier | RAM | CPU | Disk | GPU | What you get |
|---|---|---|---|---|---|
| **Minimum** | 16 GB | 4 cores (x86-64 or arm64) | 25 GB free | none | Whole stack runs; AI inference is CPU-only (5–20 s per query). Acceptable for development. |
| **Recommended** | 32 GB | 8 cores | 50 GB free | optional | Comfortable — all services + observability + browser + IDE without swap. |
| **AI-comfort** | 32 GB + GPU | 8 cores | 60 GB free | NVIDIA ≥ 8 GB VRAM or Apple Silicon M-series | Ollama uses the GPU; AI features respond in < 1 s. |
| **Free-tier deploy** (Oracle Always-Free) | 24 GB | 4 vCPU ARM Ampere | 200 GB block | none | Fits the full stack; CPU AI is slow but works. |

### RAM budget (full stack with AI, idle)

| Service | RAM |
|---|---|
| Postgres | ~300 MB |
| Redis | ~50 MB |
| Redpanda (Kafka) | ~700 MB |
| MinIO | ~200 MB |
| Keycloak | ~1.0 GB *(fallback: Spring-Security+JWT ≈ ~50 MB)* |
| Gateway (Spring Boot) | ~600 MB |
| Data-engine (Python) | ~400 MB |
| Ollama + Llama 3.1 8B Q4 loaded | ~5.5 GB |
| Caddy | ~30 MB |
| Observability (Prometheus + Grafana + Loki + Tempo) | ~1.5 GB |
| **Total idle** | **~10.3 GB** |

Under load, allow 2–4 GB headroom for pandas/polars working sets and JVM GC.

## 2. Required software (host)

Install once:

| Tool | Version | macOS | Linux | Why |
|---|---|---|---|---|
| **Docker Engine + Compose v2** | 24+, Compose v2.20+ | `brew install --cask docker` (or Colima/OrbStack) | distro package | Runs everything |
| **Git** | 2.40+ | preinstalled / `brew install git` | distro package | Source control |
| **gh CLI** | 2.40+ | `brew install gh` | distro package | Repo, issues, PRs |
| **JDK 21** *(dev only)* | OpenJDK 21 LTS | `brew install --cask temurin@21` | `apt install temurin-21-jdk` | Local gateway dev |
| **Node.js** *(dev only)* | 20.x LTS | `brew install node@20` | nvm | Local frontend dev |
| **Python** *(dev only)* | 3.12.x | `brew install python@3.12` | `uv` or distro | Local data-engine dev |
| **uv** *(dev only)* | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | same | Fast Python deps manager |
| **mkcert** *(optional)* | latest | `brew install mkcert` | distro | Locally-trusted TLS certs |

You **don't need** JDK / Node / Python if you only want to *run* the stack. `docker compose up` covers everything.

## 3. Ports map

| Port | Service | Notes |
|---|---|---|
| `8443` | Caddy (HTTPS entry) | The only port you visit in a browser |
| `8080` | Spring Boot gateway | Internal-only via Caddy; exposed in dev for direct curl |
| `8000` | Python data-engine | Internal-only |
| `5173` | Vite dev server | Only when running frontend in dev mode outside compose |
| `5432` | Postgres | Local DB clients |
| `6379` | Redis | Optional local client |
| `9092` | Redpanda Kafka API | Producers/consumers |
| `9644` | Redpanda admin | `rpk` CLI |
| `9000` | MinIO API | Pre-signed URL endpoints |
| `9001` | MinIO console | Web UI |
| `8081` | Keycloak | Admin console + OIDC discovery |
| `11434` | Ollama | LLM HTTP API |
| `3000` | Grafana | Dashboards |
| `9090` | Prometheus | Metrics |
| `3100` | Loki | Logs |
| `3200` | Tempo | Traces |

Conflicts → override in `docker-compose.override.yml` (copy from `.example`).

## 4. First-run sequence

```bash
# 1. Clone
git clone git@github.com:piyush-official/FilterNArrange.git
cd FilterNArrange

# 2. Copy env template
cp .env.example .env
# Edit .env if you want to override defaults

# 3. (Optional) Use Spring-Security+JWT instead of Keycloak to save ~1 GB RAM
echo "AUTH_PROVIDER=spring-jwt" >> .env

# 4. Pull the Ollama model in advance (~5 GB)
docker compose pull ollama
docker compose run --rm ollama-init   # pulls llama3.1:8b and qwen2.5:7b

# 5. Bring up the stack
docker compose up -d

# 6. Wait for health (polls every /health endpoint)
./scripts/wait-for-healthy.sh

# 7. Seed dev data (admin user, default tier configs, sample fixtures)
docker compose exec gateway ./bin/seed-dev

# 8. Open the browser
open https://localhost:8443
# Accept the self-signed cert; mkcert removes this prompt if installed
```

Total time on a fresh machine with broadband: ~15 minutes (5 GB model download dominates).

## 5. Daily dev loop

```bash
# Start everything
docker compose up -d

# Tail logs from one service
docker compose logs -f gateway

# Run gateway locally with hot-reload (against compose-hosted deps)
cd apps/gateway && ./gradlew bootRun

# Run data-engine locally with hot-reload
cd apps/data-engine && uv run uvicorn filternarrange_engine.api.main:app --reload

# Run frontend locally with HMR
cd apps/frontend && npm run dev   # http://localhost:5173

# Run tests for one app
cd apps/gateway && ./gradlew test
cd apps/data-engine && uv run pytest
cd apps/frontend && npm test

# Integration suite (testcontainers — slow)
./scripts/test-integration.sh

# E2E suite (Playwright against compose stack — slowest)
./scripts/test-e2e.sh

# Stop everything
docker compose down

# Stop AND wipe volumes (fresh start)
docker compose down -v
```

## 6. Configuration matrix (`.env`)

Excerpt (full reference in `docs/configuration.md` — auto-generated from JSON schema):

```ini
# Identity
AUTH_PROVIDER=keycloak              # keycloak | spring-jwt
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=changeme    # MUST override outside local dev

# AI / Ollama
OLLAMA_HOST=http://ollama:11434
NL2FILTER_MODEL=qwen2.5:7b
SUMMARY_MODEL=llama3.1:8b
AI_TIMEOUT_SECONDS=30
AI_MAX_CONCURRENT=4

# Tier defaults (override for production launch)
FREE_TIER_MAX_UPLOAD_MB=5
FREE_TIER_DAILY_OPS=20
PAID_TIER_MAX_UPLOAD_MB=500
PAID_TIER_DAILY_OPS=10000           # 0 = unlimited

# Storage
MINIO_ROOT_USER=filternarrange
MINIO_ROOT_PASSWORD=changeme
UPLOAD_RETENTION_FREE_HOURS=24
UPLOAD_RETENTION_PAID_DAYS=30

# Postgres
POSTGRES_USER=filternarrange
POSTGRES_PASSWORD=changeme
POSTGRES_DB=filternarrange

# Observability
GRAFANA_ADMIN_PASSWORD=admin
LOG_LEVEL=info                      # debug | info | warn | error
```

## 7. Health checks

Every service exposes `/health` (liveness) and `/ready` (readiness). The `wait-for-healthy.sh` script polls all of them:

```
gateway        http://localhost:8080/health
data-engine    http://localhost:8000/health
postgres       pg_isready
redis          redis-cli ping
redpanda       rpk cluster health
minio          mc ready local
keycloak       http://localhost:8081/health/ready
ollama         http://localhost:11434/api/tags
```

CI uses the same script.

## 8. Troubleshooting (top 10)

| Symptom | Likely cause | Fix |
|---|---|---|
| `docker compose up` fails with "no space left on device" | Disk full from old images | `docker system prune -af --volumes` |
| Ollama returns 404 on first AI call | Model not pulled | `docker compose exec ollama ollama pull llama3.1:8b` |
| Gateway can't reach Python service | Compose network restart | `docker compose restart gateway data-engine` |
| Postgres connection refused | Postgres still starting | wait-for-healthy script; otherwise `docker compose logs postgres` |
| Frontend HMR doesn't refresh | Volume-mount issue on macOS | use Mutagen/OrbStack or set `CHOKIDAR_USEPOLLING=true` |
| AI calls time out on CPU-only | Model too big for hardware | switch model: `NL2FILTER_MODEL=qwen2.5:3b` |
| Keycloak takes 90 s+ to start | Cold JVM + realm import | normal; or `AUTH_PROVIDER=spring-jwt` for ~5 s startup |
| File upload > limit rejected | Tier enforcement working | raise `FREE_TIER_MAX_UPLOAD_MB` for local dev |
| Port already in use | Another host service | override in `docker-compose.override.yml` |
| Tests fail in CI but pass locally | TZ / locale / line endings | `git config --global core.autocrlf input`; CI fixed to UTC |

## 9. Cleaning up

```bash
# Stop containers; keep volumes (data persists)
docker compose down

# Stop containers AND drop all data
docker compose down -v

# Nuclear — drop everything Docker-related on the host
docker system prune -af --volumes
```

## 10. Free-tier deploy preview

When lifting to Oracle Always-Free (out of v1 scope but designed for):

- ARM-compatible images required → CI builds `linux/arm64` and `linux/amd64`.
- Caddy configured with the public Oracle IP + Let's Encrypt.
- Set `AUTH_PROVIDER=spring-jwt` if Keycloak's RAM is squeezing other services.
- Postgres backups to a separate Backblaze B2 bucket (~$0.20/mo for v1-scale data).
- Detailed steps land in `docs/deploy-free-tier.md` when we actually deploy.
