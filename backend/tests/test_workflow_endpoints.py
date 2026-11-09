"""End-to-end integration test of the complete ProofLine product workflow."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

def test_full_content_governance_workflow():
    with TestClient(app) as client:
        # Step 1: Login as Creator
        login_res = client.post(
            "/auth/login",
            json={"email": "creator@proofline.ai", "password": "creator12345"},
        )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Ensure Sources are seeded
    seed_res = client.post("/sources/seed", headers=headers)
    assert seed_res.status_code == 200

    # Step 3: Create a draft containing deliberate seeded issues:
    # 1. Banned term: 'java'
    # 2. Fact contradiction: claims '500 retail locations' (approved fact is 127)
    # 3. Health claim breach: 'cures all morning fatigue' (violates TONE-01)
    draft_res = client.post(
        "/drafts",
        headers=headers,
        json={
            "content": "Grab a hot cup of java! Our blend cures all morning fatigue. We now operate 500 retail locations.",
            "channel": "instagram_post",
            "intent_lock": {
                "key_message": "energetic coffee morning",
                "audience": "coffee lovers",
                "call_to_action": "grab a cup",
            },
        },
    )
    assert draft_res.status_code == 201
    draft_id = draft_res.json()["id"]

    # Step 4: Run automated 4-layer review engine
    review_res = client.post(f"/drafts/{draft_id}/review", headers=headers)
    assert review_res.status_code == 202
    rev_data = review_res.json()
    assert rev_data["status"] == "reviewed"
    assert rev_data["findings_count"] >= 3
    assert rev_data["blockers_count"] >= 2  # java banned term + 500 store contradiction + cures health claim

    # Step 5: Fetch findings and verify every finding cites an approved source
    findings_res = client.get(f"/drafts/{draft_id}/versions/1/findings", headers=headers)
    assert findings_res.status_code == 200
    findings = findings_res.json()
    assert len(findings) >= 3

    # Every finding MUST have a non-empty source_ref ("No source, no flag")
    for f in findings:
        assert f["source_ref"] and f["source_ref"].strip()
        assert f["severity"] in ["blocker", "warning", "note"]
        assert f["confidence"] in ["high", "medium", "low"]

    # Step 6: Triage finding: creator accepts/dismisses a finding
    first_finding = findings[0]
    triage_res = client.patch(
        f"/findings/{first_finding['id']}",
        headers=headers,
        json={"status": "accepted"},
    )
    assert triage_res.status_code == 200
    assert triage_res.json()["status"] == "accepted"

    # Step 7: Request human review -> computes risk tier
    req_rev_res = client.post(f"/drafts/{draft_id}/request-review", headers=headers)
    assert req_rev_res.status_code == 202
    req_data = req_rev_res.json()
    assert req_data["status"] == "review_requested"
    assert "Level 3: High" in req_data["risk_tier"]
    assert req_data["required_role"] == "reviewer"

    # Step 8: Add inline reviewer comment
    comment_res = client.post(
        f"/drafts/{draft_id}/comments",
        headers=headers,
        json={"text": "Please update the store count to approved 127 locations and fix tone.", "range_start": 0, "range_end": 20},
    )
    assert comment_res.status_code == 201

    # Step 9: Login as Reviewer / Admin to record approval decision
    admin_login = client.post(
        "/auth/login",
        json={"email": "admin@proofline.ai", "password": "admin12345"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    decision_res = client.post(
        f"/drafts/{draft_id}/decision",
        headers=admin_headers,
        json={"decision": "approved", "reason": "All checks validated and verified."},
    )
    assert decision_res.status_code == 201

    # Step 10: Claim Receipt generated on approval
    receipt_res = client.get(f"/drafts/{draft_id}/receipt", headers=admin_headers)
    assert receipt_res.status_code == 200
    receipt_data = receipt_res.json()
    assert receipt_data["status"] == "approved"
    assert receipt_data["receipts_count"] >= 1
    assert "integrity_motto" in receipt_data["receipts"][0]["receipt_data"]

    # Step 11: Guideline Health & Analytics
    insights_res = client.get("/insights/rules", headers=admin_headers)
    assert insights_res.status_code == 200
    insights = insights_res.json()
    assert isinstance(insights, list)

    # Step 12: Audit log verification
    audit_res = client.get("/audit", headers=admin_headers)
    assert audit_res.status_code == 200
    audit_entries = audit_res.json()
    assert len(audit_entries) >= 4
    actions = [a["action"] for a in audit_entries]
    assert any("draft" in act for act in actions)
