from __future__ import annotations

import html
import re
from collections import Counter
from pathlib import Path
from typing import Any

from stock_research.sources.document_policy import classify_sec_document_record, is_trusted_financial_source


EVENT_RULES = [
    {
        "event_type": "accounting_reliability",
        "severity": "high",
        "phrases": (
            "non-reliance on previously issued financial statements",
            "non reliance on previously issued financial statements",
            "restatement of previously issued financial statements",
            "material weakness",
            "internal control over financial reporting",
            "audit committee concluded",
        ),
    },
    {
        "event_type": "auditor_change",
        "severity": "high",
        "phrases": (
            "changes in registrant's certifying accountant",
            "change in registrant's certifying accountant",
            "independent registered public accounting firm",
            "auditor resignation",
            "auditor dismissed",
            "dismissal of independent auditor",
            "appointed as the company's independent auditor",
        ),
    },
    {
        "event_type": "financing_or_debt",
        "severity": "high",
        "phrases": (
            "convertible senior notes",
            "underwriting agreement",
            "private placement",
            "subscription agreement",
            "credit agreement",
            "debt financing",
            "offering of american depositary shares",
            "follow-on public offering",
        ),
    },
    {
        "event_type": "capital_allocation",
        "severity": "medium",
        "phrases": (
            "share repurchase",
            "repurchase program",
            "buyback",
            "dividend",
            "special dividend",
        ),
    },
    {
        "event_type": "management_or_board_change",
        "severity": "medium",
        "phrases": (
            "chief executive officer",
            "chief financial officer",
            "resignation of",
            "appoints new independent director",
            "board of director changes",
            "new ceo",
            "new cfo",
        ),
    },
    {
        "event_type": "dilution_or_share_plan",
        "severity": "medium",
        "phrases": (
            "global share plan",
            "equity incentive plan",
            "share incentive plan",
            "share option plan",
            "restricted share units",
        ),
    },
    {
        "event_type": "governance_or_control",
        "severity": "medium",
        "phrases": (
            "annual general meeting",
            "extraordinary general meeting",
            "notice of meeting",
            "proxy statement",
            "shareholder meeting",
            "memorandum and articles",
            "articles of association",
            "voting rights",
        ),
    },
    {
        "event_type": "impairment_or_restructuring",
        "severity": "medium",
        "phrases": (
            "impairment",
            "restructuring",
            "asset write-down",
            "write down",
            "write-down",
        ),
    },
    {
        "event_type": "acquisition_or_divestiture",
        "severity": "medium",
        "phrases": (
            "acquisition",
            "acquire",
            "merger",
            "divestiture",
            "disposition",
            "sale of substantially all assets",
        ),
    },
    {
        "event_type": "regulatory_or_legal",
        "severity": "medium",
        "phrases": (
            "regulatory investigation",
            "government investigation",
            "settlement agreement",
            "material litigation",
            "legal proceedings",
        ),
    },
]

CATEGORY_EVENT_TYPES = {
    "KEEP_MONITORING_GOVERNANCE": "governance_or_control",
    "KEEP_MONITORING_MANAGEMENT": "management_or_board_change",
    "KEEP_MONITORING_AUDITOR_ACCOUNTING": "accounting_reliability",
    "KEEP_MONITORING_FINANCING_CAPITAL_MARKETS": "financing_or_debt",
    "KEEP_MONITORING_CAPITAL_ALLOCATION": "capital_allocation",
    "KEEP_CORE_PROSPECTUS": "prospectus_baseline",
}

CORE_EVENT_CATEGORIES = {
    "KEEP_MONITORING_GOVERNANCE",
    "KEEP_MONITORING_MANAGEMENT",
    "KEEP_MONITORING_AUDITOR_ACCOUNTING",
    "KEEP_MONITORING_FINANCING_CAPITAL_MARKETS",
    "KEEP_MONITORING_CAPITAL_ALLOCATION",
    "REVIEW_UNCLEAR_EXHIBIT",
}


def scan_material_events(documents: list[dict[str, Any]]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    skipped_untrusted = 0
    scanned = 0
    cutoff_date = _latest_annual_filing_date(documents)
    for document in documents:
        if not is_trusted_financial_source(document):
            skipped_untrusted += 1
            continue
        if cutoff_date and str(document.get("filing_date") or "") < cutoff_date:
            continue
        classification = classify_sec_document_record(document)
        category = classification.get("category")
        if not _should_scan(category):
            continue
        scanned += 1
        text = _document_text(document)
        matched = _matched_rules(text)
        if category in CATEGORY_EVENT_TYPES and not matched:
            matched = [
                {
                    "event_type": CATEGORY_EVENT_TYPES[category],
                    "severity": "medium" if category != "KEEP_MONITORING_AUDITOR_ACCOUNTING" else "high",
                    "matched_phrases": [],
                }
            ]
        for match in matched:
            events.append(_event_from_document(document, classification, match, text))

    events = _dedupe_events(events)
    severity_counts = Counter(event.get("severity", "unknown") for event in events)
    type_counts = Counter(event.get("event_type", "unknown") for event in events)
    high_priority = [
        event
        for event in events
        if event.get("severity") == "high"
        or event.get("event_type")
        in {"accounting_reliability", "auditor_change", "financing_or_debt"}
    ]
    return {
        "scanner_id": "material_event_scan_v1",
        "status": "material_events_found" if events else "no_material_events_found",
        "cutoff_filing_date": cutoff_date,
        "scanned_document_count": scanned,
        "skipped_untrusted_document_count": skipped_untrusted,
        "material_event_count": len(events),
        "high_priority_event_count": len(high_priority),
        "severity_counts": dict(sorted(severity_counts.items())),
        "event_type_counts": dict(sorted(type_counts.items())),
        "events": sorted(
            events,
            key=lambda event: (
                _severity_rank(str(event.get("severity"))),
                str(event.get("filing_date") or ""),
                str(event.get("document_id") or ""),
            ),
            reverse=True,
        ),
        "policy": (
            "Scan official non-core filings after the latest annual report for material changes only. "
            "Do not summarize every 6-K/8-K/proxy/prospectus when no material event is detected."
        ),
    }


def _latest_annual_filing_date(documents: list[dict[str, Any]]) -> str | None:
    dates = []
    for document in documents:
        classification = classify_sec_document_record(document)
        if classification.get("category") != "KEEP_CORE_ANNUAL_REPORT":
            continue
        filing_date = document.get("filing_date")
        if filing_date:
            dates.append(str(filing_date))
    return max(dates) if dates else None


def _should_scan(category: str | None) -> bool:
    if category in CORE_EVENT_CATEGORIES:
        return True
    return False


def _matched_rules(text: str) -> list[dict[str, Any]]:
    text_lower = text.lower()
    matches = []
    for rule in EVENT_RULES:
        phrases = [phrase for phrase in rule["phrases"] if phrase in text_lower]
        if phrases:
            matches.append(
                {
                    "event_type": rule["event_type"],
                    "severity": rule["severity"],
                    "matched_phrases": phrases,
                }
            )
    return matches


def _event_from_document(
    document: dict[str, Any],
    classification: dict[str, str],
    match: dict[str, Any],
    text: str,
) -> dict[str, Any]:
    event_type = match["event_type"]
    phrases = match.get("matched_phrases") or []
    snippet = _snippet_for(text, phrases[0]) if phrases else ""
    return {
        "event_id": f"{event_type}:{document.get('document_id') or document.get('local_path')}",
        "event_type": event_type,
        "severity": match["severity"],
        "document_id": document.get("document_id"),
        "document_type": document.get("document_type"),
        "filing_date": document.get("filing_date"),
        "report_date": document.get("report_date"),
        "research_category": classification.get("category"),
        "research_reason": classification.get("reason"),
        "matched_phrases": phrases,
        "evidence_snippet": snippet,
        "local_path": document.get("local_path"),
        "source_url": document.get("source_url") or document.get("archive_url"),
        "summary_rule": "Include in final report only if it changes financial risk, dilution, control, accounting reliability, or management continuity.",
    }


def _dedupe_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for event in events:
        key = (
            event.get("document_id"),
            event.get("event_type"),
        )
        current = by_key.get(key)
        if current is None or _severity_rank(str(event.get("severity"))) >= _severity_rank(str(current.get("severity"))):
            by_key[key] = event
    return list(by_key.values())


def _document_text(document: dict[str, Any]) -> str:
    path_value = document.get("local_path")
    if not path_value:
        return ""
    path = Path(path_value)
    if not path.exists() or path.suffix.lower() not in {".htm", ".html", ".txt"}:
        return ""
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _snippet_for(text: str, phrase: str) -> str:
    if not text or not phrase:
        return ""
    index = text.lower().find(phrase.lower())
    if index < 0:
        return ""
    start = max(0, index - 180)
    end = min(len(text), index + len(phrase) + 220)
    return text[start:end].strip()


def _severity_rank(severity: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(severity, -1)
