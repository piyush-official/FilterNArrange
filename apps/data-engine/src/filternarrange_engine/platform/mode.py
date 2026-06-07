"""MODE switch for the data-engine service.

Per spec §2 loose-coupling rule 6, the same Python image runs in one of four
modes. Plan D introduces ``worker``. The mode is read once at startup and
exposed as a frozen enum.
"""
from __future__ import annotations

import enum
import os


class Mode(str, enum.Enum):
    FULL = "full"      # HTTP + worker (dev convenience)
    DATA = "data"      # HTTP only — sync path
    AI = "ai"          # placeholder for Plan E
    WORKER = "worker"  # Kafka consumer only

    @classmethod
    def current(cls) -> "Mode":
        raw = os.getenv("MODE", "full").lower().strip()
        try:
            return cls(raw)
        except ValueError as exc:
            raise SystemExit(
                f"Invalid MODE={raw!r}; expected one of "
                f"{[m.value for m in cls]}"
            ) from exc


def serves_http(mode: Mode) -> bool:
    return mode in (Mode.FULL, Mode.DATA, Mode.AI)


def serves_worker(mode: Mode) -> bool:
    return mode in (Mode.FULL, Mode.WORKER)


__all__ = ["Mode", "serves_http", "serves_worker"]
