"""Comment model."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base


class Comment(Base):
    """Review comment on a draft, optionally anchored to a text range."""

    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("organisations.id", ondelete="RESTRICT", name="fk_comments_organisation"),
        nullable=False,
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(sa.Text, nullable=False)
    range_start: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    range_end: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        # Composite FK ensures comment stays in the same org as its draft.
        sa.ForeignKeyConstraint(
            ["draft_id", "organisation_id"],
            ["drafts.id", "drafts.organisation_id"],
            name="fk_comments_draft_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["author_id", "organisation_id"],
            ["users.id", "users.organisation_id"],
            name="fk_comments_author_org",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "range_end IS NULL OR range_start IS NULL OR range_end > range_start",
            name="ck_comments_range",
        ),
        sa.Index("ix_comments_organisation_id", "organisation_id"),
        sa.Index("ix_comments_draft_id", "draft_id"),
    )
