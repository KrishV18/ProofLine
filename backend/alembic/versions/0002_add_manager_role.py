"""Add manager role to user_role enum.

Revision ID: 0002_add_manager_role
Revises: 0001_initial_schema
Create Date: 2026-11-16
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "0002_add_manager_role"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE cannot run inside a transaction in PostgreSQL.
    # Commit the implicit transaction first, then run outside it.
    connection = op.get_bind()
    connection.execute(text("COMMIT"))
    connection.execute(
        text("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'manager'")
    )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; this is intentionally a no-op.
    pass
