"""Master Review Engine: Orchestrates the 4-layer review pipeline and persists results."""

import logging
import uuid
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.models.claim import Claim
from app.models.draft import Draft
from app.models.draft_version import DraftVersion
from app.models.fact import Fact
from app.models.finding import Finding
from app.models.guideline_rule import GuidelineRule
from app.models.term import Term
from app.schemas.finding import FindingBase
from app.services.review.claim_ledger import process_claim_ledger
from app.services.review.deterministic import run_deterministic_checks
from app.services.review.tone_engine import evaluate_grounded_tone
from app.services.review.validator import validate_and_filter_findings

logger = logging.getLogger(__name__)


def execute_full_review(
    db: Session,
    draft: Draft,
    version: DraftVersion,
    user_id: uuid.UUID | None = None,
) -> Dict[str, Any]:
    """Run the 4-layer review pipeline on a draft version and persist findings & claims."""
    org_id = draft.organisation_id
    content = version.content

    # 1. Fetch sources for organisation
    rules = db.scalars(
        select(GuidelineRule).where(
            GuidelineRule.organisation_id == org_id,
            GuidelineRule.is_active == True,  # noqa: E712
        )
    ).all()

    facts = db.scalars(
        select(Fact).where(Fact.organisation_id == org_id)
    ).all()

    terms = db.scalars(
        select(Term).where(Term.organisation_id == org_id)
    ).all()

    # Compile valid sources for Layer 4 validator
    valid_source_refs = set()
    for r in rules:
        valid_source_refs.add(r.rule_id)
    for f in facts:
        valid_source_refs.add(f.statement)
        if f.source:
            valid_source_refs.add(f.source)
    for t in terms:
        valid_source_refs.add(f"TERM-{t.term.upper()}")
        valid_source_refs.add(t.term)

    # Layer 1: Deterministic checks (terminology, readability)
    deterministic_findings = run_deterministic_checks(content, list(terms))

    # Layer 2: Claim Ledger (claim extraction & fact verification)
    extracted_claims, claim_findings = process_claim_ledger(content, list(facts))

    # Layer 3: Grounded Tone & Guideline check
    tone_findings = evaluate_grounded_tone(content, list(rules))

    # Combine candidates from Layers 1, 2, and 3
    candidate_findings: List[FindingBase] = (
        deterministic_findings + claim_findings + tone_findings
    )

    # Layer 4: Source Validator ("No source, no flag")
    validated_findings = validate_and_filter_findings(
        findings=candidate_findings,
        content=content,
        valid_source_refs=valid_source_refs,
    )

    # Clear old findings & claims for this specific version to support re-checking
    db.query(Finding).filter(Finding.version_id == version.id).delete()
    db.query(Claim).filter(Claim.version_id == version.id).delete()

    # Persist claims in Claim Ledger table
    persisted_claims = []
    for c in extracted_claims:
        claim_row = Claim(
            organisation_id=org_id,
            draft_id=draft.id,
            version_id=version.id,
            quoted_text=c.quoted_text,
            status=c.status.value,
            source_ref=c.source_ref,
        )
        db.add(claim_row)
        persisted_claims.append(claim_row)

    # Persist validated findings in Finding table
    persisted_findings = []
    blockers_count = 0
    warnings_count = 0

    for vf in validated_findings:
        if vf.severity == "blocker":
            blockers_count += 1
        elif vf.severity == "warning":
            warnings_count += 1

        finding_row = Finding(
            organisation_id=org_id,
            draft_id=draft.id,
            version_id=version.id,
            quoted_text=vf.quoted_text,
            start=vf.start,
            end=vf.end,
            severity=vf.severity,
            reason=vf.reason,
            source_ref=vf.source_ref,
            source_version=vf.source_version,
            confidence=vf.confidence,
            suggestion=vf.suggestion,
            status=vf.status,
            dismissal_reason=vf.dismissal_reason,
        )
        db.add(finding_row)
        persisted_findings.append(finding_row)

    # Update draft status
    draft.status = "reviewed"
    db.commit()

    # Audit log entry
    log_action(
        db=db,
        user_id=user_id,
        action="review_completed",
        entity="draft_version",
        entity_id=version.id,
        details={
            "draft_id": str(draft.id),
            "version_number": version.version_number,
            "findings_count": len(persisted_findings),
            "blockers_count": blockers_count,
            "warnings_count": warnings_count,
            "claims_count": len(persisted_claims),
        },
        organisation_id=org_id,
    )

    return {
        "draft_id": str(draft.id),
        "version": version.version_number,
        "findings_count": len(persisted_findings),
        "claims_count": len(persisted_claims),
        "blockers_count": blockers_count,
        "warnings_count": warnings_count,
        "status": "reviewed",
    }

