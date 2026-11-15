"""Role definitions and re-exported dependencies for ProofLine API."""
from __future__ import annotations

import enum
from app.core.deps import get_current_org_id, get_current_user, require_role


class Role(str, enum.Enum):
    CREATOR = "creator"
    REVIEWER = "reviewer"
    MANAGER = "manager"
    ADMIN = "admin"


__all__ = [
    "Role",
    "get_current_user",
    "require_role",
    "get_current_org_id",
]
