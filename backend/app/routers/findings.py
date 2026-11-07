"""Findings router."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/findings", tags=["findings"])


@router.patch("/{finding_id}")
async def update_finding(finding_id: str):
    """Update the status or dismissal reason of a finding."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})

