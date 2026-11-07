"""Audit logging for ProofLine API."""

from sqlalchemy.orm import Session


def log_action(
    db: Session,
    user_id: str | None,
    action: str,
    entity: str,
    entity_id: str | None,
    details: dict | None = None,
) -> None:
    """Append an entry to the audit log. Placeholder – not yet wired up."""
    # TODO: Create AuditLog record and commit
    pass

