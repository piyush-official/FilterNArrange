"""Retention sweeper core (Plan F §T27).

Iterates MinIO uploads/ and results/ buckets, looking up each object's owning
user's tier from a thin store (passed in for testability), and deletes objects
older than the tier's cutoff.

Designed to be dependency-injected: the real CLI wires it up with a MinIO
client and a Postgres-backed TierLookup; tests pass in-memory fakes.
"""
from __future__ import annotations

import datetime as _dt
import logging
from dataclasses import dataclass
from typing import Iterable, Protocol

from .config import RetentionConfig

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class BlobRef:
    bucket: str
    key: str
    last_modified: _dt.datetime
    owner_id: str


class BlobStore(Protocol):
    def list(self, bucket: str) -> Iterable[BlobRef]: ...

    def delete(self, bucket: str, key: str) -> None: ...


class TierLookup(Protocol):
    def tier_of(self, owner_id: str) -> str: ...


@dataclass(frozen=True)
class SweepResult:
    scanned: int
    deleted: int
    retained: int


class Sweeper:
    def __init__(
        self,
        cfg: RetentionConfig,
        store: BlobStore,
        tiers: TierLookup,
        *,
        uploads_bucket: str = "uploads",
        results_bucket: str = "results",
    ) -> None:
        self._cfg = cfg
        self._store = store
        self._tiers = tiers
        self._uploads = uploads_bucket
        self._results = results_bucket

    def sweep(self, now: _dt.datetime | None = None) -> SweepResult:
        now = now or _dt.datetime.now(_dt.timezone.utc)
        return SweepResult(
            scanned=(
                self._sweep_bucket(self._uploads, self._cfg.upload_cutoff, now)
                + self._sweep_bucket(self._results, self._cfg.result_cutoff, now)
            ),
            deleted=self._deleted,
            retained=self._retained,
        )

    _deleted = 0
    _retained = 0

    def _sweep_bucket(self, bucket: str, cutoff_for_tier, now: _dt.datetime) -> int:
        scanned = 0
        deleted = 0
        retained = 0
        for blob in self._store.list(bucket):
            scanned += 1
            tier = self._tiers.tier_of(blob.owner_id)
            cutoff = cutoff_for_tier(tier=tier, now=now)
            if blob.last_modified < cutoff:
                try:
                    self._store.delete(bucket, blob.key)
                    deleted += 1
                except Exception as e:
                    log.warning(
                        "retention delete failed for %s/%s: %s",
                        bucket, blob.key, e,
                    )
            else:
                retained += 1
        self._deleted += deleted
        self._retained += retained
        log.info(
            "sweep %s scanned=%d deleted=%d retained=%d",
            bucket, scanned, deleted, retained,
        )
        return scanned
