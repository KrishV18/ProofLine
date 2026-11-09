"""Test the 4-layer review engine, claim ledger, and validator."""

from datetime import date
import pytest

from app.models.fact import Fact
from app.models.guideline_rule import GuidelineRule
from app.models.term import Term
from app.schemas.claim import ClaimStatus
from app.schemas.finding import FindingBase
from app.services.review.claim_ledger import process_claim_ledger
from app.services.review.deterministic import run_deterministic_checks
from app.services.review.intent_lock import compute_side_by_side_diff, verify_intent_preservation
from app.services.review.tone_engine import evaluate_grounded_tone
from app.services.review.validator import validate_and_filter_findings


def test_layer1_deterministic_banned_terms():
    """Layer 1: Deterministic detection of banned terminology."""
    term = Term(
        term="java",
        preferred="premium roast coffee",
        banned=True,
        notes="Slang not approved in customer copy.",
    )
    content = "Grab a cup of our fresh java today!"
    findings = run_deterministic_checks(content, [term])

    assert len(findings) == 1
    f = findings[0]
    assert f.quoted_text == "java"
    assert f.severity == "blocker"
    assert f.source_ref == "TERM-JAVA"
    assert "premium roast coffee" in (f.suggestion or "")


def test_layer2_claim_ledger_conflict_and_expiry():
    """Layer 2: Claim Ledger detects contradictions and expired evidence."""
    # Active fact
    f_stores = Fact(
        statement="Number of retail locations",
        value="127",
        owner="Operations",
        source="Q3 2026 Investor Report",
        expires_on=date(2027, 3, 31),
    )
    # Expired fact (2025-12-31 is in past relative to 2026-11-09)
    f_history = Fact(
        statement="Company founding year and city",
        value="Founded in 1985 in Portland, Oregon",
        owner="Brand Team",
        source="Corporate History Archive",
        expires_on=date(2025, 12, 31),
    )

    # 1. Contradiction test: text claims 250 locations
    content_contradiction = "We now operate 250 retail locations across the country."
    claims, findings = process_claim_ledger(content_contradiction, [f_stores, f_history])
    conflict_claims = [c for c in claims if c.status == ClaimStatus.CONFLICTS]
    assert len(conflict_claims) >= 1
    assert any("127" in (c.reason or "") for c in conflict_claims)

    # 2. Expired evidence test: text quotes founding
    content_history = "Founded in 1985 in Portland, Oregon, our heritage runs deep."
    claims_hist, findings_hist = process_claim_ledger(content_history, [f_stores, f_history])
    expired_claims = [c for c in claims_hist if c.status == ClaimStatus.EXPIRED_EVIDENCE]
    assert len(expired_claims) >= 1
    assert any("expired" in (c.reason or "").lower() for c in expired_claims)


def test_layer3_grounded_tone_check():
    """Layer 3: Detects absolute health claims and pressure sales language."""
    rule_health = GuidelineRule(
        rule_id="TONE-01",
        category="Health Claims",
        text="Do not make absolute health claims (e.g. 'healthiest', 'cures').",
        version=1,
        is_active=True,
    )
    rule_sales = GuidelineRule(
        rule_id="TONE-02",
        category="Brand Voice",
        text="Maintain a warm tone. Avoid aggressive sales language.",
        version=1,
        is_active=True,
    )

    content = "Our blend cures morning fatigue and ACT NOW BEFORE IT'S GONE!"
    findings = evaluate_grounded_tone(content, [rule_health, rule_sales])

    assert len(findings) >= 2
    rule_ids = {f.source_ref for f in findings}
    assert "TONE-01" in rule_ids
    assert "TONE-02" in rule_ids


def test_layer4_validator_no_source_no_flag():
    """Layer 4: Validator strictly drops unsourced or hallucinated flags."""
    valid_sources = {"TONE-01", "TERM-JAVA", "FACT-01"}
    content = "Sample content text."

    valid_finding = FindingBase(
        quoted_text="Sample",
        start=0,
        end=6,
        severity="blocker",
        reason="Valid reason",
        source_ref="TONE-01",
        source_version=1,
        confidence="high",
        suggestion="Sample fix",
        status="open",
    )
    fabricated_ref_finding = FindingBase(
        quoted_text="content",
        start=7,
        end=14,
        severity="warning",
        reason="Random rule not in brand guidelines",
        source_ref="MADE-UP-RULE-999",
        source_version=1,
        confidence="low",
        suggestion=None,
        status="open",
    )

    filtered = validate_and_filter_findings(
        [valid_finding, fabricated_ref_finding],
        content=content,
        valid_source_refs=valid_sources,
    )

    assert len(filtered) == 1
    assert filtered[0].source_ref == "TONE-01"


def test_intent_lock_and_diff():
    """Test Intent Lock diff computation and message preservation check."""
    original = "Enjoy our fresh coffee. Click here to order online today."
    revised = "Enjoy our premium roast coffee. Click here to order online today."

    diff_tokens = compute_side_by_side_diff(original, revised)
    assert any(t["type"] == "insert" for t in diff_tokens)

    intent_lock = {
        "key_message": "premium roast coffee",
        "call_to_action": "order online today",
    }
    result = verify_intent_preservation(original, revised, intent_lock)
    assert result["intent_preserved"] is True
