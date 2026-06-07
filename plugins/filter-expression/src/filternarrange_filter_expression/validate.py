"""Schema-aware validation for ExpressionSpec."""
from __future__ import annotations
import ast
from typing import Optional

from filternarrange_engine.core.canonical import Column
from filternarrange_engine.core.filter_spec import ExpressionSpec

from .translate import translate


def validate(spec: ExpressionSpec, schema: Optional[list[Column]] = None) -> list[str]:
    errors: list[str] = []
    try:
        tree = ast.parse(translate(spec.expr), mode="eval")
    except SyntaxError as e:
        return [f"syntax error: {e.msg} at col {e.offset}"]
    if schema is not None:
        names = {c.name for c in schema}
        from .apply import registered_functions
        funcs = set(registered_functions().keys())
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id not in names \
                    and node.id not in {"True", "False", "None"} \
                    and node.id not in funcs:
                errors.append(f"unknown name: {node.id!r}")
    return errors


__all__ = ["validate"]
