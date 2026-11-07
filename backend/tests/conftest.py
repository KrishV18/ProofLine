"""Shared test fixtures for ProofLine backend tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)

