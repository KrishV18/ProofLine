"""Finding schema – the shared contract used across backend, frontend and docs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FindingBase(BaseModel):
    """Base fields for a Finding (excludes IDs)."""

    quoted_text: str
    start: int
    end: int
    severity: Literal["blocker", "warning", "note"]
    reason: str
    source_ref: str = Field(..., min_length=1)
    source_version: int
    confidence: Literal["high", "medium", "low"]
    suggestion: str | None = None
    status: Literal["open", "accepted", "edited", "dismissed"] = "open"
    dismissal_reason: str | None = None

    @field_validator("source_ref")
    @classmethod
    def source_ref_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source_ref must not be empty")
        return v


class Finding(FindingBase):
    """Full Finding with identifiers."""

    id: str
    draft_id: str
    version_id: str

    model_config = {"from_attributes": True}


class FindingUpdate(BaseModel):
    """Payload for PATCH /findings/{id}."""

    status: Literal["open", "accepted", "edited", "dismissed"] | None = None
    dismissal_reason: str | None = None

