"""Sample data seeding service for ProofLine."""

import json
from datetime import date
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.roles import Role, get_or_create_default_org
from app.core.security import hash_password
from app.models.fact import Fact
from app.models.guideline_rule import GuidelineRule
from app.models.term import Term
from app.models.user import User


def seed_sample_data(db: Session) -> dict:
    """Seed sample guidelines, facts, terminology, and test users."""
    org = get_or_create_default_org(db)

    # 1. Seed Demo Users
    demo_users = [
        ("admin@proofline.ai", "admin12345", Role.ADMIN.value),
        ("creator@proofline.ai", "creator12345", Role.CREATOR.value),
        ("reviewer@proofline.ai", "reviewer12345", Role.REVIEWER.value),
        ("manager@proofline.ai", "manager12345", Role.MANAGER.value),
    ]
    created_users = 0
    for email, pw, role in demo_users:
        existing = db.scalars(select(User).where(User.email == email)).first()
        if not existing:
            u = User(
                organisation_id=org.id,
                email=email,
                hashed_password=hash_password(pw),
                role=role,
                is_active=True,
            )
            db.add(u)
            created_users += 1

    # Locate sample-data directory
    possible_paths = [
        Path("sample-data"),
        Path("../sample-data"),
        Path(__file__).parents[4] / "sample-data",
    ]
    sample_dir = None
    for p in possible_paths:
        if p.exists() and (p / "guidelines.json").exists():
            sample_dir = p
            break

    seeded_guidelines = 0
    seeded_facts = 0
    seeded_terms = 0

    if sample_dir:
        # 2. Guidelines
        gl_file = sample_dir / "guidelines.json"
        if gl_file.exists():
            with open(gl_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    existing = db.scalars(
                        select(GuidelineRule).where(
                            GuidelineRule.organisation_id == org.id,
                            GuidelineRule.rule_id == item["rule_id"],
                        )
                    ).first()
                    if not existing:
                        db.add(
                            GuidelineRule(
                                organisation_id=org.id,
                                rule_id=item["rule_id"],
                                category=item.get("category"),
                                text=item["text"],
                                version=1,
                                is_active=True,
                            )
                        )
                        seeded_guidelines += 1

        # 3. Facts
        facts_file = sample_dir / "facts.json"
        if facts_file.exists():
            with open(facts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    existing = db.scalars(
                        select(Fact).where(
                            Fact.organisation_id == org.id,
                            Fact.statement == item["statement"],
                        )
                    ).first()
                    if not existing:
                        exp = None
                        if item.get("expires_on"):
                            exp = date.fromisoformat(item["expires_on"])
                        db.add(
                            Fact(
                                organisation_id=org.id,
                                statement=item["statement"],
                                value=str(item.get("value", "")),
                                owner=item.get("owner"),
                                source=item.get("source"),
                                expires_on=exp,
                                version=1,
                            )
                        )
                        seeded_facts += 1

        # 4. Terminology
        terms_file = sample_dir / "terminology.json"
        if terms_file.exists():
            with open(terms_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    existing = db.scalars(
                        select(Term).where(
                            Term.organisation_id == org.id,
                            Term.term == item["term"],
                        )
                    ).first()
                    if not existing:
                        db.add(
                            Term(
                                organisation_id=org.id,
                                term=item["term"],
                                preferred=item.get("preferred"),
                                banned=item.get("banned", False),
                                notes=item.get("notes"),
                            )
                        )
                        seeded_terms += 1

    db.commit()
    return {
        "status": "seeded",
        "created_users": created_users,
        "guidelines": seeded_guidelines,
        "facts": seeded_facts,
        "terms": seeded_terms,
    }

