"""Shared type inference helper for format plugins.

Walks a sample of stringified values and reports the tightest TypeTag the
column can take across the whole sample. Returns STRING when the column is
empty or mixed.
"""
from __future__ import annotations
from typing import Iterable

from .types import TypeTag


def _is_int(v: str) -> bool:
    try:
        int(v)
    except (ValueError, TypeError):
        return False
    return True


def _is_float(v: str) -> bool:
    try:
        float(v)
    except (ValueError, TypeError):
        return False
    return True


def _is_bool(v: str) -> bool:
    return isinstance(v, str) and v.strip().lower() in {"true", "false", "0", "1", "yes", "no"}


def value_to_type_tag(v) -> TypeTag:
    """Tightest TypeTag for a single Python value."""
    if v is None:
        return TypeTag.NULL
    if isinstance(v, bool):
        return TypeTag.BOOLEAN
    if isinstance(v, int):
        return TypeTag.INTEGER
    if isinstance(v, float):
        return TypeTag.NUMBER
    if isinstance(v, str):
        return TypeTag.STRING
    return TypeTag.STRING


def infer_type_tag(values: Iterable) -> TypeTag:
    """Infer the column type from a sample. Empty/None values are skipped."""
    cleaned = [v for v in values if v not in (None, "")]
    if not cleaned:
        return TypeTag.STRING
    str_cleaned = [v if isinstance(v, str) else str(v) for v in cleaned]
    if all(_is_int(v) for v in str_cleaned):
        return TypeTag.INTEGER
    if all(_is_float(v) for v in str_cleaned):
        return TypeTag.NUMBER
    if all(_is_bool(v) for v in str_cleaned):
        return TypeTag.BOOLEAN
    return TypeTag.STRING


__all__ = ["infer_type_tag", "value_to_type_tag"]
