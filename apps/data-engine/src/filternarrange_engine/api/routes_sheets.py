"""POST /sheets — list sheets in an XLSX upload.

The gateway resolves an upload-id to a MinIO ref and calls this endpoint with
the ref. We re-use the format detection from PluginRegistry so this endpoint
is a thin wrapper around format-xlsx's list_sheets().
"""
from __future__ import annotations
import io as _io
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from filternarrange_engine.platform.errors import EngineError

from .dependencies import trace_id_from_request


router = APIRouter()


class SheetsRequest(BaseModel):
    ref: str


class SheetsResponse(BaseModel):
    sheets: list[str]


@router.post("/sheets", response_model=SheetsResponse)
def sheets(req: SheetsRequest, request: Request, trace_id: str = Depends(trace_id_from_request)):
    store = request.app.state.store
    registry = request.app.state.registry

    try:
        blob = store.get(req.ref).read()
    except FileNotFoundError as e:
        raise EngineError(code="NOT_FOUND", message=str(e), http_status=404) from e

    choice = registry.detect_format(blob[:65536])
    if choice is None:
        raise EngineError(code="UNKNOWN_FORMAT", message="no plugin matched", http_status=422)
    fid, _ = choice
    if fid != "xlsx":
        raise EngineError(code="NOT_MULTI_SHEET", message=f"upload format is {fid!r}, not xlsx",
                          http_status=400)

    plugin = registry.get_format("xlsx")
    list_sheets = getattr(plugin, "list_sheets", None)
    if list_sheets is None:
        raise EngineError(code="UNSUPPORTED",
                          message="xlsx plugin does not expose list_sheets()",
                          http_status=500)
    try:
        names: list[Any] = list(list_sheets(_io.BytesIO(blob)))
    except Exception as e:  # noqa: BLE001 — surfaces as a structured envelope
        raise EngineError(code="PLUGIN_FAILURE",
                          message=f"list_sheets failed: {e}",
                          http_status=500,
                          plugin_id="xlsx") from e
    return SheetsResponse(sheets=[str(n) for n in names])
