"""Role-based access control for ProofLine API."""

import enum


class Role(str, enum.Enum):
    CREATOR = "creator"
    REVIEWER = "reviewer"
    ADMIN = "admin"


def require_role(*roles: Role):
    """Dependency that enforces role-based access. Placeholder – always passes for now."""

    async def _check():
        # TODO: Extract user from JWT, verify role
        pass

    return _check

