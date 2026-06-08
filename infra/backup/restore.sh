#!/usr/bin/env bash
# Plan G §T14 — restore from a backup file in MinIO.
# Usage: restore.sh <backup-date-or-key> [target-db]
set -euo pipefail

BACKUP="${1:?backup key required, e.g. 2026-06-07.sql.gz}"
TARGET_DB="${2:-${POSTGRES_DB}}"

TMP=$(mktemp -d)
LOCAL="${TMP}/${BACKUP##*/}"

mc alias set minio "http://${MINIO_HOST}:9000" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" >/dev/null
if [[ "${BACKUP}" == */* ]]; then
    mc cp "minio/${BACKUP}" "${LOCAL}"
else
    mc cp "minio/backups/postgres/${BACKUP}" "${LOCAL}"
fi

export PGPASSWORD="${POSTGRES_PASSWORD}"
gunzip < "${LOCAL}" | pg_restore --clean --if-exists --no-owner --no-privileges \
    -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${TARGET_DB}"

echo "{\"event\":\"restore_complete\",\"backup\":\"${BACKUP}\",\"target\":\"${TARGET_DB}\"}"
