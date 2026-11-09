"""Approval model — append-only decisions on drafts."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import Enum as PgEnum, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, DECISION_TYPE_VALUES


class Approval(Base):
    """Human approval/rejection decision. Rows are never updated or deleted."""

    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("organisations.id", ondelete="RESTRICT", name="fk_approvals_organisation"),
        nullable=False,
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    decision: Mapped[str] = mapped_column(
        PgEnum(*DECISION_TYPE_VALUES, name="decision_type", create_type=False),
        nullable=False,
    )
    override_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["draft_id", "organisation_id"],
            ["drafts.id", "drafts.organisation_id"],
            name="fk_approvals_draft_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id", "organisation_id"],
            ["users.id", "users.organisation_id"],
            name="fk_approvals_reviewer_org",
            ondelete="RESTRICT",
        ),
        sa.Index("ix_approvals_organisation_id", "organisation_id"),
        sa.Index("ix_approvals_draft_id", "draft_id"),
    )
