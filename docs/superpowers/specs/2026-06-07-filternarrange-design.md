# FilterNArrange — Design Specification

| | |
|---|---|
| **Status** | Accepted (initial design) |
| **Date** | 2026-06-07 |
| **Deciders** | piyush-official |
| **Related ADRs** | [ADR-0001 — Initial stack & principles](../../decisions/ADR-0001-initial-stack-and-principles.md) |
| **Pending ADRs** | ADR-0002 (license: AGPL-3.0 vs Apache-2.0), ADR-0003 (module-dependency & failure isolation rules), ADR-0004 (ticketing & versioning workflow) |

---

## Executive Summary

**FilterNArrange** is an open-source web service for **filtering, format conversion, and analysis of arbitrary user-provided data**, with AI assistance powered by local open-weight models. Users upload or paste data; the service auto-detects the format, lets them filter / transform / analyze in multiple modes, and exports to any supported format.

The system is **polyglot** (Spring Boot + React + Python), **loosely coupled** (versioned cross-service contracts, no shared databases, mode-flagged services), **plugin-driven** (every format, filter, analysis, and AI provider is a plugin), and **cost-aware** (entirely OSS-or-free-tier; total monthly spend in v1 is $0).

The project is being developed at <https://github.com/piyush-official/FilterNArrange> (private during initial development; will flip public once a license is chosen).

---

## §1 — Purpose & Scope

### Goals

- Accept data via **file upload** or **direct paste**.
- **Auto-detect format** and surface the result to the user (CSV, TSV, JSON, JSONL, XML, YAML, XLSX at launch; pluggable for more).
- **Filter** with four modes — column projection, row conditions, free-form expression / SQL-like, regex search.
- **Convert** any supported input format to any supported output format via a canonical intermediate model.
- **Analyze** — summary statistics, group-by aggregations, auto-generated charts, schema / structure inference.
- **AI assistance** — natural-language → filter, smart summary, AI-suggested chart, anomaly / data-quality detection. All running on local Ollama with open-weight models.
- **Tiered access** (free vs paid) with self-hosting always free; paid hosted tier funds maintenance.
- Run entirely on **open-source tooling**, designed for **local Docker Compose** in v1 and **free-tier cloud** (Oracle Always-Free) as the lift path.

### In scope (v1)

- File upload + direct paste ingestion
- Format auto-detection with confidence + fallback flows
- All four filter modes with a mode picker in the UI
- All four analysis features
- Format conversion any-to-any via canonical model
- All four AI features (Ollama-backed)
- Tier system with all four levers:
  - File-size limits (free capped; paid raised)
  - Daily-operation quotas (free per-day limit; paid unlimited or much higher)
  - **Saved recipes + extended job history** (free is effectively stateless beyond 90-day job log; paid can save named filter/convert/analyze recipes and retain job results long-term)
  - Advanced-feature gating (charts, SQL-mode filtering, schema inference, batch processing, API access — all paid-only)
- Format-request workflow: **community PR path** (free, OSS-native) + **prioritized maintainer-handled requests** (paid)
- Auth via Keycloak (with Spring Security + JWT as RAM-saving fallback)
- Async batch processing through Kafka (Redpanda OSS)
- Local Docker Compose deployment; designed for free-tier (Oracle Always-Free) lift
- Full engineering workflow: GitHub Issues, SemVer, Conventional Commits, ADRs, CI gates, test pyramid, regression tracking

### Out of scope (v1) — explicit YAGNI

- Database / URL ingestion (file + paste only)
- Real-time collaborative editing
- Multi-tenant organization management (just users + tiers)
- Mobile apps
- Enterprise SSO (Keycloak supports it later)
- Stripe integration (deferred until first paid customer signs)
- Public deployment (designed for, but not part of v1)
- Kubernetes (Docker Compose only in v1; k3s as upgrade path)
- Public share links / shared-recipe browsing (recipes are private-to-user in v1; `recipes.is_shared` exists for future use but no sharing UI ships in v1)

### Success criteria

- Filter preview on a 100 000-row CSV completes in **< 1 s** (sync path).
- Format detection is correct on **> 95 %** of well-formed inputs across the launch set.
- Adding a new format adapter requires changes to **exactly one module** and **zero core files**.
- Any one of {gateway, data-engine, AI module, Ollama, Kafka, Postgres, Redis, MinIO, Keycloak} can be replaced or upgraded without code changes in the others.
- All tooling in v1 has **$0 monthly spend** (per `docs/cost-tracking.md`).

---

## §2 — Architecture

### Service map

```
┌─────────────────────────────────────────────────────────────────────┐
│  React frontend (Vite + TypeScript, served by Nginx)                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  HTTPS  (REST /api/v1 + WebSocket)
┌──────────────────────────────▼──────────────────────────────────────┐
│  Spring Boot gateway                                                │
│  - Auth (Keycloak OIDC or Spring-JWT fallback)                      │
│  - Tier & quota enforcement                                         │
│  - Routing to data-engine                                           │
│  - Format-request ticketing                                         │
│  - Saved sessions API                                               │
│  - WebSocket push for async results                                 │
└────┬───────────────┬─────────────────────┬──────────────────────────┘
     │ REST          │ Kafka produce       │ JDBC / Redis client
     ▼               ▼                     ▼
┌─────────────┐ ┌──────────────┐  ┌──────────────────────────┐
│ Python      │ │ Redpanda     │  │ Postgres │ Redis         │
│ data-engine │ │ topics:      │  │ (users,  │ (rate-limits, │
│ + AI module │ │  jobs,       │  │  jobs,   │  sessions,    │
│ (FastAPI)   │ │  job-results,│  │  tickets,│  cache)       │
│             │ │  format-req, │  │  recipes,│               │
│             │ │  audit       │  │  audit)  │               │
└──┬──────────┘ └─────┬────────┘  └──────────┴───────────────┘
   │ async results  ▲ │
   │ pushed via WS  │ │ consume
   └────────────────┘ │
                     ┌▼────────────────────┐
                     │ Python async-worker │  (same image, MODE=worker)
                     └──┬──────────────────┘
                        │ HTTP
                        ▼
                   ┌──────────────┐    ┌─────────┐
                   │ Ollama       │    │ MinIO   │
                   │ (LLM runtime)│    │ (files) │
                   └──────────────┘    └─────────┘
```

### Loose-coupling rules (the six)

1. **One service owns each datastore.** Gateway owns Postgres. Python owns its slice. Redis is prefixed by writer service. No cross-service direct DB reads — ever.
2. **Frontend only talks to the gateway.** Python service is not network-reachable from outside the compose network.
3. **All cross-service calls are versioned contracts.** REST in OpenAPI; Kafka in JSON Schema. Both sides validate against the same file.
4. **Versioned APIs from day one.** Everything is `/api/v1/...` and `topic.v1.<name>`. Bumps are explicit.
5. **Plugins are the only extension point.** Adding a format, filter, analysis, AI provider, or storage backend never modifies core code.
6. **Mode flag on the Python service** (`MODE=full|data|ai|worker`). Same image, different responsibilities. Splitting into separate services later is a Compose-file edit, not a rewrite.

### What we deliberately don't do (cost-aware)

- No service mesh (Istio/Linkerd) — Docker Compose networking is enough.
- No gRPC/protobuf — REST + OpenAPI meets v1 latency targets.
- No service discovery — Compose DNS works.
- No event-bus abstraction over Kafka — Kafka is the bus.
- No separate AI service in v1 — controlled via `MODE` flag, splittable later.
- No managed Postgres / Kafka / object storage — self-hosted via Compose.

---

## §3 — Data Flow & Contracts

### Sync path (interactive)

Used for: format detection, filter preview, small conversions, single-call analysis on small inputs.

```
React ──POST /api/v1/detect──▶ Gateway
                                  │  check tier + quota (Redis)
                                  │  ✓
                                  ▼
                            MinIO ◀── put file blob
                                  │
                                  ▼
                            Python service (MODE=full)
                                  │  format detector → result
                                  ▼
   ◀──── 200 OK { format, confidence, schema } ── Gateway
```

**Latency budgets** (enforced by k6 in CI):

- Detection p95 < 500 ms
- Filter preview on 100 k rows p95 < 1 s
- AI NL→filter p95 < 3 s

**Sync trigger rules** (gateway-enforced): payload ≤ 25 MB **and** estimated rows ≤ 500 k **and** operation is not `batch-process`. Above any threshold → async path.

### Async path (Kafka)

Used for: paid batch jobs, large file processing, AI auto-insights on full datasets, format-request submissions.

```
React ──POST /api/v1/jobs──▶ Gateway
                              │  persist Job row (Postgres)
                              │  produce → topic.v1.jobs
                              ▼
                        { job_id, status: queued }

   React opens WebSocket to /ws/jobs/{job_id}

   Python worker consumes job → processes → writes result blob to MinIO
                              │  updates Job row + produces → topic.v1.job-results

   Gateway consumer ── push update via WebSocket ──▶ React
```

**Job state machine:** `queued → running → (completed | failed | cancelled)`. Postgres holds canonical state; Kafka is transport only.

### Contracts (the loose-coupling backbone)

```
contracts/
├── openapi/
│   ├── gateway-public.v1.yaml      # React calls
│   └── gateway-internal.v1.yaml    # gateway calls Python
└── kafka/
    ├── topic.v1.jobs.schema.json
    ├── topic.v1.job-results.schema.json
    ├── topic.v1.format-requests.schema.json
    └── topic.v1.audit-events.schema.json
```

**Rules:**

1. Contracts are versioned independently of code. A v1 contract is immutable; additive changes get a sibling v2.
2. Both sides validate against the same schema. Spring Boot generates DTOs from OpenAPI at build; Python uses `pydantic` models generated from the same files.
3. **No service imports another service's source code.** Only the schemas.
4. CI fails if a contract changes without bumping a version.

### Wire formats

| Channel | Format | Why |
|---|---|---|
| Gateway ↔ React | REST + JSON; WebSocket for push | Browser-debuggable. |
| Gateway ↔ Python | REST + JSON | No gRPC overhead until justified. |
| Kafka messages | JSON-Schema-validated JSON | Human-readable; switch to Avro only if message volume demands. |

### Backpressure & quotas

- Quota enforcement at the gateway, **before** any heavy work. Redis stores `gw:rate:user:{user_id}:ops:{date}` counters via `INCR` + TTL-to-end-of-day.
- Kafka has **per-tier consumer groups**: `python-worker-paid` consumes prioritized partitions ahead of `python-worker-free`. Free traffic cannot starve paid.
- Sync requests above tier limits → `429 Too Many Requests` with `Retry-After`.

### Data ownership

| Data | Owner | Location |
|---|---|---|
| User accounts, tier, billing | Gateway | Postgres `users`, `subscriptions` |
| Job state | Gateway | Postgres `jobs` |
| Format-request tickets | Gateway | Postgres `format_requests` |
| Uploaded files (raw) | Gateway → Python read-only | MinIO `uploads/` |
| Result blobs | Python → Gateway read-only | MinIO `results/` |
| Saved filter recipes (paid) | Gateway via Python recipe API | Postgres `recipes` (JSONB) |
| Rate-limit counters | Gateway | Redis `gw:rate:*` |
| Cache (detection / preview) | Python | Redis `py:cache:*` |
| Audit log | Gateway | Postgres `audit_log` (partitioned) |

**No service writes to a datastore another service owns.**

---

## §4 — Plugin & Extensibility Model

### Canonical intermediate model

Two canonical shapes — every parser / emitter / filter / analysis works against these, eliminating O(N²) format converters:

```
TabularData                          TreeData
─ schema: Column[]                   ─ root: Node
   ├─ name: str                         ├─ key: str
   ├─ type: TypeTag                     ├─ value: scalar | None
   └─ nullable: bool                    ├─ type: TypeTag
─ rows: AsyncIterator[Record]           └─ children: Node[]
                                     ─ meta: { depth, total_nodes, ... }
```

Both share `TypeTag` (`string | number | integer | boolean | datetime | null`).

Rows are **streamed** — never fully materialized — so a 500 MB CSV doesn't blow up RAM. Adapters that need full materialization (e.g., Excel emit) opt in explicitly.

Cross-shape conversion:
- Tabular → Tree: row becomes a tree node; rows become children of a `rows` root.
- Tree → Tabular: JSONPath / XPath flattening with explicit "explode array at path X" rules.

### Plugin type 1 — Format adapters

```python
class FormatPlugin(Protocol):
    manifest: FormatManifest
    def detect(self, sample: bytes) -> DetectResult: ...
    def parse(self, source: BinaryIO) -> TabularData | TreeData: ...
    def emit(self, data: TabularData | TreeData, sink: BinaryIO) -> None: ...
```

**Manifest** (declarative, TOML):

```toml
[plugin]
id = "csv"
display_name = "CSV / TSV"
version = "1.0.0"
license = "Apache-2.0"
author = "FilterNArrange Core"

[detect]
mime_types = ["text/csv", "text/tab-separated-values"]
extensions = [".csv", ".tsv"]
magic_bytes = []
confidence_strategy = "content-sniff"

[capabilities]
parse = true
emit = true
streaming = true
shape = "tabular"
```

**Detection pipeline** (gateway-enforced order):

1. **Magic bytes** — near-zero cost. XLSX (`PK\x03\x04`), gzip (`\x1f\x8b`), etc.
2. **Structural sniff** — try parsing first N KB with each candidate; highest confidence wins.
3. **Heuristic** — column-count consistency for CSV, valid JSON for JSON, well-formed XML for XML.
4. **Fallback** — if confidence < threshold, return `{ format: "unknown", suggestions: [...] }` and surface the **community PR link** (always visible) plus the **paid prioritized format request** flow (visible only to paid users).

The order is hard-coded; *which* detectors run is plugin-driven.

**Registration — zero-config discovery:**

```toml
[project.entry-points."filternarrange.formats"]
csv = "filternarrange_format_csv:plugin"
```

Core uses `importlib.metadata.entry_points("filternarrange.formats")` at startup. Drop a plugin into the install, restart the Python service, it's live. **Zero core changes.**

**Per-plugin directory layout:**

```
plugins/format-parquet/
├── pyproject.toml
├── README.md
├── manifest.toml
├── src/filternarrange_format_parquet/
│   ├── plugin.py
│   ├── detect.py
│   ├── parse.py
│   └── emit.py
└── tests/
    ├── fixtures/sample.parquet
    ├── test_detect.py
    ├── test_parse.py
    └── test_emit.py
```

CI runs each plugin's tests in isolation. **A broken Parquet plugin can't break CSV.**

**Launch set** (shipped as plugins in `plugins/`): `csv`, `tsv`, `json`, `jsonl`, `xml`, `yaml`, `xlsx`. Nothing is special about "core" formats — they're plugins too.

### Plugin type 2 — Filter operators

```python
class FilterPlugin(Protocol):
    manifest: FilterManifest
    def apply(self, data: Tabular | Tree, spec: FilterSpec) -> Tabular | Tree: ...
    def validate(self, spec: FilterSpec) -> list[ValidationError]: ...
    def explain(self, spec: FilterSpec) -> str: ...  # for audit + UI preview
```

`FilterSpec` is a tagged union — UI sends one shape per mode (`column`, `row`, `expression`, `regex`); core dispatches via `spec.kind`.

The **expression engine** is itself extensible via `register_function(name, fn, signature)`, so a future plugin can add `geohash_distance(a,b)` without modifying the parser.

### Plugin type 3 — Analysis modules

```python
class AnalysisPlugin(Protocol):
    manifest: AnalysisManifest
    def analyze(self, data: Tabular | Tree, options: dict) -> AnalysisResult: ...
```

Launch set: `summary_stats`, `group_by`, `chart_suggest`, `schema_infer`. Chart analyses return a **chart spec** (Vega-Lite-shaped); the frontend chart library is itself swappable because we never hard-code "ECharts options".

### Plugin type 4 — AI providers

```python
class LLMProvider(Protocol):
    def complete(self, prompt: str, schema: JsonSchema | None) -> str | dict: ...
    def embed(self, texts: list[str]) -> list[Vector]: ...
```

**Default:** `OllamaProvider`. Models configurable per capability (`NL2FILTER_MODEL=qwen2.5:7b`, `SUMMARY_MODEL=llama3.1:8b`).

**Swap path:** drop in `HuggingFaceLocalProvider` (heavier deps, more control) or — if a user explicitly opts in — `OpenAIProvider`. The provider is selected by env var; no core change required.

**AI capabilities** are themselves plugins on top of the provider, registered independently and individually disable-able via config — important for free-tier resource shaping.

Launch capabilities: `nl_to_filter`, `auto_summary`, `chart_suggest`, `anomaly_detect`.

### Plugin type 5 — Storage backends

`ObjectStore` interface (default: `MinIOStore`; alternatives: `S3Store`, `B2Store`, `LocalFsStore`). Same pattern for `RelationalStore`.

### Plugin lifecycle & safety

| Concern | Mechanism |
|---|---|
| Discovery | Python `entry_points`; frontend chart types via JS module side-effects into a chart registry. |
| Versioning | Each plugin declares the core API version it targets. Core rejects plugins targeting an incompatible API version on startup. |
| Sandboxing | All plugins run in-process in v1 (first-party + reviewed-PR plugins only). If untrusted user-uploaded plugins ever become a feature, isolate via subprocess + resource limits. **Not a v1 concern.** |
| Failure isolation | Plugin exceptions are caught at the dispatch boundary; failure → graceful error in UI, audit log entry, no other plugin affected. |
| Disable a plugin | `FILTERNARRANGE_DISABLED_PLUGINS=parquet,yaml` env var skips registration. No code change. |
| Per-tier gating | Manifest declares `required_tier = "paid"`. Gateway rejects free-tier calls to paid-only plugins. |
| Failure quarantine | If a plugin fails 3 times in 5 min, registry marks it **quarantined** for 10 min; gateway returns "temporarily unavailable" instead of retrying. Other plugins remain available. |

### Contribution path (OSS)

A community contributor adds a new format like this:

1. Fork repo. `cp -r plugins/format-csv plugins/format-yourthing`.
2. Edit manifest. Implement `detect/parse/emit`. Write tests with fixtures.
3. Open PR. CI runs **only the new plugin's tests** plus a contract-conformance suite that verifies canonical-model invariants.
4. Maintainer reviews and merges. New format auto-picked-up in next release.

Same workflow for filters, analyses, and AI providers.

---

## §5 — Storage & Data Model

### Postgres schema (owned by gateway)

```sql
-- Identity & tier
users (
  id            UUID PRIMARY KEY,
  email         CITEXT UNIQUE NOT NULL,
  external_id   TEXT UNIQUE,                    -- Keycloak subject
  display_name  TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at TIMESTAMPTZ
);

subscriptions (
  id           UUID PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES users(id),
  tier         TEXT NOT NULL CHECK (tier IN ('free', 'paid')),
  status       TEXT NOT NULL CHECK (status IN ('active', 'cancelled', 'expired')),
  started_at   TIMESTAMPTZ NOT NULL,
  expires_at   TIMESTAMPTZ,
  external_ref TEXT,                            -- Stripe sub id, nullable
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX one_active_sub_per_user
  ON subscriptions(user_id) WHERE status = 'active';

jobs (
  id           UUID PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES users(id),
  kind         TEXT NOT NULL,                    -- 'convert' | 'analyze' | 'batch-filter'
  status       TEXT NOT NULL CHECK (status IN ('queued','running','completed','failed','cancelled')),
  params       JSONB NOT NULL,                   -- input refs, filter spec, output format
  result_ref   TEXT,                             -- MinIO key on success
  error        JSONB,                            -- structured error on failure
  priority     INT NOT NULL DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at   TIMESTAMPTZ,
  finished_at  TIMESTAMPTZ
);
CREATE INDEX jobs_user_recent ON jobs(user_id, created_at DESC);
CREATE INDEX jobs_status_open ON jobs(status) WHERE status IN ('queued','running');

format_requests (
  id           UUID PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES users(id),
  sample_ref   TEXT NOT NULL,
  user_label   TEXT,
  status       TEXT NOT NULL CHECK (status IN ('open','triaged','in-progress','shipped','rejected')),
  priority     INT NOT NULL DEFAULT 0,
  github_issue INT,                              -- mirrored when triaged
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at  TIMESTAMPTZ
);

recipes (
  id           UUID PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES users(id),
  name         TEXT NOT NULL,
  recipe       JSONB NOT NULL,
  is_shared    BOOLEAN NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, name)
);

audit_log (
  id           BIGSERIAL,
  user_id      UUID,
  action       TEXT NOT NULL,
  target       TEXT,
  metadata     JSONB,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
) PARTITION BY RANGE (created_at);

plugin_registry (
  plugin_id     TEXT NOT NULL,
  kind          TEXT NOT NULL,                   -- 'format' | 'filter' | 'analysis' | 'ai-provider'
  version       TEXT NOT NULL,
  status        TEXT NOT NULL CHECK (status IN ('enabled','disabled','deprecated')),
  required_tier TEXT CHECK (required_tier IN ('free','paid')),
  installed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (plugin_id, version)
);
```

**Migrations:** Flyway (Apache 2.0). Versioned SQL files, immutable once shipped.

### JSONB usage (replaces MongoDB)

Example `jobs.params`:

```json
{
  "input": { "ref": "uploads/users/u-7/uploads/abc.csv",
             "size_bytes": 4823, "detected_format": "csv" },
  "operations": [
    { "kind": "filter", "mode": "row", "predicate": "age > 18 AND country = 'IN'" },
    { "kind": "convert", "to": "json" }
  ],
  "options": { "stream": true }
}
```

Selectively indexed: `CREATE INDEX jobs_params_input_format ON jobs ((params->'input'->>'detected_format'));`

### Redis keyspace

| Prefix | Owner | Purpose | TTL |
|---|---|---|---|
| `gw:rate:user:{user_id}:ops:{date}` | gateway | per-user daily op counter | end-of-day |
| `gw:rate:ip:{ip}:{window}` | gateway | anonymous IP rate limit | window |
| `gw:sess:{sid}` | gateway | session blob | 24 h sliding |
| `py:cache:detect:{sha256(sample)}` | python | format-detection cache | 1 h |
| `py:cache:filter-preview:{recipe-hash}` | python | filter preview memoization | 5 min |

Prefix discipline = clean separation = trivially splittable.

### MinIO buckets

| Bucket | Contents | Lifecycle |
|---|---|---|
| `uploads` | Raw user uploads | Free: delete 24 h after job. Paid: 30 days. |
| `results` | Job result blobs | Same as uploads. |
| `format-samples` | Anonymized samples for format-request tickets | Retain until ticket closed + 30 days |
| `backups` | Nightly pg_dump | 14 days |

Access: gateway issues pre-signed PUT/GET URLs to the browser; Python reads server-side. Browser never gets MinIO credentials.

### Kafka topics

| Topic | Producer | Consumer | Partition key | Retention |
|---|---|---|---|---|
| `topic.v1.jobs` | gateway | python-worker | `user_id` | 7 days |
| `topic.v1.job-results` | python-worker | gateway | `job_id` | 24 h |
| `topic.v1.format-requests` | gateway | admin notifier + GH-issue-mirror | `user_id` | 30 days |
| `topic.v1.audit-events` | any service | audit-writer | `user_id` | 7 days, then archive |

**Priority via separate consumer groups:** `python-worker-paid` consumes ahead of `python-worker-free`.

### Data lifecycle

| Data | Free retention | Paid retention | Stored in |
|---|---|---|---|
| Uploaded file | 24 h after job | 30 days (90 days if recipe-attached) | MinIO `uploads` |
| Job result | 24 h | 30 days | MinIO `results` |
| Job record | 90 days | indefinite | Postgres `jobs` |
| Saved recipe | N/A (not allowed) | indefinite while sub active | Postgres `recipes` |
| Audit log | 90 days hot, 1 yr archive | same | Postgres → MinIO archive |
| Format request | indefinite until resolved | indefinite | Postgres |

### Backup & DR

- **Postgres:** nightly `pg_dump` → MinIO `backups/postgres/YYYY-MM-DD.sql.gz`; 14-day retention. PITR (continuous WAL archiving) deferred until paid tier launches.
- **MinIO:** `mc mirror` to sibling bucket for hot copy; off-VM Backblaze B2 copy (~$0.20/mo) added once budget allows.
- **Redis:** ephemeral; AOF/RDB persistence on for crash recovery only.
- **Kafka/Redpanda:** topic retention covers replay; no separate backup.

### What we deliberately don't do (yet)

- No PgBouncer / connection-pool layer — Spring Boot HikariCP is enough.
- No read replicas — defer until p95 reads demand it.
- No sharding — Postgres single-instance scales well past v1 needs.
- No data-warehouse split — analytics on the same DB until it hurts OLTP.

---

## §6 — Module Organization, Dependency Order & Failure Isolation

### Repository layout (monorepo)

```
FilterNArrange/
├── apps/
│   ├── gateway/                 (Spring Boot)
│   ├── data-engine/             (Python + FastAPI)
│   └── frontend/                (React + TypeScript)
├── plugins/                     (formats, filters, analyses, AI providers)
├── contracts/                   (OpenAPI + Kafka JSON Schemas)
├── infra/                       (docker-compose, caddy, observability)
├── docs/
│   ├── architecture/
│   ├── decisions/               (ADRs)
│   ├── superpowers/specs/       (design specs)
│   ├── cost-tracking.md
│   └── run-guide.md
├── scripts/
└── tests/integration/           (cross-service)
```

### Per-app structure (hexagonal / ports-and-adapters)

**Gateway (Java):**

```
apps/gateway/src/main/java/io/filternarrange/gateway/
├── api/              # REST controllers — top
├── application/      # use-case services (orchestration only)
├── domain/           # entities + ports (interfaces); zero outside deps
├── infrastructure/   # adapters: persistence/, messaging/, storage/, http/
└── platform/         # auth, errors, observability — cross-cutting
```

**Data-engine (Python):**

```
apps/data-engine/src/filternarrange_engine/
├── api/              # FastAPI routers
├── application/      # orchestrators per use case
├── core/             # canonical model (TabularData, TreeData) + ports
├── adapters/         # plugin_registry/, storage/, kafka/, llm/
└── platform/         # logging, errors, config
```

**Frontend (TypeScript) — feature-sliced:**

```
apps/frontend/src/
├── app/              # shell, routing, providers
├── pages/            # route components
├── features/         # upload, filter, analyze, account
│   └── <feature>/{api,ui,state,index.ts}
└── shared/           # ui/, lib/, api/client
```

### Dependency direction rules (CI-enforced)

```
                api  →  application  →  domain
                                          ▲
                                          │ implements
                                  infrastructure
```

1. **Domain depends on nothing.** Pure types + ports.
2. **Application depends only on domain.** No SQL, no HTTP, no annotations.
3. **Infrastructure depends on domain (to implement ports). Never the other way.**
4. **API depends on application + domain.** Never directly on infrastructure.
5. **Features never import other features.** Cross-feature goes through `shared/`.
6. **Plugins depend only on the published plugin API**, never on app internals.

**Enforcement:**

| Layer | Linter |
|---|---|
| Java | ArchUnit tests in CI |
| Python | `import-linter` (declarative rules in `.importlinter`) |
| TypeScript | `eslint-plugin-boundaries` + `eslint-plugin-import` |

Lint runs on every PR. Violations block merge.

### The public surface rule

A module's **public surface = a single file**:

- Python: `__init__.py` with `__all__`
- TypeScript: `index.ts` (barrel)
- Java: top-level package types; everything in `internal/` sub-package is package-private

If a name isn't in the surface, importing it from outside the module is a lint error.

Every non-trivial module also has a `README.md` listing: purpose, public API (link), dependencies, consumed-by, open questions / limitations.

### Code-level failure isolation patterns

1. **Error envelopes at every cross-module boundary.** Modules return typed `Result<T, E>` (Java sealed type, Python `PluginResult`, TS discriminated union). Raw exceptions are caught at the boundary and converted.
2. **Single structured error model on the wire:** `{ code, plugin_id, message, trace_id }`. Stable `code` values; UI maps them to user-friendly messages.
3. **Bulkheading — pools per concern:** `web-io`, `db-io`, `kafka-producer` (Java); `data-cpu` (ProcessPool), `ai-async` (Semaphore), `plugin-async` (Semaphore) (Python). An AI surge can't drain the DB pool.
4. **Timeouts at every boundary:**

   | Edge | Default |
   |---|---|
   | Gateway → Python (sync) | 5 s |
   | Gateway → Python (AI) | 30 s |
   | Postgres query | 3 s |
   | Redis call | 250 ms |
   | Kafka produce | 10 s |
   | MinIO PUT/GET | 60 s |
   | Python → Ollama | 30 s |

5. **Circuit breakers between services.** Resilience4j between gateway and Python — open after 5 consecutive failures in 10 s, half-open after 30 s. When open: 503 + frontend renders degraded mode.
6. **Idempotency keys for all async writes.** `Idempotency-Key` header; gateway stores key → job_id in Redis (24 h). Retries don't double-process.
7. **No shared mutable state across modules.** Configuration injected, never globals.
8. **Plugin failure quarantine** (already specified in §4).

### Readability rules (enforced via review checklist)

- One module = one purpose.
- Files under 400 LOC (soft); classes/modules under 200 LOC where possible.
- No magic numbers; constants in a `constants` submodule with naming that explains why.
- Public symbols documented with one-line purpose. Implementation comments only when the why isn't obvious.
- Tests in `tests/` mirroring module structure; test name = behaviour.

---

## §7 — Engineering Workflow

### 7.1 Ticketing (GitHub Issues, $0)

**Templates** (`.github/ISSUE_TEMPLATE/`): `bug.yml`, `feature.yml`, `format-request.yml`, `plugin.yml`, `chore.yml`. Each enforces the fields the workflow depends on.

**Labels:**

| Group | Labels |
|---|---|
| Type | `bug`, `feature`, `chore`, `docs`, `format-request`, `regression` |
| Area | `area:gateway`, `area:data-engine`, `area:frontend`, `area:plugins`, `area:infra`, `area:contracts` |
| Priority | `P0-critical`, `P1-high`, `P2-medium`, `P3-low` |
| Status | `triaged`, `in-progress`, `blocked`, `needs-review`, `needs-tests` |
| Risk | `risk:low`, `risk:medium`, `risk:high` |
| Tier | `tier:free`, `tier:paid` |

**Project board:** Backlog → Triaged → In Progress → In Review → Done. Auto-transitions on PR events.

**Required ticket fields:** requirement, acceptance criteria, scope (in/out), blast radius, regression risk, test plan. Auto-populated as work progresses: commits, files changed, PR link, version shipped.

### 7.2 Pull request workflow

PR title: Conventional Commit. PR body template requires:

- Summary
- Linked issues (`Closes #N`)
- Changes (file paths)
- Impact assessment (modules touched / contracts / DB schema / public API / plugin API / infra)
- Regression risk + reasoning
- Tests added / updated / regression test (for bug fixes)
- Docs / cost-tracking / ADR update checklist

CI fails the PR if any required section is empty.

**Merge:** squash-merge. One issue → one commit on `main`. Bisects stay clean.

**Branch protection on `main`:** ≥1 approving review (CODEOWNERS), all required checks green, no force-push, no direct push, linear history.

### 7.3 Versioning & releases

**SemVer.** Pre-1.0 allowed; breaking changes can bump MINOR pre-1.0.

**Conventional Commits → automated CHANGELOG.**

| Prefix | Bump |
|---|---|
| `feat:` | MINOR |
| `fix:` | PATCH |
| `feat!:` / `BREAKING CHANGE:` | MAJOR |
| `chore` / `docs` / `refactor` / `test` / `ci` / `build` | none (visible in CHANGELOG) |

**Tooling ($0):**

- `commitlint` + `husky` — local commit-message lint hook.
- `git-cliff` — generates CHANGELOG from commits.
- `release-please` (GitHub Action) — opens a Release PR; merging tags the release, builds artifacts, publishes the release with CHANGELOG snippet, contributors, SHA.

**Tagging:** `vX.Y.Z`. Container images tagged with the same. `latest` only on `main` for non-production.

### 7.4 ADRs

One file per decision: `docs/decisions/ADR-NNNN-<slug>.md`. Format: Status / Date / Deciders / Context / Decision / Consequences / Follow-ups.

Immutable once accepted; superseded by a later ADR (cross-linked), not edited.

ADR required when: stack choice, license, schema change with migration impact, contract version bump, plugin API change, tier/quota model change.

Index at `docs/decisions/README.md`.

### 7.5 CI/CD (GitHub Actions, $0 for public; 2000 min/mo private)

PR pipeline (`pr.yml`):

```
1. lint                  (Java: spotless+checkstyle, Python: ruff+mypy, TS: eslint+tsc, commitlint)
2. unit tests            (JUnit / pytest / vitest — parallel; coverage → Codecov)
3. architecture tests    (ArchUnit / import-linter / eslint-plugin-boundaries)
4. contract validation   (OpenAPI lint, JSON Schema lint, Schemathesis fuzz)
5. plugin conformance    (canonical suite per plugin)
6. integration tests     (testcontainers: Postgres, Redis, Kafka, MinIO)
7. e2e                   (Playwright against full compose stack)
8. performance gates     (k6; fail if p95 > budget by 10 %)
9. PR template guard     (required sections filled)
```

**Required to merge:** lint + unit + architecture + contract + plugin-conformance + PR-template guard. Integration and E2E required on `main` (flaky-tolerant: one automatic retry). Performance gates blocking.

**On merge to `main`:** `release-please` opens / updates Release PR.

**On merge of Release PR:** tag created → build images → push to ghcr.io → generate SBOM (Syft) + sign (Cosign) → create GitHub Release.

**Dependabot** (weekly bumps, auto-merge if green and patch-level).

**Secret scanning** (GitHub native + `gitleaks` in pre-commit and CI).

### 7.6 Automation testing strategy

| Layer | Tooling (OSS) | Share | When |
|---|---|---|---|
| Unit | JUnit 5 / pytest / vitest | ~70 % | every PR |
| Architecture | ArchUnit / import-linter / eslint-plugin-boundaries | n/a | every PR |
| Contract | schemathesis, JSON Schema validators, PACT-style | ~5 % | every PR |
| Plugin conformance | shared canonical suite | per plugin | every PR |
| Integration | testcontainers | ~20 % | every PR |
| E2E | Playwright | ~5 % | every PR + nightly |
| Performance | k6 | latency-budget gate | every PR + deep nightly |
| Visual regression | Playwright snapshots (optional) | per page | nightly |
| Mutation testing | PIT / mutmut | critical modules | weekly |
| Load testing | k6 large profile | n/a | weekly, staging |
| Security | OWASP ZAP baseline + Trivy + gitleaks | n/a | nightly + every PR |

**Concrete rules:**

- Every new function/class has a unit test.
- Every bug fix has a regression test that fails on `main`, passes on the fix.
- Every contract change has a contract test (provider + consumer).
- Every new plugin passes the canonical conformance suite before merge.
- Latency budgets from §3 are CI-enforced.
- Coverage minimums: 80 % lines / 70 % branches per app; new-code patch coverage ≥ 85 %.

### 7.7 Change-impact + regression report (per release)

Each GitHub Release includes:

1. Summary (auto from CHANGELOG).
2. Migration notes (DB migrations, env-var changes, config changes).
3. Regression watch — top 3 risk areas from merged PRs, monitoring pointers.
4. Performance snapshot — k6 numbers vs previous release.
5. Plugin compatibility — plugin API version, any quarantined plugins.

Generated semi-automatically by `release-please` + custom aggregator workflow.

### 7.8 All tooling costs

**$0 across the board.** See `docs/cost-tracking.md` §20 ("Development & testing tooling") for the line-by-line catalog and upgrade paths.

---

## §8 — Run Guide & System Requirements

See **[docs/run-guide.md](../../run-guide.md)** for the complete, current-canonical guide. The spec only mirrors the headline requirements:

| Tier | RAM | CPU | Disk | GPU | Suitability |
|---|---|---|---|---|---|
| Minimum | 16 GB | 4 cores | 25 GB free | none | Works; CPU AI slow |
| Recommended | 32 GB | 8 cores | 50 GB | optional | Comfortable |
| AI-comfort | 32 GB + GPU | 8 cores | 60 GB | ≥ 8 GB VRAM or Apple Silicon | AI < 1 s |
| Free-tier deploy | 24 GB | 4 vCPU ARM | 200 GB | none | Whole stack fits |

Required host tools: Docker 24+ with Compose v2.20+; Git; `gh` CLI. Optional for local-development of individual services: JDK 21, Node 20, Python 3.12 (via `uv`), `mkcert`.

---

## §9 — Roadmap & Out of Scope

### v1 deliverables (this design)

- Working stack: gateway, data-engine, frontend, supporting infra in Docker Compose.
- Launch format plugins: csv, tsv, json, jsonl, xml, yaml, xlsx.
- Four filter modes, four analyses, four AI capabilities.
- Tier system + format-request workflow (open-core model).
- CI/CD pipeline, test pyramid, ADR practice.
- Cost-tracking doc maintained continuously.
- License selected (ADR-0002) — required before flipping the repo public.

### Out of scope for v1 (explicit YAGNI)

- DB / URL ingestion
- Real-time collaboration
- Enterprise SSO
- Multi-tenant orgs
- Mobile apps
- Stripe / billing wiring
- Public hosted deployment
- Kubernetes orchestration

### Future work (post-v1, not committed)

- Public hosted deploy on Oracle Always-Free
- Stripe wiring on first paid signup
- Additional format plugins (Parquet, Avro, Markdown tables, fixed-width)
- Additional AI capabilities (data cleaning suggestions, schema-guided extraction)
- API access tier (for paid users embedding FilterNArrange programmatically)
- Optional SaaS-managed dependencies (Neon Postgres, Upstash Redis, etc.)

---

## §10 — Open Questions / Follow-ups

| # | Open question | Tracked in |
|---|---|---|
| 1 | License: AGPL-3.0 vs Apache-2.0 | ADR-0002 (pending) — must resolve before flipping repo public |
| 2 | Concrete tier thresholds for production launch (file-size cap, daily ops, retention windows) | ADR follow-up after first usage data |
| 3 | Free-tier deployment specifics (Oracle Always-Free networking, certificates) | `docs/deploy-free-tier.md` — written at deploy time |
| 4 | Module-dependency & failure-isolation rules ADR | ADR-0003 (to be written from §6) |
| 5 | Ticketing & versioning workflow ADR | ADR-0004 (to be written from §7) |

---

## §11 — References

- **Repository:** <https://github.com/piyush-official/FilterNArrange>
- **Cost tracking:** [docs/cost-tracking.md](../../cost-tracking.md)
- **Run guide:** [docs/run-guide.md](../../run-guide.md)
- **ADRs:** [docs/decisions/](../../decisions/)
- **CHANGELOG:** [CHANGELOG.md](../../../CHANGELOG.md)
