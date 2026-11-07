"""Drafts router."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/drafts", tags=["drafts"])


@router.post("")
async def create_draft():
    """Create a new draft."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


@router.post("/{draft_id}/review")
async def trigger_review(draft_id: str):
    """Trigger an automated review of the draft."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


@router.get("/{draft_id}/versions/{version}/findings")
async def get_findings(draft_id: str, version: int):
    """Get all findings for a specific draft version."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


@router.post("/{draft_id}/request-review")
async def request_review(draft_id: str):
    """Request a human review of the draft."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


@router.post("/{draft_id}/comments")
async def add_comment(draft_id: str):
    """Add a comment to a draft."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


@router.post("/{draft_id}/decision")
async def record_decision(draft_id: str):
    """Record an approval decision on a draft."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


@router.get("/{draft_id}/receipt")
async def get_receipt(draft_id: str):
    """Get the review receipt for a draft."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})

