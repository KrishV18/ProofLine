"""Claim Receipt Service: Generates cryptographic/immutable evidence receipts upon approval."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.claim_receipt import ClaimReceipt
from app.models.draft import Draft
from app.models.draft_version import DraftVersion
from app.models.user import User


def generate_claim_receipts(
    db: Session,
    draft: Draft,
    version: DraftVersion,
    approved_by: User,
) -> List[ClaimReceipt]:
    """Generate and persist an immutable Claim Receipt for every claim in the approved draft."""
    claims = db.scalars(select(Claim).where(Claim.version_id == version.id)).all()

    receipts: List[ClaimReceipt] = []
    approval_timestamp = datetime.now(timezone.utc).isoformat()

    for claim in claims:
        receipt_payload: Dict[str, Any] = {
            "receipt_id": str(uuid.uuid4()),
            "draft_id": str(draft.id),
            "version_number": version.version_number,
            "claim_quoted_text": claim.quoted_text,
            "claim_status": claim.status,
            "source_ref": claim.source_ref,
            "approved_by_user_id": str(approved_by.id),
            "approved_by_email": approved_by.email,
            "approved_by_role": approved_by.role,
            "approval_timestamp": approval_timestamp,
            "integrity_motto": "Every claim linked to its proof. No source, no flag.",
        }

        receipt = ClaimReceipt(
            organisation_id=draft.organisation_id,
            claim_id=claim.id,
            receipt_data=receipt_payload,
        )
        db.add(receipt)
        receipts.append(receipt)

    db.commit()
    return receipts

