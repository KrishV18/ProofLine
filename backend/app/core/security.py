"""Security utilities for ProofLine API."""

# TODO: Implement JWT token creation and verification
# TODO: Implement password hashing with passlib


def create_access_token(data: dict) -> str:
    """Create a JWT access token. Not yet implemented."""
    raise NotImplementedError("JWT token creation not yet implemented")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its hash. Not yet implemented."""
    raise NotImplementedError("Password verification not yet implemented")


def hash_password(password: str) -> str:
    """Hash a password. Not yet implemented."""
    raise NotImplementedError("Password hashing not yet implemented")

