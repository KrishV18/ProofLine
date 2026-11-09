"""AuditLog model — strictly append-only."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy import ForeignKey, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base


class AuditLog(Base):
    """Immutable record of every significant action in the system.

    UPDATE, DELETE, and TRUNCATE are blocked by a database trigger.
    ``user_id`` is nullable to allow system/automated actions.
    """

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("organisations.id", ondelete="RESTRICT", name="fk_audit_log_organisation"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="RESTRICT", name="fk_audit_log_user"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(sa.Text, nullable=False)
    entity: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    guideline_versions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        sa.Index("ix_audit_log_organisation_created_at", "organisation_id", "created_at"),
        sa.Index("ix_audit_log_organisation_id", "organisation_id"),
    )
