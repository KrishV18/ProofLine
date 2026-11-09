"""Drafts router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.roles import require_role

router = APIRouter(prefix="/drafts", tags=["drafts"])


@router.post("", dependencies=[Depends(require_role("creator"))])
async def create_draft():
    """Create a new draft."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/{id}/review", dependencies=[Depends(require_role("creator"))])
async def trigger_review(id: str):
    """Trigger an automated review of the draft."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/{id}/versions/{v}/findings", dependencies=[Depends(require_role("creator", "reviewer"))])
async def get_findings(id: str, v: int):
    """Get all findings for a specific draft version."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/{id}/request-review", dependencies=[Depends(require_role("creator"))])
async def request_review(id: str):
    """Request a human review of the draft."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/{id}/comments", dependencies=[Depends(require_role("creator", "reviewer"))])
async def add_comment(id: str):
    """Add a comment to a draft."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/{id}/decision", dependencies=[Depends(require_role("reviewer"))])
async def record_decision(id: str):
    """Record an approval decision on a draft."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/{id}/receipt", dependencies=[Depends(require_role("creator", "reviewer", "admin"))])
async def get_receipt(id: str):
    """Get the review receipt for a draft."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
