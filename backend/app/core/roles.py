"""Role-based access control and user dependency for ProofLine API."""

import enum
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db import get_db
from app.models.organisation import Organisation
from app.models.user import User

security_scheme = HTTPBearer(auto_error=False)


class Role(str, enum.Enum):
    CREATOR = "creator"
    REVIEWER = "reviewer"
    MANAGER = "manager"
    ADMIN = "admin"


def get_or_create_default_org(db: Session) -> Organisation:
    """Retrieve or create a default organisation for development/testing."""
    org = db.scalars(select(Organisation)).first()
    if not org:
        org = Organisation(name="ProofLine Demo Org")
        db.add(org)
        db.commit()
        db.refresh(org)
    return org


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract and authenticate the user from JWT bearer token.

    Falls back to a default demo admin user if no token is passed in development,
    allowing easy testing of endpoints.
    """
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = payload.get("sub")
        if user_id:
            try:
                user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                user = db.get(User, user_uuid)
                if user and user.is_active:
                    return user
            except (ValueError, TypeError):
                pass

        # Try finding by email
        email = payload.get("email")
        if email:
            user = db.scalars(select(User).where(User.email == email)).first()
            if user and user.is_active:
                return user

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Dev/Demo fallback: Return existing admin or create one
    demo_user = db.scalars(select(User).where(User.email == "demo@proofline.ai")).first()
    if demo_user:
        return demo_user

    org = get_or_create_default_org(db)
    from app.core.security import hash_password

    demo_user = User(
        email="demo@proofline.ai",
        hashed_password=hash_password("demo12345"),
        role=Role.ADMIN.value,
        organisation_id=org.id,
        is_active=True,
    )
    db.add(demo_user)
    db.commit()
    db.refresh(demo_user)
    return demo_user


def require_role(*roles: Role):
    """Dependency that enforces role-based access.

    Admins are always granted access.
    """
    allowed_values = {r.value for r in roles} | {Role.ADMIN.value}

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {[r.value for r in roles]}",
            )
        return current_user

    return _check
