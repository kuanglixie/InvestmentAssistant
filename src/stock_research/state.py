from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TypedDict


class ResearchState(TypedDict, total=False):
    run_id: str
    run_dir: str
    company_query: str
    canonical_company: dict[str, Any] | None
    market: str
    requested_years: str
    source_candidates: list[dict[str, Any]]
    approved_sources: list[dict[str, Any]]
    source_discovery: dict[str, Any]
    documents: list[dict[str, Any]]
    raw_extracted_facts: list[dict[str, Any]]
    extracted_facts: list[dict[str, Any]]
    extraction_summary: dict[str, Any]
    ir_cross_validation: dict[str, Any]
    verification_results: list[dict[str, Any]]
    market_inputs: dict[str, Any]
    metrics: list[dict[str, Any]]
    learning_context: dict[str, Any]
    business_model_findings: dict[str, Any]
    external_moat_findings: dict[str, Any]
    public_voice_findings: dict[str, Any]
    leadership_findings: dict[str, Any]
    executive_transcript_findings: dict[str, Any]
    official_event_transcript_findings: dict[str, Any]
    alternative_data_findings: dict[str, Any]
    video_manifest: dict[str, Any]
    video_manifest_path: str | None
    valuation_findings: dict[str, Any]
    customer_happiness_findings: dict[str, Any]
    competitor_findings: dict[str, Any]
    agent_reports: list[dict[str, Any]]
    final_report_path: str | None
    financial_results_report_path: str | None
    business_model_report_path: str | None
    data_linkage_report_path: str | None
    audit_events: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    human_review_required: bool
    graph_backend: str


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_initial_state(
    *,
    run_id: str,
    run_dir: str,
    company: str,
    market: str,
    requested_years: str = "all_available",
) -> ResearchState:
    return {
        "run_id": run_id,
        "run_dir": run_dir,
        "company_query": company,
        "canonical_company": None,
        "market": market,
        "requested_years": requested_years,
        "source_candidates": [],
        "approved_sources": [],
        "source_discovery": {},
        "documents": [],
        "raw_extracted_facts": [],
        "extracted_facts": [],
        "extraction_summary": {},
        "ir_cross_validation": {},
        "verification_results": [],
        "market_inputs": {},
        "metrics": [],
        "learning_context": {},
        "business_model_findings": {},
        "external_moat_findings": {},
        "public_voice_findings": {},
        "leadership_findings": {},
        "executive_transcript_findings": {},
        "official_event_transcript_findings": {},
        "alternative_data_findings": {},
        "video_manifest": {},
        "video_manifest_path": None,
        "valuation_findings": {},
        "customer_happiness_findings": {},
        "competitor_findings": {},
        "agent_reports": [],
        "final_report_path": None,
        "financial_results_report_path": None,
        "business_model_report_path": None,
        "data_linkage_report_path": None,
        "audit_events": [],
        "errors": [],
        "human_review_required": False,
        "graph_backend": "unknown",
    }
