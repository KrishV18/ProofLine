"""User model."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import Enum as PgEnum, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models._base import Base, USER_ROLE_VALUES


class User(Base):
    """ProofLine user. Belongs to exactly one organisation."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("organisations.id", ondelete="RESTRICT", name="fk_users_organisation"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        # Lowercasing is enforced at application level; uniqueness is global.
    )
    password_hash: Mapped[str] = mapped_column(sa.Text, nullable=False)
    full_name: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    role: Mapped[str] = mapped_column(
        PgEnum(*USER_ROLE_VALUES, name="user_role", create_type=False),
        nullable=False,
        server_default="creator",
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=text("true"),
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
        # Email is globally unique (not per-org, as per spec).
        sa.UniqueConstraint("email", name="uq_users_email"),
        # Support composite FK from org-scoped children.
        sa.UniqueConstraint("id", "organisation_id", name="uq_users_id_org"),
        sa.Index("ix_users_organisation_id", "organisation_id"),
    )
