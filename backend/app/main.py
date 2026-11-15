"""ProofLine API – pre-publication brand-governance backend."""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text

from app.config import settings
from app.core.security import validate_jwt_secret
from app.db import SessionLocal, engine, init_db
from app.routers import audit, auth, drafts, findings, insights, sources
from app.services.workflow.seed_service import seed_sample_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for ProofLine API."""
    validate_jwt_secret()
    if settings.database_url.startswith("sqlite"):
        init_db()
        try:
            db = SessionLocal()
            seed_sample_data(db)
            db.close()
        except Exception:
            pass
    else:
        # Ensure PostgreSQL native ENUM has 'manager' role
        try:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'manager'"))
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
