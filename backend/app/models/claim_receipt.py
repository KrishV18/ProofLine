"""Claim and ClaimReceipt models."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import Enum as PgEnum, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, CLAIM_STATUS_VALUES


class Claim(Base):
    """A factual claim extracted from a draft version and checked against facts."""

    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("organisations.id", ondelete="RESTRICT", name="fk_claims_organisation"),
        nullable=False,
    )
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    claim_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    claim_type: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str] = mapped_column(
        PgEnum(*CLAIM_STATUS_VALUES, name="claim_status", create_type=False),
        nullable=False,
    )
    evidence_fact_key: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    evidence_version: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["version_id", "organisation_id"],
            ["draft_versions.id", "draft_versions.organisation_id"],
            name="fk_claims_version_org",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("id", "organisation_id", name="uq_claims_id_org"),
        sa.Index("ix_claims_organisation_id", "organisation_id"),
        sa.Index("ix_claims_version_id", "version_id"),
    )


class ClaimReceipt(Base):
    """Immutable record created when a draft version is approved.

    One receipt per approved version (UNIQUE version_id).
    Rows are blocked from UPDATE and DELETE by a DB trigger.
    """

    __tablename__ = "claim_receipts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("organisations.id", ondelete="RESTRICT", name="fk_claim_receipts_organisation"),
        nullable=False,
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    approved_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="RESTRICT", name="fk_claim_receipts_approved_by"),
        nullable=False,
    )
    approved_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(sa.CHAR(64), nullable=False)
    claims_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    guideline_versions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    override_reasons: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["version_id", "organisation_id"],
            ["draft_versions.id", "draft_versions.organisation_id"],
            name="fk_claim_receipts_version_org",
            ondelete="RESTRICT",
        ),
        # One receipt per approved version.
        sa.UniqueConstraint("version_id", name="uq_claim_receipts_version_id"),
        sa.Index("ix_claim_receipts_organisation_id", "organisation_id"),
    )
