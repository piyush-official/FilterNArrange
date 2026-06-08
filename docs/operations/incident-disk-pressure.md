# Incident — disk pressure

Plan G §T23.

## Diagnose

- `df -h` on the host — which mount is full?
- `du -sh /var/lib/docker/* | sort -h | tail -10` — which container is at fault?
- Check MinIO bucket sizes: `mc du minio/uploads minio/results minio/backups`

## Common offenders

1. **Old MinIO backups** — `backups/postgres/` should self-prune at 14 days; verify the backup container's cron is alive
2. **Stale uploads** — retention-worker should sweep these; check its logs (`docker compose logs retention-worker`)
3. **Postgres WAL growth** — large autovacuum or replication lag holding WAL

## Quick wins (in order)

1. `mc rm --recursive --force --older-than 30d minio/uploads/` (only on confirmed orphans)
2. `docker system prune -af` if Docker image cache is the culprit
3. `psql -c 'CHECKPOINT;'` then `pg_archivecleanup` if Postgres WAL is stuck
4. As a last resort: scale up the volume / migrate to a bigger host
