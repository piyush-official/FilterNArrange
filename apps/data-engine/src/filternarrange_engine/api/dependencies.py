"""FastAPI dependency providers."""
from __future__ import annotations
import uuid
from contextvars import ContextVar
from fastapi import Request

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def trace_id_from_request(request: Request) -> str:
    existing = request.headers.get("X-Trace-Id")
    tid = existing if existing else str(uuid.uuid4())
    trace_id_var.set(tid)
    return tid
