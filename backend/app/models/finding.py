"""Finding model."""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"), nullable=False)
    draft_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drafts.id"), nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("draft_versions.id"), nullable=False)
    quoted_text: Mapped[str | None] = mapped_column(Text)
    start: Mapped[int | None] = mapped_column(Integer)
    end: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    source_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    source_version: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    suggestion: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")
    dismissal_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(server_default=func.now())

