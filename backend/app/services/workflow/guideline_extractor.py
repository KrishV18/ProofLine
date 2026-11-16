"""AI-powered Guideline & Policy Extraction Service.

Parses arbitrary company documentation (PDF, DOCX, PPTX, TXT) and converts
unstructured brand policies into structured GuidelineRules, Facts, and Terminology.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.services.review.llm import call_llm_json, is_llm_configured

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class ExtractedGuideline(BaseModel):
    rule_id: str = Field(description="Unique code, e.g. RULE-001 or LEGAL-01")
    category: str = Field(default="Brand Voice", description="Category e.g. Legal, Tone, Claims, Accessibility, Style")
    rule_text: str = Field(description="The concrete policy rule or requirement")
    severity: str = Field(default="warning", description="Severity: blocker, warning, or note")


class ExtractedFact(BaseModel):
    fact_key: str = Field(description="Unique code, e.g. FACT-001")
    statement: str = Field(description="Verifiable factual claim or specification")
    value: Optional[str] = Field(default="", description="Key value, metric, or pricing if applicable")
    owner: Optional[str] = Field(default="Company Policy", description="Department or policy owner")
    expires_on: Optional[str] = Field(default=None, description="ISO date YYYY-MM-DD if date is specified")


class ExtractedTerm(BaseModel):
    term: str = Field(description="The term or phrase")
    preferred: Optional[str] = Field(default=None, description="Preferred alternative phrasing")
    banned: bool = Field(default=True, description="True if forbidden/deprecated, False if approved")
    notes: Optional[str] = Field(default="", description="Usage guidance or rationale")


class ExtractedPolicyResult(BaseModel):
    filename: Optional[str] = None
    raw_text_length: int = 0
    summary: str = ""
    guidelines: List[ExtractedGuideline] = []
    facts: List[ExtractedFact] = []
    terms: List[ExtractedTerm] = []


# ---------------------------------------------------------------------------
# Extraction Logic
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are ProofLine's Brand Governance Engine AI.
Your job is to read raw company documentation (which may be brand guidelines, style guides, legal policies, product fact sheets, pricing sheets, or company slide decks) and extract structured brand rules into three strict categories:

1. Guidelines (`guidelines`): Prescriptive rules on what writers must do, should do, or must avoid.
   - rule_id: concise code like "RULE-LEGAL-01", "RULE-TONE-01", etc.
   - category: one of ["Legal", "Brand Voice", "Claims", "Tone", "Accessibility", "Design", "Pricing", "General"]
   - rule_text: clear, actionable rule statement.
   - severity: "blocker" (legal/regulatory/strict violations), "warning" (brand style/tone), or "note" (best practice).

2. Facts (`facts`): Verifiable, objective facts, statistics, numbers, pricing, feature specs, or company data.
   - fact_key: concise code like "FACT-001", "FACT-PRICE-01", etc.
   - statement: complete factual claim.
   - value: key metric, price, or number if applicable (e.g. "₹1,299/mo", "99.9%").
   - owner: department responsible (e.g. "Legal", "Finance", "Product", "Engineering").
   - expires_on: date in YYYY-MM-DD format if an expiration or validity date is mentioned, else null.

3. Terminology (`terms`): Specific brand words, product names, approved terms, and forbidden jargon.
   - term: the word or phrase.
   - preferred: the recommended or approved replacement (or null if the term is itself the approved standard).
   - banned: true if writers should avoid this term, false if it is the approved term.
   - notes: brief rationale or context.

Respond strictly with a JSON object:
{
  "summary": "1-2 sentence overview of this policy document",
  "guidelines": [...],
  "facts": [...],
  "terms": [...]
}"""


def _heuristic_fallback_extraction(raw_text: str, filename: Optional[str] = None) -> ExtractedPolicyResult:
    """Deterministic fallback parser for when LLM is unconfigured or in offline/test mode."""
    guidelines: List[ExtractedGuideline] = []
    facts: List[ExtractedFact] = []
    terms: List[ExtractedTerm] = []

    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    g_count = 1
    f_count = 1
    t_count = 1

    current_section = "General"

    for line in lines:
        lower = line.lower()

        # Section header detection
        if len(line) < 60 and (line.endswith(":") or line.isupper() or line.startswith("#")):
            cleaned_hdr = line.strip("#: ").title()
            if any(w in lower for w in ["legal", "compliance", "law"]):
                current_section = "Legal"
            elif any(w in lower for w in ["voice", "tone", "writing", "style"]):
                current_section = "Brand Voice"
            elif any(w in lower for w in ["claim", "evidence", "substantiat"]):
                current_section = "Claims"
            elif any(w in lower for w in ["term", "word", "glossary", "naming"]):
                current_section = "Terminology"
            elif any(w in lower for w in ["fact", "price", "pricing", "metric", "stat"]):
                current_section = "Pricing"
            else:
                current_section = cleaned_hdr or "General"
            continue

        # Terminology detection: "Use X instead of Y" or "Avoid X" or "X -> Y"
        if ("instead of" in lower or "don't use" in lower or "avoid" in lower or "never use" in lower or "->" in line):
            banned_match = re.search(r"(?:avoid|don't use|never use|do not use)\s+[\"']?([^\"',.;]+)[\"']?", line, re.I)
            pref_match = re.search(r"(?:use|prefer)\s+[\"']?([^\"',.;]+)[\"']?", line, re.I)
            arrow_match = re.search(r"[\"']?([^\"'->]+)[\"']?\s*->\s*[\"']?([^\"'\n]+)[\"']?", line)

            if arrow_match:
                term_val = arrow_match.group(1).strip()
                pref_val = arrow_match.group(2).strip()
            elif banned_match:
                term_val = banned_match.group(1).strip()
                pref_val = pref_match.group(1).strip() if pref_match else None
            else:
                term_val = line[:40].strip()
                pref_val = None

            if term_val and len(term_val) > 2:
                terms.append(ExtractedTerm(
                    term=term_val,
                    preferred=pref_val,
                    banned=True,
                    notes=line[:120],
                ))
                t_count += 1
                continue

        # Facts detection: numbers, percentages, currency, dates, versions
        if re.search(r"(?:₹|\$|€|%|\b\d+(?:\.\d+)?\s*(?:gb|mb|users|uptime|days|per month|/mo|projects)\b)", lower):
            val_match = re.search(r"(?:₹|\$|€)?\d+(?:,\d+)*(?:\.\d+)?(?:\s*%)?(?:\s*(?:gb|mb|users|uptime|days|per month|/mo))?", line, re.I)
            val = val_match.group(0).strip() if val_match else ""
            facts.append(ExtractedFact(
                fact_key=f"FACT-{f_count:03d}",
                statement=line,
                value=val,
                owner="Policy Document",
                expires_on=None,
            ))
            f_count += 1
            continue

        # Guideline detection: "must", "always", "ensure", "should", "required"
        if any(w in lower for w in ["must", "always", "ensure", "should", "required", "prohibit", "forbidden", "disclaimer", "all "]):
            sev = "blocker" if any(w in lower for w in ["must", "forbidden", "prohibit", "never", "legal"]) else "warning"
            guidelines.append(ExtractedGuideline(
                rule_id=f"RULE-{g_count:03d}",
                category=current_section,
                rule_text=line,
                severity=sev,
            ))
            g_count += 1

    # Ensure at least one item if the document had any text
    if not guidelines and not facts and not terms and lines:
        guidelines.append(ExtractedGuideline(
            rule_id="RULE-001",
            category="General",
            rule_text=lines[0],
            severity="warning",
        ))

    return ExtractedPolicyResult(
        filename=filename,
        raw_text_length=len(raw_text),
        summary=f"Extracted {len(guidelines)} guidelines, {len(facts)} facts, and {len(terms)} terminology items from document.",
        guidelines=guidelines,
        facts=facts,
        terms=terms,
    )


def extract_guidelines_from_text(raw_text: str, filename: Optional[str] = None) -> ExtractedPolicyResult:
    """Extract guidelines, facts, and terminology from document text using LLM (or heuristic fallback)."""
    clean_text = raw_text.strip()
    if not clean_text:
        return ExtractedPolicyResult(filename=filename, raw_text_length=0, summary="Empty document provided.")

    if not is_llm_configured():
        logger.info("LLM not configured or mock_ai=true, using heuristic guideline extraction.")
        return _heuristic_fallback_extraction(clean_text, filename)

    # Truncate to reasonable context window if exceptionally huge (e.g. 50k chars)
    trimmed_text = clean_text[:40000]

    user_prompt = f"""Document filename: {filename or 'policy_document'}
Document text:
----------------------------------------
{trimmed_text}
----------------------------------------

Please extract all brand guidelines, verified facts, and terminology rules into the specified JSON format."""

    try:
        response_json = call_llm_json(SYSTEM_PROMPT, user_prompt)
        if not response_json or not isinstance(response_json, dict):
            logger.warning("LLM returned non-dict response for guideline extraction, falling back to heuristics.")
            return _heuristic_fallback_extraction(clean_text, filename)

        guidelines_raw = response_json.get("guidelines") or []
        facts_raw = response_json.get("facts") or []
        terms_raw = response_json.get("terms") or []
        summary = response_json.get("summary") or "Guidelines extracted via AI."

        guidelines = [ExtractedGuideline(**item) for item in guidelines_raw if isinstance(item, dict) and item.get("rule_text")]
        facts = [ExtractedFact(**item) for item in facts_raw if isinstance(item, dict) and item.get("statement")]
        terms = [ExtractedTerm(**item) for item in terms_raw if isinstance(item, dict) and item.get("term")]

        return ExtractedPolicyResult(
            filename=filename,
            raw_text_length=len(clean_text),
            summary=summary,
            guidelines=guidelines,
            facts=facts,
            terms=terms,
        )
    except Exception as exc:
        logger.warning("Error during LLM guideline extraction: %s; falling back to heuristics.", exc)
        return _heuristic_fallback_extraction(clean_text, filename)

