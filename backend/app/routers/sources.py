"""Sources router – guidelines, facts, terminology."""
from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.roles import require_role
from app.db import get_db
from app.models.source import Fact, GuidelineRule, Term
from app.models.user import User
from app.services.parsing.parser import parse_document
from app.services.workflow.guideline_extractor import extract_guidelines_from_text
from app.services.workflow.seed_service import seed_sample_data

router = APIRouter(prefix="/sources", tags=["sources"])


class GuidelineCreate(BaseModel):
    rule_id: str
    text: str
    category: Optional[str] = None


class FactCreate(BaseModel):
    statement: str
    fact_key: Optional[str] = None
    value: Optional[str] = None
    owner: Optional[str] = None
    source: Optional[str] = None
    expires_on: Optional[date] = None


class TermCreate(BaseModel):
    term: str
    preferred: Optional[str] = None
    banned: bool = False
    notes: Optional[str] = None


class BulkImportRequest(BaseModel):
    guidelines: List[GuidelineCreate] = []
    facts: List[FactCreate] = []
    terms: List[TermCreate] = []


@router.get("")
async def list_sources(
    current_user: User = Depends(require_role("creator", "reviewer", "manager", "admin")),
    db: Session = Depends(get_db),
):
    """List all active sources (guidelines, facts, terminology) for the organisation."""
    org_id = current_user.organisation_id

    guidelines = db.scalars(
        select(GuidelineRule).where(
            GuidelineRule.organisation_id == org_id,
            GuidelineRule.is_active == True,  # noqa: E712
        )
    ).all()

    facts = db.scalars(
        select(Fact).where(
            Fact.organisation_id == org_id,
            Fact.is_active == True,  # noqa: E712
        )
    ).all()

    terms = db.scalars(
        select(Term).where(
            Term.organisation_id == org_id,
            Term.is_active == True,  # noqa: E712
        )
    ).all()

    return {
        "guidelines": [
            {
                "id": str(g.id),
                "rule_id": g.rule_id,
                "text": g.rule_text,
                "category": g.category,
                "version": g.version,
                "is_active": g.is_active,
            }
            for g in guidelines
        ],
        "facts": [
            {
                "id": str(f.id),
                "fact_key": f.fact_key,
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
                "version": t.version,
            }
            for t in terms
        ],
    }


@router.post("/guidelines", status_code=status.HTTP_201_CREATED)
async def create_guideline(
    req: GuidelineCreate,
    current_user: User = Depends(require_role("manager", "reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """Upload or create a versioned guideline rule for the organisation."""
    org_id = current_user.organisation_id
    latest = db.scalars(
        select(GuidelineRule)
        .where(GuidelineRule.organisation_id == org_id, GuidelineRule.rule_id == req.rule_id)
        .order_by(desc(GuidelineRule.version))
    ).first()

    next_version = (latest.version + 1) if latest else 1
    if latest and latest.is_active:
        latest.is_active = False
        db.flush()

    rule = GuidelineRule(
        organisation_id=org_id,
        rule_id=req.rule_id,
        rule_text=req.text,
        category=req.category,
        version=next_version,
        is_active=True,
        created_by=current_user.id,
    )
    db.add(rule)
    db.flush()

    log_action(
        db=db,
        organisation_id=org_id,
        user_id=current_user.id,
        action="guideline_created",
        entity="guideline_rule",
        entity_id=rule.id,
        details={"rule_id": rule.rule_id, "version": rule.version},
    )
    db.commit()
    db.refresh(rule)

    return {
        "id": str(rule.id),
        "rule_id": rule.rule_id,
        "text": rule.rule_text,
        "category": rule.category,
        "version": rule.version,
        "is_active": rule.is_active,
    }


@router.post("/facts", status_code=status.HTTP_201_CREATED)
async def create_fact(
    req: FactCreate,
    current_user: User = Depends(require_role("manager", "reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """Upload or create a versioned fact entry for the organisation."""
    org_id = current_user.organisation_id
    f_key = req.fact_key or f"FACT-{uuid.uuid4().hex[:6].upper()}"

    latest = db.scalars(
        select(Fact)
        .where(Fact.organisation_id == org_id, Fact.fact_key == f_key)
        .order_by(desc(Fact.version))
    ).first()

    next_version = (latest.version + 1) if latest else 1
    if latest and latest.is_active:
        latest.is_active = False
        db.flush()

    fact = Fact(
        organisation_id=org_id,
        fact_key=f_key,
        statement=req.statement,
        value=req.value,
        owner=req.owner,
        source=req.source,
        expires_on=req.expires_on,
        version=next_version,
        is_active=True,
        created_by=current_user.id,
    )
    db.add(fact)
    db.flush()

    log_action(
        db=db,
        organisation_id=org_id,
        user_id=current_user.id,
        action="fact_created",
        entity="fact",
        entity_id=fact.id,
        details={"fact_key": fact.fact_key, "statement": fact.statement, "value": fact.value},
    )
    db.commit()
    db.refresh(fact)

    return {
        "id": str(fact.id),
        "fact_key": fact.fact_key,
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
    current_user: User = Depends(require_role("manager", "reviewer", "admin")),
    db: Session = Depends(get_db),
):
    """Upload or create a versioned terminology entry for the organisation."""
    org_id = current_user.organisation_id
    latest = db.scalars(
        select(Term)
        .where(Term.organisation_id == org_id, Term.term == req.term)
        .order_by(desc(Term.version))
    ).first()

    next_version = (latest.version + 1) if latest else 1
    if latest and latest.is_active:
        latest.is_active = False
        db.flush()

    term_row = Term(
        organisation_id=org_id,
        term=req.term,
        preferred=req.preferred,
        banned=req.banned,
        notes=req.notes,
        version=next_version,
        is_active=True,
    )
    db.add(term_row)
    db.flush()

    log_action(
        db=db,
        organisation_id=org_id,
        user_id=current_user.id,
        action="term_created",
        entity="term",
        entity_id=term_row.id,
        details={"term": term_row.term, "banned": term_row.banned},
    )
    db.commit()
    db.refresh(term_row)

    return {
        "id": str(term_row.id),
        "term": term_row.term,
        "preferred": term_row.preferred,
        "banned": term_row.banned,
        "notes": term_row.notes,
        "version": term_row.version,
    }


@router.post("/seed")
async def seed_sources(
    current_user: User = Depends(require_role("creator", "reviewer", "manager", "admin")),
    db: Session = Depends(get_db),
):
    """Seed sample data from sample-data directory into database."""
    return seed_sample_data(db)


@router.get("/rag-search")
async def rag_search(
    query: str,
    top_k: int = 5,
    current_user: User = Depends(require_role("creator", "reviewer", "manager", "admin")),
):
    """Search Dhruv's ingested RAG knowledge records for relevant evidence."""
    from app.services.rag.lexical import search_rag_knowledge

    return search_rag_knowledge(query=query, top_k=top_k)


@router.post("/extract-document")
async def extract_document_sources(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("creator", "reviewer", "manager", "admin")),
):
    """Extract guidelines, verified facts, and terminology from an uploaded document."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        raw_text, doc_type = parse_document(file.filename, content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse document: {exc}")

    if not raw_text.strip():
        raise HTTPException(
            status_code=400,
            detail="No readable text could be extracted from this document."
        )

    result = extract_guidelines_from_text(raw_text, filename=file.filename)
    return result.model_dump()


@router.post("/bulk-import", status_code=status.HTTP_201_CREATED)
async def bulk_import_sources(
    req: BulkImportRequest,
    current_user: User = Depends(require_role("creator", "reviewer", "manager", "admin")),
    db: Session = Depends(get_db),
):
    """Import multiple extracted guidelines, facts, and terms into the brand library."""
    org_id = current_user.organisation_id

    imported_guidelines = 0
    imported_facts = 0
    imported_terms = 0

    # 1. Guidelines
    for g in req.guidelines:
        rule_id = g.rule_id.strip()
        if not rule_id or not g.text.strip():
            continue

        latest = db.scalars(
            select(GuidelineRule)
            .where(GuidelineRule.organisation_id == org_id, GuidelineRule.rule_id == rule_id)
            .order_by(desc(GuidelineRule.version))
        ).first()

        next_ver = (latest.version + 1) if latest else 1
        if latest and latest.is_active:
            latest.is_active = False
            db.flush()

        new_rule = GuidelineRule(
            organisation_id=org_id,
            rule_id=rule_id,
            rule_text=g.text.strip(),
            category=g.category or "General",
            version=next_ver,
            is_active=True,
            created_by=current_user.id,
        )
        db.add(new_rule)
        imported_guidelines += 1

    # 2. Facts
    for f in req.facts:
        stmt = f.statement.strip()
        if not stmt:
            continue
        fact_key = (f.fact_key or f"FACT-{uuid.uuid4().hex[:6].upper()}").strip()

        latest = db.scalars(
            select(Fact)
            .where(Fact.organisation_id == org_id, Fact.fact_key == fact_key)
            .order_by(desc(Fact.version))
        ).first()

        next_ver = (latest.version + 1) if latest else 1
        if latest and latest.is_active:
            latest.is_active = False
            db.flush()

        new_fact = Fact(
            organisation_id=org_id,
            fact_key=fact_key,
            statement=stmt,
            value=f.value or "",
            owner=f.owner or "Imported Policy",
            source=f.source or "Document Import",
            expires_on=f.expires_on,
            version=next_ver,
            is_active=True,
            created_by=current_user.id,
        )
        db.add(new_fact)
        imported_facts += 1

    # 3. Terms
    for t in req.terms:
        term_str = t.term.strip()
        if not term_str:
            continue

        latest = db.scalars(
            select(Term)
            .where(Term.organisation_id == org_id, Term.term == term_str)
            .order_by(desc(Term.version))
        ).first()

        next_ver = (latest.version + 1) if latest else 1
        if latest and latest.is_active:
            latest.is_active = False
            db.flush()

        new_term = Term(
            organisation_id=org_id,
            term=term_str,
            preferred=t.preferred,
            banned=t.banned,
            notes=t.notes or "",
            version=next_ver,
            is_active=True,
        )
        db.add(new_term)
        imported_terms += 1

    db.flush()
    log_action(
        db=db,
        organisation_id=org_id,
        user_id=current_user.id,
        action="sources_bulk_imported",
        entity="source",
        entity_id=None,
        details={
            "guidelines": imported_guidelines,
            "facts": imported_facts,
            "terms": imported_terms,
        },
    )
    db.commit()

    return {
        "status": "success",
        "imported": {
            "guidelines": imported_guidelines,
            "facts": imported_facts,
            "terms": imported_terms,
            "total": imported_guidelines + imported_facts + imported_terms,
        },
    }
