from fastapi import APIRouter, Depends, Request
from .schemas import ConvertRequest, ConvertResponse
from .dependencies import trace_id_from_request

router = APIRouter()


@router.post("/convert", response_model=ConvertResponse)
def convert(req: ConvertRequest, request: Request, trace_id: str = Depends(trace_id_from_request)):
    svc = request.app.state.convert
    result = svc.run(req.ref, req.filter.model_dump(), req.outputFormat)
    return ConvertResponse(resultRef=result["resultRef"])
