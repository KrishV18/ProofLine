"""Findings router."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.roles import get_current_user
from app.db import get_db
from app.models.finding import Finding
from app.models.user import User

router = APIRouter(prefix="/findings", tags=["findings"])


class FindingUpdate(BaseModel):
    status: Optional[str] = None
    dismissal_reason: Optional[str] = None


@router.patch("/{finding_id}")
async def update_finding(
    finding_id: str,
    req: FindingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the status or dismissal reason of a finding."""
    finding_uuid = uuid.UUID(finding_id)
    finding = db.get(Finding, finding_uuid)
    if not finding or finding.organisation_id != current_user.organisation_id:
        raise HTTPException(status_code=404, detail="Finding not found")

    if req.status:
        valid_statuses = {"open", "accepted", "edited", "dismissed"}
        if req.status.lower() not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of {valid_statuses}",
            )
        finding.status = req.status.lower()

    if req.dismissal_reason is not None:
        finding.dismissal_reason = req.dismissal_reason

    db.commit()
    db.refresh(finding)

    log_action(
        db=db,
        user_id=current_user.id,
        action=f"finding_{finding.status}",
        entity="finding",
        entity_id=finding.id,
        details={
            "source_ref": finding.source_ref,
            "status": finding.status,
            "dismissal_reason": finding.dismissal_reason,
        },
        organisation_id=current_user.organisation_id,
    )

    return {
        "id": str(finding.id),
        "status": finding.status,
        "dismissal_reason": finding.dismissal_reason,
    }
