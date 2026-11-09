"""Approval & Review Workflow Service with Role-Based Risk Matrix."""

import uuid
from typing import Any, Dict
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.models.approval import Approval
from app.models.draft import Draft
from app.models.draft_version import DraftVersion
from app.models.finding import Finding
from app.models.user import User
from app.services.workflow.receipt_service import generate_claim_receipts


def calculate_risk_tier(db: Session, version_id: uuid.UUID) -> Dict[str, Any]:
    """Calculate role-based risk tier according to the Code-Titans hackathon matrix:

    - Level 1 (Low): Routine phrasing / grammar tweaks -> Creator / SM Executive self-sign-off
    - Level 2 (Medium): Standard promo copy, feature descriptions -> Department Manager sign-off
    - Level 3 (High): Pricing contradictions, unsupported claims, legal disclaimers -> Senior Brand Manager / Legal Counsel sign-off
    """
    findings = db.scalars(select(Finding).where(Finding.version_id == version_id)).all()

    has_blockers = any(f.severity == "blocker" for f in findings)
    has_warnings = any(f.severity == "warning" for f in findings)

    if has_blockers:
        return {
            "risk_tier": "Level 3: High",
            "required_role": "reviewer",
            "action": "Strict quarantine; mandatory compliance review and sign-off.",
        }
    elif has_warnings:
        return {
            "risk_tier": "Level 2: Medium",
            "required_role": "manager",
            "action": "Requires department manager sign-off.",
        }
    else:
        return {
            "risk_tier": "Level 1: Low",
            "required_role": "creator",
            "action": "Auto-approved or quick peer review.",
        }


def request_human_review(db: Session, draft: Draft, user: User) -> Dict[str, Any]:
    """Submit a draft for human review and assign appropriate risk tier."""
    latest_version = db.scalars(
        select(DraftVersion)
        .where(DraftVersion.draft_id == draft.id)
        .order_by(desc(DraftVersion.version_number))
    ).first()

    risk_info = (
        calculate_risk_tier(db, latest_version.id)
        if latest_version
        else {"risk_tier": "Level 1: Low", "required_role": "creator"}
    )

    draft.status = "review_requested"
    db.commit()

    log_action(
        db=db,
        user_id=user.id,
        action="review_requested",
        entity="draft",
        entity_id=draft.id,
        details={
            "risk_tier": risk_info["risk_tier"],
            "required_role": risk_info["required_role"],
            "version_number": latest_version.version_number if latest_version else 1,
        },
        organisation_id=draft.organisation_id,
    )

    return {
        "draft_id": str(draft.id),
        "status": "review_requested",
        "risk_tier": risk_info["risk_tier"],
        "required_role": risk_info["required_role"],
    }


def record_approval_decision(
    db: Session,
    draft: Draft,
    user: User,
    decision: str,
    reason: str | None = None,
) -> Approval:
    """Record an approval, rejection, or request-changes decision."""
    latest_version = db.scalars(
        select(DraftVersion)
        .where(DraftVersion.draft_id == draft.id)
        .order_by(desc(DraftVersion.version_number))
    ).first()

    # Map decision to draft status
    if decision.lower() in ["approved", "approve"]:
        draft.status = "approved"
        # Generate Claim Receipts upon approval
        if latest_version:
            generate_claim_receipts(db, draft, latest_version, user)
    elif decision.lower() in ["needs_changes", "request_changes"]:
        draft.status = "changes_requested"
    elif decision.lower() in ["rejected", "reject"]:
        draft.status = "rejected"

    approval_entry = Approval(
        organisation_id=draft.organisation_id,
        draft_id=draft.id,
        user_id=user.id,
        decision=decision,
        reason=reason,
    )
    db.add(approval_entry)
    db.commit()
    db.refresh(approval_entry)

    log_action(
        db=db,
        user_id=user.id,
        action=f"draft_{decision.lower()}",
        entity="approval",
        entity_id=approval_entry.id,
        details={
            "draft_id": str(draft.id),
            "decision": decision,
            "reason": reason,
        },
        organisation_id=draft.organisation_id,
    )

    return approval_entry

