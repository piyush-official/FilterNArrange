"""Validate RegexSpec — pattern compiles and flags are recognised."""
from __future__ import annotations
import re
from typing import Optional

from filternarrange_engine.core.canonical import Column
from filternarrange_engine.core.filter_spec import RegexSpec


def validate(spec: RegexSpec, schema: Optional[list[Column]] = None) -> list[str]:
    errors: list[str] = []
    try:
        re.compile(spec.pattern)
    except re.error as e:
        errors.append(f"invalid regex: {e}")
    for f in spec.flags:
        if f not in {"i", "m", "s"}:
            errors.append(f"unknown flag: {f!r}")
    return errors


__all__ = ["validate"]
