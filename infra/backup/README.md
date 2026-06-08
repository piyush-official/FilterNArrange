# Backup container

Nightly logical Postgres backup + MinIO mirror, all into the same MinIO
instance under a separate prefix. Designed to be cheap insurance during dev/
single-VM ops; off-VM copy is Plan H.

## Schedule

- **02:30 UTC** — `pg_dump --format=c | gzip` → `minio/backups/postgres/YYYY-MM-DD.sql.gz`. 14-day retention.
- **03:00 UTC** — `mc mirror` of `uploads/` and `results/` into a sibling `mirror/` prefix.

## Restore

```sh
docker compose -f infra/docker-compose/docker-compose.yml run --rm \
  backup /usr/local/bin/restore.sh 2026-06-07.sql.gz
```

## Out of scope (Plan H)

- Off-VM Backblaze B2 copy
- Continuous WAL archiving (PITR)
- Cross-region replication of the MinIO bucket
