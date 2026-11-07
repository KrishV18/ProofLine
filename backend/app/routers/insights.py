"""Insights router."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/rules")
async def get_rule_insights():
    """Get rule performance analytics."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})

