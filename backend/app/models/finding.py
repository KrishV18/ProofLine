"""Finding model.

Column naming note
------------------
The API contract uses ``start`` and ``end`` as field names (see
app/schemas/finding.py).  ``end`` is an SQL reserved word, so the database
columns are named ``start_offset`` and ``end_offset``.  The Pydantic schema
bridges the gap via Field aliases.
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import Enum as PgEnum, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import (
    Base,
    FINDING_SEVERITY_VALUES,
    FINDING_CONFIDENCE_VALUES,
    FINDING_STATUS_VALUES,
    SOURCE_TYPE_VALUES,
)


class Finding(Base):
    """A single flag raised by the review engine against a draft version.

    Database-level guarantees:
    - source_ref is never empty (CHECK constraint).
    - end_offset > start_offset (CHECK constraint).
    - dismissal_reason is non-null when status = 'dismissed' (CHECK constraint).
    """

    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("organisations.id", ondelete="RESTRICT", name="fk_findings_organisation"),
        nullable=False,
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    quoted_text: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # DB column names are start_offset / end_offset; API names are start / end.
    start_offset: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    severity: Mapped[str] = mapped_column(
        PgEnum(*FINDING_SEVERITY_VALUES, name="finding_severity", create_type=False),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(sa.Text, nullable=False)
    source_type: Mapped[str | None] = mapped_column(
        PgEnum(*SOURCE_TYPE_VALUES, name="source_type", create_type=False),
        nullable=True,
    )
    source_ref: Mapped[str] = mapped_column(sa.Text, nullable=False)
    source_version: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    confidence: Mapped[str] = mapped_column(
        PgEnum(*FINDING_CONFIDENCE_VALUES, name="finding_confidence", create_type=False),
        nullable=False,
    )
    suggestion: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str] = mapped_column(
        PgEnum(*FINDING_STATUS_VALUES, name="finding_status", create_type=False),
        nullable=False,
        server_default="open",
    )
    dismissal_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="RESTRICT", name="fk_findings_resolved_by"),
        nullable=True,
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
        # Composite FK ensures finding stays within the same org as its version.
        sa.ForeignKeyConstraint(
            ["version_id", "organisation_id"],
            ["draft_versions.id", "draft_versions.organisation_id"],
            name="fk_findings_version_org",
            ondelete="RESTRICT",
        ),
        # "No source, no flag" enforced at the database level.
        sa.CheckConstraint("source_ref <> ''", name="ck_findings_source_ref_nonempty"),
        sa.CheckConstraint(
            "start_offset >= 0 AND end_offset > start_offset",
            name="ck_findings_offsets",
        ),
        sa.CheckConstraint(
            "status <> 'dismissed' OR dismissal_reason IS NOT NULL",
            name="ck_findings_dismissed_reason",
        ),
        sa.Index("ix_findings_version_id", "version_id"),
        sa.Index("ix_findings_organisation_source_ref", "organisation_id", "source_ref"),
        sa.Index("ix_findings_organisation_id", "organisation_id"),
    )
