"""ProofLine database engine, session factory and dependency.

The SQLAlchemy ``Base`` lives in ``app.models._base`` and is re-exported
here for backward compatibility with any code that imports ``from app.db import Base``.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models._base import Base  # re-export for compatibility  # noqa: F401

engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
