"""Draft and DraftVersion models."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import Enum as PgEnum, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, DRAFT_STATUS_VALUES


class Draft(Base):
    """A document being reviewed through the ProofLine workflow."""

    __tablename__ = "drafts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("organisations.id", ondelete="RESTRICT", name="fk_drafts_organisation"),
        nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="RESTRICT", name="fk_drafts_owner"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    channel: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str] = mapped_column(
        PgEnum(*DRAFT_STATUS_VALUES, name="draft_status", create_type=False),
        nullable=False,
        server_default="draft",
    )
    intent_lock: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    current_version_number: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=text("1"),
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        # Composite unique allows children to enforce cross-org FK.
        sa.UniqueConstraint("id", "organisation_id", name="uq_drafts_id_org"),
        sa.Index("ix_drafts_organisation_status", "organisation_id", "status"),
        sa.Index("ix_drafts_organisation_id", "organisation_id"),
    )


class DraftVersion(Base):
    """Immutable snapshot of draft content at a point in time.

    Rows are NEVER updated or deleted (enforced by a DB trigger).
    content_hash is the SHA-256 hex digest of ``content``.
    """

    __tablename__ = "draft_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("organisations.id", ondelete="RESTRICT", name="fk_draft_versions_organisation"),
        nullable=False,
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(sa.CHAR(64), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="RESTRICT", name="fk_draft_versions_created_by"),
        nullable=True,
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        # Composite FK to drafts enforces org isolation.
        sa.ForeignKeyConstraint(
            ["draft_id", "organisation_id"],
            ["drafts.id", "drafts.organisation_id"],
            name="fk_draft_versions_draft_org",
            ondelete="RESTRICT",
        ),
        # Composite unique so findings can reference (version_id, org_id).
        sa.UniqueConstraint("id", "organisation_id", name="uq_draft_versions_id_org"),
        sa.UniqueConstraint("draft_id", "version_number", name="uq_draft_versions_draft_version"),
        sa.Index("ix_draft_versions_organisation_id", "organisation_id"),
        sa.Index("ix_draft_versions_draft_id", "draft_id"),
    )
