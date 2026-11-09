"""Insights router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.roles import require_role

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/rules", dependencies=[Depends(require_role("reviewer", "admin"))])
async def get_rule_insights():
    """Get rule performance analytics."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
