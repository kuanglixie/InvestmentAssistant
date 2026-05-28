from __future__ import annotations

import html
import re
from collections import Counter
from pathlib import Path
from typing import Any


TAG_PATTERN = re.compile(r"<[^>]+>")
SCRIPT_STYLE_PATTERN = re.compile(
    r"<(script|style)\b.*?</\1>",
    flags=re.IGNORECASE | re.DOTALL,
)
SPACE_PATTERN = re.compile(r"\s+")


OFFICIAL_EVENT_TERMS = {
    "long_term_investment": [
        "long-term",
        "long term",
        "invest",
        "investment",
        "sustainable",
        "high-quality development",
    ],
    "customer_value": [
        "consumer",
        "customer",
        "value-for-money",
        "value for money",
        "affordable",
        "quality",
    ],
    "merchant_support": [
        "merchant",
        "seller",
        "businesses",
        "supply chain",
        "ecosystem",
        "logistics",
    ],
    "competition_and_pressure": [
        "competition",
        "competitive",
        "profitability",
        "margin",
        "fluctuation",
        "uncertainty",
    ],
    "temu_global": [
        "Temu",
        "global",
        "cross-border",
        "international",
        "overseas",
    ],
}


EXECUTIVE_MATERIAL_TERMS = {
    "founder_or_leadership_voice": [
        "Zheng Huang",
        "Colin Zheng Huang",
        "Chen Lei",
        "Jiazhen Zhao",
        "co-chief executive",
        "chief executive",
        "chairman",
    ],
    "operating_values": [
        "Ben Fen",
        "be honest and trustworthy",
        "do the right things",
        "create value for the public",
        "value it creates for its users",
        "long term intrinsic value",
        "long-term intrinsic value",
        "investing in the future",
        "social responsibility",
    ],
    "capital_allocation_or_org": [
        "repurchase program",
        "share repurchase",
        "global share plan",
        "repurchase",
        "capital allocation",
        "beneficial ownership",
        "voting power",
    ],
}


def build_business_model_subagent_cluster(state: dict[str, Any]) -> dict[str, Any]:
    """Build the business-model evidence subagent cluster.

    The cluster separates evidence by source quality and research job. This is
    intentionally a synthesis/orchestration layer: collection still happens in
    the source-specific agents, while this layer records what each subagent can
    and cannot conclude.
    """

    company = state.get("canonical_company") or {}
    business_model = state.get("business_model_findings") or {}
    official_analysis = business_model.get("official_report_analysis") or {}
    public_voice = state.get("public_voice_findings") or {}
    customer_happiness = state.get("customer_happiness_findings") or {}
    external_moat = state.get("external_moat_findings") or {}
    executive_transcripts = state.get("executive_transcript_findings") or {}
    official_events = state.get("official_event_transcript_findings") or {}
    documents = state.get("documents") or []

    subagents = [
        _official_reports_subagent(official_analysis, documents),
        _official_calls_and_events_subagent(external_moat, documents, official_events),
        _executive_materials_subagent(external_moat, documents, executive_transcripts),
        _customer_happiness_subagent(customer_happiness, public_voice, external_moat),
        _merchant_profitability_subagent(official_analysis, public_voice, external_moat),
    ]
    status_counts = Counter(str(agent.get("status", "unknown")) for agent in subagents)
    confidence_counts = Counter(str(agent.get("confidence", "unknown")) for agent in subagents)

    return {
        "status": _cluster_status(subagents),
        "company_id": company.get("company_id"),
        "scope": (
            "Business-model/moat evidence cluster. Each subagent owns one source family "
            "and reports source quality, current answer, limits, and next collection steps."
        ),
        "subagents": subagents,
        "status_counts": dict(sorted(status_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "orchestration_policy": [
            "Tier 1 official filings/reports anchor business description and financial facts.",
            "Management calls, investor days, and executive interviews explain framing but cannot override filings.",
            "Customer and merchant public voice is lead evidence unless repeated across stronger sources.",
            "Merchant profitability requires rules/fees/logistics/returns evidence, not just merchant count.",
            "The coordinator may form hypotheses, but final moat conclusions require triangulation across subagents.",
        ],
        "standard_output_schema": {
            "claim": "Specific business-model or moat claim being tested.",
            "source_family": "official_filings, official_events, executive_materials, customer_voice, or merchant_voice.",
            "source_quality_tier": "Tier 1-4 using the external moat registry.",
            "evidence_direction": "supporting, contradicting, mixed, or lead_only.",
            "confidence": "low, medium, or high.",
            "source_locator": "Document id, URL, query, platform locator, or local path.",
            "limitation": "Why the evidence may be incomplete or biased.",
            "next_test": "Next collection or validation step.",
        },
    }


def _official_reports_subagent(
    official_analysis: dict[str, Any],
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    annual_docs = [
        doc
        for doc in documents
        if str(doc.get("document_type", "")).startswith(("20-F", "10-K", "annual_report_pdf"))
    ]
    quarterly_docs = [
        doc
        for doc in documents
        if doc.get("research_category") == "KEEP_CORE_INTERIM_EARNINGS"
    ]
    deep_dive = official_analysis.get("business_model_deep_dive") or {}
    answer_cards = deep_dive.get("answer_cards") or []
    financial_bridge = (deep_dive.get("revenue_engine") or {}).get("financial_bridge") or {}
    evidence_records = _official_report_evidence_records(
        answer_cards=answer_cards,
        official_analysis=official_analysis,
    )
    official_interim_records = _document_keyword_evidence_records(
        documents=quarterly_docs,
        term_groups=OFFICIAL_EVENT_TERMS,
        source_family="official_filings_and_reports",
        source_quality_tier=1,
        evidence_type="official_interim_earnings_release_commentary",
        max_records=18,
    )
    all_evidence_records = evidence_records + official_interim_records

    return {
        "subagent_id": "official_reports_reader",
        "name": "Official Reports Reader",
        "source_family": "official_filings_and_reports",
        "source_quality_tier": 1,
        "status": "completed_v1" if official_analysis else "pending_official_report_analysis",
        "working_level": "functional_v1",
        "confidence": "high_for_reported_facts_medium_for_moat",
        "source_scope": [
            "annual reports / 20-F / 10-K",
            "quarterly or interim earnings releases filed through official channels",
            "MD&A / business overview / segment notes / revenue notes / risk factors",
        ],
        "documents_seen": {
            "annual_report_count": len(annual_docs),
            "official_interim_earnings_count": len(quarterly_docs),
            "latest_official_report": (official_analysis.get("latest_source") or {}).get("document_id"),
        },
        "current_output": _join_sentences(
            [
                "This subagent can describe PDD's official business model, revenue engine, disclosed KPIs, risk factors, and official interim earnings-release commentary.",
                _first_answer(answer_cards, "economic_engine"),
                _official_interim_release_read(official_interim_records),
                "It now flags latest-year pressure signals instead of treating strong company-level metrics as a complete moat answer.",
            ]
        ),
        "claims_tested": _claim_summary(all_evidence_records),
        "evidence_record_count": len(all_evidence_records),
        "evidence_records": all_evidence_records,
        "evidence_highlights": (
            [
                f"Annual report documents available: {len(annual_docs)}",
                f"Official interim earnings-release documents available: {len(quarterly_docs)}",
                f"Official interim commentary records extracted: {len(official_interim_records)}",
            ]
            + financial_bridge.get("latest_snapshot", [])[:5]
            + financial_bridge.get("yoy_pressure", [])[:7]
        ),
        "limits": [
            "Official reports cannot prove customer happiness, merchant profitability, or competitor inability to copy the model.",
            "PDD does not fully separate Pinduoduo and Temu unit economics.",
        ],
        "next_steps": [
            "Keep extracting official annual and interim data first.",
            "Add section-level extraction for sales/marketing, fulfillment/logistics language, and working-capital pressure.",
        ],
    }


def _official_interim_release_read(records: list[dict[str, Any]]) -> str:
    if not records:
        return ""
    claim_counts = Counter(str(record.get("claim_id")) for record in records)
    themes = []
    if claim_counts.get("long_term_investment"):
        themes.append("long-term investment / high-quality development")
    if claim_counts.get("merchant_support"):
        themes.append("merchant support and ecosystem/supply-chain investment")
    if claim_counts.get("competition_and_pressure"):
        themes.append("competition, revenue-growth moderation, and margin/investment pressure")
    if claim_counts.get("customer_value"):
        themes.append("consumer value and quality language")
    if claim_counts.get("temu_global"):
        themes.append("Temu/global operating context and risk language")
    if not themes:
        return "The official interim earnings releases add management commentary, but V1 has not summarized recurring themes yet."
    return "The official interim earnings releases add recent management commentary around " + ", ".join(themes) + "."


def _official_event_transcript_records(official_events: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in official_events.get("evidence_items") or []:
        records.append(
            _evidence_record(
                claim_id=str(item.get("claim_id") or "official_event_transcript"),
                claim=str(item.get("claim") or "Official event transcript evidence."),
                source_family="official_management_events",
                source_quality_tier=item.get("source_quality_tier") or 1,
                evidence_type=str(item.get("evidence_type") or "official_event_transcript_segment"),
                source_locator=str(item.get("source_locator") or item.get("source_url") or ""),
                excerpt=str(item.get("excerpt") or ""),
                evidence_direction="supporting_or_context",
                confidence=str(item.get("confidence") or "medium"),
                limitation=str(
                    item.get("limitation")
                    or "Official event transcripts are management commentary and require cross-checking."
                ),
                extra={
                    "source_name": item.get("source_name"),
                    "matched_terms": item.get("matched_terms", []),
                },
            )
        )
    return records


def _official_calls_and_events_subagent(
    external_moat: dict[str, Any],
    documents: list[dict[str, Any]],
    official_events: dict[str, Any],
) -> dict[str, Any]:
    # Official 6-K earnings-release exhibits are routed to Official Reports Reader.
    # This subagent is reserved for actual call transcripts, Q&A, investor days, and IR presentations.
    earnings_docs = [
        doc for doc in documents if doc.get("research_category") == "KEEP_CORE_INTERIM_EARNINGS"
    ]
    source_results = official_events.get("source_results") or []
    evidence_records = _official_event_transcript_records(official_events)
    transcript_source_count = int(official_events.get("transcript_source_count") or 0)
    transcript_record_count = int(official_events.get("transcript_record_count") or 0)
    transcript_segment_count = int(official_events.get("transcript_segment_count") or 0)
    source_count = int(official_events.get("source_count") or 0)
    alpha_vantage_source_count = int(official_events.get("alpha_vantage_source_count") or 0)
    local_transcript_source_count = int(official_events.get("local_transcript_source_count") or 0)
    source_candidate_count = int(official_events.get("source_candidate_count") or 0)
    status = (
        "completed_v1_earnings_call_transcripts_collected"
        if transcript_record_count
        else "provider_chain_ready_with_source_candidates"
        if source_candidate_count
        else "provider_chain_registered_pending_transcripts"
        if source_count
        else "planned_pending_call_transcripts_and_investor_day_materials"
    )
    working_level = (
        "functional_v1_for_cached_provider_transcripts_and_question_pack"
        if transcript_record_count
        else "functional_v1_for_provider_chain_and_link_only_candidates"
        if source_count
        else "planned_v1_no_call_or_investor_day_material_collected"
    )
    confidence = "medium_for_provider_transcripts_high_for_traceability" if transcript_record_count else "not_evaluated"
    source_status_counts = official_events.get("source_status_counts") or {}
    question_pack = official_events.get("business_model_question_pack") or {}
    transcript_source_lines = [
        f"{result.get('quarter') or result.get('period')}: {result.get('provider')} | segments={result.get('transcript_segment_count', 0)} | status={result.get('status')}"
        for result in source_results
        if int(result.get("transcript_record_count") or 0) > 0
    ][:8]
    question_answer_counts = question_pack.get("answer_status_counts") or {}
    return {
        "subagent_id": "official_calls_investor_day_reader",
        "name": "Official Earnings Calls / Investor Day Reader",
        "source_family": "official_management_events",
        "source_quality_tier": 1,
        "status": status,
        "working_level": working_level,
        "confidence": confidence,
        "source_scope": [
            "official earnings-call transcripts when available",
            "earnings-call Q&A",
            "investor-day presentations",
            "IR presentations and prepared remarks",
        ],
        "documents_seen": {
            "official_interim_earnings_release_count_routed_to_official_reports_reader": len(earnings_docs),
            "official_event_source_count": source_count,
            "alpha_vantage_source_count": alpha_vantage_source_count,
            "local_transcript_source_count": local_transcript_source_count,
            "source_candidate_count": source_candidate_count,
            "call_transcript_count": transcript_record_count,
            "call_transcript_source_count": transcript_source_count,
            "call_transcript_segment_count": transcript_segment_count,
            "investor_day_material_count": 0,
            "business_model_question_count": question_pack.get("question_count", 0),
            "transcript_question_source_count": question_pack.get("source_question_set_count", 0),
            "transcript_question_results": question_pack.get("total_question_results", 0),
        },
        "current_output": (
            "This subagent now uses the productionized earnings-call transcript provider chain adopted from the working prototype. "
            "Official SEC 6-K earnings-release exhibits are handled by the Official Reports Reader because they are filed official reports. "
            + (
                "Cached PDD earnings-call transcript records are available and have been run through the business-model question pack."
                if transcript_record_count
                else "No full earnings-call transcript record has been collected yet; link-only source candidates are tracked for manual/licensed follow-up."
            )
        ),
        "claims_tested": _claim_summary(evidence_records),
        "evidence_record_count": len(evidence_records),
        "evidence_records": evidence_records,
        "evidence_highlights": [
            f"Official interim earnings-release documents routed to Official Reports Reader: {len(earnings_docs)}",
            f"Provider-chain registry sources: {source_count}",
            f"Alpha Vantage backfill sources registered: {alpha_vantage_source_count}",
            f"Local transcript intake sources registered: {local_transcript_source_count}",
            f"Link-only source candidates recorded: {source_candidate_count}",
            f"Full earnings-call transcript records collected: {transcript_record_count}",
            f"Earnings-call transcript segments collected: {transcript_segment_count}",
            "Provider-chain status counts: "
            + ", ".join(f"{key}={value}" for key, value in sorted(source_status_counts.items())),
            "Investor-day materials collected: 0",
            f"Business-model question pack questions: {question_pack.get('question_count', 0)}",
            f"Transcript question sets run: {question_pack.get('source_question_set_count', 0)}",
            "Business-model question answer statuses: "
            + (", ".join(f"{key}={value}" for key, value in sorted(question_answer_counts.items())) or "none"),
            *[f"Collected transcript: {line}" for line in transcript_source_lines],
            f"External source plan status: {external_moat.get('status', 'not built')}",
        ],
        "limits": [
            "Provider transcripts are management framing and Q&A, not independent proof.",
            "Alpha Vantage is a third-party API source; official filings and IR releases remain the source of record for financial numbers.",
            "Full text redistribution rights still need review before exporting transcript text outside this system.",
        ],
        "next_steps": [
            "Backfill any missing quarters once Alpha Vantage quota resets.",
            "Add official IR transcript/presentation discovery when PDD publishes transcript/deck files.",
            "Use local transcript intake for licensed StockAnalysis/Motley Fool/Quartr/user-provided text.",
            "Extract business-model claims, KPI commentary, and explanations for margin pressure.",
            "Link each event claim back to later filings to test consistency.",
        ],
    }


def _executive_materials_subagent(
    external_moat: dict[str, Any],
    documents: list[dict[str, Any]],
    executive_transcripts: dict[str, Any],
) -> dict[str, Any]:
    executive_docs = [
        doc
        for doc in documents
        if doc.get("research_category")
        in {
            "KEEP_CORE_ANNUAL_REPORT",
            "KEEP_MONITORING_MANAGEMENT",
        }
    ]
    evidence_records = _executive_material_evidence_records(
        documents=executive_docs,
        max_records=18,
    )
    transcript_records = _executive_transcript_evidence_records(
        executive_transcripts=executive_transcripts,
        max_records=12,
    )
    all_evidence_records = evidence_records + transcript_records
    transcript_source_results = executive_transcripts.get("source_results") or []
    transcript_status = executive_transcripts.get("status") or "not_run"
    return {
        "subagent_id": "executive_materials_reader",
        "name": "Executive Materials / Interview Reader",
        "source_family": "executive_interviews_and_longform_materials",
        "source_quality_tier": "2-4_by_source",
        "status": (
            "completed_v1_official_and_video_executive_material_reader"
            if all_evidence_records and transcript_records
            else "completed_v1_official_executive_material_reader"
            if evidence_records
            else "planned_pending_source_specific_collectors"
        ),
        "working_level": "functional_v1_for_official_materials_and_video_transcript_intake",
        "confidence": "low_until_collected_and_triangulated",
        "source_scope": [
            "official annual-report letters and governance/management filings",
            "founder/executive interviews",
            "YouTube / Bilibili / podcasts",
            "public speeches and letters",
            "official company videos or long-form strategy material",
        ],
        "current_output": (
            "This subagent now extracts leadership and operating-value evidence from official annual reports, "
            "governance filings, management-change disclosures, and any collected executive video transcripts. "
            "External interviews/videos stay lower-tier management-context evidence until cross-checked."
        ),
        "documents_seen": {
            "official_executive_or_governance_document_count": len(executive_docs),
            "executive_video_source_count": len(transcript_source_results),
            "executive_video_transcript_sources_collected": executive_transcripts.get("transcript_source_count", 0),
            "executive_video_transcript_segments": executive_transcripts.get("transcript_segment_count", 0),
            "executive_video_collector_status": transcript_status,
        },
        "claims_tested": _claim_summary(all_evidence_records),
        "evidence_record_count": len(all_evidence_records),
        "evidence_records": all_evidence_records,
        "evidence_highlights": [
            f"Official executive/governance documents scanned: {len(executive_docs)}",
            f"Executive-material evidence records extracted: {len(evidence_records)}",
            f"Executive video transcript collector status: {transcript_status}",
            f"Video transcript evidence records extracted: {len(transcript_records)}",
            f"External source plan status: {external_moat.get('status', 'not built')}",
        ],
        "limits": [
            "Executive material can explain intent but cannot prove moat durability.",
            "Edited interviews and promotional videos need strong source labels and date/context capture.",
            "If captions/subtitles are unavailable, V1 records the source state and does not infer the missing transcript.",
        ],
        "next_steps": [
            "Create a curated PDD/Pinduoduo/Temu executive-material source registry.",
            "Extract strategy claims, leadership principles, and repeated operating priorities.",
            "Cross-check executive claims against filings, customer evidence, merchant evidence, and financial outcomes.",
        ],
    }


def _customer_happiness_subagent(
    customer_happiness: dict[str, Any],
    public_voice: dict[str, Any],
    external_moat: dict[str, Any],
) -> dict[str, Any]:
    dimensions = customer_happiness.get("dimensions") or []
    top_dimensions = sorted(
        dimensions,
        key=lambda item: int(item.get("evidence_count", 0) or 0),
        reverse=True,
    )[:5]
    evidence_count = int(customer_happiness.get("evidence_item_count") or public_voice.get("evidence_item_count") or 0)
    evidence_records = _customer_happiness_evidence_records(customer_happiness, public_voice)
    return {
        "subagent_id": "customer_happiness_collector",
        "name": "Customer Happiness / Complaint Collector",
        "source_family": "customer_public_voice",
        "source_quality_tier": "2-4_by_source",
        "status": "completed_v1_public_voice_synthesis" if evidence_count else "planned_pending_collection",
        "working_level": "functional_v1_for_public_voice_patterns",
        "confidence": "low",
        "source_scope": [
            "app stores and review aggregators",
            "Reddit and forums",
            "YouTube / Instagram / Facebook / TikTok public material where accessible",
            "Bilibili / 知乎 / 小红书 / other Chinese public platforms where accessible",
        ],
        "current_output": customer_happiness.get("current_conclusion")
        or "No customer-happiness conclusion yet.",
        "claims_tested": _claim_summary(evidence_records),
        "evidence_record_count": len(evidence_records),
        "evidence_records": evidence_records,
        "evidence_highlights": [
            f"Evidence items considered: {evidence_count}",
            *[
                f"{item.get('label')}: {item.get('evidence_count')} items | {item.get('current_read')}"
                for item in top_dimensions
            ],
        ],
        "limits": [
            "Public complaints overrepresent unhappy customers.",
            "Individual posts/videos are lead evidence unless repeated across independent sources.",
            "Current V1 public evidence is mostly Temu/customer-side and not enough to prove PDD-wide customer happiness.",
        ],
        "next_steps": [
            "Add app-store aggregate snapshots and recent-review sampling.",
            "Add video/social-source collectors with creator-incentive labels.",
            "Separate Pinduoduo China customer evidence from Temu global customer evidence.",
        ],
        "linked_external_collectors": _collector_ids(external_moat, {"customer_forum_collector", "app_review_and_review_site_collector"}),
    }


def _merchant_profitability_subagent(
    official_analysis: dict[str, Any],
    public_voice: dict[str, Any],
    external_moat: dict[str, Any],
) -> dict[str, Any]:
    kpis = official_analysis.get("operating_kpi_analysis") or {}
    latest = kpis.get("latest_by_metric") or {}
    theme_counts = (public_voice.get("theme_summary") or {}).get("counts") or {}
    merchant_voice_count = int(theme_counts.get("merchant_seller_economics") or 0)
    active_merchants = latest.get("active_merchants")
    transaction_per_merchant = latest.get("average_transaction_services_revenue_per_active_merchant")
    evidence_records = _merchant_evidence_records(
        active_merchants=active_merchants,
        transaction_per_merchant=transaction_per_merchant,
        public_voice=public_voice,
    )

    return {
        "subagent_id": "merchant_profitability_sustainability_collector",
        "name": "Merchant Profitability / Sustainability Collector",
        "source_family": "merchant_rules_and_seller_voice",
        "source_quality_tier": "1_for_rules_3-4_for_seller_voice",
        "status": (
            "completed_v1_official_kpi_and_seller_voice_leads"
            if evidence_records
            else "planned_pending_merchant_source_collection"
        ),
        "working_level": "functional_v1_for_scale_and_seller_pain_leads",
        "confidence": "low",
        "source_scope": [
            "official seller center / merchant rules / fee and logistics policy pages",
            "merchant forums and seller communities",
            "Chinese seller discussions and complaint platforms",
            "public ecommerce operator interviews when source quality is clear",
        ],
        "current_output": (
            "Official reports show merchant scale and transaction-service monetization, but V1 cannot yet answer "
            "whether merchants are profitable and willing to stay after ads, returns, logistics, penalties, and discounts."
        ),
        "claims_tested": _claim_summary(evidence_records),
        "evidence_record_count": len(evidence_records),
        "evidence_records": evidence_records,
        "evidence_highlights": [
            _operating_record_line("Active merchants", active_merchants),
            _operating_record_line(
                "Average transaction-services revenue per active merchant",
                transaction_per_merchant,
            ),
            f"Merchant/seller public-voice leads: {merchant_voice_count}",
        ],
        "limits": [
            "Active merchant count is not merchant retention or merchant profit.",
            "Average transaction-services revenue per merchant is PDD monetization, not seller ROI.",
            "Seller forums can reveal pain points but need triangulation and date/platform labels.",
        ],
        "next_steps": [
            "Collect official seller rules, fees, logistics, return/refund obligations, and penalty policy.",
            "Build a merchant economics worksheet: traffic/ad cost, take rate/fees, return burden, fulfillment burden, payout timing.",
            "Separate Pinduoduo domestic merchant evidence from Temu cross-border seller evidence.",
        ],
        "linked_external_collectors": _collector_ids(external_moat, {"merchant_feedback_collector"}),
    }


def _official_report_evidence_records(
    *,
    answer_cards: list[dict[str, Any]],
    official_analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for card in answer_cards:
        snippets = card.get("source_evidence") or []
        supports = card.get("official_support") or []
        for index, snippet in enumerate(snippets[:2]):
            records.append(
                _evidence_record(
                    claim_id=str(card.get("question_id") or "official_report_answer"),
                    claim=str(card.get("question") or card.get("current_answer") or "Official-report answer"),
                    source_family="official_filings_and_reports",
                    source_quality_tier=1,
                    evidence_type="official_report_answer_card",
                    source_locator="official_report_analysis.business_model_deep_dive.answer_cards",
                    excerpt=str(snippet),
                    evidence_direction="supporting",
                    confidence=str(card.get("evidence_grade") or "medium"),
                    limitation="Official reports describe management's disclosed model; they cannot prove external durability.",
                    extra={
                        "supporting_point": supports[index] if index < len(supports) else None,
                    },
                )
            )

    kpi_analysis = official_analysis.get("operating_kpi_analysis") or {}
    for metric, record in sorted((kpi_analysis.get("latest_by_metric") or {}).items()):
        records.append(
            _evidence_record(
                claim_id="official_operating_kpi",
                claim=f"Official KPI extracted: {record.get('label') or metric}",
                source_family="official_filings_and_reports",
                source_quality_tier=1,
                evidence_type="official_operating_kpi",
                source_locator=(record.get("source_document") or {}).get("document_id") or "official_report_analysis.operating_kpi_analysis",
                excerpt=str(record.get("evidence") or ""),
                evidence_direction="supporting",
                confidence="high_for_extracted_number_medium_for_interpretation",
                limitation=str(record.get("note") or "A KPI by itself does not prove retention, satisfaction, or merchant profit."),
                extra={
                    "metric": metric,
                    "value": record.get("value"),
                    "unit": record.get("unit"),
                    "period_end": record.get("period_end"),
                },
            )
        )
    return records


def _document_keyword_evidence_records(
    *,
    documents: list[dict[str, Any]],
    term_groups: dict[str, list[str]],
    source_family: str,
    source_quality_tier: Any,
    evidence_type: str,
    max_records: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    sorted_docs = sorted(
        documents,
        key=lambda doc: str(doc.get("filing_date") or doc.get("report_date") or ""),
        reverse=True,
    )
    for document in sorted_docs[:40]:
        if len(records) >= max_records:
            break
        text = _document_text(document)
        if not text:
            continue
        for group_id, terms in term_groups.items():
            if len(records) >= max_records:
                break
            key = (str(document.get("document_id")), group_id)
            if key in seen:
                continue
            snippet = _first_matching_snippet(text, terms)
            if not snippet:
                continue
            seen.add(key)
            records.append(
                _evidence_record(
                    claim_id=group_id,
                    claim=_claim_from_group_id(group_id),
                    source_family=source_family,
                    source_quality_tier=source_quality_tier,
                    evidence_type=evidence_type,
                    source_locator=document.get("source_url") or document.get("local_path") or document.get("document_id"),
                    source_document_id=document.get("document_id"),
                    excerpt=snippet,
                    evidence_direction="supporting_or_context",
                    confidence="medium" if source_quality_tier == 1 else "low",
                    limitation="Keyword extraction finds relevant management language; it still needs human reading before strong conclusions.",
                    extra={
                        "filing_date": document.get("filing_date"),
                        "document_type": document.get("document_type"),
                        "matched_group": group_id,
                    },
                )
            )
    return records


def _executive_material_evidence_records(
    *,
    documents: list[dict[str, Any]],
    max_records: int,
) -> list[dict[str, Any]]:
    annual_docs = [
        doc
        for doc in documents
        if str(doc.get("research_category") or "") == "KEEP_CORE_ANNUAL_REPORT"
    ]
    management_docs = [
        doc
        for doc in documents
        if str(doc.get("research_category") or "") == "KEEP_MONITORING_MANAGEMENT"
    ]
    source_docs = sorted(
        annual_docs + management_docs,
        key=lambda doc: str(doc.get("filing_date") or doc.get("report_date") or ""),
        reverse=True,
    )
    high_value_terms = {
        "founder_shareholder_letters": [
            "2018 LETTER TO SHAREHOLDERS",
            "Colin Zheng Huang",
            "On behalf of Pinduoduo",
            "P.S. I attach the letter from our IPO",
        ],
        "customer_first_operating_philosophy": [
            "value it creates for its users",
            "derive happiness",
            "value-for-money merchandise",
            "meet users' changing needs",
            "meet users’ changing needs",
        ],
        "ben_fen_operating_values": [
            "Ben Fen",
            "be honest and trustworthy",
            "Never take advantage of others",
            "Self-reflect and take responsibilities",
        ],
        "long_term_intrinsic_value": [
            "long term intrinsic value",
            "long-term intrinsic value",
            "investing in the future",
            "create value for the public",
        ],
        "current_named_executives": [
            "Mr. Lei Chen",
            "Mr. Jiazhen Zhao",
            "Co-Chief Executive Officer",
            "co-chief executive officer",
        ],
        "capital_allocation_and_incentives": [
            "share repurchase",
            "repurchase program",
            "Global Share Plan",
            "beneficial ownership",
            "voting power",
        ],
    }
    records: list[dict[str, Any]] = []
    seen_groups: set[str] = set()

    # Older annual reports contain founder letters that are far more useful than
    # generic governance pages, so scan all annual reports before falling back to
    # recent management filings.
    for group_id, terms in high_value_terms.items():
        if len(records) >= max_records:
            break
        best_record = None
        for document in source_docs:
            text = _document_text(document)
            if not text:
                continue
            snippet = _best_matching_snippet(text, terms)
            if not snippet:
                continue
            best_record = _evidence_record(
                claim_id=group_id,
                claim=_claim_from_group_id(group_id),
                source_family="executive_materials",
                source_quality_tier="1_for_official_filings_3_for_external_interviews",
                evidence_type="official_executive_material",
                source_locator=document.get("source_url") or document.get("local_path") or document.get("document_id"),
                source_document_id=document.get("document_id"),
                excerpt=snippet,
                evidence_direction="supporting_or_context",
                confidence="medium_for_official_text_low_for_people_judgment",
                limitation="Official executive material explains philosophy and incentives; it does not prove execution quality or integrity.",
                extra={
                    "filing_date": document.get("filing_date"),
                    "document_type": document.get("document_type"),
                    "matched_group": group_id,
                },
            )
            break
        if best_record:
            records.append(best_record)
            seen_groups.add(group_id)

    if len(records) < min(max_records, len(high_value_terms)):
        fallback = _document_keyword_evidence_records(
            documents=source_docs,
            term_groups={key: terms for key, terms in EXECUTIVE_MATERIAL_TERMS.items() if key not in seen_groups},
            source_family="executive_materials",
            source_quality_tier="1_for_official_filings_3_for_external_interviews",
            evidence_type="official_executive_or_governance_material",
            max_records=max_records - len(records),
        )
        records.extend(fallback)
    return records[:max_records]


def _executive_transcript_evidence_records(
    *,
    executive_transcripts: dict[str, Any],
    max_records: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in executive_transcripts.get("evidence_items") or []:
        if len(records) >= max_records:
            break
        records.append(
            _evidence_record(
                claim_id=str(item.get("claim_id") or "executive_video_transcript"),
                claim=str(item.get("claim") or "Executive transcript evidence"),
                source_family="executive_interviews_and_video_transcripts",
                source_quality_tier=item.get("source_quality_tier") or "unknown",
                evidence_type=str(item.get("evidence_type") or "executive_video_transcript_excerpt"),
                source_locator=item.get("source_url") or item.get("source_id"),
                excerpt=str(item.get("excerpt") or ""),
                evidence_direction=str(item.get("evidence_direction") or "management_context_or_claim"),
                confidence=str(item.get("confidence") or "low_until_cross_checked"),
                limitation=str(
                    item.get("limitation")
                    or "Executive transcript excerpts need cross-checking against filings and outcomes."
                ),
                extra={
                    "platform": item.get("platform"),
                    "language": item.get("language"),
                    "executive_names": item.get("executive_names", []),
                    "transcript_method": item.get("transcript_method"),
                    "start_seconds": item.get("start_seconds"),
                    "matched_terms": item.get("matched_terms", []),
                },
            )
        )
    return records


def _customer_happiness_evidence_records(
    customer_happiness: dict[str, Any],
    public_voice: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for dimension in sorted(
        customer_happiness.get("dimensions") or [],
        key=lambda item: int(item.get("evidence_count", 0) or 0),
        reverse=True,
    ):
        if int(dimension.get("evidence_count", 0) or 0) <= 0:
            continue
        theme = str(dimension.get("theme") or dimension.get("dimension_id") or "")
        best_item = _best_public_voice_item(public_voice, theme)
        examples = dimension.get("representative_examples") or []
        excerpt = (
            best_item.get("excerpt")
            if best_item
            else examples[0].get("excerpt")
            if examples
            else dimension.get("summary")
        )
        records.append(
            _evidence_record(
                claim_id=str(dimension.get("dimension_id") or dimension.get("theme") or "customer_dimension"),
                claim=f"Customer happiness dimension: {dimension.get('label')}",
                source_family="customer_public_voice",
                source_quality_tier=", ".join(str(tier) for tier in dimension.get("source_quality_tiers", [])) or "unknown",
                evidence_type="customer_voice_dimension",
                source_locator=(
                    best_item.get("comment_url")
                    or best_item.get("source_url")
                    if best_item
                    else examples[0].get("comment_url")
                    if examples
                    else "customer_happiness_findings.dimensions"
                ),
                excerpt=str(excerpt or ""),
                evidence_direction=str(dimension.get("current_read") or "lead_only"),
                confidence=str(dimension.get("confidence") or "low"),
                limitation="Public voice is selection-biased and cannot by itself prove population-wide customer happiness.",
                extra={
                    "evidence_count": dimension.get("evidence_count"),
                    "source_names": dimension.get("source_names", []),
                },
            )
        )

    for result in public_voice.get("source_results") or []:
        aggregate = result.get("aggregate_summary") or {}
        if not aggregate:
            continue
        records.append(
            _evidence_record(
                claim_id="aggregate_review_profile",
                claim=f"Aggregate public review profile: {result.get('name')}",
                source_family="customer_public_voice",
                source_quality_tier=result.get("quality_tier"),
                evidence_type="aggregate_review_profile",
                source_locator=result.get("url") or result.get("search_locator") or result.get("source_id"),
                excerpt=_aggregate_summary_text(aggregate),
                evidence_direction="lead_only",
                confidence="low",
                limitation="Review-site aggregates are useful signals but have sampling, authenticity, and moderation bias.",
            )
        )
    return records


def _merchant_evidence_records(
    *,
    active_merchants: dict[str, Any] | None,
    transaction_per_merchant: dict[str, Any] | None,
    public_voice: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for label, record in [
        ("Active merchant scale", active_merchants),
        ("PDD transaction-service monetization per active merchant", transaction_per_merchant),
    ]:
        if not record:
            continue
        records.append(
            _evidence_record(
                claim_id="merchant_scale_or_monetization",
                claim=label,
                source_family="official_filings_and_reports",
                source_quality_tier=1,
                evidence_type="official_merchant_kpi",
                source_locator=(record.get("source_document") or {}).get("document_id") or "official_report_analysis.operating_kpi_analysis",
                excerpt=str(record.get("evidence") or ""),
                evidence_direction="supporting",
                confidence="high_for_number_low_for_profitability",
                limitation="This measures platform scale or PDD monetization, not seller profit or seller retention.",
                extra={
                    "value": record.get("value"),
                    "unit": record.get("unit"),
                    "period_end": record.get("period_end"),
                },
            )
        )

    merchant_items = [
        item
        for item in public_voice.get("evidence_items") or []
        if "merchant_seller_economics" in (item.get("themes") or [])
    ]
    merchant_items = sorted(
        merchant_items,
        key=lambda item: (
            0 if item.get("source_id") == "temu_seller_center_official" else 1,
            0 if item.get("source_quality_tier") == 1 else 1,
            0 if item.get("evidence_type") in {"web_reader_paragraph", "review_site_aggregate"} else 1,
            str(item.get("source_id") or ""),
        ),
    )
    used_sources: set[str] = set()
    for item in merchant_items:
        source_key = str(item.get("source_id") or item.get("source_name") or item.get("comment_url"))
        if len(records) >= 10:
            break
        if source_key in used_sources and len(used_sources) >= 3:
            continue
        used_sources.add(source_key)
        records.append(
            _evidence_record(
                claim_id="merchant_seller_economics_public_voice",
                claim="Merchant/seller public voice raises economics, fee, return, ad, or penalty leads.",
                source_family="merchant_rules_and_seller_voice",
                source_quality_tier=item.get("source_quality_tier"),
                evidence_type=item.get("evidence_type") or item.get("voice_type") or "merchant_public_voice",
                source_locator=item.get("comment_url") or item.get("post_url") or item.get("source_url"),
                excerpt=str(item.get("excerpt") or ""),
                evidence_direction="lead_only",
                confidence="low",
                limitation="Seller public voice is useful for pain-point discovery but must be triangulated with rules, fees, and seller economics.",
                extra={
                    "source_name": item.get("source_name"),
                    "post_title": item.get("post_title"),
                    "themes": item.get("themes", []),
                },
            )
        )
    return records


def _evidence_record(
    *,
    claim_id: str,
    claim: str,
    source_family: str,
    source_quality_tier: Any,
    evidence_type: str,
    source_locator: Any,
    excerpt: str,
    evidence_direction: str,
    confidence: str,
    limitation: str,
    source_document_id: Any | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "claim_id": claim_id,
        "claim": claim,
        "source_family": source_family,
        "source_quality_tier": source_quality_tier,
        "evidence_type": evidence_type,
        "source_locator": source_locator,
        "source_document_id": source_document_id,
        "excerpt": _trim_excerpt(excerpt),
        "evidence_direction": evidence_direction,
        "confidence": confidence,
        "limitation": limitation,
        "requires_human_review": source_quality_tier != 1 or confidence.startswith("low"),
    }
    if extra:
        record.update({key: value for key, value in extra.items() if value is not None})
    return record


def _claim_summary(evidence_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(str(record.get("claim_id") or "unknown") for record in evidence_records)
    return [
        {
            "claim_id": claim_id,
            "evidence_record_count": count,
            "claim": next(
                (
                    str(record.get("claim"))
                    for record in evidence_records
                    if str(record.get("claim_id") or "unknown") == claim_id
                ),
                claim_id,
            ),
        }
        for claim_id, count in sorted(counts.items())
    ]


def _document_text(document: dict[str, Any]) -> str:
    path_value = document.get("local_path")
    if not path_value:
        return ""
    path = Path(str(path_value))
    if not path.exists():
        return ""
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = SCRIPT_STYLE_PATTERN.sub(" ", raw)
    text = TAG_PATTERN.sub(" ", raw)
    return SPACE_PATTERN.sub(" ", html.unescape(text)).strip()


def _first_matching_snippet(text: str, terms: list[str], *, context: int = 260) -> str:
    lower = text.lower()
    positions = [
        lower.find(term.lower())
        for term in terms
        if term and lower.find(term.lower()) >= 0
    ]
    if not positions:
        return ""
    start = max(0, min(positions) - context)
    end = min(len(text), min(positions) + context)
    return _trim_excerpt(text[start:end], limit=520)


def _best_matching_snippet(text: str, terms: list[str], *, context: int = 300) -> str:
    lower = text.lower()
    best: tuple[int, int, str] | None = None
    for term in terms:
        if not term:
            continue
        position = lower.find(term.lower())
        if position < 0:
            continue
        # Prefer rarer, more specific phrases and earlier matches within the
        # document. This avoids broad governance or risk-factor boilerplate.
        specificity = len(term)
        candidate = (-specificity, position, term)
        if best is None or candidate < best:
            best = candidate
    if best is None:
        return ""
    position = best[1]
    start = max(0, position - context)
    end = min(len(text), position + context)
    return _trim_excerpt(text[start:end], limit=620)


def _trim_excerpt(text: str, *, limit: int = 420) -> str:
    clean = SPACE_PATTERN.sub(" ", str(text).replace("\xa0", " ")).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def _claim_from_group_id(group_id: str) -> str:
    labels = {
        "long_term_investment": "Management frames business-model decisions around long-term investment.",
        "customer_value": "Management discusses the customer value proposition.",
        "merchant_support": "Management discusses merchant support, ecosystem, logistics, or supply-chain claims.",
        "competition_and_pressure": "Management discusses competition, profitability, margin pressure, or uncertainty.",
        "temu_global": "Management discusses Temu/global expansion.",
        "founder_or_leadership_voice": "Official materials identify leadership voice and executive context.",
        "operating_values": "Executive materials discuss operating values or long-term principles.",
        "capital_allocation_or_org": "Executive materials discuss capital allocation, shareholders, board, or organization.",
        "founder_shareholder_letters": "Founder/shareholder letters explain PDD's early operating philosophy.",
        "customer_first_operating_philosophy": "Executive materials frame user value as the operating center.",
        "ben_fen_operating_values": "Executive materials describe Ben Fen and related operating values.",
        "long_term_intrinsic_value": "Executive materials emphasize long-term intrinsic value and future investment.",
        "current_named_executives": "Official materials identify current named executives and leadership continuity.",
        "capital_allocation_and_incentives": "Official materials surface capital-allocation and incentive-plan markers.",
    }
    return labels.get(group_id, group_id.replace("_", " "))


def _best_public_voice_item(public_voice: dict[str, Any], theme: str) -> dict[str, Any] | None:
    items = [
        item
        for item in public_voice.get("evidence_items") or []
        if theme in (item.get("themes") or [])
    ]
    if not items:
        return None

    def score(item: dict[str, Any]) -> tuple[int, int, int, str]:
        source_id = str(item.get("source_id") or "")
        evidence_type = str(item.get("evidence_type") or "")
        source_rank = 0
        if source_id in {"trustpilot_temu_reviews", "sitejabber_temu_reviews"}:
            source_rank = 0
        elif source_id in {"temu_support_shipping_returns", "temu_seller_center_official"}:
            source_rank = 1
        elif "reddit" in source_id:
            source_rank = 2
        else:
            source_rank = 3
        evidence_rank = 0 if evidence_type in {"review_site_review", "web_reader_paragraph", "review_site_aggregate"} else 1
        length_rank = 0 if len(str(item.get("excerpt") or "")) >= 80 else 1
        return (source_rank, evidence_rank, length_rank, source_id)

    return sorted(items, key=score)[0]


def _aggregate_summary_text(summary: dict[str, Any]) -> str:
    parts = []
    for key in ["rating", "review_count", "recommend_percent", "positive_reviews_last_12_months_percent"]:
        if summary.get(key) is not None:
            parts.append(f"{key}: {summary[key]}")
    counts = summary.get("category_mention_counts") or {}
    if counts:
        parts.append("category_mention_counts: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    return "; ".join(parts) or str(summary)


def _cluster_status(subagents: list[dict[str, Any]]) -> str:
    completed_or_partial = [
        agent
        for agent in subagents
        if str(agent.get("status", "")).startswith(("completed", "partial"))
    ]
    if len(completed_or_partial) == len(subagents):
        return "all_subagents_have_v1_outputs"
    if completed_or_partial:
        return "partial_subagent_cluster_ready"
    return "planned_pending_collection"


def _collector_ids(external_moat: dict[str, Any], wanted: set[str]) -> list[str]:
    groups = external_moat.get("collector_groups") or []
    return [
        str(group.get("collector_id"))
        for group in groups
        if str(group.get("collector_id")) in wanted
    ]


def _first_answer(answer_cards: list[dict[str, Any]], question_id: str) -> str | None:
    for card in answer_cards:
        if card.get("question_id") == question_id:
            return str(card.get("current_answer") or "")
    return None


def _join_sentences(items: list[str | None]) -> str:
    return " ".join(str(item).strip() for item in items if item)


def _operating_record_line(label: str, record: dict[str, Any] | None) -> str:
    if not record:
        return f"{label}: not disclosed/extracted"
    return f"{label}: {_format_operating_record_value(record)} as of {record.get('period_end')}"


def _format_operating_record_value(record: dict[str, Any]) -> str:
    value = record.get("value")
    if value is None:
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    unit = record.get("unit")
    if unit == "CNY":
        return f"RMB {numeric / 1_000_000_000:.1f}B"
    if unit in {"users", "merchants", "orders"}:
        if numeric >= 1_000_000_000:
            return f"{numeric / 1_000_000_000:.1f}B"
        return f"{numeric / 1_000_000:.1f}M"
    if unit in {"CNY_per_active_buyer", "CNY_per_active_merchant"}:
        return f"RMB {numeric:,.1f}"
    return f"{numeric:,.0f}"
