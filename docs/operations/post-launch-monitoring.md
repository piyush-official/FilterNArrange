# Post-launch monitoring

Plan H §T10. What to watch in the first weeks after v1.0.0 ships.

## Dashboards to keep open

- **Gateway overview** — request rate, p95 latency, 5xx rate, circuit-breaker state. Grafana folder: FilterNArrange.
- **Job pipeline** — Kafka consumer lag on ``topic.v1.jobs.{paid,free}``; ``handle_job`` failure rate; result-emit p95.
- **Host** — CPU / RAM / disk via node-exporter. Disk crossing 80% should already alert via ``DiskHigh`` (Plan G).
- **Ollama** — token-throughput proxy via ``ai_capability_seconds`` histogram. P95 > 3s on nl_to_filter triggers ``NLToFilterP95High``.

## What "normal" looks like

| Metric | Healthy range (first 30 days) |
|---|---|
| Gateway p95 (``/api/v1/detect``) | < 350 ms |
| Gateway 5xx rate | < 0.5 % |
| Job queue depth | usually 0; spikes to < 50 are fine |
| Disk used on `/` | 35–65 % |
| Ollama RAM | < 9 GB resident |
| Memory pressure (free -h) | Available > 5 GB |
| OOM-kills (`journalctl -k | grep oom`) | 0 |

## Scale-down playbook (RAM pressure)

If Available memory dips below 3 GB:

1. Drop the larger Ollama model: set ``SUMMARY_MODEL=qwen2.5:3b`` in prod.env, restart data-engine.
2. Disable retention-worker temporarily: ``docker compose stop retention-worker``. Re-enable in off-hours.
3. If Postgres is the offender, drop ``max_connections`` (default 100 → 50) — restart required.
4. As a last resort, take the Keycloak service down (only relevant after Plan G PR-1 follow-ups land).

## Graceful offline

For maintenance windows:

```sh
sudo systemctl stop filternarrange
# do work
sudo systemctl start filternarrange
```

Caddy holds the TLS cert across restarts via ``/var/lib/filternarrange/caddy-data``.

## Incident log

Every alert that pages someone should be logged in
``docs/postmortems/YYYY-MM-DD-<slug>.md`` within 48 hours. Template lives
at ``docs/postmortems/_template.md`` (TBD — add when the first real incident happens).
