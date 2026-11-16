"""Tests for the AI Document Policy Extraction feature."""
import io
import pytest
from pptx import Presentation
from docx import Document
from fastapi.testclient import TestClient

from app.main import app
from app.services.parsing.parser import parse_document, parse_pptx
from app.services.workflow.guideline_extractor import (
    extract_guidelines_from_text,
    ExtractedPolicyResult,
)


def test_parse_document_text():
    content = b"Legal Policy:\nAll advertisements must include Terms apply.\nDo not use 'cheap tier'."
    text, doc_type = parse_document("policy.txt", content)
    assert doc_type == "text"
    assert "Legal Policy" in text
    assert "Terms apply" in text


def test_parse_document_docx():
    doc = Document()
    doc.add_heading("Brand Voice Guide", level=1)
    doc.add_paragraph("Writers must avoid pressure tactics and hyperbole.")
    stream = io.BytesIO()
    doc.save(stream)
    content = stream.getvalue()

    text, doc_type = parse_document("guide.docx", content)
    assert doc_type == "docx"
    assert "Brand Voice Guide" in text
    assert "pressure tactics" in text


def test_parse_document_pptx():
    prs = Presentation()
    slide_layout = prs.slide_layouts[0]  # Title slide
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = "Acme Corp Pricing 2026"
    slide.placeholders[1].text = "Starter plan costs \u20b91,299 per month.\nNever say 'cheap pack' -> 'Starter plan'."

    stream = io.BytesIO()
    prs.save(stream)
    content = stream.getvalue()

    text, doc_type = parse_document("pricing.pptx", content)
    assert doc_type == "pptx"
    assert "Acme Corp Pricing 2026" in text
    assert "Starter plan costs" in text


def test_heuristic_guideline_extraction():
    sample_text = """
    Brand Guidelines & Pricing Policy:

    Legal Requirements:
    All promotions must display 'Terms apply' prominently.
    Superlatives and unverified claims are strictly forbidden.

    Pricing & Metrics:
    The Starter plan costs \u20b91,299/mo and includes 5 projects.
    Enterprise tier guarantees 99.9% uptime.

    Terminology:
    Never use 'cheap pack' -> 'Starter plan'.
    Avoid 'best in class' because it is unprovable.
    """
    result: ExtractedPolicyResult = extract_guidelines_from_text(sample_text, "policy.txt")

    assert len(result.guidelines) >= 1
    assert len(result.facts) >= 1
    assert len(result.terms) >= 1

    # Check guideline attributes
    gl = result.guidelines[0]
    assert gl.rule_id.startswith("RULE-")
    assert gl.severity in {"blocker", "warning", "note"}

    # Check fact attributes
    fact = result.facts[0]
    assert fact.fact_key.startswith("FACT-")
    assert fact.statement

    # Check term attributes
    term = result.terms[0]
    assert term.term
    assert term.banned is True


def test_extract_document_endpoint_empty_file():
    with TestClient(app) as client:
        # Login first to get JWT
        login_res = client.post("/auth/login", json={"email": "admin@proofline.ai", "password": "admin12345"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Empty file
        res = client.post(
            "/sources/extract-document",
            files={"file": ("empty.txt", b"", "text/plain")},
            headers=headers,
        )
        assert res.status_code == 400
        assert "empty" in res.json()["detail"].lower()


def test_extract_and_bulk_import_flow():
    with TestClient(app) as client:
        # Login as manager
        login_res = client.post("/auth/login", json={"email": "admin@proofline.ai", "password": "admin12345"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Upload a valid policy doc
        doc_content = b"""
        Acme Corp Compliance Guide:
        All outbound messages must include an unsubscribe link.
        The pro tier costs $49/mo.
        Avoid 'foolproof' in all copy.
        """
        extract_res = client.post(
            "/sources/extract-document",
            files={"file": ("acme_policy.txt", doc_content, "text/plain")},
            headers=headers,
        )
        assert extract_res.status_code == 200
        data = extract_res.json()
        assert "guidelines" in data
        assert "facts" in data
        assert "terms" in data

        # Now test bulk-import
        import_payload = {
            "guidelines": [
                {
                    "rule_id": "RULE-TEST-001",
                    "text": "All outbound messages must include an unsubscribe link.",
                    "category": "Legal",
                }
            ],
            "facts": [
                {
                    "fact_key": "FACT-TEST-001",
                    "statement": "The pro tier costs $49/mo.",
                    "value": "$49/mo",
                    "owner": "Finance",
                }
            ],
            "terms": [
                {
                    "term": "foolproof",
                    "preferred": "reliable",
                    "banned": True,
                    "notes": "Do not make absolute claims.",
                }
            ],
        }

        import_res = client.post(
            "/sources/bulk-import",
            json=import_payload,
            headers=headers,
        )
        assert import_res.status_code == 201
        res_data = import_res.json()
        assert res_data["status"] == "success"
        assert res_data["imported"]["guidelines"] == 1
        assert res_data["imported"]["facts"] == 1
        assert res_data["imported"]["terms"] == 1

        # Verify that GET /sources returns the newly imported items
        sources_res = client.get("/sources", headers=headers)
        assert sources_res.status_code == 200
        sources_data = sources_res.json()
        rule_ids = [g["rule_id"] for g in sources_data["guidelines"]]
        fact_keys = [f["fact_key"] for f in sources_data["facts"]]
        terms = [t["term"] for t in sources_data["terms"]]

        assert "RULE-TEST-001" in rule_ids
        assert "FACT-TEST-001" in fact_keys
        assert "foolproof" in terms

