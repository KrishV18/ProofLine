"""ProofLine SQLAlchemy declarative base, mixins and shared enum definitions.

All models import from this module to ensure a single metadata object and
consistent column conventions across every table.
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ---------------------------------------------------------------------------
# PostgreSQL native ENUM type names
# ---------------------------------------------------------------------------
# These are defined here so both the ORM and the migration can reference the
# same string names, preventing drift.

USER_ROLE_VALUES       = ("creator", "reviewer", "admin")
DRAFT_STATUS_VALUES    = ("draft", "in_review", "changes_requested", "approved")
FINDING_SEVERITY_VALUES = ("blocker", "warning", "note")
FINDING_CONFIDENCE_VALUES = ("high", "medium", "low")
FINDING_STATUS_VALUES  = ("open", "accepted", "edited", "dismissed")
CLAIM_STATUS_VALUES    = ("supported", "conflicts", "expired_evidence", "unsupported", "needs_human")
SOURCE_TYPE_VALUES     = ("guideline", "fact", "term")
DECISION_TYPE_VALUES   = ("approved", "changes_requested")


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Shared declarative base for all ProofLine ORM models."""
    pass


# ---------------------------------------------------------------------------
# Reusable column helpers
# ---------------------------------------------------------------------------

def _uuid_pk() -> Mapped[uuid.UUID]:
    """Standard UUID primary key with server-side gen_random_uuid()."""
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


def _timestamptz_now(nullable: bool = False) -> sa.Column:
    """TIMESTAMPTZ column defaulting to now() on the server."""
    return sa.Column(
        sa.TIMESTAMP(timezone=True),
        nullable=nullable,
        server_default=text("now()"),
    )

