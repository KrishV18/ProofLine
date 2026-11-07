"""Initial ProofLine schema.

Revision ID: 001_initial
Revises: None
Create Date: 2026-11-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, UUID

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organisations
    op.create_table(
        "organisations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="creator"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Guideline rules
    op.create_table(
        "guideline_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("rule_id", sa.String(50), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("version", sa.Integer, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Facts
    op.create_table(
        "facts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("statement", sa.Text, nullable=False),
        sa.Column("value", sa.String(255)),
        sa.Column("owner", sa.String(255)),
        sa.Column("source", sa.String(255)),
        sa.Column("expires_on", sa.Date),
        sa.Column("version", sa.Integer, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Terms
    op.create_table(
        "terms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("term", sa.String(255), nullable=False),
        sa.Column("preferred", sa.String(255)),
        sa.Column("banned", sa.Boolean, server_default=sa.text("false")),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Drafts
    op.create_table(
        "drafts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("channel", sa.String(100)),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("intent_lock", JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Draft versions
    op.create_table(
        "draft_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("draft_id", UUID(as_uuid=True), sa.ForeignKey("drafts.id"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Findings
    op.create_table(
        "findings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("draft_id", UUID(as_uuid=True), sa.ForeignKey("drafts.id"), nullable=False),
        sa.Column("version_id", UUID(as_uuid=True), sa.ForeignKey("draft_versions.id"), nullable=False),
        sa.Column("quoted_text", sa.Text),
        sa.Column("start", sa.Integer),
        sa.Column("end", sa.Integer),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text),
        sa.Column("source_ref", sa.String(100), nullable=False),
        sa.Column("source_version", sa.Integer),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("suggestion", sa.Text),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("dismissal_reason", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Claims
    op.create_table(
        "claims",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("draft_id", UUID(as_uuid=True), sa.ForeignKey("drafts.id"), nullable=False),
        sa.Column("version_id", UUID(as_uuid=True), sa.ForeignKey("draft_versions.id"), nullable=False),
        sa.Column("quoted_text", sa.Text),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("source_ref", sa.String(100)),
        sa.Column("checked_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Claim receipts
    op.create_table(
        "claim_receipts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("receipt_data", JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Comments
    op.create_table(
        "comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("draft_id", UUID(as_uuid=True), sa.ForeignKey("drafts.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("range_start", sa.Integer),
        sa.Column("range_end", sa.Integer),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Approvals
    op.create_table(
        "approvals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("draft_id", UUID(as_uuid=True), sa.ForeignKey("drafts.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("reason", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Audit log (append-only)
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True)),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity", sa.String(100)),
        sa.Column("entity_id", UUID(as_uuid=True)),
        sa.Column("details", JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("approvals")
    op.drop_table("comments")
    op.drop_table("claim_receipts")
    op.drop_table("claims")
    op.drop_table("findings")
    op.drop_table("draft_versions")
    op.drop_table("drafts")
    op.drop_table("terms")
    op.drop_table("facts")
    op.drop_table("guideline_rules")
    op.drop_table("users")
    op.drop_table("organisations")

