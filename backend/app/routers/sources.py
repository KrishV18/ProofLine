"""Sources router (guidelines, facts, terminology)."""

from datetime import date
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.roles import Role, get_current_user, require_role
from app.db import get_db
from app.models.fact import Fact
from app.models.guideline_rule import GuidelineRule
from app.models.term import Term
from app.models.user import User
from app.services.workflow.seed_service import seed_sample_data

router = APIRouter(prefix="/sources", tags=["sources"])


class GuidelineCreate(BaseModel):
    rule_id: str
    text: str
    category: Optional[str] = None


class FactCreate(BaseModel):
    statement: str
    value: Optional[str] = None
    owner: Optional[str] = None
    source: Optional[str] = None
    expires_on: Optional[date] = None


class TermCreate(BaseModel):
    term: str
    preferred: Optional[str] = None
    banned: bool = False
    notes: Optional[str] = None


@router.post("/guidelines", status_code=status.HTTP_201_CREATED)
async def create_guideline(
    req: GuidelineCreate,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """Upload or create guideline rules for the organisation."""
    rule = GuidelineRule(
        organisation_id=current_user.organisation_id,
        rule_id=req.rule_id,
        text=req.text,
        category=req.category,
        version=1,
        is_active=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    log_action(
        db=db,
        user_id=current_user.id,
        action="guideline_created",
        entity="guideline_rule",
        entity_id=rule.id,
        details={"rule_id": rule.rule_id},
        organisation_id=current_user.organisation_id,
    )

    return {
        "id": str(rule.id),
        "rule_id": rule.rule_id,
        "text": rule.text,
        "category": rule.category,
        "version": rule.version,
        "is_active": rule.is_active,
    }


@router.post("/facts", status_code=status.HTTP_201_CREATED)
async def create_fact(
    req: FactCreate,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """Upload or create fact entries for the organisation."""
    fact = Fact(
        organisation_id=current_user.organisation_id,
        statement=req.statement,
        value=req.value,
        owner=req.owner,
        source=req.source,
        expires_on=req.expires_on,
        version=1,
    )
    db.add(fact)
    db.commit()
    db.refresh(fact)

    log_action(
        db=db,
        user_id=current_user.id,
        action="fact_created",
        entity="fact",
        entity_id=fact.id,
        details={"statement": fact.statement, "value": fact.value},
        organisation_id=current_user.organisation_id,
    )

    return {
        "id": str(fact.id),
        "statement": fact.statement,
        "value": fact.value,
        "owner": fact.owner,
        "source": fact.source,
        "expires_on": fact.expires_on.isoformat() if fact.expires_on else None,
        "version": fact.version,
    }


@router.post("/terms", status_code=status.HTTP_201_CREATED)
async def create_term(
    req: TermCreate,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """Upload or create terminology entries for the organisation."""
    term_row = Term(
        organisation_id=current_user.organisation_id,
        term=req.term,
        preferred=req.preferred,
        banned=req.banned,
        notes=req.notes,
    )
    db.add(term_row)
    db.commit()
    db.refresh(term_row)

    log_action(
        db=db,
        user_id=current_user.id,
        action="term_created",
        entity="term",
        entity_id=term_row.id,
        details={"term": term_row.term, "banned": term_row.banned},
        organisation_id=current_user.organisation_id,
    )

    return {
        "id": str(term_row.id),
        "term": term_row.term,
        "preferred": term_row.preferred,
        "banned": term_row.banned,
        "notes": term_row.notes,
    }


@router.get("")
async def list_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all sources (guidelines, facts, terminology) for the organisation."""
    org_id = current_user.organisation_id

    guidelines = db.scalars(
        select(GuidelineRule).where(GuidelineRule.organisation_id == org_id)
    ).all()

    facts = db.scalars(
        select(Fact).where(Fact.organisation_id == org_id)
    ).all()

    terms = db.scalars(
        select(Term).where(Term.organisation_id == org_id)
    ).all()

    return {
        "guidelines": [
            {
                "id": str(g.id),
                "rule_id": g.rule_id,
                "text": g.text,
                "category": g.category,
                "version": g.version,
                "is_active": g.is_active,
            }
            for g in guidelines
        ],
        "facts": [
            {
                "id": str(f.id),
                "statement": f.statement,
                "value": f.value,
                "owner": f.owner,
                "source": f.source,
                "expires_on": f.expires_on.isoformat() if f.expires_on else None,
                "version": f.version,
            }
            for f in facts
        ],
        "terms": [
            {
                "id": str(t.id),
                "term": t.term,
                "preferred": t.preferred,
                "banned": t.banned,
                "notes": t.notes,
            }
            for t in terms
        ],
    }


@router.post("/seed")
async def seed_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Seed sample data from sample-data folder into database."""
    res = seed_sample_data(db)
    return res
