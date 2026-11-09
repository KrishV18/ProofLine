"""Shared test fixtures for ProofLine backend tests.

DB-layer fixtures:
  - `db_url`     : reads TEST_DATABASE_URL env var, falls back to default.
  - `db_engine`  : SQLAlchemy engine; session-scoped; SKIPS if no PG reachable.
  - `alembic_cfg`: loaded AlembicConfig pointing at this project's alembic.ini.
  - `db_conn`    : per-test connection with automatic transaction rollback.

Non-DB fixtures:
  - `client`     : FastAPI TestClient (unchanged from original).
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ---------------------------------------------------------------------------
# FastAPI test client (no DB needed)
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Database fixtures (require a running PostgreSQL)
# ---------------------------------------------------------------------------

DEFAULT_TEST_DB_URL = (
    "postgresql+psycopg://proofline:proofline@localhost:5432/proofline_test"
)


@pytest.fixture(scope="session")
def db_url() -> str:
    """Return the database URL to use for the test session."""
    return os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DB_URL)


@pytest.fixture(scope="session")
def db_engine(db_url):
    """Create a SQLAlchemy engine for the test DB.

    Skips the entire test session if PostgreSQL is not reachable at ``db_url``.
    The caller must run Alembic migrations separately (see ``test_migrations.py``
    or the ``migrated_db`` fixture below) before using the engine.
    """
    from sqlalchemy import create_engine, text as sa_text
    from sqlalchemy.exc import OperationalError

    # Add a short TCP connect_timeout so the skip fires quickly when no PG
    # is available locally (avoids hanging for the OS-level TCP timeout).
    _url = db_url
    if "connect_timeout" not in _url:
        sep = "&" if "?" in _url else "?"
        _url = f"{_url}{sep}connect_timeout=3"
    engine = create_engine(_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
    except (OperationalError, Exception) as exc:
        pytest.skip(
            f"PostgreSQL not reachable at {db_url!r}. "
            f"Set TEST_DATABASE_URL and start a test database to run DB tests. "
            f"Original error: {exc}"
        )
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def alembic_cfg(db_url):
    """Return an Alembic Config object pointed at this project's alembic.ini."""
    import pathlib
    from alembic.config import Config

    # The alembic.ini lives two directories up from tests/ (at backend/).
    ini_path = pathlib.Path(__file__).parent.parent / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


@pytest.fixture(scope="session")
def migrated_db(db_engine, alembic_cfg):
    """Ensure the schema is at HEAD before running schema-level tests.

    Runs ``alembic upgrade head``.  After the session, runs
    ``alembic downgrade base`` to leave the DB clean for the next run.
    """
    from alembic import command

    command.upgrade(alembic_cfg, "head")
    yield db_engine
    command.downgrade(alembic_cfg, "base")


@pytest.fixture
def db_conn(migrated_db):
    """Per-test database connection with automatic rollback.

    Uses a SAVEPOINT so individual tests can test constraint violations without
    aborting the outer transaction.
    """
    with migrated_db.connect() as conn:
        trans = conn.begin()
        yield conn
        trans.rollback()
