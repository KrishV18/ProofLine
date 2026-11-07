"""Sources router – guidelines, facts, terminology."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("/guidelines")
async def create_guideline():
    """Upload or create a guideline rule."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


@router.post("/facts")
async def create_fact():
    """Upload or create a fact entry."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


@router.post("/terms")
async def create_term():
    """Upload or create a terminology entry."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


@router.get("")
async def list_sources():
    """List all sources (guidelines, facts, terminology)."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})

