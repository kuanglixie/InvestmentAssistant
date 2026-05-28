from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any


FINANCIAL_EXTRACTION_CATEGORIES = {
    "KEEP_CORE_ANNUAL_REPORT",
    "KEEP_CORE_INTERIM_EARNINGS",
    "KEEP_SECONDARY_INTERIM_FINANCIAL_CONTEXT",
}

DROP_FROM_RESEARCH_CATEGORIES = {
    "DROP_SEC_INDEX_OR_HEADERS",
}


def classify_sec_document_record(document: dict[str, Any]) -> dict[str, str]:
    existing = document.get("research_category")
    if existing:
        return {
            "category": str(existing),
            "decision": str(document.get("research_decision") or ""),
            "reason": str(document.get("research_reason") or ""),
        }

    path = document.get("local_path")
    text = ""
    if path and Path(path).exists():
        text = _read_text(Path(path))
    return classify_sec_document_text(
        filename=str(document.get("downloaded_file") or document.get("primary_document") or ""),
        form=_document_form(document),
        role=_document_role(document),
        text=text,
    )


def classify_sec_document_text(
    *,
    filename: str,
    form: str,
    role: str,
    text: str,
) -> dict[str, str]:
    form = form.upper()
    role = role.lower()
    filename_lower = filename.lower()
    text_lower = text.lower()

    if form in {"20-F", "20-F/A", "10-K", "10-K/A"}:
        return _classification(
            "KEEP_CORE_ANNUAL_REPORT",
            "Keep",
            "Annual report; core source for annual financials, business, risk, ownership, and governance.",
        )
    if "index" in filename_lower or "headers" in filename_lower:
        return _classification(
            "DROP_SEC_INDEX_OR_HEADERS",
            "Drop from research corpus",
            "SEC index/header helper file; useful only for debugging the download package.",
        )
    if form in {"6-K", "6-K/A"} and role == "primary":
        return _classification(
            "LOW_KEEP_WRAPPER_METADATA",
            "Keep metadata only",
            "6-K wrapper; normally points to exhibits and has little research content.",
        )
    if _is_earnings_release(text_lower):
        return _classification(
            "KEEP_CORE_INTERIM_EARNINGS",
            "Keep",
            "Earnings or unaudited financial-results exhibit; core source for quarterly/interim extraction.",
        )
    if _contains_any(
        text_lower,
        (
            "documentfiscalperiodfocus",
            "unaudited interim condensed consolidated",
            "interim condensed consolidated financial statements",
            "management's discussion and analysis of financial condition and results",
        ),
    ):
        return _classification(
            "KEEP_SECONDARY_INTERIM_FINANCIAL_CONTEXT",
            "Keep secondary",
            "Interim statements or MD&A outside a normal earnings release; use for cross-checking.",
        )
    if _contains_any(
        text_lower,
        (
            "annual general meeting",
            "extraordinary general meeting",
            "notice of meeting",
            "proxy statement",
            "proxy card",
            "shareholder meeting",
            "memorandum and articles",
            "articles of association",
            "global share plan",
            "compensation committee",
        ),
    ):
        return _classification(
            "KEEP_MONITORING_GOVERNANCE",
            "Keep secondary",
            "Governance, shareholder meeting, or compensation-plan document.",
        )
    if _contains_any(
        text_lower,
        (
            "names new ceo",
            "new ceo",
            "chief executive officer",
            "chief financial officer",
            "general counsel",
            "vp of finance",
            "board of director changes",
            "appoints new independent director",
            "resignation of",
        ),
    ):
        return _classification(
            "KEEP_MONITORING_MANAGEMENT",
            "Keep secondary",
            "Management or board-change disclosure.",
        )
    if _contains_any(
        text_lower,
        (
            "convertible senior notes",
            "offering of american depositary shares",
            "follow-on public offering",
            "underwriting agreement",
            "private placement",
            "global institutional investor",
            "subscribes to",
            "convertible bonds",
            "subscription agreement",
        ),
    ):
        return _classification(
            "KEEP_MONITORING_FINANCING_CAPITAL_MARKETS",
            "Keep secondary",
            "Financing or capital-markets disclosure; useful for dilution, debt, and capital allocation review.",
        )
    if _contains_any(text_lower, ("share repurchase", "repurchase program", "buyback", "dividend")):
        return _classification(
            "KEEP_MONITORING_CAPITAL_ALLOCATION",
            "Keep secondary",
            "Capital-allocation disclosure.",
        )
    return _classification(
        "REVIEW_UNCLEAR_EXHIBIT",
        "Review manually",
        "Unclear exhibit; inspect before using as research evidence.",
    )


def is_financial_extraction_document(document: dict[str, Any]) -> bool:
    category = classify_sec_document_record(document)["category"]
    return category in FINANCIAL_EXTRACTION_CATEGORIES


def _document_form(document: dict[str, Any]) -> str:
    form = document.get("form")
    if form:
        return str(form)
    document_type = str(document.get("document_type") or "")
    return document_type.split(":", 1)[0]


def _document_role(document: dict[str, Any]) -> str:
    role = document.get("document_role")
    if role:
        return str(role)
    document_type = str(document.get("document_type") or "")
    if ":" in document_type:
        return document_type.split(":", 1)[1]
    return ""


def _classification(category: str, decision: str, reason: str) -> dict[str, str]:
    return {
        "category": category,
        "decision": decision,
        "reason": reason,
    }


def _is_earnings_release(text: str) -> bool:
    return (
        ("announces fourth quarter" in text and "financial results" in text)
        or ("announces third quarter" in text and "financial results" in text)
        or ("announces second quarter" in text and "financial results" in text)
        or ("announces first quarter" in text and "financial results" in text)
        or "unaudited financial results" in text
        or ("fourth quarter and fiscal year" in text and "financial results" in text)
    )


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _read_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()
