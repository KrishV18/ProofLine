"""Claim receipt model."""

import uuid

from sqlalchemy import ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ClaimReceipt(Base):
    __tablename__ = "claim_receipts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organisations.id"), nullable=False)
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id"), nullable=False)
    receipt_data: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(server_default=func.now())

