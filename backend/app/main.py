"""ProofLine API – pre-publication brand-governance backend."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import SessionLocal, init_db
from app.routers import audit, auth, drafts, findings, insights, sources
from app.services.workflow.seed_service import seed_sample_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and seed baseline data on startup."""
    init_db()
    try:
        db = SessionLocal()
        seed_sample_data(db)
        db.close()
    except Exception:
        pass
    yield


app = FastAPI(
    title="ProofLine API",
    description="Pre-publication brand-governance platform – every claim linked to its proof.",
    version="0.1.0",
    lifespan=lifespan,
)

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
