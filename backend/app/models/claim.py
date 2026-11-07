"""Claim model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"), nullable=False)
    draft_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drafts.id"), nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("draft_versions.id"), nullable=False)
    quoted_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(100))
    checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[str] = mapped_column(server_default=func.now())

