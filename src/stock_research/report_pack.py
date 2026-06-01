from __future__ import annotations

from collections import Counter
from typing import Any

from stock_research.metrics.v1 import annual_fact_rows, quarterly_fact_rows
from stock_research.state import ResearchState, utc_now_iso


FINANCIAL_REPORT_PACK_SCHEMA_VERSION = "financial_report_pack_v1"


def build_financial_report_pack(state: ResearchState) -> dict[str, Any]:
    metrics = state.get("metrics", [])
    valuation_metrics = state.get("valuation_metrics", [])
    diagnostic_findings = state.get("diagnostic_findings") or {}
    material_event_scan = state.get("material_event_scan") or {}
    extraction_summary = state.get("extraction_summary") or {}
    pack = {
        "schema_version": FINANCIAL_REPORT_PACK_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "run_id": state.get("run_id"),
        "company": state.get("canonical_company") or {},
        "market": state.get("market"),
        "source_inventory": _source_inventory(state),
        "document_inventory": _document_inventory(state.get("documents", [])),
        "annual_report_baseline": _annual_report_baseline(state),
        "annual_facts": annual_fact_rows(state.get("extracted_facts", [])),
        "quarterly_facts": quarterly_fact_rows(state.get("extracted_facts", [])),
        "financial_metrics": metrics,
        "valuation_metrics": valuation_metrics,
        "latest_interim_trend": _metric_by_id(metrics, "latest_interim_trend_v1"),
        "diagnostic_findings": diagnostic_findings,
        "financial_investigation_notes": state.get("financial_investigation_notes")
        or {
            "status": "not_run",
            "notes": [],
            "instruction": "Use docs/financial-evidence-investigation-skill-v1.md before report writing when abnormal diagnostics need source-level explanation.",
        },
        "material_event_scan": material_event_scan,
        "verification_results": state.get("verification_results", []),
        "ir_cross_validation": state.get("ir_cross_validation", {}),
        "missing_facts": _missing_facts(extraction_summary, metrics),
        "human_review_flags": _human_review_flags(state),
        "report_controls": {
            "source_policy": "Official regulator/exchange filings and company investor-relations documents only for financial facts.",
            "formula_policy": "Metrics come from deterministic Python formula code, not the report-writing layer.",
            "interpretation_policy": "The writing layer may summarize this pack but must not recalculate numbers or invent facts.",
            "valuation_policy": "Valuation metrics are included only when produced by the Valuation Agent.",
        },
    }
    return pack


def _source_inventory(state: ResearchState) -> dict[str, Any]:
    candidates = state.get("source_candidates", [])
    approved = state.get("approved_sources", [])
    return {
        "candidate_count": len(candidates),
        "approved_count": len(approved),
        "trust_tier_counts": dict(Counter(str(source.get("trust_tier", "unknown")) for source in candidates)),
        "approved_sources": approved,
    }


def _document_inventory(documents: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "document_count": len(documents),
        "document_type_counts": dict(
            Counter(str(document.get("document_type", "unknown")).split(":", 1)[0] for document in documents)
        ),
        "research_category_counts": dict(
            Counter(str(document.get("research_category", "uncategorized")) for document in documents)
        ),
        "latest_annual_report": _latest_document(
            documents,
            prefixes=("10-K", "20-F", "annual_report_pdf"),
        ),
        "latest_interim_report": _latest_document(
            documents,
            prefixes=("10-Q", "6-K", "interim_report_pdf"),
        ),
    }


def _annual_report_baseline(state: ResearchState) -> dict[str, Any]:
    documents = state.get("documents", [])
    latest_annual = _latest_document(
        documents,
        prefixes=("10-K", "20-F", "annual_report_pdf"),
    )
    diagnostics = state.get("diagnostic_findings") or {}
    answered_questions = [
        {
            "question_id": question.get("question_id"),
            "status": question.get("status"),
            "priority": question.get("priority"),
            "current_answer": question.get("current_answer"),
            "warning_flags": question.get("warning_flags", []),
            "missing": question.get("missing", []),
        }
        for question in diagnostics.get("questions", [])
    ]
    return {
        "status": "baseline_available" if latest_annual else "missing_annual_report",
        "latest_annual_report": latest_annual,
        "baseline_rule": "Annual report / 10-K / 20-F is the baseline. Interim filings can confirm or change that baseline, but cannot replace it.",
        "diagnostic_questions": answered_questions,
    }


def _missing_facts(extraction_summary: dict[str, Any], metrics: list[dict[str, Any]]) -> dict[str, Any]:
    coverage = extraction_summary.get("coverage") or {}
    metric_missing = {}
    for metric in metrics:
        missing = []
        for row in metric.get("annual_results", []):
            missing.extend(row.get("missing", []))
        if metric.get("missing"):
            missing.extend(metric.get("missing", []))
        if missing:
            metric_missing[str(metric.get("formula_id"))] = sorted({str(item) for item in missing})
    return {
        "priority_a": (coverage.get("priority_a") or {}).get("missing", []),
        "priority_b": (coverage.get("priority_b") or {}).get("missing", []),
        "by_metric_family": metric_missing,
    }


def _human_review_flags(state: ResearchState) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    for flag in (state.get("extraction_summary") or {}).get("review_flags", []):
        flags.append({"source": "financial_extraction", **flag})
    for result in state.get("verification_results", []):
        if result.get("status") == "material_conflict":
            flags.append(
                {
                    "source": "financial_verification",
                    "flag_id": "official_fact_material_conflict",
                    "severity": "high",
                    "metric": result.get("metric"),
                    "period": result.get("end_date") or result.get("instant"),
                    "mismatch_pct": result.get("mismatch_pct"),
                }
            )
    for metric in state.get("metrics", []) + state.get("valuation_metrics", []):
        formula_id = metric.get("formula_id")
        for row in metric.get("annual_results", []):
            if row.get("review_required") or row.get("limitations") or row.get("assumption") or row.get("interpretation_limit"):
                flags.append(
                    {
                        "source": "financial_metrics",
                        "flag_id": "metric_review_required",
                        "severity": "medium",
                        "formula_id": formula_id,
                        "year": row.get("year"),
                        "assumption": row.get("assumption"),
                        "limitations": row.get("limitations", []),
                        "interpretation_limit": row.get("interpretation_limit"),
                    }
                )
    for event in (state.get("material_event_scan") or {}).get("events", []):
        if event.get("severity") == "high":
            flags.append(
                {
                    "source": "material_event_scan",
                    "flag_id": "high_priority_material_event",
                    "severity": "high",
                    "event_type": event.get("event_type"),
                    "document_id": event.get("document_id"),
                    "filing_date": event.get("filing_date"),
                }
            )
    return _dedupe_flags(flags)


def _dedupe_flags(flags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for flag in flags:
        key = (
            flag.get("source"),
            flag.get("flag_id"),
            flag.get("severity"),
            flag.get("metric"),
            flag.get("formula_id"),
            flag.get("event_type"),
            flag.get("period"),
            flag.get("year"),
            flag.get("document_id"),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(flag)
    return output


def _metric_by_id(metrics: list[dict[str, Any]], formula_id: str) -> dict[str, Any] | None:
    for metric in metrics:
        if metric.get("formula_id") == formula_id:
            return metric
    return None


def _latest_document(documents: list[dict[str, Any]], *, prefixes: tuple[str, ...]) -> dict[str, Any] | None:
    normalized_prefixes = tuple(prefix.upper() for prefix in prefixes)
    matches = []
    for document in documents:
        document_type = str(document.get("document_type", "")).upper()
        form = str(document.get("form", "")).upper()
        if document_type.startswith(normalized_prefixes) or form.startswith(normalized_prefixes):
            matches.append(document)
    if not matches:
        return None
    latest = sorted(matches, key=lambda document: document.get("filing_date") or "")[-1]
    return {
        "document_id": latest.get("document_id"),
        "document_type": latest.get("document_type"),
        "filing_date": latest.get("filing_date"),
        "report_date": latest.get("report_date"),
        "local_path": latest.get("local_path"),
        "source_url": latest.get("source_url"),
        "research_category": latest.get("research_category"),
    }
