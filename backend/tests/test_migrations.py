"""test_migrations.py — upgrade / downgrade / upgrade cycle.

Requires a running PostgreSQL.  Set TEST_DATABASE_URL or use the default
(postgresql+psycopg://proofline:proofline@localhost:5432/proofline_test).

The ``db_engine`` and ``alembic_cfg`` fixtures from conftest.py handle
connectivity checks and skip gracefully when no DB is available.
"""
from alembic import command


def test_upgrade_downgrade_upgrade(db_engine, alembic_cfg):
    """The migration must be fully reversible and re-applicable.

    1. upgrade head   — create all tables / triggers / enums
    2. downgrade base — drop everything in reverse dependency order
    3. upgrade head   — re-create from scratch (idempotency check)
    """
    # 1. Up
    command.upgrade(alembic_cfg, "head")

    # Verify at least one expected table exists after upgrade.
    from sqlalchemy import inspect as sa_inspect
    insp = sa_inspect(db_engine)
    tables_up = set(insp.get_table_names())
    expected = {
        "organisations", "users", "guideline_rules", "facts", "terms",
        "drafts", "draft_versions", "findings", "claims", "claim_receipts",
        "comments", "approvals", "audit_log",
    }
    missing = expected - tables_up
    assert not missing, f"Tables missing after upgrade: {missing}"

    # 2. Down
    command.downgrade(alembic_cfg, "base")
    insp2 = sa_inspect(db_engine)
    tables_down = set(insp2.get_table_names())
    # alembic_version table may persist — ignore it
    remaining = tables_down - {"alembic_version"}
    assert not remaining, f"Tables still present after downgrade: {remaining}"

    # 3. Up again
    command.upgrade(alembic_cfg, "head")
    insp3 = sa_inspect(db_engine)
    tables_up2 = set(insp3.get_table_names())
    missing2 = expected - tables_up2
    assert not missing2, f"Tables missing after second upgrade: {missing2}"
