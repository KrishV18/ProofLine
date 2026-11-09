"""Audit router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.roles import require_role

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", dependencies=[Depends(require_role("admin"))])
async def get_audit_log():
    """Get the audit log entries."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
