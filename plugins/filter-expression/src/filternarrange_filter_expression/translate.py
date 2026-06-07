"""Shared SQL-ish → Python translator (used by both apply and validate)."""
from __future__ import annotations
import re


def translate(expr: str) -> str:
    expr = re.sub(r"(?<![<>=!])=(?!=)", "==", expr)
    expr = re.sub(r"\bAND\b", "and", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bOR\b",  "or",  expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bNOT\b", "not", expr, flags=re.IGNORECASE)
    return expr


__all__ = ["translate"]
