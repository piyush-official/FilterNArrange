from fastapi import APIRouter, Depends, Request
from .schemas import RefRequest, DetectResponse
from .dependencies import trace_id_from_request

router = APIRouter()


@router.post("/detect", response_model=DetectResponse, response_model_by_alias=True)
def detect(req: RefRequest, request: Request, trace_id: str = Depends(trace_id_from_request)):
    svc = request.app.state.detect
    result = svc.run(req.ref)
    return DetectResponse(format=result["format"], confidence=result["confidence"],
                          **{"schema": result["schema"]})
