"""Plan D Task 11 — MODE switch."""
from __future__ import annotations
import pytest

from filternarrange_engine.platform.mode import Mode, serves_http, serves_worker


def test_current_defaults_to_full(monkeypatch):
    monkeypatch.delenv("MODE", raising=False)
    assert Mode.current() is Mode.FULL


@pytest.mark.parametrize("raw,expected", [
    ("full", Mode.FULL),
    ("data", Mode.DATA),
    ("ai", Mode.AI),
    ("worker", Mode.WORKER),
    ("  WORKER ", Mode.WORKER),  # case + whitespace tolerant
])
def test_current_parses(monkeypatch, raw, expected):
    monkeypatch.setenv("MODE", raw)
    assert Mode.current() is expected


def test_current_rejects_unknown(monkeypatch):
    monkeypatch.setenv("MODE", "bogus")
    with pytest.raises(SystemExit):
        Mode.current()


def test_serves_predicates():
    assert serves_http(Mode.FULL) and serves_worker(Mode.FULL)
    assert serves_http(Mode.DATA) and not serves_worker(Mode.DATA)
    assert not serves_http(Mode.WORKER) and serves_worker(Mode.WORKER)
    assert serves_http(Mode.AI) and not serves_worker(Mode.AI)
