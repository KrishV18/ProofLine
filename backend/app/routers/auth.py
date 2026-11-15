"""Authentication router for ProofLine API."""
from __future__ import annotations

import re
import uuid
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)
from app.db import get_db
from app.models.organisation import Organisation
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    """Quick writer-only signup (creates a personal org automatically)."""
    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=72)


class RegisterRequest(BaseModel):
    """Full company registration (creates org + first user)."""
    company_name: str
    full_name: str
    email: str
    password: str
    role: str = "manager"  # first user defaults to manager


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    organisation_id: str
    organisation_name: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


class CompanyItem(BaseModel):
    id: str
    name: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALLOWED_ROLES = {"creator", "manager"}


def _build_user_profile(user: User, org_name: str | None) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "organisation_id": str(user.organisation_id),
        "organisation_name": org_name,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user and receive a JWT access token."""
    email = req.email.strip().lower()
    user = db.scalars(select(User).where(User.email == email)).first()

    if not user:
        verify_dummy_password(req.password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    is_password_valid = verify_password(req.password, user.password_hash)
    if not is_password_valid or not user.is_active:
        log_action(
            db=db,
            organisation_id=user.organisation_id,
            user_id=None,
            action="login_failed",
            entity="user",
            entity_id=user.id,
            details={"email": email},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Fetch org name for the response
    org = db.scalars(
        select(Organisation).where(Organisation.id == user.organisation_id)
    ).first()
    org_name = org.name if org else None

    log_action(
        db=db,
        organisation_id=user.organisation_id,
        user_id=user.id,
        action="login_success",
        entity="user",
        entity_id=user.id,
        details={"email": email},
    )
    db.commit()

    token = create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _build_user_profile(user, org_name),
    }


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    """Quick signup: create a creator account in an auto-named organisation.

    This is a lightweight alternative to /register for writers who don't need
    to pick a company name up front.
    """
    email = req.email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if len(req.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=422, detail="Password must be at most 72 bytes")

    organisation_id = uuid4()
    db.add(Organisation(id=organisation_id, name=f"Writer workspace {organisation_id}"))
    try:
        db.flush()
        db.add(User(
            organisation_id=organisation_id,
            email=email,
            password_hash=hash_password(req.password),
            role="creator",
        ))
        db.commit()
    except IntegrityError:
        db.rollback()
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        raise
    return {"email": email}


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new company and its first user (manager by default).

    - Creates an Organisation record (company_name must be unique).
    - Creates the first User for that company.
    - Returns a JWT so the user is logged in immediately.
    """
    role = req.role.strip().lower()
    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Role must be one of: {', '.join(sorted(ALLOWED_ROLES))}",
        )

    email = req.email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address")

    # Check email uniqueness upfront for a nicer error message
    existing_email = db.scalars(select(User).where(User.email == email)).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Create org
    org = Organisation(name=req.company_name.strip())
    db.add(org)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A company with this name already exists",
        )

    # Create first user
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=req.full_name.strip(),
        password_hash=hash_password(req.password),
        role=role,
        organisation_id=org.id,
        is_active=True,
    )
    db.add(user)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    log_action(
        db=db,
        organisation_id=org.id,
        user_id=user.id,
        action="company_registered",
        entity="organisation",
        entity_id=org.id,
        details={"company_name": org.name, "email": email, "role": role},
    )
    db.commit()

    token = create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _build_user_profile(user, org.name),
    }


@router.get("/companies", response_model=list[CompanyItem])
async def list_companies(db: Session = Depends(get_db)):
    """Return all company names for login company-picker autocomplete."""
    orgs = db.scalars(select(Organisation).order_by(Organisation.name)).all()
    return [{"id": str(o.id), "name": o.name} for o in orgs]


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the current authenticated user profile."""
    org = db.scalars(
        select(Organisation).where(Organisation.id == current_user.organisation_id)
    ).first()
    return _build_user_profile(current_user, org.name if org else None)
