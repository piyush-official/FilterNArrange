#!/usr/bin/env bash
# Plan G §T14 — mirror uploads/results into a sibling 'mirror/' bucket.
# Cheap insurance against accidental delete of the primary blob bucket.
set -euo pipefail

mc alias set minio "http://${MINIO_HOST}:9000" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" >/dev/null
mc mb --ignore-existing minio/mirror
mc mirror --overwrite --remove minio/uploads minio/mirror/uploads
mc mirror --overwrite --remove minio/results minio/mirror/results
echo "{\"event\":\"mirror_complete\"}"
