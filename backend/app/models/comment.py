"""Comment model."""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"), nullable=False)
    draft_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drafts.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    range_start: Mapped[int | None] = mapped_column(Integer)
    range_end: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(server_default=func.now())

