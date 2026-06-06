from __future__ import annotations

import os
from typing import Any

from stock_research.alternative_data import collect_alternative_data_signals
from stock_research.companies import resolve_company_from_registry
from stock_research.diagnostics import run_v1_financial_diagnostics
from stock_research.extraction.ir_pdf import cross_validate_and_fill_from_ir_reports
from stock_research.extraction.xbrl import extract_financial_facts_from_documents, verify_financial_facts
from stock_research.evidence_communication import (
    build_evidence_communication_pack,
    build_evidence_communication_report,
)
from stock_research.feedback_loop import (
    apply_feedback_to_layer1_question_pack,
    build_feedback_loop_pack,
    build_feedback_loop_report,
)
from stock_research.learning.lessons import (
    DEFAULT_LESSON_REGISTRY,
    lesson_context_for_agent,
    lesson_status_counts,
    load_lesson_registry,
)
from stock_research.layer1_questions import build_layer1_question_pack
from stock_research.material_events import scan_material_events
from stock_research.management_communication import build_management_communication_pack
from stock_research.metrics.v1 import calculate_v1_financial_metrics, calculate_v1_valuation_metrics
from stock_research.official_evidence import (
    build_official_report_evidence_pack,
    build_official_report_evidence_report,
)
from stock_research.qualitative.annual_report import (
    BUSINESS_MODEL_TOPICS,
    LEADERSHIP_TOPICS,
    annual_report_topic_evidence,
    official_report_business_model_analysis,
)
from stock_research.qualitative.business_model_evidence import (
    build_business_model_evidence_pack,
    build_business_model_evidence_report,
    build_business_model_unit_economics_chinese_report,
    build_business_model_unit_economics_pack,
    build_business_model_unit_economics_report,
)
from stock_research.qualitative.business_model_sources import build_business_model_source_coverage
from stock_research.qualitative.business_model_subagents import build_business_model_subagent_cluster
from stock_research.qualitative.external_moat import build_external_moat_validation_plan
from stock_research.qualitative.executive_transcripts import collect_executive_video_transcripts
from stock_research.qualitative.official_events import collect_official_event_transcripts
from stock_research.qualitative.video_manifest import merge_video_manifests
from stock_research.qualitative.public_voice import collect_public_voice_evidence, synthesize_customer_happiness
from stock_research.qualitative.right_people import build_right_people_analysis
from stock_research.report_pack import build_financial_report_pack
from stock_research.research_workflow import build_research_workflow_artifacts
from stock_research.reports.markdown import (
    build_business_model_report,
    build_data_linkage_report,
    build_final_report,
    build_financial_results_report,
    build_right_people_chinese_report,
    build_right_people_report,
)
from stock_research.reports.financial_interpretation import build_financial_easy_reading_report
from stock_research.reports.financial_research_draft import build_financial_research_draft
from stock_research.reports.financial_visual import build_financial_visual_report
from stock_research.sources.discovery import discover_pdd_sources, discover_tencent_sources
from stock_research.sources.document_policy import classify_sec_document_record
from stock_research.state import ResearchState
from stock_research.storage import (
    complete_node,
    save_state,
    write_business_model_report,
    write_business_model_evidence_pack,
    write_business_model_evidence_report,
    write_business_model_unit_economics_chinese_report,
    write_business_model_unit_economics_pack,
    write_business_model_unit_economics_report,
    write_data_linkage_report,
    write_final_report,
    write_financial_easy_reading_report,
    write_evidence_communication_pack,
    write_evidence_communication_report,
    write_decision_question_pack,
    write_evidence_plan,
    write_evidence_registry,
    write_filing_deep_read_pack,
    write_feedback_loop_pack,
    write_feedback_loop_report,
    write_financial_report_pack,
    write_layer1_question_pack,
    write_financial_research_draft,
    write_financial_results_report,
    write_financial_visual_report,
    write_official_report_evidence_pack,
    write_official_report_evidence_report,
    write_management_communication_pack,
    write_pillar_judgment_stub,
    write_question_evidence_completion_pack,
    write_question_dossier_pack,
    write_qa_gap_triage,
    write_right_people_chinese_report,
    write_right_people_report,
    write_source_map,
    write_theme_workpaper_evidence_appendix,
    write_theme_workpaper_pack,
    write_theme_workpaper_report,
    write_video_manifest,
)
from stock_research.valuation.market_data import collect_market_inputs
from stock_research.valuation.market_inputs import load_manual_market_inputs


def company_resolver(state: ResearchState) -> ResearchState:
    company = resolve_company_from_registry(state["company_query"], market=state["market"])
    if company is None:
        company = {
            "company_id": state["company_query"].lower(),
            "legal_name": state["company_query"],
            "common_names": [state["company_query"]],
            "tickers": [{"symbol": state["company_query"], "market": state["market"]}],
            "market": state["market"],
            "listing_type": "unknown",
            "sec_cik": None,
            "primary_filing_systems": [],
            "investor_relations_url": None,
            "source_languages": ["English"],
            "source_pipeline_status": "unconfigured",
        }

    state["canonical_company"] = company
    body = "\n".join(
        [
            "Resolved the company identity package for downstream agents.",
            "",
            f"- Legal name: {company['legal_name']}",
            f"- Market: {company['market']}",
            f"- Listing type: {company['listing_type']}",
            f"- Filing systems: {', '.join(company['primary_filing_systems']) or 'not yet configured'}",
            f"- Source pipeline status: {company.get('source_pipeline_status', 'unknown')}",
            "",
            "Company identity comes from the local audited company registry.",
        ]
    )
    return complete_node(state, agent_id="company_resolver", title="Company Resolver", report_body=body)


def source_discovery(state: ResearchState) -> ResearchState:
    company_id = (state.get("canonical_company") or {}).get("company_id")
    if company_id == "pdd" and os.environ.get("STOCK_RESEARCH_OFFLINE") != "1":
        try:
            discovery = discover_pdd_sources(cache_root="data/raw", download_reports=True)
            state["source_discovery"] = discovery
            sec_identity = discovery["sec_identity"]
            if state.get("canonical_company"):
                state["canonical_company"]["sec_cik"] = sec_identity.get("cik")
                state["canonical_company"]["sec_cik_padded"] = sec_identity.get("cik_padded")
                state["canonical_company"]["sec_company_title"] = sec_identity.get("title")
            state["source_candidates"] = _source_candidates_from_discovery(discovery)
            state["approved_sources"] = [
                source for source in state["source_candidates"] if source["trust_tier"] == 1
            ]
            state["documents"] = [
                _document_record_from_download(document)
                for document in discovery.get("downloaded_documents", [])
            ]
            category_counts = discovery.get("downloaded_document_category_counts") or {}
            category_summary = ", ".join(
                f"{category}: {count}" for category, count in sorted(category_counts.items())
            )
            body = "\n".join(
                [
                    "Discovered official PDD sources using live SEC/PDD IR fetches.",
                    "",
                    f"- SEC CIK: {sec_identity.get('cik_padded')}",
                    f"- Total SEC filings indexed: {len(discovery.get('sec_filings', []))}",
                    f"- Financial-report filings identified: {len(discovery.get('financial_filings', []))}",
                    f"- Deep filing-stack filings identified: {len(discovery.get('deep_research_filings', []))}",
                    f"- Reports downloaded: {len(discovery.get('downloaded_documents', []))}",
                    f"- Downloaded document categories: {category_summary or 'none'}",
                    f"- Download errors: {len(discovery.get('download_errors', []))}",
                    f"- PDD IR home fetched: {'yes' if discovery.get('pdd_ir') else 'no'}",
                    f"- PDD IR fetch error: {discovery.get('pdd_ir_error') or 'none'}",
                    f"- Latest PDD IR financial release fetched: {'yes' if discovery.get('pdd_ir_latest_financial_release') else 'no'}",
                    f"- Latest PDD IR financial release error: {discovery.get('pdd_ir_latest_financial_release_error') or 'none'}",
                    "",
                    "Official filings and company IR remain the source of record.",
                ]
            )
            return complete_node(
                state,
                agent_id="source_discovery",
                title="Source Discovery Agent",
                report_body=body,
            )
        except Exception as exc:  # noqa: BLE001 - preserved as an auditable fallback.
            state.setdefault("errors", []).append(
                {
                    "agent_id": "source_discovery",
                    "error": str(exc),
                    "fallback": "placeholder_sources",
                }
            )
    if company_id == "tencent" and os.environ.get("STOCK_RESEARCH_OFFLINE") != "1":
        try:
            discovery = discover_tencent_sources(cache_root="data/raw", download_reports=True)
            state["source_discovery"] = discovery
            state["source_candidates"] = _source_candidates_from_tencent_discovery(discovery)
            state["approved_sources"] = [
                source for source in state["source_candidates"] if source["trust_tier"] == 1
            ]
            state["documents"] = discovery.get("downloaded_documents", [])
            body = "\n".join(
                [
                    "Discovered official Tencent sources using Tencent investor-relations financial reports.",
                    "",
                    f"- Financial reports indexed: {discovery.get('financial_reports_indexed', 0)}",
                    f"- Annual reports downloaded: {len(discovery.get('annual_reports', []))}",
                    f"- Interim reports downloaded: {len(discovery.get('interim_reports', []))}",
                    f"- Download errors: {len(discovery.get('download_errors', []))}",
                    f"- Tencent IR fetch error: {discovery.get('tencent_ir_error') or 'none'}",
                    "",
                    "Tencent IR reports are official company sources. HKEX cross-checking is planned as the next official-source layer.",
                ]
            )
            return complete_node(
                state,
                agent_id="source_discovery",
                title="Source Discovery Agent",
                report_body=body,
            )
        except Exception as exc:  # noqa: BLE001 - preserved as an auditable fallback.
            state.setdefault("errors", []).append(
                {
                    "agent_id": "source_discovery",
                    "error": str(exc),
                    "fallback": "placeholder_sources",
                }
            )

    state["source_candidates"] = _placeholder_sources_for_company(
        state.get("canonical_company") or {},
        fallback_query=state["company_query"],
    )
    state["approved_sources"] = [
        source for source in state["source_candidates"] if source["trust_tier"] == 1
    ]
    body = "\n".join(
        [
            "Created placeholder source candidates using the V1 source policy.",
            "",
            "- Tier 1 sources: official regulator/exchange filings and company investor relations when configured.",
            "- Tier 2 sources: third-party databases for sanity checks only.",
            "- No low-quality source is approved for financial numbers.",
            "- Live discovery was skipped or failed; check state.errors for details.",
        ]
    )
    return complete_node(state, agent_id="source_discovery", title="Source Discovery Agent", report_body=body)


def _placeholder_sources_for_company(company: dict, *, fallback_query: str) -> list[dict]:
    company_id = company.get("company_id") or fallback_query.lower()
    legal_name = company.get("legal_name") or fallback_query
    sources: list[dict] = []
    if company.get("sec_cik") or any("SEC" in system for system in company.get("primary_filing_systems", [])):
        sources.append(
            {
                "source_id": f"sec_edgar_{company_id}",
                "name": f"SEC EDGAR filings for {legal_name}",
                "type": "sec_filing",
                "trust_tier": 1,
                "status": "placeholder",
                "cik": company.get("sec_cik"),
                "cik_padded": company.get("sec_cik_padded"),
                "reason": "Official regulator filings should be source of record for financial numbers.",
            }
        )
    if any("HKEX" in system for system in company.get("primary_filing_systems", [])):
        sources.append(
            {
                "source_id": f"hkex_{company_id}",
                "name": f"HKEX disclosures for {legal_name}",
                "type": "hkex_disclosure",
                "trust_tier": 1,
                "status": "identity_only_v1",
                "reason": "Official exchange disclosures should be source of record for Hong Kong-listed companies.",
            }
        )
    if company.get("investor_relations_url"):
        sources.append(
            {
                "source_id": f"investor_relations_{company_id}",
                "name": f"{legal_name} investor relations",
                "type": "company_investor_relations",
                "trust_tier": 1,
                "url": company.get("investor_relations_url"),
                "status": "placeholder",
                "reason": "Official company reports and releases are primary sources.",
            }
        )
    sources.append(
        {
            "source_id": f"secondary_finance_sanity_check_{company_id}",
            "name": f"Free third-party financial database sanity checks for {legal_name}",
            "type": "reputable_free_financial_database",
            "trust_tier": 2,
            "status": "placeholder",
            "reason": "May flag mismatches, but cannot override official sources.",
        }
    )
    return sources


def document_acquisition(state: ResearchState) -> ResearchState:
    if state.get("documents"):
        downloaded = [doc for doc in state["documents"] if doc.get("local_path")]
        body = "\n".join(
            [
                "Using documents downloaded by the source discovery pipeline.",
                "",
                f"- Document records: {len(state['documents'])}",
                f"- Downloaded local files: {len(downloaded)}",
                "Raw files are cached under data/raw/.",
            ]
        )
        return complete_node(
            state,
            agent_id="document_acquisition",
            title="Document Acquisition Agent",
            report_body=body,
        )

    company = state.get("canonical_company") or {}
    state["documents"] = [
        {
            "document_id": f"{source.get('source_id')}_document_placeholder",
            "source_id": source.get("source_id"),
            "document_type": "official_financial_report_or_disclosure",
            "status": "not_downloaded_v1",
            "checksum": None,
        }
        for source in state.get("approved_sources", [])
        if source.get("type") in {"sec_filing", "hkex_disclosure", "company_investor_relations"}
    ]
    if not state["documents"]:
        state["documents"] = [
            {
                "document_id": f"{company.get('company_id', state['company_query'].lower())}_document_placeholder",
                "source_id": "unconfigured_official_source",
                "document_type": "official_financial_report_or_disclosure",
                "status": "not_downloaded_v1",
                "checksum": None,
            }
        ]
    body = "\n".join(
        [
            "Registered placeholder document records.",
            "",
            "Company-specific downloaders will cache and fingerprint official documents as they are implemented.",
            "The workflow intentionally avoids pretending that any missing filing was fetched.",
        ]
    )
    return complete_node(
        state,
        agent_id="document_acquisition",
        title="Document Acquisition Agent",
        report_body=body,
    )


def _source_candidates_from_discovery(discovery: dict) -> list[dict]:
    sec_identity = discovery["sec_identity"]
    candidates = [
        {
            "source_id": "sec_edgar_pdd",
            "name": f"SEC EDGAR filings for {sec_identity.get('title', 'PDD')}",
            "type": "sec_filing",
            "trust_tier": 1,
            "status": "live_indexed",
            "cik": sec_identity.get("cik"),
            "cik_padded": sec_identity.get("cik_padded"),
            "filings_indexed": len(discovery.get("sec_filings", [])),
            "financial_filings": len(discovery.get("financial_filings", [])),
            "reason": "Official regulator filings are source of record for financial numbers.",
        },
        {
            "source_id": "pdd_investor_relations",
            "name": "PDD Holdings investor relations",
            "type": "company_investor_relations",
            "trust_tier": 1,
            "url": "https://investor.pddholdings.com/",
            "status": "live_fetched" if discovery.get("pdd_ir") else "fetch_failed",
            "reason": "Official company reports and releases are primary sources.",
        },
        {
            "source_id": "secondary_finance_sanity_check",
            "name": "Free third-party financial database sanity checks",
            "type": "reputable_free_financial_database",
            "trust_tier": 2,
            "status": "not_used_phase_2",
            "reason": "May flag mismatches, but cannot override official sources.",
        },
    ]
    return candidates


def _source_candidates_from_tencent_discovery(discovery: dict) -> list[dict]:
    ir = discovery.get("tencent_ir") or {}
    candidates = [
        {
            "source_id": "tencent_investor_relations",
            "name": "Tencent investor relations financial reports",
            "type": "company_investor_relations",
            "trust_tier": 1,
            "url": ir.get("url") or "https://www.tencent.com/en-us/investors/financial-reports.html",
            "status": "live_indexed" if ir else "fetch_failed",
            "financial_reports_indexed": discovery.get("financial_reports_indexed", 0),
            "reason": "Official Tencent annual and interim reports are primary financial sources.",
        },
        {
            "source_id": "hkex_tencent",
            "name": "HKEX disclosures for Tencent Holdings Limited",
            "type": "hkex_disclosure",
            "trust_tier": 1,
            "status": "planned_cross_check",
            "reason": "HKEX disclosures should be used as the next official-source cross-check layer.",
        },
        {
            "source_id": "secondary_finance_sanity_check_tencent",
            "name": "Free third-party financial database sanity checks for Tencent",
            "type": "reputable_free_financial_database",
            "trust_tier": 2,
            "status": "not_used_v1",
            "reason": "May flag mismatches, but cannot override official sources.",
        },
    ]
    return candidates


def _document_record_from_download(document: dict) -> dict:
    downloaded_file = document.get("downloaded_file") or document.get("primary_document")
    role = document.get("document_role", "primary")
    source_id = document.get("source_id") or "sec_edgar_pdd"
    document_id = document.get("document_id") or f"{document.get('accession_number')}:{downloaded_file}"
    form = document.get("form")
    document_type = document.get("document_type") or f"{form}:{role}"
    record = {
        "document_id": document_id,
        "source_id": source_id,
        "document_type": document_type,
        "filing_date": document.get("filing_date"),
        "report_date": document.get("report_date"),
        "primary_document": document.get("primary_document"),
        "downloaded_file": downloaded_file,
        "primary_doc_description": document.get("primary_doc_description"),
        "source_url": document.get("archive_url"),
        "local_path": document.get("local_path"),
        "checksum": document.get("sha256"),
        "byte_length": document.get("byte_length"),
        "status": "downloaded",
    }
    classification = classify_sec_document_record({**document, **record})
    record.update(
        {
            "research_category": classification["category"],
            "research_decision": classification["decision"],
            "research_reason": classification["reason"],
        }
    )
    return record


def _topic_hit_summary(evidence: dict) -> str:
    if evidence.get("status") != "evidence_collected":
        return evidence.get("status", "not collected")
    topics = evidence.get("topics", {})
    if not topics:
        return "no topic hits"
    parts = [
        f"{topic}={details.get('total_hits', 0)}"
        for topic, details in sorted(topics.items())
    ]
    source = evidence.get("source_document", {})
    filing_date = source.get("filing_date", "unknown date")
    return f"{filing_date}; " + ", ".join(parts)


def financial_extraction(state: ResearchState) -> ResearchState:
    extraction = extract_financial_facts_from_documents(state.get("documents", []))
    state["raw_extracted_facts"] = extraction["raw_facts"]
    state["extracted_facts"] = extraction["selected_facts"]
    state["extraction_summary"] = extraction["summary"]
    counts_by_metric = extraction["summary"].get("counts_by_metric", {})
    top_counts = ", ".join(
        f"{metric}: {count}" for metric, count in sorted(counts_by_metric.items())[:12]
    )
    coverage = extraction["summary"].get("coverage", {})
    priority_a_missing = coverage.get("priority_a", {}).get("missing", [])
    question_coverage = coverage.get("question_coverage", [])
    question_status = ", ".join(
        f"{item.get('question_id')}: {item.get('status')}" for item in question_coverage[:5]
    )
    review_flags = extraction["summary"].get("review_flags", [])
    flag_summary = ", ".join(
        str(flag.get("flag_id")) for flag in review_flags[:5] if flag.get("flag_id")
    )
    body = "\n".join(
        [
            "Extracted mapped financial facts from locally cached official financial documents.",
            "",
            f"- Raw facts extracted: {len(state['raw_extracted_facts'])}",
            f"- Selected/deduplicated facts: {len(state['extracted_facts'])}",
            f"- Extraction errors: {len(extraction['summary'].get('extraction_errors', []))}",
            f"- Metric coverage: {top_counts or 'none'}",
            f"- Priority-A gaps: {', '.join(priority_a_missing) if priority_a_missing else 'none'}",
            f"- Question coverage: {question_status or 'none'}",
            f"- Review flags: {flag_summary or 'none'}",
            "",
            "The extractor uses mapped official-source tags or table labels only. Missing values stay missing; no financial number is invented.",
        ]
    )
    return complete_node(
        state,
        agent_id="financial_extraction",
        title="Financial Extraction Agent",
        report_body=body,
    )


def ir_pdf_cross_validation_agent(state: ResearchState) -> ResearchState:
    company_id = (state.get("canonical_company") or {}).get("company_id")
    if company_id == "tencent":
        result = _tencent_official_pdf_internal_cross_validation(state.get("raw_extracted_facts", []))
        state["ir_cross_validation"] = result
        material_conflicts = result.get("material_conflicts", [])
        if material_conflicts:
            state["human_review_required"] = True
        comparison_counts: dict[str, int] = {}
        for comparison in result.get("comparisons", []):
            status = comparison.get("status", "unknown")
            comparison_counts[status] = comparison_counts.get(status, 0) + 1
        body = "\n".join(
            [
                "Cross-checked Tencent's official PDF tables against other tables in the same official report.",
                "",
                f"- Status: {result.get('status')}",
                f"- Comparison groups: {len(result.get('comparisons', []))}",
                "- Comparison status counts: "
                + (", ".join(f"{status}: {count}" for status, count in sorted(comparison_counts.items())) or "none"),
                f"- Material internal official-source conflicts: {len(material_conflicts)}",
                "",
                "Tencent V1 now checks overlapping official PDF facts, such as annual financial-summary values versus audited statement-table values. HKEX remains the next independent official-source layer.",
            ]
        )
        return complete_node(
            state,
            agent_id="ir_pdf_cross_validation",
            title="IR PDF Cross-Validation Agent",
            report_body=body,
        )

    result = cross_validate_and_fill_from_ir_reports(
        company=state.get("canonical_company") or {},
        documents=state.get("documents", []),
        extracted_facts=state.get("extracted_facts", []),
    )
    updated_facts = result.pop("updated_facts", state.get("extracted_facts", []))
    state["extracted_facts"] = updated_facts
    state["ir_cross_validation"] = result
    material_conflicts = result.get("material_conflicts", [])
    if material_conflicts:
        state["human_review_required"] = True

    comparison_counts: dict[str, int] = {}
    for comparison in result.get("comparisons", []):
        status = comparison.get("status", "unknown")
        comparison_counts[status] = comparison_counts.get(status, 0) + 1
    source_attempts = result.get("source_attempts", [])
    source_lines = [
        f"- {attempt.get('fiscal_year')}: {attempt.get('status')} | {attempt.get('pdf_error') or 'no PDF error'}"
        for attempt in source_attempts
    ]
    body = "\n".join(
        [
            "Cross-checked SEC extracted facts against configured official IR annual-report PDFs.",
            "",
            f"- Status: {result.get('status')}",
            f"- Source attempts: {len(source_attempts)}",
            *source_lines,
            "- Comparison status counts: "
            + (", ".join(f"{status}: {count}" for status, count in sorted(comparison_counts.items())) or "none"),
            f"- Missing facts filled from official annual-report text: {len(result.get('filled_facts', []))}",
            f"- Material IR/SEC conflicts: {len(material_conflicts)}",
            "",
            "If an IR PDF cannot be downloaded or parsed locally, the agent falls back to the cached SEC HTML copy of the same official 20-F filing and records that fallback.",
        ]
    )
    return complete_node(
        state,
        agent_id="ir_pdf_cross_validation",
        title="IR PDF Cross-Validation Agent",
        report_body=body,
    )


def _tencent_official_pdf_internal_cross_validation(raw_facts: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for fact in raw_facts:
        if fact.get("source_id") != "tencent_investor_relations":
            continue
        key = (
            fact.get("metric"),
            fact.get("unit"),
            fact.get("period_type"),
            fact.get("start_date"),
            fact.get("end_date"),
            fact.get("instant"),
        )
        grouped.setdefault(key, []).append(fact)

    comparisons = []
    material_conflicts = []
    for key, facts in sorted(grouped.items(), key=lambda item: str(item[0])):
        methods = sorted({str(fact.get("extraction_method")) for fact in facts if fact.get("extraction_method")})
        if len(methods) <= 1:
            continue
        values = [float(fact["value"]) for fact in facts if fact.get("value") is not None]
        if not values:
            continue
        low = min(values)
        high = max(values)
        mismatch_pct = abs(high - low) / max(abs(high), abs(low), 1.0)
        status = "matched" if mismatch_pct <= 0.02 else "material_conflict"
        comparison = {
            "status": status,
            "metric": key[0],
            "unit": key[1],
            "period_type": key[2],
            "start_date": key[3],
            "end_date": key[4],
            "instant": key[5],
            "mismatch_pct": mismatch_pct,
            "min_value": low,
            "max_value": high,
            "methods": methods,
            "source_documents": sorted({str(fact.get("document_id")) for fact in facts if fact.get("document_id")}),
        }
        comparisons.append(comparison)
        if status == "material_conflict":
            material_conflicts.append(comparison)

    return {
        "status": "tencent_official_pdf_internal_cross_check",
        "comparisons": comparisons,
        "filled_facts": [],
        "source_attempts": [],
        "material_conflicts": material_conflicts,
        "notes": [
            "This is not yet HKEX cross-validation.",
            "It checks overlapping values inside Tencent official IR PDFs, such as five-year summary tables versus audited statement tables.",
        ],
    }


def financial_verification(state: ResearchState) -> ResearchState:
    state["verification_results"] = verify_financial_facts(state.get("raw_extracted_facts", []))
    material_conflicts = [
        result for result in state["verification_results"] if result.get("status") == "material_conflict"
    ]
    if material_conflicts:
        state["human_review_required"] = True
    body = "\n".join(
        [
            "Checked duplicate official filing facts against the V1 materiality rule.",
            "",
            f"- Verification records: {len(state['verification_results'])}",
            f"- Material conflicts over 2%: {len(material_conflicts)}",
            "- Rounding differences at or below 2% are accepted and logged.",
            "- Third-party full financial-statement sanity checks are still pending; market quotes already use separate source cross-checks where available.",
        ]
    )
    return complete_node(
        state,
        agent_id="financial_verification",
        title="Financial Verification Agent",
        report_body=body,
    )


def market_data_agent(state: ResearchState) -> ResearchState:
    state["market_inputs"] = collect_market_inputs(
        company=state.get("canonical_company") or {},
        documents=state.get("documents", []),
    )
    validation = state["market_inputs"].get("validation") or {}
    conflicts = validation.get("conflicts", [])
    if conflicts:
        state["human_review_required"] = True
    inputs = state["market_inputs"].get("inputs") or {}
    body = "\n".join(
        [
            "Collected V1 market data for yield valuation.",
            "",
            f"- Status: {state['market_inputs'].get('status')}",
            f"- Collection method: {state['market_inputs'].get('collection_method')}",
            f"- Input required: {state['market_inputs'].get('input_required')}",
            f"- Review required: {state['market_inputs'].get('review_required')}",
            f"- Market cap source: {inputs.get('source', 'not available')}",
            f"- FX source: {inputs.get('fx_source', 'not available')}",
            f"- Validation conflicts: {len(conflicts)}",
            "- Market cap is calculated from quote price and official share structure when possible.",
        ]
    )
    return complete_node(state, agent_id="market_data", title="Market Data Agent", report_body=body)


def metrics_agent(state: ResearchState) -> ResearchState:
    state["metrics"] = calculate_v1_financial_metrics(state.get("extracted_facts", []))
    calculated = [
        metric for metric in state["metrics"] if metric.get("status") == "calculated"
    ]
    pending = [
        metric for metric in state["metrics"] if metric.get("status") != "calculated"
    ]
    body = "\n".join(
        [
            "Calculated V1 financial-quality metrics where the verified fact set was sufficient.",
            "",
            f"- Metric families calculated: {len(calculated)}",
            f"- Metric families pending: {len(pending)}",
            "- Owner earnings is labelled as a proxy; V1 uses D&A as the maintenance CapEx approximation.",
            "- Enterprise value, yield, and estimated-return style metrics now belong to the Valuation Agent.",
            "- ROIC is calculated as a financing-side invested-capital proxy without applying a threshold.",
            "- Formula changes still require human approval.",
        ]
    )
    return complete_node(state, agent_id="metrics", title="Metrics Agent", report_body=body)


def diagnostic_rules_agent(state: ResearchState) -> ResearchState:
    findings = run_v1_financial_diagnostics(
        extracted_facts=state.get("extracted_facts", []),
        metrics=state.get("metrics", []),
    )
    state["diagnostic_findings"] = findings
    summary = findings.get("summary", {})
    body = "\n".join(
        [
            "Applied deterministic financial diagnostic rules to the calculated metric families.",
            "",
            f"- Status: {findings.get('status')}",
            f"- Questions answered: {summary.get('answered', 0)}",
            f"- Questions partial: {summary.get('partial', 0)}",
            f"- Questions missing: {summary.get('missing', 0)}",
            f"- Warning flags: {summary.get('warning_flags', 0)}",
            "- Diagnostics ask what to verify; Metrics calculate the underlying numbers.",
        ]
    )
    return complete_node(state, agent_id="diagnostic_rules", title="Diagnostic Rules Agent", report_body=body)


def material_event_scan_agent(state: ResearchState) -> ResearchState:
    scan = scan_material_events(state.get("documents", []))
    state["material_event_scan"] = scan
    if scan.get("high_priority_event_count", 0):
        state["human_review_required"] = True
    sample_lines = [
        f"- {event.get('filing_date') or 'no date'} | {event.get('event_type')} | {event.get('severity')} | {event.get('document_id')}"
        for event in scan.get("events", [])[:6]
    ]
    body = "\n".join(
        [
            "Scanned official non-core filings for material events without turning every filing into a research section.",
            "",
            f"- Status: {scan.get('status')}",
            f"- Documents scanned: {scan.get('scanned_document_count', 0)}",
            f"- Material events found: {scan.get('material_event_count', 0)}",
            f"- High-priority events: {scan.get('high_priority_event_count', 0)}",
            "- Event samples:",
            *(sample_lines or ["- none"]),
            "",
            "Only accounting reliability, auditor, financing, governance/control, management, dilution, capital allocation, legal/regulatory, acquisition, impairment, and restructuring signals are promoted.",
        ]
    )
    return complete_node(
        state,
        agent_id="material_event_scan",
        title="Material Event Scanner",
        report_body=body,
    )


def financial_report_pack_agent(state: ResearchState) -> ResearchState:
    state["financial_report_pack"] = build_financial_report_pack(state)
    write_financial_report_pack(state)
    pack = state["financial_report_pack"]
    review_flags = pack.get("human_review_flags", [])
    body = "\n".join(
        [
            "Built the structured FinancialReportPack for source-constrained report writing.",
            "",
            f"- Schema version: {pack.get('schema_version')}",
            f"- Annual fact rows: {len(pack.get('annual_facts', []))}",
            f"- Quarterly fact rows: {len(pack.get('quarterly_facts', []))}",
            f"- Financial metric families: {len(pack.get('financial_metrics', []))}",
            f"- Material events: {(pack.get('material_event_scan') or {}).get('material_event_count', 0)}",
            f"- Human review flags: {len(review_flags)}",
            f"- Pack path: `{state.get('financial_report_pack_path')}`",
            "",
            "The interpretation layer may summarize this pack but must not recalculate numbers or add facts outside the pack.",
        ]
    )
    return complete_node(
        state,
        agent_id="financial_report_pack",
        title="Financial Report Pack Builder",
        report_body=body,
    )


def layer1_question_pack_agent(state: ResearchState) -> ResearchState:
    pack = build_layer1_question_pack(state)
    state["layer1_question_pack"] = pack
    write_layer1_question_pack(state)
    if state.get("financial_report_pack") is not None:
        state["financial_report_pack"]["layer1_question_pack_summary"] = pack.get("summary") or {}
        state["financial_report_pack"]["layer1_question_pack_path"] = state.get("layer1_question_pack_path")
        write_financial_report_pack(state)
    summary = pack.get("summary") or {}
    body = "\n".join(
        [
            "Built the Layer-1 Question Pack from deterministic financial numbers and diagnostic rules.",
            "",
            f"- Schema version: {pack.get('schema_version')}",
            f"- Standard questions: {summary.get('standard_question_count', 0)}",
            f"- Research questions: {summary.get('research_question_count', 0)}",
            f"- Numeric anomalies: {summary.get('numeric_anomaly_count', 0)}",
            f"- Disclosure gaps: {summary.get('disclosure_gap_count', 0)}",
            f"- Financial extractor handoffs: {summary.get('financial_extractor_handoff_count', 0)}",
            f"- Pack path: `{state.get('layer1_question_pack_path')}`",
            "",
            "This pack owns the hard-number questions. It does not read MD&A, footnotes, transcripts, or management narrative.",
        ]
    )
    return complete_node(
        state,
        agent_id="layer1_question_pack",
        title="Layer-1 Question Pack Agent",
        report_body=body,
    )


def official_report_evidence_agent(state: ResearchState) -> ResearchState:
    pack = build_official_report_evidence_pack(state)
    state["official_report_evidence_pack"] = pack
    write_official_report_evidence_pack(state)
    report = build_official_report_evidence_report(pack)
    write_official_report_evidence_report(state, report)
    body = "\n".join(
        [
            "Built the filings-only Official Report Evidence package.",
            "",
            f"- Schema version: {pack.get('schema_version')}",
            f"- Question answers: {len(pack.get('question_answers', []))}",
            f"- Decision-relevant narratives: {len(pack.get('decision_relevant_narratives', []))}",
            f"- Pack path: `{state.get('official_report_evidence_pack_path')}`",
            f"- Report path: `{state.get('official_report_evidence_report_path')}`",
            "",
            "This layer separates filing facts, management explanations, our inference, and unknowns. It does not use earnings-call transcripts or third-party data.",
        ]
    )
    return complete_node(
        state,
        agent_id="official_report_evidence",
        title="Official Report Evidence Agent",
        report_body=body,
    )


def evidence_communication_agent(state: ResearchState) -> ResearchState:
    if not state.get("official_report_evidence_pack"):
        official_pack = build_official_report_evidence_pack(state)
        state["official_report_evidence_pack"] = official_pack
        write_official_report_evidence_pack(state)
        official_report = build_official_report_evidence_report(official_pack)
        write_official_report_evidence_report(state, official_report)
    if not state.get("management_communication_pack"):
        state["management_communication_pack"] = build_management_communication_pack(state)
        write_management_communication_pack(state)

    pack = build_evidence_communication_pack(state)
    state["evidence_communication_pack"] = pack
    write_evidence_communication_pack(state)
    report = build_evidence_communication_report(pack)
    write_evidence_communication_report(state, report)
    if state.get("financial_report_pack") is not None:
        state["financial_report_pack"]["official_report_evidence_pack_path"] = state.get(
            "official_report_evidence_pack_path"
        )
        state["financial_report_pack"]["management_communication_pack_path"] = state.get(
            "management_communication_pack_path"
        )
        state["financial_report_pack"]["evidence_communication_pack_summary"] = pack.get("summary") or {}
        state["financial_report_pack"]["evidence_communication_pack_path"] = state.get(
            "evidence_communication_pack_path"
        )
        write_financial_report_pack(state)

    summary = pack.get("summary") or {}
    body = "\n".join(
        [
            "Built the unified Evidence & Communication Pack.",
            "",
            f"- Schema version: {pack.get('schema_version')}",
            f"- Question answers: {summary.get('question_answer_count', 0)}",
            f"- Proactive discoveries: {summary.get('proactive_discovery_count', 0)}",
            f"- Narrative records: {summary.get('narrative_count', 0)}",
            f"- Analyst concerns: {summary.get('analyst_concern_count', 0)}",
            f"- Financial extractor handoffs: {summary.get('financial_extractor_handoff_count', 0)}",
            f"- Pack path: `{state.get('evidence_communication_pack_path')}`",
            f"- Report path: `{state.get('evidence_communication_report_path')}`",
            "",
            "This node is now the main non-numeric evidence layer. The old official/management split packs remain as transitional source packs.",
        ]
    )
    return complete_node(
        state,
        agent_id="evidence_communication",
        title="Evidence & Communication Extraction Agent",
        report_body=body,
    )


def feedback_loop_agent(state: ResearchState) -> ResearchState:
    pack = build_feedback_loop_pack(state)
    state["feedback_loop_pack"] = pack
    write_feedback_loop_pack(state)
    pack.setdefault("source_artifacts", {})["feedback_loop_pack_path"] = state.get("feedback_loop_pack_path")
    write_feedback_loop_pack(state)

    state["layer1_question_pack"] = apply_feedback_to_layer1_question_pack(
        state.get("layer1_question_pack", {}),
        pack,
    )
    write_layer1_question_pack(state)

    report = build_feedback_loop_report(pack)
    write_feedback_loop_report(state, report)

    if state.get("financial_report_pack") is not None:
        state["financial_report_pack"]["layer1_question_pack_summary"] = (
            state.get("layer1_question_pack") or {}
        ).get("summary", {})
        state["financial_report_pack"]["layer1_question_pack_path"] = state.get("layer1_question_pack_path")
        state["financial_report_pack"]["feedback_loop_pack_summary"] = pack.get("summary") or {}
        state["financial_report_pack"]["feedback_loop_pack_path"] = state.get("feedback_loop_pack_path")
        write_financial_report_pack(state)

    summary = pack.get("summary") or {}
    body = "\n".join(
        [
            "Built the Feedback Loop Router pack.",
            "",
            f"- Schema version: {pack.get('schema_version')}",
            f"- Closed-loop status: {pack.get('closed_loop_status')}",
            f"- Financial extractor requests: {summary.get('financial_extractor_request_count', 0)}",
            f"- Metric recalculation requests: {summary.get('metric_recalculation_request_count', 0)}",
            f"- Layer-1 requery requests: {summary.get('layer1_requery_request_count', 0)}",
            f"- Evidence/communication follow-ups: {summary.get('evidence_communication_followup_count', 0)}",
            f"- Pack path: `{state.get('feedback_loop_pack_path')}`",
            f"- Report path: `{state.get('feedback_loop_report_path')}`",
            "",
            "This node closes the loop: new evidence-layer questions are routed back to extraction, metrics, Layer 1, or further evidence reading instead of staying as prose only.",
        ]
    )
    return complete_node(
        state,
        agent_id="feedback_loop",
        title="Feedback Loop Router",
        report_body=body,
    )


def business_model_evidence_agent(state: ResearchState) -> ResearchState:
    pack = build_business_model_evidence_pack(state)
    state["business_model_evidence_pack"] = pack
    write_business_model_evidence_pack(state)
    report = build_business_model_evidence_report(pack)
    write_business_model_evidence_report(state, report)

    unit_pack = build_business_model_unit_economics_pack(state, pack)
    state["business_model_unit_economics_pack"] = unit_pack
    write_business_model_unit_economics_pack(state)
    unit_report = build_business_model_unit_economics_report(unit_pack)
    write_business_model_unit_economics_report(state, unit_report)
    unit_chinese_report = build_business_model_unit_economics_chinese_report(unit_pack)
    write_business_model_unit_economics_chinese_report(state, unit_chinese_report)

    confidence_counts = {}
    for question in pack.get("questions", []):
        confidence = str(question.get("confidence") or "unknown")
        confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1
    body = "\n".join(
        [
            "Built the fixed-question Business Model Evidence Agent output.",
            "",
            f"- Agent version: {pack.get('version')}",
            f"- Questions answered: {len(pack.get('questions', []))}",
            f"- Business model quality: {(pack.get('summary') or {}).get('business_model_quality')}",
            f"- Confidence mix: {', '.join(f'{key}: {value}' for key, value in sorted(confidence_counts.items())) or 'none'}",
            f"- Evidence pack path: `{state.get('business_model_evidence_pack_path')}`",
            f"- Evidence report path: `{state.get('business_model_evidence_report_path')}`",
            f"- BMUE workpaper questions: {len(unit_pack.get('question_answers', []))}",
            f"- BMUE pack path: `{state.get('business_model_unit_economics_pack_path')}`",
            f"- BMUE report path: `{state.get('business_model_unit_economics_report_path')}`",
            f"- BMUE Chinese report path: `{state.get('business_model_unit_economics_chinese_report_path')}`",
            "- Scope: Q1-Q9 business-model evidence, financial cross-checks, fragility points, and downstream-agent questions.",
            "- New workpaper scope: BMQ-01-BMQ-18 business model and unit-economics evidence pack.",
            "- This agent does not produce Buy / Sell / Hold.",
        ]
    )
    return complete_node(
        state,
        agent_id="business_model_evidence",
        title="Business Model Evidence Agent",
        report_body=body,
    )


def alternative_data_agent(state: ResearchState) -> ResearchState:
    findings = collect_alternative_data_signals(state)
    state["alternative_data_findings"] = findings
    connector_status = findings.get("connector_status", {})
    ready = [
        connector_id
        for connector_id, status in connector_status.items()
        if status.get("status") == "collected_from_seed_observations"
    ]
    pending = [
        connector_id
        for connector_id, status in connector_status.items()
        if status.get("status") != "collected_from_seed_observations"
    ]
    body = "\n".join(
        [
            "Built the Alternative Data Agent signal pack.",
            "",
            "- Responsibility: collect and normalize non-financial-report signals only.",
            "- Excluded: buy/sell recommendation, moat judgment, sentiment interpretation, and valuation.",
            f"- Status: {findings.get('status')}",
            f"- Region / window: {findings.get('region')} / {findings.get('time_window')}",
            f"- Raw observations: {findings.get('raw_observation_count', 0)}",
            f"- Normalized metrics: {findings.get('normalized_metric_count', 0)}",
            f"- Text events for sentiment agent: {findings.get('text_event_count', 0)}",
            f"- Metric summaries: {findings.get('metric_summary_count', 0)}",
            f"- Connectors with data: {', '.join(ready) or 'none yet'}",
            f"- Connectors pending live/cached inputs: {', '.join(pending) or 'none'}",
            f"- Raw store: {findings.get('raw_observation_store_path')}",
            f"- Metric store: {findings.get('metric_store_path')}",
            f"- Text-event store: {findings.get('text_event_store_path')}",
        ]
    )
    return complete_node(
        state,
        agent_id="alternative_data",
        title="Alternative Data Agent",
        report_body=body,
    )


def learning_materials_agent(state: ResearchState) -> ResearchState:
    registry = load_lesson_registry()
    counts = lesson_status_counts(registry)
    source_materials = registry.get("source_materials", [])
    state["learning_context"] = {
        "registry_path": str(DEFAULT_LESSON_REGISTRY),
        "source_materials": source_materials,
        "status_counts": counts,
        "activation_rule": registry.get("activation_policy", {}).get("behavior_rule"),
    }
    body = "\n".join(
        [
            "Loaded the candidate lesson registry extracted from the user's Drive notes.",
            "",
            f"- Registry: {DEFAULT_LESSON_REGISTRY}",
            f"- Source materials: {len(source_materials)}",
            "- Lesson statuses: "
            + (", ".join(f"{status}: {count}" for status, count in counts.items()) or "none"),
            "- No lesson was activated automatically.",
            "- Candidate lessons can inform future review, but only approved lessons may change agent behavior.",
        ]
    )
    return complete_node(
        state,
        agent_id="learning_materials",
        title="Learning Materials Agent",
        report_body=body,
    )


def business_model_moat_agent(state: ResearchState) -> ResearchState:
    learning = lesson_context_for_agent("business_model_moat")
    company = state.get("canonical_company") or {}
    annual_report_evidence = annual_report_topic_evidence(
        state.get("documents", []),
        topic_terms=BUSINESS_MODEL_TOPICS,
    )
    official_report_analysis = official_report_business_model_analysis(
        company=company,
        documents=state.get("documents", []),
        extracted_facts=state.get("extracted_facts", []),
        metrics=state.get("metrics", []),
        raw_extracted_facts=state.get("raw_extracted_facts", []),
    )
    source_coverage = build_business_model_source_coverage(company=company)
    state["business_model_findings"] = {
        "status": official_report_analysis.get("status")
        if official_report_analysis.get("status") != "missing_official_annual_report"
        else "scaffolded_pending_qualitative_research",
        "principle": "right business model",
        "learning_context": learning,
        "source_coverage": source_coverage,
        "annual_report_evidence": annual_report_evidence,
        "official_report_analysis": official_report_analysis,
        "subagent_reports": official_report_analysis.get("subagent_reports", []),
        "right_business_model_checklist": official_report_analysis.get("right_business_model_checklist", []),
        "missing_evidence": official_report_analysis.get("missing_evidence", []),
        "conclusion_limit": official_report_analysis.get("conclusion_limit"),
        "prepared_financial_signals": [
            "revenue growth history",
            "gross profit history",
            "cash conversion",
            "unlevered ROIC",
        ],
        "evidence_needed": [
            "business model description from annual reports",
            "unit economics and take-rate drivers",
            "network effects or scale advantages",
            "competitive threats and regulation",
        ],
    }
    subagent_lines = [
        f"- {report.get('name')}: {report.get('status')}"
        for report in state["business_model_findings"].get("subagent_reports", [])
    ]
    dossier = official_report_analysis.get("official_report_dossier") or {}
    dossier_counts = dossier.get("status_counts") or {}
    dossier_line = (
        f"- Official report dossier fields: {dossier.get('field_count', 0)}"
        + (
            " ("
            + ", ".join(f"{status}: {count}" for status, count in sorted(dossier_counts.items()))
            + ")"
            if dossier_counts
            else ""
        )
    )
    operating_kpi_analysis = official_report_analysis.get("operating_kpi_analysis") or {}
    operating_kpi_line = (
        f"- Operating KPI records: {operating_kpi_analysis.get('record_count', 0)} numeric; "
        f"{len(operating_kpi_analysis.get('defined_only_markers', []))} defined-only markers."
    )
    management_framing_analysis = official_report_analysis.get("management_framing_analysis") or {}
    management_framing_line = (
        f"- Management framing themes: {management_framing_analysis.get('theme_count', 0)} source-linked themes."
    )
    checklist_lines = [
        f"- {item.get('item')}: {item.get('status')}"
        for item in state["business_model_findings"].get("right_business_model_checklist", [])
    ]
    source_gap_lines = [
        "- {group_id}: {priority} | {status} | {count} targets".format(
            group_id=gap.get("group_id"),
            priority=gap.get("priority"),
            status=gap.get("status"),
            count=gap.get("source_target_count", 0),
        )
        for gap in source_coverage.get("top_connected_gaps", [])
    ]
    body = "\n".join(
        [
            "Ran the official-report-only Business Model / Moat Agent.",
            "",
            f"- Status: {state['business_model_findings']['status']}.",
            "- Input scope: official reports, MD&A/business overview/segment/revenue/risk notes, and extracted financial metrics.",
            f"- Business-model source registry: {source_coverage.get('registry_path')}",
            (
                f"- Business-model source groups: {source_coverage.get('source_group_count', 0)}; "
                f"targets: {source_coverage.get('source_target_count', 0)}"
            ),
            f"- Annual-report evidence: {_topic_hit_summary(annual_report_evidence)}",
            dossier_line,
            operating_kpi_line,
            management_framing_line,
            "- Connected source gaps:",
            *(source_gap_lines or ["- not configured"]),
            "- Subagents:",
            *(subagent_lines or ["- none"]),
            "- Right business model checklist:",
            *(checklist_lines or ["- not available"]),
            f"- Candidate lessons available: {len(learning['candidate_lessons'])}; approved lessons active: {len(learning['approved_lessons'])}.",
            "- Conclusion limit: official reports can support a moat hypothesis, but external validation is still required.",
        ]
    )
    return complete_node(
        state,
        agent_id="business_model_moat",
        title="Business Model / Moat Agent",
        report_body=body,
    )


def external_moat_validation_agent(state: ResearchState) -> ResearchState:
    plan = build_external_moat_validation_plan(
        company=state.get("canonical_company") or {},
        business_model_findings=state.get("business_model_findings", {}),
    )
    state["external_moat_findings"] = plan
    source_lines = plan.get("source_lines", [])
    review_count = plan.get("review_needed_decision_count", 0)
    status_counts = plan.get("status_counts", {})
    tier_counts = plan.get("tier_counts", {})
    collector_groups = plan.get("collector_groups", [])
    collector_status_counts = plan.get("collector_status_counts", {})
    body = "\n".join(
        [
            "Built the external moat validation source prototype.",
            "",
            f"- Status: {plan.get('status')}.",
            f"- Scope: {plan.get('scope')}",
            f"- Hypotheses to test: {len(plan.get('hypotheses', []))}",
            f"- Source lines: {len(source_lines)}",
            f"- Controlled collector groups: {len(collector_groups)}",
            "- Collector statuses: "
            + (", ".join(f"{status}: {count}" for status, count in sorted(collector_status_counts.items())) or "none"),
            "- Source-line statuses: "
            + (", ".join(f"{status}: {count}" for status, count in sorted(status_counts.items())) or "none"),
            "- Quality-tier coverage: "
            + (", ".join(f"tier {tier}: {count}" for tier, count in sorted(tier_counts.items())) or "none"),
            f"- Decisions recorded for user review: {review_count}",
            "- External source plan is collection-ready but has not produced moat conclusions.",
            "- No external source is allowed to override official financial numbers.",
        ]
    )
    return complete_node(
        state,
        agent_id="external_moat_validation",
        title="External Moat Validation Source Agent",
        report_body=body,
    )


def public_voice_evidence_agent(state: ResearchState) -> ResearchState:
    findings = collect_public_voice_evidence(
        company=state.get("canonical_company") or {},
        offline=os.environ.get("STOCK_RESEARCH_OFFLINE") == "1",
    )
    state["public_voice_findings"] = findings
    theme_counts = (findings.get("theme_summary") or {}).get("counts") or {}
    source_results = findings.get("source_results", [])
    collected_sources = [
        result for result in source_results if result.get("status") == "comments_collected"
    ]
    body = "\n".join(
        [
            "Ran the Public Voice Evidence Agent.",
            "",
            f"- Status: {findings.get('status')}.",
            f"- Source registry: {findings.get('registry_path')}",
            f"- Sources registered: {findings.get('source_count', 0)}",
            f"- Collectable adapters in V1: {findings.get('collectable_source_count', 0)}",
            f"- Manual/source-specific adapters pending: {findings.get('manual_or_blocked_source_count', 0)}",
            f"- Evidence items collected: {findings.get('evidence_item_count', 0)}",
            "- Collection breadth: "
            + _public_voice_collection_breadth(findings.get("collection_stats") or {}),
            f"- Sources with comments collected: {len(collected_sources)}",
            "- Theme counts: "
            + (", ".join(f"{theme}: {count}" for theme, count in sorted(theme_counts.items())) or "none"),
            "- Forum/comment evidence is Tier 3/Tier 4 lead evidence only and cannot prove a moat by itself.",
        ]
    )
    return complete_node(
        state,
        agent_id="public_voice_evidence",
        title="Public Voice Evidence Agent",
        report_body=body,
    )


def _public_voice_collection_breadth(stats: dict[str, Any]) -> str:
    if not stats:
        return "not available"
    return (
        f"{stats.get('searches_attempted', 0)} searches, "
        f"{stats.get('posts_collected', 0)} pages/posts fetched, "
        f"{stats.get('comments_seen_before_filter', 0)} public-voice items scanned, "
        f"{stats.get('comments_collected', 0)} items kept"
    )


def leadership_people_agent(state: ResearchState) -> ResearchState:
    findings = build_right_people_analysis(state)
    findings["learning_context"] = lesson_context_for_agent("leadership_people")
    state["leadership_findings"] = findings
    subagent_lines = [
        "- {name}: {status} | {records} evidence records".format(
            name=report.get("name") or report.get("agent_id"),
            status=report.get("status"),
            records=report.get("evidence_records", 0),
        )
        for report in findings.get("subagent_reports", [])
    ]
    checklist_lines = [
        f"- {item.get('item')}: {item.get('status')}"
        for item in findings.get("right_people_checklist", [])
    ]
    coverage = findings.get("source_coverage") or {}
    body = "\n".join(
        [
            "Ran the Right People / Management Quality Agent.",
            "",
            f"- Status: {findings.get('status')}.",
            f"- Current read: {findings.get('overall_read')}",
            f"- Official filing cards: {coverage.get('official_filing_evidence_cards', 0)}",
            f"- Financial signals: {coverage.get('financial_signal_count', 0)}",
            f"- Management transcript signals: {coverage.get('management_transcript_signal_count', 0)}",
            f"- Red flags: {coverage.get('red_flag_count', 0)}",
            "- Subagents:",
            *(subagent_lines or ["- none"]),
            "- Right people checklist:",
            *(checklist_lines or ["- not available"]),
            f"- Candidate lessons available: {len(findings['learning_context']['candidate_lessons'])}; approved lessons active: {len(findings['learning_context']['approved_lessons'])}.",
            "- V1 is evidence-mapping and review-oriented; it does not infer personal integrity beyond source-backed signals.",
        ]
    )
    return complete_node(
        state,
        agent_id="leadership_people",
        title="Leadership / People Agent",
        report_body=body,
    )


def executive_transcript_agent(state: ResearchState) -> ResearchState:
    findings = collect_executive_video_transcripts(
        company=state.get("canonical_company") or {},
        offline=os.environ.get("STOCK_RESEARCH_OFFLINE") == "1",
    )
    state["executive_transcript_findings"] = findings
    state["video_manifest"] = merge_video_manifests(state.get("video_manifest"), findings.get("video_manifest"))
    write_video_manifest(state)
    status_counts = findings.get("source_status_counts") or {}
    source_lines = [
        "- {name}: {status} | {segments} transcript segments | {items} evidence items".format(
            name=result.get("name") or result.get("source_id"),
            status=result.get("status"),
            segments=result.get("transcript_segment_count", 0),
            items=len(result.get("evidence_items", [])),
        )
        for result in findings.get("source_results", [])
    ]
    body = "\n".join(
        [
            "Ran the Executive Video Transcript Agent.",
            "",
            f"- Status: {findings.get('status')}.",
            f"- Source registry: {findings.get('registry_path')}",
            f"- Sources registered: {findings.get('source_count', 0)}",
            f"- Collectable adapters in V1: {findings.get('collectable_source_count', 0)}",
            f"- Transcript sources collected: {findings.get('transcript_source_count', 0)}",
            f"- Transcript segments collected: {findings.get('transcript_segment_count', 0)}",
            f"- Evidence items extracted: {findings.get('evidence_item_count', 0)}",
            f"- Video manifest records: {(state.get('video_manifest') or {}).get('record_count', 0)}",
            "- Source statuses: "
            + (", ".join(f"{status}: {count}" for status, count in sorted(status_counts.items())) or "none"),
            "- Source results:",
            *(source_lines or ["- none"]),
            "- This agent supports YouTube caption tracks and Bilibili subtitle APIs; it records blocked/no-caption states without fabricating transcript content.",
        ]
    )
    return complete_node(
        state,
        agent_id="executive_transcripts",
        title="Executive Video Transcript Agent",
        report_body=body,
    )


def official_event_transcript_agent(state: ResearchState) -> ResearchState:
    findings = collect_official_event_transcripts(
        company=state.get("canonical_company") or {},
        offline=os.environ.get("STOCK_RESEARCH_OFFLINE") == "1",
    )
    state["official_event_transcript_findings"] = findings
    state["video_manifest"] = merge_video_manifests(state.get("video_manifest"), findings.get("video_manifest"))
    write_video_manifest(state)
    status_counts = findings.get("source_status_counts") or {}
    source_lines = [
        "- {name}: {status} | provider: {provider} | quarter: {quarter} | transcript segments: {segments}".format(
            name=result.get("name") or result.get("source_id"),
            status=result.get("status"),
            provider=result.get("provider") or result.get("platform") or "n/a",
            quarter=result.get("quarter") or result.get("period") or "n/a",
            segments=result.get("transcript_segment_count", 0),
        )
        for result in findings.get("source_results", [])[:12]
    ]
    body = "\n".join(
        [
            "Ran the Official Event Transcript Agent.",
            "",
            f"- Status: {findings.get('status')}.",
            f"- Source registry: {findings.get('registry_path')}",
            f"- Provider chain: {', '.join(findings.get('provider_chain') or []) or 'none'}",
            f"- Registry sources: {findings.get('source_count', 0)}",
            f"- Source results: {findings.get('source_result_count', 0)}",
            f"- Transcript records collected: {findings.get('transcript_record_count', 0)}",
            f"- Transcript source results collected: {findings.get('transcript_source_count', 0)}",
            f"- Transcript segments collected: {findings.get('transcript_segment_count', 0)}",
            f"- Evidence items extracted: {findings.get('evidence_item_count', 0)}",
            f"- Link-only source candidates recorded: {findings.get('source_candidate_count', 0)}",
            f"- Video manifest records: {(state.get('video_manifest') or {}).get('record_count', 0)}",
            "- Source statuses: "
            + (", ".join(f"{status}: {count}" for status, count in sorted(status_counts.items())) or "none"),
            "- Source results:",
            *(source_lines or ["- none"]),
            "- The collector now reuses cached provider transcript records before making live Alpha Vantage requests, and records third-party transcript pages as link-only candidates unless storage rights are confirmed.",
        ]
    )
    return complete_node(
        state,
        agent_id="official_event_transcripts",
        title="Official Event Transcript Agent",
        report_body=body,
    )


def valuation_agent(state: ResearchState) -> ResearchState:
    learning = lesson_context_for_agent("valuation")
    company_id = (state.get("canonical_company") or {}).get("company_id")
    if not state.get("market_inputs"):
        state["market_inputs"] = load_manual_market_inputs(company_id)
    market_inputs = state.get("market_inputs", {})
    state["valuation_metrics"] = calculate_v1_valuation_metrics(
        state.get("extracted_facts", []),
        market_inputs=market_inputs,
        financial_metrics=state.get("metrics", []),
    )
    if market_inputs.get("review_required") and not market_inputs.get("missing"):
        state["human_review_required"] = True
    financial_metric_statuses = {
        metric.get("formula_id"): metric.get("status")
        for metric in state.get("metrics", [])
    }
    valuation_metric_statuses = {
        metric.get("formula_id"): metric.get("status")
        for metric in state.get("valuation_metrics", [])
    }
    has_calculated_valuation_metric = any(
        metric.get("status") == "calculated" for metric in state.get("valuation_metrics", [])
    )
    state["valuation_findings"] = {
        "status": "valuation_metrics_calculated"
        if has_calculated_valuation_metric
        else "pending_market_data_or_financial_inputs",
        "principle": "right price",
        "learning_context": learning,
        "market_inputs": market_inputs,
        "financial_metric_statuses": financial_metric_statuses,
        "valuation_metric_statuses": valuation_metric_statuses,
        "prepared_inputs": [
            "owner earnings",
            "cash conversion",
            "ROIC",
            "cash and debt",
        ],
        "blocked_by": [
            "reviewed market capitalization",
            "discount rate",
            "growth scenarios",
            "maintenance capex refinement",
            "excess cash treatment",
        ],
    }
    body = "\n".join(
        [
            "Ran the Valuation Agent.",
            "",
            f"- Status: {state['valuation_findings']['status']}.",
            f"- Market input status: {market_inputs.get('status', 'not loaded')}.",
            f"- Enterprise value status: {valuation_metric_statuses.get('enterprise_value_v1', 'not run')}.",
            f"- Owner earnings yield status: {valuation_metric_statuses.get('true_yield_v1', 'not run')}.",
            f"- FCF yield status: {valuation_metric_statuses.get('free_cash_flow_yield_v1', 'not run')}.",
            "- Prepared financial inputs include owner earnings, cash/debt, cash conversion, and ROIC.",
            f"- Candidate lessons available: {len(learning['candidate_lessons'])}; approved lessons active: {len(learning['approved_lessons'])}.",
            "- No intrinsic value estimate is produced yet.",
        ]
    )
    return complete_node(state, agent_id="valuation", title="Valuation Agent", report_body=body)


def customer_happiness_agent(state: ResearchState) -> ResearchState:
    learning = lesson_context_for_agent("customer_happiness")
    synthesis = synthesize_customer_happiness(state.get("public_voice_findings", {}))
    state["customer_happiness_findings"] = {
        **synthesis,
        "learning_context": learning,
        "allowed_sources": [
            "Reddit",
            "YouTube",
            "Bilibili",
            "forums",
            "app reviews",
            "product reviews",
            "other customer/community channels",
        ],
        "evidence_needed": [
            "merchant/customer satisfaction",
            "product quality complaints",
            "repeat usage indicators",
            "platform trust and service quality",
        ],
    }
    top_dimensions = sorted(
        synthesis.get("dimensions", []),
        key=lambda item: int(item.get("evidence_count", 0)),
        reverse=True,
    )[:4]
    top_lines = [
        f"- {dimension.get('label')}: {dimension.get('evidence_count')} evidence items | {dimension.get('current_read')}"
        for dimension in top_dimensions
    ]
    body = "\n".join(
        [
            "Ran the Customer Happiness Agent from source-labeled public voice evidence.",
            "",
            f"- Status: {state['customer_happiness_findings']['status']}.",
            f"- Evidence items considered: {synthesis.get('evidence_item_count', 0)}",
            "- Source-quality counts: "
            + (
                ", ".join(
                    f"tier {tier}: {count}"
                    for tier, count in sorted((synthesis.get("source_quality_counts") or {}).items())
                )
                or "none"
            ),
            "- Top customer/merchant dimensions:",
            *(top_lines or ["- no public-voice dimensions available"]),
            f"- Candidate lessons available: {len(learning['candidate_lessons'])}; approved lessons active: {len(learning['approved_lessons'])}.",
            f"- Current conclusion: {synthesis.get('current_conclusion')}",
        ]
    )
    return complete_node(
        state,
        agent_id="customer_happiness",
        title="Customer Happiness Agent",
        report_body=body,
    )


def business_model_subagent_cluster_agent(state: ResearchState) -> ResearchState:
    cluster = build_business_model_subagent_cluster(state)
    business_model = state.setdefault("business_model_findings", {})
    business_model["evidence_subagent_cluster"] = cluster
    business_model["expanded_subagents"] = cluster.get("subagents", [])
    subagent_lines = [
        f"- {agent.get('name')}: {agent.get('status')} | {agent.get('working_level')} | "
        f"{agent.get('evidence_record_count', 0)} evidence records | {agent.get('confidence')}"
        for agent in cluster.get("subagents", [])
    ]
    body = "\n".join(
        [
            "Built the Business Model evidence subagent cluster.",
            "",
            f"- Status: {cluster.get('status')}.",
            f"- Subagents: {len(cluster.get('subagents', []))}",
            "- Status counts: "
            + (
                ", ".join(
                    f"{status}: {count}"
                    for status, count in sorted((cluster.get("status_counts") or {}).items())
                )
                or "none"
            ),
            "- Subagent lines:",
            *(subagent_lines or ["- none"]),
            "- The cluster separates official filings, official events, executive materials, customer voice, and merchant economics.",
        ]
    )
    return complete_node(
        state,
        agent_id="business_model_subagent_cluster",
        title="Business Model Subagent Cluster",
        report_body=body,
    )


def competitor_comparison_agent(state: ResearchState) -> ResearchState:
    learning = lesson_context_for_agent("competitor_comparison")
    state["competitor_findings"] = {
        "status": "scaffolded_pending_competitor_research",
        "comparison_rule": "Competitors should go through the same research workflow before comparison.",
        "next_expansion_target": "Tencent",
        "learning_context": learning,
        "evidence_needed": [
            "competitor identity/source pipeline",
            "competitor financial extraction",
            "competitor business model and leadership reports",
            "side-by-side metrics and moat comparison",
        ],
    }
    body = "\n".join(
        [
            "Scaffolded the Competitor Comparison Agent.",
            "",
            "- Status: pending competitor company runs.",
            "- Next expansion target recorded: Tencent.",
            f"- Candidate lessons available: {len(learning['candidate_lessons'])}; approved lessons active: {len(learning['approved_lessons'])}.",
            "- No comparison conclusion is produced yet.",
        ]
    )
    return complete_node(
        state,
        agent_id="competitor_comparison",
        title="Competitor Comparison Agent",
        report_body=body,
    )


def financial_results_report_agent(state: ResearchState) -> ResearchState:
    report = build_financial_results_report(state, audit_status="Draft pending audit review")
    write_financial_results_report(state, report)
    easy_report = build_financial_easy_reading_report(
        state.get("financial_report_pack", {}),
        audit_status="Draft pending audit review",
        official_evidence_pack=state.get("official_report_evidence_pack", {}),
        management_communication_pack=state.get("management_communication_pack", {}),
    )
    write_financial_easy_reading_report(state, easy_report)
    research_draft = build_financial_research_draft(
        state.get("financial_report_pack", {}),
        audit_status="Draft pending audit review",
        layer1_question_pack=state.get("layer1_question_pack", {}),
        evidence_communication_pack=state.get("evidence_communication_pack", {}),
        feedback_loop_pack=state.get("feedback_loop_pack", {}),
        official_evidence_pack=state.get("official_report_evidence_pack", {}),
        management_communication_pack=state.get("management_communication_pack", {}),
    )
    write_financial_research_draft(state, research_draft)
    visual_report = build_financial_visual_report(
        state.get("financial_report_pack", {}),
        audit_status="Draft pending audit review",
        markdown_report_path=state.get("financial_easy_reading_report_path"),
        official_evidence_pack=state.get("official_report_evidence_pack", {}),
        management_communication_pack=state.get("management_communication_pack", {}),
    )
    write_financial_visual_report(state, visual_report)
    body = "\n".join(
        [
            "Built the dedicated Financial Results Report draft.",
            "",
            f"- Financial results report path: {state['financial_results_report_path']}",
            f"- Easy-reading financial report path: {state['financial_easy_reading_report_path']}",
            f"- Financial research draft path: {state['financial_research_draft_path']}",
            f"- Financial visual report path: {state['financial_visual_report_path']}",
            "- Scope: official financial statements, operating KPIs, calculated financial-quality metrics, diagnostics, material-event boundaries, official verification, layer-one question pack, and evidence/communication pack.",
            "- Excluded: market/yield inputs, valuation commentary, third-party financial databases, and buy/sell conclusions.",
            "- Detailed fact IDs and formulas remain in the data-linkage report.",
        ]
    )
    return complete_node(
        state,
        agent_id="financial_results_report",
        title="Financial Results Report Agent",
        report_body=body,
    )


def business_model_report_agent(state: ResearchState) -> ResearchState:
    report = build_business_model_report(state, audit_status="Draft pending audit review")
    write_business_model_report(state, report)
    body = "\n".join(
        [
            "Built the dedicated Business Model / Moat Report draft.",
            "",
            f"- Business model report path: {state['business_model_report_path']}",
            "- Scope: official-report business model evidence, unit-economics proxies, moat hypotheses, anti-moat risks, external validation plans, public voice, and transcript evidence.",
            "- Detailed evidence cards and source snippets remain in the data-linkage report.",
        ]
    )
    return complete_node(
        state,
        agent_id="business_model_report",
        title="Business Model Report Agent",
        report_body=body,
    )


def right_people_report_agent(state: ResearchState) -> ResearchState:
    report = build_right_people_report(state, audit_status="Draft pending audit review")
    chinese_report = build_right_people_chinese_report(state, audit_status="Draft pending audit review")
    write_right_people_report(state, report)
    write_right_people_chinese_report(state, chinese_report)
    body = "\n".join(
        [
            "Built the dedicated Right People / Management Quality Report draft.",
            "",
            f"- Right people report path: {state['right_people_report_path']}",
            f"- Chinese right people report path: {state['right_people_chinese_report_path']}",
            "- Scope: governance/control, incentives, capital allocation, communication quality, execution record, and red flags.",
            "- Detailed evidence linkage remains in the data-linkage report.",
        ]
    )
    return complete_node(
        state,
        agent_id="right_people_report",
        title="Right People Report Agent",
        report_body=body,
    )


def research_workflow_artifacts_agent(state: ResearchState) -> ResearchState:
    artifacts = build_research_workflow_artifacts(state)
    state["source_map"] = artifacts["source_map"]
    write_source_map(state)
    state["decision_question_pack"] = artifacts["decision_question_pack"]
    state["decision_question_pack"]["source_map_path"] = state.get("source_map_path")
    write_decision_question_pack(state)
    state["evidence_plan"] = artifacts["evidence_plan"]
    write_evidence_plan(state)
    state["filing_deep_read_pack"] = artifacts["filing_deep_read_pack"]
    write_filing_deep_read_pack(state)
    state["question_evidence_completion_pack"] = artifacts["question_evidence_completion_pack"]
    write_question_evidence_completion_pack(state)
    state["evidence_registry"] = artifacts["evidence_registry"]
    write_evidence_registry(state)
    state["theme_workpaper_pack"] = artifacts["theme_workpaper_pack"]
    write_theme_workpaper_pack(state)
    state["question_dossier_pack"] = artifacts["question_dossier_pack"]
    write_question_dossier_pack(state)
    write_theme_workpaper_report(state, artifacts["theme_workpaper_report"])
    write_theme_workpaper_evidence_appendix(state, artifacts["theme_workpaper_evidence_appendix"])
    state["qa_gap_triage"] = artifacts["qa_gap_triage"]
    write_qa_gap_triage(state)
    state["pillar_judgment_stub"] = artifacts["pillar_judgment_stub"]
    write_pillar_judgment_stub(state)

    source_summary = state["source_map"].get("coverage_summary") or {}
    registry_summary = state["evidence_registry"].get("registry_summary") or {}
    qa_summary = state["qa_gap_triage"].get("triage_summary") or {}
    body = "\n".join(
        [
            "Built the v1.0-v1.4 decision-question-led workflow artifacts.",
            "",
            f"- v1.0 source map: `{state.get('source_map_path')}`",
            f"- v1.1 decision question pack: `{state.get('decision_question_pack_path')}`",
            f"- v1.1 evidence plan: `{state.get('evidence_plan_path')}`",
            f"- v1.25 filing deep read pack: `{state.get('filing_deep_read_pack_path')}`",
            f"- v1.45 question evidence completion pack: `{state.get('question_evidence_completion_pack_path')}`",
            f"- v1.2 evidence registry: `{state.get('evidence_registry_path')}`",
            f"- v1.3 theme workpaper pack: `{state.get('theme_workpaper_pack_path')}`",
            f"- v1.3 theme workpaper report: `{state.get('theme_workpaper_report_path')}`",
            f"- v1.35 question dossier pack: `{state.get('question_dossier_pack_path')}`",
            f"- v1.35 evidence appendix: `{state.get('theme_workpaper_evidence_appendix_path')}`",
            f"- v1.4 QA / gap triage: `{state.get('qa_gap_triage_path')}`",
            f"- v1.4 pillar judgment stub: `{state.get('pillar_judgment_stub_path')}`",
            "",
            f"- Sources mapped: {source_summary.get('source_count', 0)}",
            f"- Decision questions: {len(state['decision_question_pack'].get('questions', []))}",
            f"- Evidence items: {registry_summary.get('evidence_item_count', 0)}",
            f"- Supplemental targeted-read evidence: {registry_summary.get('supplemental_evidence_count', 0)}",
            f"- Deep-read evidence cards: {((state.get('filing_deep_read_pack') or {}).get('summary') or {}).get('evidence_card_count', 0)}",
            f"- Question dossiers: {((state.get('question_dossier_pack') or {}).get('summary') or {}).get('question_count', 0)}",
            f"- Workpapers: {len(state['theme_workpaper_pack'].get('workpapers', []))}",
            f"- QA next action: {qa_summary.get('next_action')}",
            "",
            "This node does not make buy/sell conclusions. It organizes sources, questions, evidence, workpapers, and gaps for later judgment agents.",
        ]
    )
    return complete_node(
        state,
        agent_id="research_workflow_artifacts",
        title="Decision-Question-Led Workflow Artifacts",
        report_body=body,
    )


def report_builder(state: ResearchState) -> ResearchState:
    report = build_final_report(state, audit_status="Draft pending audit review")
    linkage_report = build_data_linkage_report(state, audit_status="Draft pending audit review")
    write_final_report(state, report)
    write_data_linkage_report(state, linkage_report)
    body = "\n".join(
        [
            "Built the first Markdown report drafts.",
            "",
            f"- Report path: {state['final_report_path']}",
            f"- Financial results report path: {state.get('financial_results_report_path')}",
            f"- Financial easy-reading report path: {state.get('financial_easy_reading_report_path')}",
            f"- Business model report path: {state.get('business_model_report_path')}",
            f"- Right people report path: {state.get('right_people_report_path')}",
            f"- Chinese right people report path: {state.get('right_people_chinese_report_path')}",
            f"- Data linkage path: {state['data_linkage_report_path']}",
            "- The main report is the cross-section readout; the specialized reports split financial results, business-model analysis, and management-quality analysis.",
            "- The linkage report contains source and audit trails.",
        ]
    )
    return complete_node(state, agent_id="report_builder", title="Report Builder Agent", report_body=body)


def audit_review(state: ResearchState) -> ResearchState:
    material_conflicts = [
        result for result in state.get("verification_results", []) if result.get("status") == "material_conflict"
    ]
    if material_conflicts:
        state["human_review_required"] = True
    if state.get("extracted_facts"):
        extraction_status = "source discovery and first-pass official financial extraction"
    else:
        extraction_status = "company identity and source-policy scaffolding"
    conflict_status = (
        "with material conflicts recorded for later review"
        if material_conflicts
        else "with no material conflicts detected in available facts"
    )
    audit_status = (
        f"Pass for V1 {extraction_status}, {conflict_status}. "
        "This is still not a complete investment research report."
    )
    company_id = (state.get("canonical_company") or {}).get("company_id")
    fact_source_line = (
        "- Financial facts come from downloaded official Tencent IR PDF tables."
        if company_id == "tencent"
        else "- Financial facts come from downloaded official SEC XBRL filings."
    )
    body = "\n".join(
        [
            audit_status,
            "",
            "Audit checks completed:",
            "- No fake financial numbers were generated.",
            "- Source hierarchy is visible.",
            fact_source_line,
            "- Metrics are calculated only where required facts exist.",
            "- Human review gates are represented in the workflow.",
        ]
    )
    state = complete_node(state, agent_id="audit_review", title="Audit Review Agent", report_body=body)
    financial_report = build_financial_results_report(state, audit_status=audit_status)
    business_model_report = build_business_model_report(state, audit_status=audit_status)
    right_people_report = build_right_people_report(state, audit_status=audit_status)
    right_people_chinese_report = build_right_people_chinese_report(state, audit_status=audit_status)
    report = build_final_report(state, audit_status=audit_status)
    linkage_report = build_data_linkage_report(state, audit_status=audit_status)
    write_financial_results_report(state, financial_report)
    write_business_model_report(state, business_model_report)
    write_right_people_report(state, right_people_report)
    write_right_people_chinese_report(state, right_people_chinese_report)
    write_final_report(state, report)
    write_data_linkage_report(state, linkage_report)
    save_state(state)
    return state
