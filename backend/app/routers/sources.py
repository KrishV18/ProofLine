"""Sources router – guidelines, facts, terminology."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.roles import require_role

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", dependencies=[Depends(require_role("creator", "reviewer", "admin"))])
async def list_sources():
    """List all sources (guidelines, facts, terminology)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/guidelines", dependencies=[Depends(require_role("admin"))])
async def create_guideline():
    """Upload or create a guideline rule."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/facts", dependencies=[Depends(require_role("admin"))])
async def create_fact():
    """Upload or create a fact entry."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.post("/terms", dependencies=[Depends(require_role("admin"))])
async def create_term():
    """Upload or create a terminology entry."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
