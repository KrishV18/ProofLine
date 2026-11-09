"""Drafts router."""

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.roles import Role, get_current_user, require_role
from app.db import get_db
from app.models.claim import Claim
from app.models.claim_receipt import ClaimReceipt
from app.models.comment import Comment
from app.models.draft import Draft
from app.models.draft_version import DraftVersion
from app.models.finding import Finding
from app.models.user import User
from app.schemas.finding import Finding as FindingSchema
from app.services.parsing.parser import parse_document
from app.services.review.engine import execute_full_review
from app.services.review.intent_lock import compute_side_by_side_diff, verify_intent_preservation
from app.services.workflow.approval_service import record_approval_decision, request_human_review

router = APIRouter(prefix="/drafts", tags=["drafts"])


class DraftCreateRequest(BaseModel):
    content: str
    channel: Optional[str] = None
    intent_lock: Optional[Dict[str, Any]] = None


class CommentCreateRequest(BaseModel):
    text: str
    range_start: Optional[int] = None
    range_end: Optional[int] = None


class DecisionRequest(BaseModel):
    decision: str
    reason: Optional[str] = None


class DiffRequest(BaseModel):
    original_text: str
    revised_text: str


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_draft(
    req: DraftCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new draft with initial version 1."""
    draft = Draft(
        organisation_id=current_user.organisation_id,
        created_by=current_user.id,
        channel=req.channel,
        status="draft",
        intent_lock=req.intent_lock,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    version = DraftVersion(
        organisation_id=current_user.organisation_id,
        draft_id=draft.id,
        version_number=1,
        content=req.content,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    log_action(
        db=db,
        user_id=current_user.id,
        action="draft_created",
        entity="draft",
        entity_id=draft.id,
        details={"channel": draft.channel, "content_length": len(req.content)},
        organisation_id=current_user.organisation_id,
    )

    return {
        "id": str(draft.id),
        "organisation_id": str(draft.organisation_id),
        "created_by": str(draft.created_by),
        "channel": draft.channel,
        "status": draft.status,
        "created_at": draft.created_at,
    }


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document_draft(
    file: UploadFile = File(...),
    channel: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a PDF, DOCX, or text file and automatically create a new draft."""
    file_bytes = await file.read()
    try:
        extracted_text, detected_type = parse_document(file.filename or "uploaded_doc", file_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse document: {str(exc)}",
        )

    draft = Draft(
        organisation_id=current_user.organisation_id,
        created_by=current_user.id,
        channel=channel or f"Upload: {file.filename}",
        status="draft",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    version = DraftVersion(
        organisation_id=current_user.organisation_id,
        draft_id=draft.id,
        version_number=1,
        content=extracted_text,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    log_action(
        db=db,
        user_id=current_user.id,
        action="draft_uploaded",
        entity="draft",
        entity_id=draft.id,
        details={"filename": file.filename, "file_type": detected_type},
        organisation_id=current_user.organisation_id,
    )

    return {
        "id": str(draft.id),
        "filename": file.filename,
        "detected_type": detected_type,
        "content_length": len(extracted_text),
        "status": draft.status,
    }


@router.get("")
async def list_drafts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List drafts for current organisation."""
    drafts = db.scalars(
        select(Draft)
        .where(Draft.organisation_id == current_user.organisation_id)
        .order_by(desc(Draft.created_at))
    ).all()

    items = []
    for d in drafts:
        latest_ver = db.scalars(
            select(DraftVersion)
            .where(DraftVersion.draft_id == d.id)
            .order_by(desc(DraftVersion.version_number))
        ).first()

        items.append(
            {
                "id": str(d.id),
                "channel": d.channel,
                "status": d.status,
                "created_at": d.created_at,
                "created_by": str(d.created_by),
                "latest_version": latest_ver.version_number if latest_ver else 1,
                "content_preview": (latest_ver.content[:120] + "...") if latest_ver else "",
            }
        )

    return items


@router.get("/{draft_id}")
async def get_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve draft details and latest version content."""
    draft_uuid = uuid.UUID(draft_id)
    draft = db.get(Draft, draft_uuid)
    if not draft or draft.organisation_id != current_user.organisation_id:
        raise HTTPException(status_code=404, detail="Draft not found")

    latest_ver = db.scalars(
        select(DraftVersion)
        .where(DraftVersion.draft_id == draft.id)
        .order_by(desc(DraftVersion.version_number))
    ).first()

    return {
        "id": str(draft.id),
        "channel": draft.channel,
        "status": draft.status,
        "intent_lock": draft.intent_lock,
        "created_at": draft.created_at,
        "created_by": str(draft.created_by),
        "latest_version": latest_ver.version_number if latest_ver else 1,
        "content": latest_ver.content if latest_ver else "",
    }


@router.post("/{draft_id}/review", status_code=status.HTTP_202_ACCEPTED)
async def trigger_review(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger automated 4-layer review of draft's latest version."""
    draft_uuid = uuid.UUID(draft_id)
    draft = db.get(Draft, draft_uuid)
    if not draft or draft.organisation_id != current_user.organisation_id:
        raise HTTPException(status_code=404, detail="Draft not found")

    latest_ver = db.scalars(
        select(DraftVersion)
        .where(DraftVersion.draft_id == draft.id)
        .order_by(desc(DraftVersion.version_number))
    ).first()

    if not latest_ver:
        raise HTTPException(status_code=400, detail="Draft has no content versions")

    review_res = execute_full_review(db, draft, latest_ver, current_user.id)
    return review_res


@router.get("/{draft_id}/versions/{version}/findings")
async def get_findings(
    draft_id: str,
    version: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all findings for a specific draft version."""
    draft_uuid = uuid.UUID(draft_id)
    draft = db.get(Draft, draft_uuid)
    if not draft or draft.organisation_id != current_user.organisation_id:
        raise HTTPException(status_code=404, detail="Draft not found")

    target_ver = db.scalars(
        select(DraftVersion).where(
            DraftVersion.draft_id == draft.id,
            DraftVersion.version_number == version,
        )
    ).first()

    if not target_ver:
        return []

    findings = db.scalars(
        select(Finding).where(Finding.version_id == target_ver.id)
    ).all()

    return [
        {
            "id": str(f.id),
            "draft_id": str(f.draft_id),
            "version_id": str(f.version_id),
            "quoted_text": f.quoted_text or "",
            "start": f.start or 0,
            "end": f.end or 0,
            "severity": f.severity,
            "reason": f.reason or "",
            "source_ref": f.source_ref,
            "source_version": f.source_version or 1,
            "confidence": f.confidence,
            "suggestion": f.suggestion,
            "status": f.status,
            "dismissal_reason": f.dismissal_reason,
        }
        for f in findings
    ]


@router.get("/{draft_id}/versions/{version}/claims")
async def get_claims(
    draft_id: str,
    version: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Claim Ledger items for a specific draft version."""
    draft_uuid = uuid.UUID(draft_id)
    draft = db.get(Draft, draft_uuid)
    if not draft or draft.organisation_id != current_user.organisation_id:
        raise HTTPException(status_code=404, detail="Draft not found")

    target_ver = db.scalars(
        select(DraftVersion).where(
            DraftVersion.draft_id == draft.id,
            DraftVersion.version_number == version,
        )
    ).first()

    if not target_ver:
        return []

    claims = db.scalars(
        select(Claim).where(Claim.version_id == target_ver.id)
    ).all()

    return [
        {
            "id": str(c.id),
            "draft_id": str(c.draft_id),
            "version_id": str(c.version_id),
            "quoted_text": c.quoted_text,
            "status": c.status,
            "source_ref": c.source_ref,
            "checked_at": c.checked_at,
        }
        for c in claims
    ]


@router.post("/{draft_id}/diff")
async def compute_diff(
    draft_id: str,
    req: DiffRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compute visual side-by-side diff and check Intent Lock message preservation."""
    draft_uuid = uuid.UUID(draft_id)
    draft = db.get(Draft, draft_uuid)
    if not draft or draft.organisation_id != current_user.organisation_id:
        raise HTTPException(status_code=404, detail="Draft not found")

    diff_tokens = compute_side_by_side_diff(req.original_text, req.revised_text)
    intent_eval = verify_intent_preservation(req.original_text, req.revised_text, draft.intent_lock)

    return {
        "diff_tokens": diff_tokens,
        "intent_preservation": intent_eval,
    }


@router.post("/{draft_id}/request-review", status_code=status.HTTP_202_ACCEPTED)
async def trigger_request_review(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Request human review of the draft, evaluating risk tier."""
    draft_uuid = uuid.UUID(draft_id)
    draft = db.get(Draft, draft_uuid)
    if not draft or draft.organisation_id != current_user.organisation_id:
        raise HTTPException(status_code=404, detail="Draft not found")

    result = request_human_review(db, draft, current_user)
    return result


@router.post("/{draft_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(
    draft_id: str,
    req: CommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a comment to a draft."""
    draft_uuid = uuid.UUID(draft_id)
    draft = db.get(Draft, draft_uuid)
    if not draft or draft.organisation_id != current_user.organisation_id:
        raise HTTPException(status_code=404, detail="Draft not found")

    comment = Comment(
        organisation_id=draft.organisation_id,
        draft_id=draft.id,
        user_id=current_user.id,
        text=req.text,
        range_start=req.range_start,
        range_end=req.range_end,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        "id": str(comment.id),
        "draft_id": str(comment.draft_id),
        "user_id": str(comment.user_id),
        "text": comment.text,
        "range_start": comment.range_start,
        "range_end": comment.range_end,
        "created_at": comment.created_at,
    }


@router.get("/{draft_id}/comments")
async def list_comments(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List comments on a draft."""
    draft_uuid = uuid.UUID(draft_id)
    comments = db.scalars(
        select(Comment)
        .where(Comment.draft_id == draft_uuid)
        .order_by(Comment.created_at)
    ).all()

    return [
        {
            "id": str(c.id),
            "draft_id": str(c.draft_id),
            "user_id": str(c.user_id),
            "text": c.text,
            "range_start": c.range_start,
            "range_end": c.range_end,
            "created_at": c.created_at,
        }
        for c in comments
    ]


@router.post("/{draft_id}/decision", status_code=status.HTTP_201_CREATED)
async def record_decision(
    draft_id: str,
    req: DecisionRequest,
    current_user: User = Depends(require_role(Role.REVIEWER, Role.MANAGER, Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """Record an approval decision on a draft."""
    draft_uuid = uuid.UUID(draft_id)
    draft = db.get(Draft, draft_uuid)
    if not draft or draft.organisation_id != current_user.organisation_id:
        raise HTTPException(status_code=404, detail="Draft not found")

    approval = record_approval_decision(db, draft, current_user, req.decision, req.reason)
    return {
        "id": str(approval.id),
        "draft_id": str(approval.draft_id),
        "user_id": str(approval.user_id),
        "decision": approval.decision,
        "reason": approval.reason,
        "created_at": approval.created_at,
    }


@router.get("/{draft_id}/receipt")
async def get_receipt(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the Claim Receipts generated for an approved draft."""
    draft_uuid = uuid.UUID(draft_id)
    draft = db.get(Draft, draft_uuid)
    if not draft or draft.organisation_id != current_user.organisation_id:
        raise HTTPException(status_code=404, detail="Draft not found")

    receipts = db.scalars(
        select(ClaimReceipt).where(ClaimReceipt.organisation_id == draft.organisation_id)
    ).all()

    # Filter receipts matching this draft
    draft_receipts = [
        {
            "id": str(r.id),
            "claim_id": str(r.claim_id),
            "organisation_id": str(r.organisation_id),
            "receipt_data": r.receipt_data,
        }
        for r in receipts
        if r.receipt_data and str(r.receipt_data.get("draft_id")) == str(draft.id)
    ]

    return {
        "draft_id": str(draft.id),
        "status": draft.status,
        "receipts_count": len(draft_receipts),
        "receipts": draft_receipts,
    }
