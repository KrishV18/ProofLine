"""test_schema.py — schema-level constraint tests.

All tests in this module require a running PostgreSQL with the ProofLine
schema applied (via the ``db_conn`` fixture from conftest.py, which depends
on ``migrated_db`` which runs alembic upgrade head once per session).

Tests are designed to be independent: each test uses a per-test connection
with a rolled-back transaction so constraint violations cannot contaminate
other tests.
"""
from __future__ import annotations

import hashlib
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_id() -> str:
    return str(uuid.uuid4())


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _insert_org(conn, name: str | None = None) -> str:
    """Insert an organisation and return its id."""
    org_id = _new_id()
    name = name or f"org-{org_id[:8]}"
    conn.execute(
        text("INSERT INTO organisations (id, name) VALUES (:id, :name)"),
        {"id": org_id, "name": name},
    )
    return org_id


def _insert_user(conn, org_id: str) -> str:
    """Insert a minimal user and return its id."""
    user_id = _new_id()
    conn.execute(
        text(
            "INSERT INTO users (id, organisation_id, email, password_hash, role) "
            "VALUES (:id, :org, :email, :pw, 'creator')"
        ),
        {"id": user_id, "org": org_id, "email": f"{user_id}@example.com", "pw": "x"},
    )
    return user_id


def _insert_draft(conn, org_id: str, owner_id: str) -> str:
    """Insert a draft and return its id."""
    d_id = _new_id()
    conn.execute(
        text(
            "INSERT INTO drafts (id, organisation_id, owner_id, title) "
            "VALUES (:id, :org, :owner, 'Test draft')"
        ),
        {"id": d_id, "org": org_id, "owner": owner_id},
    )
    return d_id


def _insert_draft_version(conn, org_id: str, draft_id: str, vnum: int = 1) -> str:
    """Insert a draft_version and return its id."""
    v_id = _new_id()
    content = f"content-v{vnum}"
    conn.execute(
        text(
            "INSERT INTO draft_versions "
            "(id, organisation_id, draft_id, version_number, content, content_hash) "
            "VALUES (:id, :org, :did, :vnum, :content, :hash)"
        ),
        {
            "id": v_id,
            "org": org_id,
            "did": draft_id,
            "vnum": vnum,
            "content": content,
            "hash": _sha256(content),
        },
    )
    return v_id


# ---------------------------------------------------------------------------
# test_org_column
# ---------------------------------------------------------------------------

def test_org_column():
    """Every table except 'organisations' must have an organisation_id column.

    This test inspects SQLAlchemy metadata only — no DB required.
    """
    import app.models as m

    for table_name, table in m.Base.metadata.tables.items():
        if table_name == "organisations":
            continue
        col_names = {c.name for c in table.columns}
        assert "organisation_id" in col_names, (
            f"Table '{table_name}' is missing organisation_id column"
        )


# ---------------------------------------------------------------------------
# test_versioning
# ---------------------------------------------------------------------------

def test_versioning_second_version_inserts(db_conn):
    """Inserting a second version (v2) of a guideline rule must succeed."""
    org_id = _insert_org(db_conn)
    user_id = _insert_user(db_conn, org_id)

    for version in (1, 2):
        db_conn.execute(
            text(
                "INSERT INTO guideline_rules "
                "(id, organisation_id, rule_id, text, version, is_active, created_by) "
                "VALUES (:id, :org, :rule_id, :text, :version, false, :created_by)"
            ),
            {
                "id": _new_id(),
                "org": org_id,
                "rule_id": "TONE-01",
                "text": f"Rule text v{version}",
                "version": version,
                "created_by": user_id,
            },
        )
    # Both inserts succeeded — test passes if no exception raised.


def test_versioning_two_active_versions_fails(db_conn):
    """Two active versions of the same rule_id in the same org must fail."""
    org_id = _insert_org(db_conn)
    user_id = _insert_user(db_conn, org_id)

    # Insert active v1
    db_conn.execute(
        text(
            "INSERT INTO guideline_rules "
            "(id, organisation_id, rule_id, text, version, is_active, created_by) "
            "VALUES (:id, :org, 'TONE-01', 'Version 1', 1, true, :created_by)"
        ),
        {"id": _new_id(), "org": org_id, "created_by": user_id},
    )

    with pytest.raises(Exception, match="unique|duplicate|ix_guideline_rules_one_active"):
        # Insert another active version for the same rule_id — partial unique idx
        db_conn.execute(
            text(
                "INSERT INTO guideline_rules "
                "(id, organisation_id, rule_id, text, version, is_active, created_by) "
                "VALUES (:id, :org, 'TONE-01', 'Version 2 active', 2, true, :created_by)"
            ),
            {"id": _new_id(), "org": org_id, "created_by": user_id},
        )


# ---------------------------------------------------------------------------
# test_findings_constraints
# ---------------------------------------------------------------------------

def test_findings_empty_source_ref_fails(db_conn):
    """source_ref = '' must violate the CHECK constraint (no source, no flag)."""
    org_id = _insert_org(db_conn)
    user_id = _insert_user(db_conn, org_id)
    draft_id = _insert_draft(db_conn, org_id, user_id)
    version_id = _insert_draft_version(db_conn, org_id, draft_id)

    with pytest.raises(Exception, match="ck_findings_source_ref_nonempty|check"):
        db_conn.execute(
            text(
                "INSERT INTO findings "
                "(id, organisation_id, draft_id, version_id, start_offset, end_offset, "
                " severity, reason, source_ref, confidence) "
                "VALUES (:id, :org, :did, :vid, 0, 5, 'blocker', 'reason', '', 'high')"
            ),
            {"id": _new_id(), "org": org_id, "did": draft_id, "vid": version_id},
        )


def test_findings_bad_offsets_fails(db_conn):
    """end_offset <= start_offset must violate the CHECK constraint."""
    org_id = _insert_org(db_conn)
    user_id = _insert_user(db_conn, org_id)
    draft_id = _insert_draft(db_conn, org_id, user_id)
    version_id = _insert_draft_version(db_conn, org_id, draft_id)

    with pytest.raises(Exception, match="ck_findings_offsets|check"):
        db_conn.execute(
            text(
                "INSERT INTO findings "
                "(id, organisation_id, draft_id, version_id, start_offset, end_offset, "
                " severity, reason, source_ref, confidence) "
                "VALUES (:id, :org, :did, :vid, 10, 5, 'blocker', 'reason', 'TONE-01', 'high')"
            ),
            {"id": _new_id(), "org": org_id, "did": draft_id, "vid": version_id},
        )


def test_findings_dismissed_without_reason_fails(db_conn):
    """A dismissed finding with NULL dismissal_reason must violate CHECK."""
    org_id = _insert_org(db_conn)
    user_id = _insert_user(db_conn, org_id)
    draft_id = _insert_draft(db_conn, org_id, user_id)
    version_id = _insert_draft_version(db_conn, org_id, draft_id)

    with pytest.raises(Exception, match="ck_findings_dismissed_reason|check"):
        db_conn.execute(
            text(
                "INSERT INTO findings "
                "(id, organisation_id, draft_id, version_id, start_offset, end_offset, "
                " severity, reason, source_ref, confidence, status, dismissal_reason) "
                "VALUES (:id, :org, :did, :vid, 0, 5, 'note', 'reason', "
                "        'TONE-01', 'low', 'dismissed', NULL)"
            ),
            {"id": _new_id(), "org": org_id, "did": draft_id, "vid": version_id},
        )


# ---------------------------------------------------------------------------
# test_cross_org
# ---------------------------------------------------------------------------

def test_cross_org_finding_blocked(db_conn):
    """A finding in org_b cannot reference a draft_version owned by org_a."""
    # Set up org_a with a draft and version.
    org_a = _insert_org(db_conn, "org-alpha")
    user_a = _insert_user(db_conn, org_a)
    draft_a = _insert_draft(db_conn, org_a, user_a)
    version_a = _insert_draft_version(db_conn, org_a, draft_a)

    # Set up org_b.
    org_b = _insert_org(db_conn, "org-beta")

    with pytest.raises(Exception):
        # version_a belongs to org_a, but we pass org_b as organisation_id →
        # the composite FK (version_id, organisation_id) → draft_versions will
        # reject this because no (version_a, org_b) tuple exists there.
        db_conn.execute(
            text(
                "INSERT INTO findings "
                "(id, organisation_id, draft_id, version_id, start_offset, end_offset, "
                " severity, reason, source_ref, confidence) "
                "VALUES (:id, :org_b, :did, :vid, 0, 5, 'note', 'x', 'SRC-01', 'low')"
            ),
            {"id": _new_id(), "org_b": org_b, "did": draft_a, "vid": version_a},
        )


# ---------------------------------------------------------------------------
# test_immutability
# ---------------------------------------------------------------------------

def test_audit_log_update_blocked(db_conn):
    """UPDATE on audit_log must raise (append-only trigger)."""
    org_id = _insert_org(db_conn)
    log_id = _new_id()
    db_conn.execute(
        text(
            "INSERT INTO audit_log (id, organisation_id, action, entity) "
            "VALUES (:id, :org, 'test_action', 'test_entity')"
        ),
        {"id": log_id, "org": org_id},
    )
    with pytest.raises(Exception, match="immutable"):
        db_conn.execute(
            text("UPDATE audit_log SET action = 'changed' WHERE id = :id"),
            {"id": log_id},
        )


def test_audit_log_delete_blocked(db_conn):
    """DELETE on audit_log must raise (append-only trigger)."""
    org_id = _insert_org(db_conn)
    log_id = _new_id()
    db_conn.execute(
        text(
            "INSERT INTO audit_log (id, organisation_id, action, entity) "
            "VALUES (:id, :org, 'delete_me', 'test_entity')"
        ),
        {"id": log_id, "org": org_id},
    )
    with pytest.raises(Exception, match="immutable"):
        db_conn.execute(
            text("DELETE FROM audit_log WHERE id = :id"),
            {"id": log_id},
        )


def test_draft_version_content_update_blocked(db_conn):
    """UPDATE of draft_versions.content must raise (immutable-content trigger)."""
    org_id = _insert_org(db_conn)
    user_id = _insert_user(db_conn, org_id)
    draft_id = _insert_draft(db_conn, org_id, user_id)
    version_id = _insert_draft_version(db_conn, org_id, draft_id)

    with pytest.raises(Exception, match="immutable"):
        db_conn.execute(
            text(
                "UPDATE draft_versions SET content = 'tampered', "
                "content_hash = :h WHERE id = :id"
            ),
            {"h": _sha256("tampered"), "id": version_id},
        )


def test_claim_receipts_delete_blocked(db_conn):
    """DELETE on claim_receipts must raise (immutable-row trigger)."""
    org_id = _insert_org(db_conn)
    user_id = _insert_user(db_conn, org_id)
    draft_id = _insert_draft(db_conn, org_id, user_id)
    version_id = _insert_draft_version(db_conn, org_id, draft_id)

    receipt_id = _new_id()
    content = "approved content"
    db_conn.execute(
        text(
            "INSERT INTO claim_receipts "
            "(id, organisation_id, draft_id, version_id, approved_by, approved_at, "
            " content_hash, claims_snapshot, guideline_versions) "
            "VALUES (:id, :org, :did, :vid, :user, now(), :hash, '{}', '{}')"
        ),
        {
            "id": receipt_id,
            "org": org_id,
            "did": draft_id,
            "vid": version_id,
            "user": user_id,
            "hash": _sha256(content),
        },
    )

    with pytest.raises(Exception, match="immutable"):
        db_conn.execute(
            text("DELETE FROM claim_receipts WHERE id = :id"),
            {"id": receipt_id},
        )


# ---------------------------------------------------------------------------
# test_unique_receipt
# ---------------------------------------------------------------------------

def test_unique_receipt_per_version(db_conn):
    """A second claim_receipt for the same version_id must fail (UNIQUE)."""
    org_id = _insert_org(db_conn)
    user_id = _insert_user(db_conn, org_id)
    draft_id = _insert_draft(db_conn, org_id, user_id)
    version_id = _insert_draft_version(db_conn, org_id, draft_id)
    content = "approved"

    def _insert_receipt(receipt_id: str):
        db_conn.execute(
            text(
                "INSERT INTO claim_receipts "
                "(id, organisation_id, draft_id, version_id, approved_by, approved_at, "
                " content_hash, claims_snapshot, guideline_versions) "
                "VALUES (:id, :org, :did, :vid, :user, now(), :hash, '{}', '{}')"
            ),
            {
                "id": receipt_id,
                "org": org_id,
                "did": draft_id,
                "vid": version_id,
                "user": user_id,
                "hash": _sha256(content),
            },
        )

    _insert_receipt(_new_id())  # First receipt — must succeed.

    with pytest.raises(Exception, match="unique|duplicate|uq_claim_receipts_version_id"):
        _insert_receipt(_new_id())  # Second receipt for same version — must fail.
