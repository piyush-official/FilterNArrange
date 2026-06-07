from fastapi import APIRouter, Depends, Request
from .schemas import FilterRequest, FilterResponse
from .dependencies import trace_id_from_request

router = APIRouter()


@router.post("/filter", response_model=FilterResponse, response_model_by_alias=True)
def filter_(req: FilterRequest, request: Request, trace_id: str = Depends(trace_id_from_request)):
    svc = request.app.state.filter
    result = svc.run(req.ref, req.filter.model_dump(), req.sampleSize)
    return FilterResponse(rows=result["rows"], **{"schema": result["schema"]})
