"""Authentication router."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login():
    """Authenticate a user and return a JWT token."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})

