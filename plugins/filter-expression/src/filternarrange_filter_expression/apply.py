"""Expression evaluation via simpleeval over dict-shaped rows."""
from __future__ import annotations
from typing import AsyncIterator, Callable

from simpleeval import FunctionNotDefined, NameNotDefined, SimpleEval

from filternarrange_engine.core.canonical import TabularData
from filternarrange_engine.core.filter_spec import ExpressionSpec

from .translate import translate


_FUNCTIONS: dict[str, Callable] = {}
_SIGNATURES: dict[str, str] = {}


def register_function(name: str, fn: Callable, signature: str) -> None:
    _FUNCTIONS[name] = fn
    _SIGNATURES[name] = signature


def registered_functions() -> dict[str, str]:
    return dict(_SIGNATURES)


def apply(data: TabularData, spec: ExpressionSpec) -> TabularData:
    py_expr = translate(spec.expr)

    async def out() -> AsyncIterator[dict]:
        async for row in data.rows:
            ev = SimpleEval(names=dict(row), functions=dict(_FUNCTIONS))
            try:
                if bool(ev.eval(py_expr)):
                    yield row
            except (FunctionNotDefined, NameNotDefined, SyntaxError):
                continue

    return TabularData(schema=data.schema, rows=out(), meta=data.meta)


__all__ = ["apply", "register_function", "registered_functions"]
