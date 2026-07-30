import asyncio
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from ai_filter_service import get_status, run_filter, _state
from schemas import AiFilterStatus

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ai-filter/run", status_code=202)
async def trigger_filter(model: str = "gpt-4o-mini") -> dict:
    if _state["status"] == "running":
        return JSONResponse(status_code=409, content={"detail": "Filter already running"})
    asyncio.create_task(run_filter(model))
    return {"status": "started"}


@router.get("/ai-filter/status", response_model=AiFilterStatus)
def get_filter_status() -> AiFilterStatus:
    return AiFilterStatus(**get_status())


@router.post("/ai-filter/cancel")
def cancel_filter() -> dict:
    _state["cancel_requested"] = True
    return {"status": "cancel_requested"}
