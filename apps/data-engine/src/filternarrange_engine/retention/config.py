"""Retention worker configuration (Plan F §T26).

All knobs are env-driven so the same image can run with different policies in
dev / staging / prod without code changes. A value of ``0`` is rejected at
construction time — pass small values for testing instead.
"""
from __future__ import annotations

import datetime as _dt
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RetentionConfig:
    upload_free_hours: int = 24
    upload_paid_days: int = 30
    result_free_hours: int = 24
    result_paid_days: int = 30
    interval_minutes: int = 60

    @classmethod
    def from_env(cls) -> "RetentionConfig":
        return cls(
            upload_free_hours=int(os.environ.get("UPLOAD_RETENTION_FREE_HOURS", "24")),
            upload_paid_days=int(os.environ.get("UPLOAD_RETENTION_PAID_DAYS", "30")),
            result_free_hours=int(os.environ.get("RESULT_RETENTION_FREE_HOURS", "24")),
            result_paid_days=int(os.environ.get("RESULT_RETENTION_PAID_DAYS", "30")),
            interval_minutes=int(os.environ.get("RETENTION_INTERVAL_MINUTES", "60")),
        )

    def upload_cutoff(self, *, tier: str, now: _dt.datetime) -> _dt.datetime:
        if tier == "paid":
            return now - _dt.timedelta(days=self.upload_paid_days)
        return now - _dt.timedelta(hours=self.upload_free_hours)

    def result_cutoff(self, *, tier: str, now: _dt.datetime) -> _dt.datetime:
        if tier == "paid":
            return now - _dt.timedelta(days=self.result_paid_days)
        return now - _dt.timedelta(hours=self.result_free_hours)
