"""Schema-aware validation for RowSpec."""
from __future__ import annotations
from typing import Optional

from filternarrange_engine.core.canonical import Column
from filternarrange_engine.core.filter_spec import RowSpec


_VALID_OPS = {
    "eq", "ne", "gt", "gte", "lt", "lte",
    "contains", "starts_with", "ends_with",
    "regex", "in", "not_in", "is_null", "is_not_null",
}


def validate(spec: RowSpec, schema: Optional[list[Column]] = None) -> list[str]:
    errors: list[str] = []
    if spec.predicate.op not in _VALID_OPS:
        errors.append(f"unknown op: {spec.predicate.op}")
    if schema is not None:
        names = {c.name for c in schema}
        if spec.predicate.col not in names:
            errors.append(f"unknown column: {spec.predicate.col!r} (available: {sorted(names)})")
    if spec.predicate.op in {"in", "not_in"} and not isinstance(spec.predicate.value, list):
        errors.append(f"{spec.predicate.op} requires a list value")
    return errors


__all__ = ["validate"]
