"""Retention CLI — runs the sweeper either once or on an interval (Plan F §T28).

Entry point registered in pyproject so ``retention-sweep`` and
``retention-sweep --loop`` work after install.
"""
from __future__ import annotations

import argparse
import logging
import time

from .config import RetentionConfig

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="retention-sweep")
    p.add_argument("--loop", action="store_true",
                   help="Run continuously, sleeping interval_minutes between sweeps.")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    cfg = RetentionConfig.from_env()
    log.info("retention worker starting with %s", cfg)

    sweeper = _build_default_sweeper(cfg)
    if not args.loop:
        result = sweeper.sweep()
        log.info("one-shot sweep complete: %s", result)
        return 0

    while True:
        try:
            result = sweeper.sweep()
            log.info("sweep complete: %s", result)
        except Exception:
            log.exception("sweep crashed; will retry next interval")
        time.sleep(cfg.interval_minutes * 60)


def _build_default_sweeper(cfg: RetentionConfig):
    """Wire up the production sweeper from env: MinIO + Postgres-backed tier lookup.

    Kept inline so the module's main classes (Sweeper, RetentionConfig) stay
    pure and testable; this is the imperative shell.
    """
    import os
    from .sweeper import Sweeper, BlobRef
    from minio import Minio
    import psycopg

    minio = Minio(
        endpoint=os.environ.get("MINIO_ENDPOINT", "minio:9000").replace("http://", "").replace("https://", ""),
        # Match the rest of data-engine (platform/config.py) — both server-side
        # ``MINIO_ROOT_USER`` and client-side ``MINIO_ACCESS_KEY`` get used
        # depending on context; we accept either to avoid environment drift.
        access_key=os.environ.get("MINIO_ACCESS_KEY") or os.environ["MINIO_ROOT_USER"],
        secret_key=os.environ.get("MINIO_SECRET_KEY") or os.environ["MINIO_ROOT_PASSWORD"],
        secure=os.environ.get("MINIO_ENDPOINT", "").startswith("https://"),
    )

    class _MinioStore:
        def list(self, bucket):
            for obj in minio.list_objects(bucket, recursive=True):
                owner = obj.object_name.split("/", 1)[0] if "/" in obj.object_name else "unknown"
                yield BlobRef(
                    bucket=bucket,
                    key=obj.object_name,
                    last_modified=obj.last_modified,
                    owner_id=owner,
                )

        def delete(self, bucket, key):
            minio.remove_object(bucket, key)

    dsn = (
        f"postgresql://{os.environ['POSTGRES_USER']}:"
        f"{os.environ['POSTGRES_PASSWORD']}@"
        f"{os.environ.get('POSTGRES_HOST', 'postgres')}:"
        f"{os.environ.get('POSTGRES_PORT', '5432')}/"
        f"{os.environ['POSTGRES_DB']}"
    )

    class _PgTierLookup:
        def tier_of(self, owner_id: str) -> str:
            try:
                with psycopg.connect(dsn) as conn, conn.cursor() as cur:
                    cur.execute(
                        "SELECT tier FROM subscriptions "
                        "WHERE user_id::text = %s AND status = 'active' "
                        "ORDER BY started_at DESC LIMIT 1",
                        (owner_id,),
                    )
                    row = cur.fetchone()
                    return row[0] if row else "free"
            except Exception as e:
                log.warning("tier lookup failed for %s: %s — defaulting to free", owner_id, e)
                return "free"

    return Sweeper(cfg, _MinioStore(), _PgTierLookup())


if __name__ == "__main__":
    raise SystemExit(main())
