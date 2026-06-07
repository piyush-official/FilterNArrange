#!/usr/bin/env bash
# Plan G §T14 — Postgres logical backup → MinIO with 14-day retention.
set -euo pipefail

DATE=$(date -u +%Y-%m-%d)
TMP=$(mktemp -d)
OUT="${TMP}/${DATE}.sql.gz"

export PGPASSWORD="${POSTGRES_PASSWORD}"
pg_dump --format=c --no-owner --no-privileges \
    -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  | gzip -9 > "${OUT}"

SIZE=$(stat -c '%s' "${OUT}")
echo "{\"event\":\"backup_created\",\"date\":\"${DATE}\",\"bytes\":${SIZE}}"

mc alias set minio "http://${MINIO_HOST}:9000" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" >/dev/null
mc mb --ignore-existing minio/backups
mc cp "${OUT}" "minio/backups/postgres/${DATE}.sql.gz"

# 14-day retention. Anything older than the cutoff gets pruned.
CUTOFF=$(date -u -d '14 days ago' +%Y-%m-%d)
mc ls "minio/backups/postgres/" | awk '{print $NF}' | while read -r f; do
    name="${f%.sql.gz}"
    if [[ "${name}" < "${CUTOFF}" ]]; then
        mc rm "minio/backups/postgres/${f}" || true
        echo "{\"event\":\"backup_pruned\",\"date\":\"${name}\"}"
    fi
done
