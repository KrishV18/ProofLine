"""Audit router."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def get_audit_log():
    """Get the audit log entries."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})

