"""ProofLine API – pre-publication brand-governance backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import audit, auth, drafts, findings, insights, sources

app = FastAPI(title="ProofLine API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sources.router)
app.include_router(drafts.router)
app.include_router(findings.router)
app.include_router(insights.router)
app.include_router(audit.router)


@app.get("/health")
async def health():
    """Health-check endpoint."""
    return {"status": "ok", "service": "proofline-api"}

