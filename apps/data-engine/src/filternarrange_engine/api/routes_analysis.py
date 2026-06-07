from fastapi import APIRouter, Depends, Request

from .dependencies import trace_id_from_request
from .schemas import AnalyzeRequest, AnalyzeResponse


router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest, request: Request, trace_id: str = Depends(trace_id_from_request)):
    svc = request.app.state.analysis
    result = await svc.run(req.ref, req.analysis, filter_spec=req.filter)
    return AnalyzeResponse(**result)
