"""Test authentication endpoints."""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_auth_flow():
    with TestClient(app) as client:
        # 1. Register a test creator
        unique_suffix = uuid.uuid4().hex[:8]
        email = f"creator_{unique_suffix}@proofline.ai"
        reg_res = client.post(
            "/auth/register",
            json={"email": email, "password": "securepassword123", "role": "creator"},
        )
        assert reg_res.status_code == 201
    data = reg_res.json()
    assert data["email"] == email
    assert data["role"] == "creator"
    assert "access_token" in data

    # 2. Login with valid credentials
    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": "securepassword123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token

    # 3. Access /auth/me with bearer token
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # 4. Fail login with wrong password
    bad_login = client.post(
        "/auth/login",
        json={"email": email, "password": "wrongpassword"},
    )
    assert bad_login.status_code == 401
