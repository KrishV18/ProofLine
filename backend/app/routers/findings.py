"""Findings router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.roles import require_role

router = APIRouter(prefix="/findings", tags=["findings"])


@router.patch("/{id}", dependencies=[Depends(require_role("creator"))])
async def update_finding(id: str):
    """Update the status or dismissal reason of a finding."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
