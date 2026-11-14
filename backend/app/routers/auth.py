"""Authentication router for ProofLine API."""
from __future__ import annotations

import re
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_dummy_password, verify_password
from app.db import get_db
from app.models.organisation import Organisation
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=72)


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    """Create a creator account in a separate organisation."""
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


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    organisation_id: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user and receive a JWT access token.

    Always returns 401 with 'Invalid email or password' on any authentication failure.
    Runs a dummy constant-time verification when email is unknown to prevent timing attacks.
    """
    email = req.email.strip().lower()
    user = db.scalars(select(User).where(User.email == email)).first()

    if not user:
        # Unknown email: perform dummy bcrypt computation for timing resistance
        verify_dummy_password(req.password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check password and active status
    is_password_valid = verify_password(req.password, user.password_hash)
    if not is_password_valid or not user.is_active:
        # Log failure for known organisation, user_id=None
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

    # Success: log action and issue token
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
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "organisation_id": str(user.organisation_id),
        },
    }


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user profile."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "organisation_id": str(current_user.organisation_id),
    }
