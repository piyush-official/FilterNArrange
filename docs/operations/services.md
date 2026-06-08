# Per-service deployment guidelines

Companion to `oracle-provisioning.md` (host bootstrap) and `migration-policy.md` (DB-only changes). This document describes what each service does, what it depends on, how to deploy it independently, what to monitor, and what its failure modes look like.

Order in this doc mirrors the **safe-startup order** — bring services up in this sequence; bring them down in reverse.

---

## 1. `postgres` — primary RDBMS

**Role:** Source of truth for users, sessions, subscriptions, jobs, audit log, format-requests, recipes, plugin registry. Flyway migrations V1-V10 are applied by the **gateway** on startup; postgres itself doesn't run any migration logic.

**Image:** `postgres:16-alpine`
**Ports:** `5432`
**Persistent state:** Docker volume `postgres-data` mounted at `/var/lib/postgresql/data`.
**Depends on:** Nothing.

**Required env:**
- `POSTGRES_USER` — DB role + default DB owner
- `POSTGRES_PASSWORD` — secret, must come from vault ([[feedback-secrets-vault-pattern]])
- `POSTGRES_DB` — initial database name

**Health:** `pg_isready` over the internal Docker network. Compose's healthcheck does `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB`.

**Deploy by itself:**
```bash
docker compose -f infra/docker-compose/docker-compose.yml up -d postgres
docker compose exec postgres psql -U filternarrange -d filternarrange -c '\l'
```

**Backup / restore:** see the `backup` service (cron-driven `pg_dump` to MinIO `backups/postgres/` bucket); restore via `infra/backup/restore.sh` (Plan G §T14).

**Failure modes:**
- *Disk full* → writes return `ERROR: could not extend file` → gateway 500s. Mitigation: alertmanager rule `DiskHigh` fires at 80% on the node-exporter `node_filesystem_avail_bytes`. See `incident-disk-pressure.md`.
- *WAL fsync stalls* → checkpoint logs show `slow checkpoint`. Common after kernel-page-cache pressure; restart the host process.
- *Migration drift* → gateway refuses to start (Flyway checksum mismatch). See `migration-policy.md`.

---

## 2. `redis` (Valkey 7)

**Role:** Rate-limiting counters, JWT denylist, session tier cache, idempotency keys.

**Image:** `valkey/valkey:7-alpine` (Valkey is the OSS Redis-compatible fork)
**Ports:** `6379`
**Persistent state:** ephemeral. All cached data is regeneratable; if the container restarts, IP rate-limit counters reset (acceptable in dev; in prod, the burst-window granularity tolerates this).
**Depends on:** Nothing.

**Required env:** none. No auth in dev. In prod, set `REDIS_PASSWORD` and reference from the gateway's `application.yml` (`REDIS_PASSWORD` env → `spring.data.redis.password`).

**Health:** `redis-cli ping`.

**Failure modes:**
- *Connection refused / DNS fail* → gateway tier filters (Plan F §T1-T5) **fail-open** so requests still complete. Audit-event for the bypass is emitted with `reason=redis-down`.
- *Memory pressure (`maxmemory` hit)* → eviction policy is `allkeys-lru`. Hot keys (rate-limit counters) survive; old denylist entries get evicted.

---

## 3. `minio` — S3-compatible object store

**Role:** Holds uploaded files (`uploads/` bucket), conversion/analysis results (`results/` bucket), and backups (`backups/` bucket).

**Image:** `minio/minio:latest`
**Ports:** `9000` (S3 API), `9001` (web console)
**Persistent state:** volume `minio-data` mounted at `/data`.

**Required env:**
- `MINIO_ROOT_USER` — admin login (server side)
- `MINIO_ROOT_PASSWORD` — admin secret (vault!)
- Apps (`gateway`, `data-engine`, `retention-worker`) read `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` (separate env names — compose bridges them; see PR #25 for the history).

**Health:** `mc ready local` or HTTP `GET /minio/health/live`.

**Buckets:** Gateway auto-creates `uploads/`, `results/`, `backups/` on startup (`MinioConfig.ensureBucket()`). Plan F retention worker (`retention-sweep --loop`) prunes per-tier blobs on a schedule.

**Failure modes:**
- *Auth mismatch* → "The Access Key Id you provided does not exist in our records" (this exact bug shipped before PR #25; the failure mode is now well-known). Always confirm `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY` match `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`.
- *Disk full* → writes 503. Alert from disk-pressure metric.
- *First-start credential drift* — once the volume is initialized with one set of credentials, changing the env-var values has no effect. Either rotate via `mc admin user`, or `down -v` the volume (destroys data) and recreate.

---

## 4. `redpanda` (Kafka-compatible)

**Role:** Async job pipeline backbone. Topics:
- `topic.v1.jobs.paid` / `topic.v1.jobs.free` — tier-routed work queues
- `topic.v1.job-results` — completion events back to the gateway
- `topic.v1.audit` — append-only audit stream
- `topic.v1.format-requests` — admin triage feed (Plan F §T15-T24)

**Image:** `redpandadata/redpanda:latest` (Kafka API compatible, no Zookeeper)
**Ports:** `9092` (Kafka, external), `19092` (internal), `9644` (Redpanda admin)
**Persistent state:** volume `redpanda-data` at `/var/lib/redpanda/data`.
**Depends on:** Nothing.

**Topic creation:** the one-shot `kafka-init` service runs `infra/kafka-init/create-topics.sh` after redpanda is healthy. Idempotent.

**Failure modes:**
- *Broker unreachable from worker* → workers retry forever (kafka-python default). Audit emits `reason=kafka-down`.
- *Disk full* → producers block; gateway timeouts on `JobService.publish()`. Alert: disk-pressure rule.
- *Topic missing* → first publish fails. Re-run `kafka-init` or recreate manually with `rpk topic create`.

---

## 5. `keycloak` (optional, `AUTH_PROVIDER=keycloak` only)

**Role:** OIDC identity provider. Dual-mode auth: default is `spring-jwt` (gateway-owned); flip `AUTH_PROVIDER=keycloak` to delegate.

**Image:** `quay.io/keycloak/keycloak:25.0`
**Ports:** `8085 → 8080` (HTTP), `9000` (management)
**Persistent state:** **none in dev** — `KC_DB=dev-mem` runs the embedded H2. For prod, switch to `KC_DB=postgres` and add a `keycloak-data` volume.
**Depends on:** Nothing for dev; postgres for prod.

**Required config:**
- `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD` — bootstrap admin (vault!)
- Mount the realm JSON: `infra/keycloak/realm-export.json` → `/opt/keycloak/data/import/`
- For prod, **DO NOT** commit dev users into the realm. See `secrets.md` and [[feedback-secrets-vault-pattern]].

**Deploy by itself (dev):**
```bash
AUTH_PROVIDER=keycloak docker compose up -d keycloak gateway frontend caddy
```

**Failure modes:**
- *Startup timeout* — realm import can take 60-90s on first boot. Bump healthcheck `start_period` accordingly.
- *Vert.x NPE on `HttpServerRequest.authority()`* — happens when a client (or healthcheck) sends HTTP/1.0 with no Host header. PR #25 fixed the dev healthcheck; any external clients must also use HTTP/1.1.
- *Realm import idempotency* — re-importing an already-imported realm is a no-op only if the file hash hasn't changed. Editing `realm-export.json` while the container is up requires a restart.

---

## 6. `ollama` (optional, only when AI capabilities are enabled)

**Role:** Local LLM runner. Hosts the NL→filter (qwen2.5) and summary (llama3.1) models.

**Image:** `ollama/ollama:latest`
**Ports:** `11434`
**Persistent state:** volume `ollama-data` at `/root/.ollama` — holds the downloaded models (each 2-8 GB).
**Depends on:** Nothing.

**Model download:** the `ollama-init` one-shot does `ollama pull qwen2.5:7b` + `ollama pull llama3.1:8b` after the daemon is healthy. **Not started by default** — the local-deploy-minus-AI path skips this on purpose. Without models, all `/api/v1/ai/*` gateway endpoints return `404 AI_CAPABILITY_DISABLED` (graceful by design).

**Resource cost:** at least one model in memory means **~6 GB RSS**. Don't run this on Oracle Always-Free's 24 GB without sizing the other services down.

**Deploy with full AI:**
```bash
docker compose up -d ollama ollama-init  # one-shot pulls; takes ~10-20 min
# then the rest of the stack as usual
```

---

## 7. `gateway` (Spring Boot, Java 21)

**Role:** Public API surface. Receives requests, applies auth + rate-limit + tier filters, talks to data-engine + Kafka + Postgres + Redis + MinIO. The OTel Java agent auto-instruments outbound HTTP + Kafka.

**Image:** `ghcr.io/piyush-official/filternarrange/gateway:vX.Y.Z` (built multi-arch)
**Ports:** `8080`
**Persistent state:** none. All state lives in postgres / redis / minio.
**Depends on:** postgres, redis, redpanda, minio (all `condition: service_healthy`).

**Required env (production-relevant subset):**
| Var | Purpose | Vault? |
|---|---|---|
| `SPRING_PROFILES_ACTIVE` | `prod` (enables JSON logging via logback-spring.xml) | no |
| `POSTGRES_HOST` / `_PORT` / `_USER` / `_PASSWORD` / `_DB` | DB connection | password |
| `REDIS_HOST` / `_PORT` / `_PASSWORD` | cache | password |
| `KAFKA_BOOTSTRAP` | comma-separated broker list | no |
| `MINIO_ENDPOINT` / `_ACCESS_KEY` / `_SECRET_KEY` | blob store | secret |
| `AUTH_PROVIDER` | `spring-jwt` or `keycloak` | no |
| `GATEWAY_JWT_SECRET` | HS256 signing key for spring-jwt mode | **yes** |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTel collector URL | no |
| `OTEL_TRACES_EXPORTER` | `otlp` or `none` | no |

**Health:** `GET /health` returns `{"status":"UP"}` (Spring Boot Actuator). `/actuator/prometheus` exposes metrics; `/actuator/info` exposes build info.

**Deploy:**
```bash
docker pull ghcr.io/piyush-official/filternarrange/gateway:v1.1.0
# inject env from vault, then:
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d gateway
```

**Smoke test post-deploy:**
```bash
curl -sf https://${PUBLIC_HOST}/health
curl -sf https://${PUBLIC_HOST}/api/v1/auth/config
```

**Failure modes:**
- *Flyway migration fails* → app refuses to start. See `migration-policy.md` for the expand-contract pattern.
- *MinIO credential mismatch* → `RuntimeException: minio ensure bucket: The Access Key Id you provided does not exist`. Check the access-key/secret-key vs root-user/root-password naming (this exact bug was a session-long debugging arc; see PR #25).
- *OTel agent loads but collector unreachable* → harmless warnings; metrics + traces silently dropped. No effect on request handling.
- *Circuit breaker open against data-engine* → 502 with `code=DATA_ENGINE_UNAVAILABLE`. Resilience4j; see `incident-circuit-breaker-open.md`.

---

## 8. `data-engine` (Python 3.12 FastAPI)

**Role:** Plugin-driven detect / filter / convert / analyse pipeline. Two run modes:
- `DATA_ENGINE_MODE=full` (default): serves HTTP on `:8000`
- `DATA_ENGINE_MODE=worker`: consumes from `topic.v1.jobs.*`, no HTTP server

**Image:** `ghcr.io/piyush-official/filternarrange/data-engine:vX.Y.Z`
**Ports:** `8000` (full mode only)
**Persistent state:** none.
**Depends on:** redis, redpanda, minio, ollama.

**Required env:**
| Var | Purpose | Vault? |
|---|---|---|
| `DATA_ENGINE_MODE` | `full` or `worker` | no |
| `REDIS_HOST` / `_PORT` / `_PASSWORD` |   | password |
| `KAFKA_BOOTSTRAP` |   | no |
| `MINIO_ENDPOINT` / `_ACCESS_KEY` / `_SECRET_KEY` |   | secret |
| `OLLAMA_HOST` | optional; `/api/v1/ai/*` returns 404 if unreachable | no |
| `OTEL_EXPORTER_OTLP_ENDPOINT` / `_TRACES_EXPORTER` |   | no |
| `LOG_LEVEL` | `info` (default), `debug` for noise |   |
| `FILTERNARRANGE_DISABLED_PLUGINS` | comma-separated entry-point names to skip |   |

**Health:** `GET /healthz` returns `{"status":"ok", formats, filters, analyses}`. **Currently formats/filters/analyses are empty** — known bug #18 in [[resume-v1-pending]] (plugins live outside the Dockerfile build context).

**Failure modes:**
- *Ollama unreachable* → AI endpoints 404 gracefully with `code=AI_CAPABILITY_DISABLED`. Not fatal.
- *Plugin missing* → request to detect/filter/convert returns 422 with `code=PLUGIN_NOT_FOUND`.
- *Worker mode + Kafka unreachable* → exponential backoff retry loop. Audit emits.

---

## 9. `frontend` (React 18 + Vite, served by nginx)

**Role:** Static SPA. Talks to the gateway via Caddy.

**Image:** `ghcr.io/piyush-official/filternarrange/frontend:vX.Y.Z`
**Ports:** `80` (internal only; Caddy fronts it)
**Persistent state:** none.
**Depends on:** gateway healthy.

**Health:** `GET /health` returns `{"status":"UP"}` on the in-container `127.0.0.1` (busybox wget resolves `localhost` to IPv6 first — see PR #25 history).

**Failure modes:**
- *API path mismatch* — frontend's typed client is generated from `contracts/openapi/gateway-public.v1.yaml` via `npm run gen:api`. The generated client may drift from the spec — see resume-v1-pending #12.
- *Chart panels show empty data* — resume-v1-pending #1 (real user-facing bug).
- *Healthcheck false-negative* — fixed in PR #25; reads `127.0.0.1` explicitly.

---

## 10. `retention-worker` (Python sweeper, daemon)

**Role:** Plan F §T29 retention sweeper. Walks `uploads/` and `results/` MinIO buckets every `RETENTION_INTERVAL_MINUTES` (default 60), reads each object's owner UUID + tier from the path / metadata, deletes per-tier expired blobs.

**Image:** same as `data-engine`; entrypoint overridden to `retention-sweep --loop`.
**Persistent state:** none.
**Depends on:** postgres (tier lookup), minio (blob walk).

**Required env:** subset of data-engine's env. See compose for the full list. Both `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` and `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY` are accepted (PR #25 made the cli.py forgiving).

**Health:** no healthcheck — liveness = process running.

**Failure modes:**
- *Postgres tier lookup fails* → falls back to `free` tier cutoffs (conservative; deletes older).
- *MinIO list_objects 503* → sweep skipped; next interval retries.

---

## 11. `caddy` — TLS terminator + reverse proxy

**Role:** Public edge. Routes `/api/* /ws/* /health` → gateway; everything else → frontend. Holds Let's Encrypt certs in `caddy-data` volume.

**Image:** `ghcr.io/piyush-official/filternarrange/caddy:vX.Y.Z` (xcaddy build with `caddy-ratelimit` module)
**Ports:** `8443` (dev) or `443` (prod).
**Persistent state:** `caddy-data` + `caddy-config` volumes (holds ACME account, cert chain). **Don't `down -v` in prod** — you'll re-issue certs and hit Let's Encrypt rate limits.
**Depends on:** gateway + frontend healthy.

**Config:** dev uses `infra/caddy/Caddyfile` (`local_certs`); prod uses `infra/caddy/Caddyfile.prod` (Let's Encrypt + rate-limits 10/min on auth, 600/min on API).

**Failure modes:**
- *Cert renewal blocked* → existing cert remains valid until expiry; alert on `caddy_certificates_expires_seconds < 7d`.
- *Backend upstream down* → 502; client retries.

---

## 12-15. Observability quartet (`prometheus`, `alertmanager`, `grafana`, `node-exporter`)

**Role:** metrics. Prometheus scrapes gateway `/actuator/prometheus`, data-engine `/metrics`, and node-exporter for host metrics. Alertmanager handles routing. Grafana renders the 5 FilterNArrange dashboards (api-latency, plugin-performance, job-pipeline, ai-capabilities, infra) + the standard Prometheus / Loki / Tempo datasources.

**Persistent state:**
- `prometheus`: stores TSDB at `/prometheus`. In dev, ephemeral; in prod, persist with a `prometheus-data` volume.
- `grafana`: SQLite at `/var/lib/grafana`. Dashboards are file-provisioned (read-only from `/var/lib/grafana/dashboards`).

**Configs:** `infra/observability/{prometheus,alertmanager,grafana}/`. See [[reference-colima-testcontainers-fix]] for the Loki/Tempo IDs referenced from dashboards.

**Failure modes:**
- *Prometheus disk fill* → drops old samples per `--storage.tsdb.retention.time` (default 15d).
- *Grafana datasource unhealthy* → individual panels show "no data" rather than failing the dashboard.

---

## 16-19. Log + trace pipeline (`loki`, `promtail`, `tempo`, `otel-collector`)

**Role:** logs (`loki` + `promtail`) and traces (`tempo` + `otel-collector`).

**Persistent state:**
- `loki`: chunks at `/tmp/loki` — ephemeral in dev. Prod needs a `loki-data` volume.
- `tempo`: blocks at `/tmp/tempo` — same.

**Known issue (see [[resume-v1-pending]] #19):** Promtail's relabel_configs only set `container`/`job` labels for containers matching `/fna-.*/` — other containers ship label-less streams and Loki rejects them with `at least one label pair is required per stream`. Logs from FNA services should be there, but application-side log panels in Grafana render empty until #19 is fixed.

**Failure modes:**
- *Loki disk fill* → 503 on writes; Promtail buffers and retries.
- *Tempo block-time misconfig* → searches return empty even when traces are flushing. Default 24h block_retention is fine for dev.
- *OTel Collector backpressure* → memory_limiter trips at 256 MiB; spans dropped with a metric `otelcol_processor_dropped_spans`. Tune limit_mib up in prod.

---

## 20. `backup` (cron container)

**Role:** Plan G §T14. Alpine + `dcron`. 02:30 UTC: `pg_dump | gzip` → `minio/backups/postgres/{date}.sql.gz` with 14-day retention. 03:00 UTC: `mc mirror` of `uploads/` + `results/` to `backups/snapshots/`.

**Image:** custom — built from `infra/backup/Dockerfile`.
**Persistent state:** none — backups are written into MinIO.
**Depends on:** postgres, minio.

**Restore:** see `infra/backup/restore.sh` (manual; planned to be auto-tested by Plan G PR-3 T15 once it lands — see [[resume-v1-pending]] #5).

---

# Cross-service rollout patterns

## Routine deploy (a new tag landed; nothing schema-breaking)
1. CI publishes `:vX.Y.Z` images to GHCR (`deploy.yml` workflow).
2. SSH `deploy.yml` step updates `FNA_VERSION` in `/etc/filternarrange/prod.env`.
3. `systemctl restart filternarrange` — compose pulls new images and recreates containers.
4. Wait 90s for healthy; bash smoke runs.
5. On smoke pass: `last-good-tag` recorded. On fail: rollback to the previous tag, restart.

## Schema-breaking deploy (Flyway migration)
See `migration-policy.md` — expand-contract pattern, never destructive in one step.

## Adding a new service (Loki / Tempo etc. landed via §T8 was a recent example)
1. Add the service block to `docker-compose.yml`.
2. Add config files under `infra/observability/<service>/`.
3. Bring up locally: `docker compose up -d <service>`. Check `docker compose logs <service>` for parse errors.
4. Wire any dependents' env or volume mounts.
5. Add a dashboard panel or Prometheus scrape config so the service is observable.

## Pulling images by tag
```bash
docker pull ghcr.io/piyush-official/filternarrange/gateway:v1.1.0
docker pull ghcr.io/piyush-official/filternarrange/data-engine:v1.1.0
docker pull ghcr.io/piyush-official/filternarrange/frontend:v1.1.0
docker pull ghcr.io/piyush-official/filternarrange/caddy:v1.1.0
```
All multi-arch (linux/arm64 + linux/amd64). Public — no GHCR login needed.

## Tearing down cleanly
```bash
docker compose -f infra/docker-compose/docker-compose.yml down       # stop, keep volumes
docker compose -f infra/docker-compose/docker-compose.yml down -v    # stop AND delete volumes (loses postgres / minio / etc.)
```
