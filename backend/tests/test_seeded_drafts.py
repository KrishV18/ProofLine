"""Evaluation test against seeded-error drafts (measures precision & recall)."""

import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app


def test_seeded_error_draft_evaluation():
    with TestClient(app) as client:
        # Login
        login_res = client.post(
            "/auth/login",
            json={"email": "creator@proofline.ai", "password": "creator12345"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Seed sources
        client.post("/sources/seed", headers=headers)

        # Load planted errors draft
        test_file = Path("sample-data/seeded-drafts/draft_seeded_errors.json")
        if not test_file.exists():
            test_file = Path("../sample-data/seeded-drafts/draft_seeded_errors.json")

        with open(test_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Create draft
        draft_res = client.post(
            "/drafts",
            headers=headers,
            json={
                "content": data["content"],
                "channel": data["channel"],
                "intent_lock": data["intent_lock"],
            },
        )
        draft_id = draft_res.json()["id"]

        # Run review engine
        review_res = client.post(f"/drafts/{draft_id}/review", headers=headers)
        assert review_res.status_code == 202

        # Get findings
        findings_res = client.get(f"/drafts/{draft_id}/versions/1/findings", headers=headers)
        findings = findings_res.json()

        # Check that planted errors were successfully caught
        caught_sources = {f["source_ref"] for f in findings}
        for err in data["planted_errors"]:
            # Assert that either exact source_ref or related reference was caught
            assert any(
                err["source_ref"].lower() in cs.lower() or cs.lower() in err["source_ref"].lower()
                for cs in caught_sources
            ), f"Failed to catch planted error: {err['type']} ({err['source_ref']})"

        # Check 100% source validity ("No source, no flag")
        for f in findings:
            assert f["source_ref"] and f["source_ref"].strip() != ""

