# FilterNArrange — Cost Tracking

Single source of truth for **what costs what** in this project. Updated every time a module/tool is added or changed.

## Guiding rules

1. **Always choose Free first.** Only escalate to Cost-effective if Free can't meet a hard need. Only escalate to Paid when truly unavoidable.
2. **Every module lists its upgrade path.** Free → Cost-effective → Paid, so we know exactly what happens if we outgrow Free.
3. **Every module lists scaling options.** Horizontal (more instances) and Vertical (bigger instance) with realistic monthly costs.
4. **Anything that hits real money is highlighted clearly.** No surprises.

## Legend

| Tag | Meaning |
|---|---|
| 🟢 **Free** | $0 today, no monthly bill. May have soft limits but well within v1 needs. |
| 🟡 **Cost-effective** | Low monthly spend (<$20/mo) for material upgrade. Only adopt if Free is genuinely insufficient. |
| 🔴 **Paid** | Material monthly cost (>$20/mo) or per-usage charges. Avoid unless required by scale or feature. |
| ⚪ **Deferred** | Not used yet. Wire only when triggered. |

---

## Status — v1 (2026-06-07)

**Total active monthly spend: $0.**
**Optional next escalation: domain name ~$10/yr (one-time-per-year).**

---

## Module-by-module

### 1. Frontend hosting (static)

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **Nginx in Docker Compose**, static React build | $0 | Served from same VM as backend. |
| 🟡 Upgrade | Cloudflare Pages / Netlify free | $0 | Free for hobby; CDN-backed. Triggered when traffic spikes. |
| 🔴 Paid | Vercel Pro | $20/mo | Only if commercial features needed. |

**Scaling**
- **Horizontal:** N/A locally; CDN scales transparently if migrated.
- **Vertical:** N/A — static files.

---

### 2. API gateway — Spring Boot

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **Spring Boot 3.x, OpenJDK 21** (containerized) | $0 | Apache 2.0 license. |

**Scaling**
- **Horizontal:** Add more gateway containers behind a load balancer. Cost: only the extra VM(s). Oracle Always-Free fits 1–2 small instances; beyond that Hetzner ARM ~$4/mo per node.
- **Vertical:** Larger VM. Oracle Always-Free max already gives 4 vCPU / 24 GB RAM combined; vertical past that → Hetzner CCX13 ~$14/mo for 2 dedicated vCPU / 8 GB, or Oracle paid VM.

---

### 3. Data engine + AI service — Python (FastAPI)

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **Python 3.12, FastAPI, pandas, polars, lxml, openpyxl** | $0 | All permissive OSS. |

**Scaling**
- **Horizontal:** Run multiple `MODE=data` instances; gateway round-robins. Free as long as VM count fits free tier.
- **Vertical:** Larger VM — polars/pandas benefit greatly from RAM. Same cost ladder as gateway.

---

### 4. AI model runtime — Ollama + open models

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **Ollama** running Llama 3.1 8B Q4 + Qwen2.5 7B | $0 software | Models are free weights. **Hardware cost is hidden:** needs ~6 GB free RAM; CPU inference 5–20s/query, GPU inference <1s. |
| 🟡 Upgrade | Self-hosted small GPU box (Hetzner GEX44 RTX 4000) | ~€199/mo | Only if AI traffic justifies it. |
| 🟡 Upgrade alt | Vast.ai or RunPod spot GPU | $0.10–0.40/hr | Pay only when inferring. |
| 🔴 Paid | OpenAI / Anthropic API | per-token | **Avoid in OSS path.** |

**Scaling**
- **Horizontal:** Multiple Ollama instances; Python service load-balances. Useful when concurrency is the bottleneck.
- **Vertical:** Bigger model (Llama 3.1 70B Q4 ≈ 40 GB RAM) or GPU. Quality vs cost trade-off.

---

### 5. Relational database — PostgreSQL

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **Postgres 16** in Docker Compose, with JSONB columns for nested data | $0 | Replaces MongoDB. PostgreSQL License (BSD-like). |
| 🟡 Upgrade | Managed: Neon free tier / Supabase free tier | $0 → $19/mo | Free tiers are generous; only escalate when storage > 0.5 GB or you want managed backups. |
| 🔴 Paid | AWS RDS / GCP Cloud SQL | $15+/mo | Reserve for production scale. |

**Scaling**
- **Horizontal:** Read replicas via streaming replication. One primary + N replicas. Same VM cost per replica.
- **Vertical:** RAM is the lever — bigger shared_buffers, larger working set fits in memory. Linear cost with VM size.

---

### 6. Cache / rate-limit store — Redis

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **Redis 7 OSS** in Docker Compose | $0 | BSD-3 license. (Note: Redis ≥7.4 has dual SSPL/RSAL; stay on 7.2 OSS or use **Valkey** fork if license matters.) |
| 🟡 Upgrade | Upstash free → pay-per-request | $0 → ~$0.20/100k ops | Managed, serverless. |

**Scaling**
- **Horizontal:** Redis Cluster (3+ nodes). Each is a VM cost.
- **Vertical:** RAM is everything — choose VM size by dataset size.

---

### 7. Messaging — Kafka

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **Redpanda OSS** (Kafka-API-compatible, single-binary, no ZooKeeper) | $0 | Lighter footprint than Apache Kafka — better for free-tier RAM. Source-available BSL→Apache 2.0 after 4 years; for strict-OSS users, swap to **Apache Kafka KRaft mode**. |
| 🟡 Upgrade | Confluent Cloud Basic / Redpanda Cloud | $0 free tier → ~$1/GB | Triggered when self-hosting Kafka becomes operationally painful. |

**Scaling**
- **Horizontal:** Add brokers + partitions. Each broker is a VM.
- **Vertical:** Disk and RAM. Modest scaling possible on one node.

---

### 8. Object storage — MinIO

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **MinIO** (S3-compatible) in Docker Compose | $0 | AGPL-3.0 license. Important if your project license is also AGPL — check compatibility before shipping. |
| 🟡 Upgrade | Backblaze B2 | $6/TB/mo storage + $0.01/GB egress | Way cheaper than AWS S3. Triggered when data exceeds local disk. |
| 🔴 Paid | AWS S3 | $0.023/GB/mo + egress | Avoid unless on AWS for other reasons. |

**Scaling**
- **Horizontal:** MinIO distributed mode (4+ nodes). Each = VM + disk cost.
- **Vertical:** Bigger block storage. Oracle Always-Free includes 200 GB free.

---

### 9. Identity / auth — Keycloak

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **Keycloak** in Docker Compose | $0 | Apache 2.0. Heavy on RAM (~1 GB minimum). |
| 🟡 Alt-Free | **Spring Security + JWT, self-managed** | $0 | Lower RAM; less feature-rich. Acceptable fallback if Keycloak doesn't fit free tier. |
| 🟡 Upgrade | Zitadel Cloud / Authentik Cloud | $0–$20/mo | Managed alternatives. |
| 🔴 Paid | Auth0 / Clerk | $25+/mo | **Avoid in OSS path.** |

**Scaling**
- **Horizontal:** Keycloak supports clustering. Each node = VM cost.
- **Vertical:** RAM-bound; bigger VM helps.

---

### 10. Container orchestration

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **Docker Compose** | $0 | Works for single-VM deploy. |
| 🟡 Upgrade | **k3s** (lightweight Kubernetes) | $0 | When multi-node deploy is needed. |
| 🔴 Paid | Managed Kubernetes (EKS/GKE/AKS) | $70+/mo | Defer indefinitely. |

---

### 11. Observability — metrics, logs, traces

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **Prometheus + Grafana + Loki + Tempo** self-hosted | $0 | All OSS, run in same Compose stack. |
| 🟡 Upgrade | Grafana Cloud free tier | $0 → $8/mo | 10k series, 50 GB logs free. Triggered when ops burden of self-hosting grows. |
| 🔴 Paid | Datadog / New Relic | $15+/host/mo | Avoid. |

**Scaling**
- Self-hosted Loki scales horizontally with object storage backend (MinIO).
- Prometheus can shard via Thanos when needed; defer.

---

### 12a. Source code hosting

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **GitHub** (private repo: `piyush-official/FilterNArrange`) | $0 | Personal account; unlimited private repos free. Will flip to public when license is decided. |
| 🟡 Alt | GitLab / Codeberg | $0 | Direct alternatives if GitHub dependence becomes a concern. |

### 12. CI / CD

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **GitHub Actions** on public repo | $0 | Unlimited minutes for public repos. |
| 🟡 Upgrade | Self-hosted runner on Oracle Always-Free | $0 | If concurrency or larger builds needed. |

---

### 13. Container registry

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **GitHub Container Registry (ghcr.io)** | $0 | Free for public images. |
| 🟡 Alt | Docker Hub | $0 → $5/mo | Free for public; paid plan if rate limits hit. |

---

### 14. Reverse proxy / TLS

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **Caddy** (auto-HTTPS via Let's Encrypt) | $0 | Apache 2.0. Single config file. |
| 🟡 Alt | Nginx + certbot | $0 | More config, equally free. |

---

### 15. DNS

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **Cloudflare DNS free tier** | $0 | DDoS protection included. |

---

### 16. Domain name

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| ⚪ Deferred | Not registered yet | $0 | Use Oracle public IP for now. |
| 🟡 Trigger | Register `.dev` / `.app` / `.io` etc. | ~$10–60/yr | Buy when ready for public launch. Cloudflare Registrar / Porkbun cheapest. |

---

### 17. Transactional email

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| ⚪ Deferred | Not wired yet | $0 | Wire only when signup confirmation/password reset is implemented. |
| 🟢 Trigger | **Brevo free tier** | $0 (300/day) | Sufficient for early users. |
| 🟡 Upgrade | AWS SES | $0.10/1k emails | Cheapest at scale. |

---

### 18. Payments

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| ⚪ Deferred | Not wired yet | $0 | Wire only when first paid customer signs. |
| 🟢 Trigger | **Stripe** | 2.9% + $0.30/txn, no monthly fee | Industry standard. |
| 🟡 Alt | Open Collective | 5–10% platform fee | OSS-friendly; donation-based. |
| 🟡 Alt | GitHub Sponsors | 0% fee for OSS maintainers | Best for pure-OSS monetization. |

---

### 20. Development & testing tooling

All chosen for $0 cost and OSS licensing. See spec §7 for usage details.

| Module | Choice | Tier | Notes |
|---|---|---|---|
| Commit-message lint | **commitlint + husky** | 🟢 Free | npm; local pre-commit hook. |
| CHANGELOG generation | **git-cliff** | 🟢 Free | Single Rust binary. |
| Release automation | **release-please** (GitHub Action) | 🟢 Free | Opens release PRs, tags, builds GH releases. |
| Java architecture tests | **ArchUnit** | 🟢 Free | Apache 2.0. |
| Python architecture tests | **import-linter** | 🟢 Free | BSD-3. |
| TS architecture tests | **eslint-plugin-boundaries** + **eslint-plugin-import** | 🟢 Free | MIT. |
| OpenAPI fuzz / contract tests | **schemathesis** | 🟢 Free | MIT. |
| Integration test harness | **testcontainers** (JVM + Python) | 🟢 Free | MIT/Apache 2.0. |
| E2E browser tests | **Playwright** | 🟢 Free | Apache 2.0. |
| Performance / load | **k6** (OSS edition) | 🟢 Free | AGPL-3.0 (binary only — does not contaminate test scripts). |
| Coverage | **Codecov** (free for OSS) | 🟢 Free | Triggered if private repo exceeds free limits → self-host **Sonarqube CE** ($0). |
| Mutation testing (Java) | **PIT** | 🟢 Free | Apache 2.0. |
| Mutation testing (Python) | **mutmut** | 🟢 Free | BSD. |
| Security — DAST | **OWASP ZAP** (baseline scan) | 🟢 Free | Apache 2.0. |
| Security — container image scan | **Trivy** | 🟢 Free | Apache 2.0. |
| Security — secret scanning | **gitleaks** + GitHub native | 🟢 Free | MIT. |
| Supply chain — SBOM | **Syft** | 🟢 Free | Apache 2.0. |
| Supply chain — image signing | **Cosign** | 🟢 Free | Apache 2.0. |
| Dependency updates | **Dependabot** | 🟢 Free | GitHub native. |

**Scaling notes**
- All tools above are pure-PR-time cost on GitHub Actions; the 2 000 min/mo private quota is plenty for v1. Once public the quota becomes unlimited.
- If GitHub Actions minutes ever pinch (e.g. heavy nightly E2E + mutation), self-host a runner on the same VM as the deploy ($0 extra) before considering paid CI tiers.

### 19. Hosting / compute

| Tier | Choice | Cost | Notes |
|---|---|---|---|
| 🟢 In-use | **Local Docker Compose** (your machine) | $0 | Dev only. |
| 🟢 Trigger | **Oracle Cloud Always-Free** (4 vCPU ARM Ampere / 24 GB RAM / 200 GB block / 10 TB egress / 1 public IPv4) | $0 forever | Generous, but Oracle can revoke if abused. |
| 🟡 Upgrade | **Hetzner ARM CAX11** | ~€4/mo | 2 vCPU / 4 GB / 40 GB SSD. Predictable, simple. |
| 🟡 Upgrade | **Hetzner CCX13 dedicated** | ~€14/mo | Stable performance for production. |
| 🔴 Paid | AWS / GCP / Azure | $50+/mo | Avoid unless free options exhausted. |

---

## How to update this file

When you add a new module/tool:
1. Add a new section in module order above.
2. Fill in **all four** tiers (Free / Cost-effective / Paid / Deferred), even if some are "N/A" — explicit beats implicit.
3. Always fill in horizontal & vertical scaling notes.
4. Update **Status — v1** at the top if monthly spend changes.

When a tier escalates (e.g., we move Postgres from self-hosted to Neon Paid):
1. Mark the old row 🟢 In-use → 🟢 (no longer in-use).
2. Mark the new row as 🟡 In-use or 🔴 In-use.
3. Update **Status — v1** with the new monthly total.
