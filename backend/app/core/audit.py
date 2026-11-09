"""Audit logging service for ProofLine API."""

import uuid
from typing import Any, Dict, Optional, Union
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.organisation import Organisation


def log_action(
    db: Session,
    user_id: Optional[Union[str, uuid.UUID]],
    action: str,
    entity: str,
    entity_id: Optional[Union[str, uuid.UUID]],
    details: Optional[Dict[str, Any]] = None,
    organisation_id: Optional[Union[str, uuid.UUID]] = None,
) -> AuditLog:
    """Append an immutable entry to the audit log."""
    parsed_user_id = None
    if user_id:
        parsed_user_id = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id

    parsed_entity_id = None
    if entity_id:
        try:
            parsed_entity_id = uuid.UUID(str(entity_id)) if not isinstance(entity_id, uuid.UUID) else entity_id
        except (ValueError, TypeError):
            pass

    parsed_org_id = None
    if organisation_id:
        parsed_org_id = uuid.UUID(str(organisation_id)) if not isinstance(organisation_id, uuid.UUID) else organisation_id
    else:
        # Fallback to first organisation
        first_org = db.query(Organisation).first()
        if first_org:
            parsed_org_id = first_org.id

    entry = AuditLog(
        organisation_id=parsed_org_id or uuid.uuid4(),
        user_id=parsed_user_id,
        action=action,
        entity=entity,
        entity_id=parsed_entity_id,
        details=details or {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
