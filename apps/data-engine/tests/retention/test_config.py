import datetime

import pytest

from filternarrange_engine.retention.config import RetentionConfig


_ENV_VARS = [
    "UPLOAD_RETENTION_FREE_HOURS",
    "UPLOAD_RETENTION_PAID_DAYS",
    "RESULT_RETENTION_FREE_HOURS",
    "RESULT_RETENTION_PAID_DAYS",
    "RETENTION_INTERVAL_MINUTES",
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in _ENV_VARS:
        monkeypatch.delenv(k, raising=False)


def test_defaults_match_spec():
    cfg = RetentionConfig.from_env()
    assert cfg.upload_free_hours == 24
    assert cfg.upload_paid_days == 30
    assert cfg.result_free_hours == 24
    assert cfg.result_paid_days == 30


def test_overrides(monkeypatch):
    monkeypatch.setenv("UPLOAD_RETENTION_FREE_HOURS", "6")
    monkeypatch.setenv("UPLOAD_RETENTION_PAID_DAYS", "90")
    cfg = RetentionConfig.from_env()
    assert cfg.upload_free_hours == 6
    assert cfg.upload_paid_days == 90


def test_cutoffs():
    cfg = RetentionConfig.from_env()
    now = datetime.datetime(2026, 6, 7, 12, 0, tzinfo=datetime.timezone.utc)
    assert cfg.upload_cutoff(tier="free", now=now) == now - datetime.timedelta(hours=24)
    assert cfg.upload_cutoff(tier="paid", now=now) == now - datetime.timedelta(days=30)
    assert cfg.result_cutoff(tier="free", now=now) == now - datetime.timedelta(hours=24)
    assert cfg.result_cutoff(tier="paid", now=now) == now - datetime.timedelta(days=30)
