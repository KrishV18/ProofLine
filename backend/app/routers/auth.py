"""Authentication router."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.roles import Role, get_current_user, get_or_create_default_org
from app.core.security import create_access_token, hash_password, verify_password
from app.db import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    role: str = "creator"


@router.post("/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user and receive a JWT token."""
    user = db.scalars(select(User).where(User.email == req.email.strip())).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user (convenience endpoint for local/demo setup)."""
    existing = db.scalars(select(User).where(User.email == req.email.strip())).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    org = get_or_create_default_org(db)
    user_role = req.role.lower()
    if user_role not in [r.value for r in Role]:
        user_role = Role.CREATOR.value

    new_user = User(
        organisation_id=org.id,
        email=req.email.strip(),
        hashed_password=hash_password(req.password),
        role=user_role,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(
        data={"sub": str(new_user.id), "email": new_user.email, "role": new_user.role}
    )
    return {
        "id": str(new_user.id),
        "email": new_user.email,
        "role": new_user.role,
        "access_token": token,
        "token_type": "bearer",
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role,
        "organisation_id": str(current_user.organisation_id),
    }
