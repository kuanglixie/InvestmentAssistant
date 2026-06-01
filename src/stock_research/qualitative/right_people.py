from __future__ import annotations

import html
import re
from collections import Counter
from pathlib import Path
from typing import Any

from stock_research.qualitative.annual_report import (
    LEADERSHIP_TOPICS,
    annual_report_topic_evidence,
    latest_annual_report_document,
)
from stock_research.state import ResearchState, utc_now_iso


RIGHT_PEOPLE_SCHEMA_VERSION = "right_people_analysis_v3"


EVIDENCE_BUCKETS = [
    {
        "bucket": "fact",
        "definition": "Legally filed, directly observable, audited, certified, or externally adjudicated evidence.",
        "default_use": "Foundation for right-people analysis.",
        "examples": [
            "voting rights",
            "diluted shares",
            "auditor changes",
            "restatements",
            "related-party disclosures",
        ],
    },
    {
        "bucket": "management_claim",
        "definition": "What management says it will do, why results look the way they do, or how it frames priorities.",
        "default_use": "Hypothesis to test against later filings and outcomes.",
        "examples": [
            "long-term investment language",
            "capital-allocation philosophy",
            "strategic priorities",
        ],
    },
    {
        "bucket": "external_evidence",
        "definition": "Independent validation or contradiction outside management's own story.",
        "default_use": "Corroboration or risk cue; source quality must be labeled.",
        "examples": [
            "regulator records",
            "court records",
            "reputable investigative reporting",
            "customer or employee evidence",
        ],
    },
    {
        "bucket": "inference",
        "definition": "Analyst or system judgment after weighing facts, claims, and external evidence.",
        "default_use": "Final analyst conclusion only when evidence chain is explicit.",
        "examples": [
            "management appears owner-oriented",
            "control risk remains unresolved",
            "capital allocation is partially supported",
        ],
    },
]


SOURCE_HIERARCHY = [
    {
        "tier": "high",
        "sources": "10-K, 20-F, audited annual reports, proxy/DEF 14A when applicable, S-1/F-1/424B4, governance documents, definitive agreements, enforcement orders, final judgments",
        "use": "Control, incentives, compensation, related parties, audited financial outcomes, and hard red flags.",
    },
    {
        "tier": "medium_high",
        "sources": "10-Q, 6-K, 8-K, 13D/13G, Forms 3/4/5, director/officer change filings",
        "use": "Event-driven changes, ownership changes, interim financials, auditor issues, and turnover.",
    },
    {
        "tier": "medium",
        "sources": "Earnings calls, shareholder letters, investor days, conference decks, executive interviews",
        "use": "Management mindset, priorities, promises, KPI framing, and communication quality.",
    },
    {
        "tier": "low_to_medium",
        "sources": "Customer, supplier, merchant, employee, competitor, media, forum, app-review, and expert inputs",
        "use": "External validation only; useful for patterns, not standalone proof.",
    },
]


OFFICIAL_FILING_TERM_GROUPS = {
    "control_and_governance": [
        "voting power",
        "beneficial ownership",
        "board of directors",
        "directors and executive officers",
        "variable interest entity",
        "VIE",
        "contractual arrangements",
        "dual-class",
        "shareholder meeting",
    ],
    "incentives_and_compensation": [
        "share-based compensation",
        "share incentive plan",
        "restricted share units",
        "options",
        "compensation",
        "equity incentive",
    ],
    "capital_allocation": [
        "repurchase",
        "dividend",
        "no plan to pay any cash dividends",
        "capital allocation",
        "investment commitments",
        "reinvestment",
        "long-term value",
    ],
    "integrity_red_flags": [
        "related party",
        "related-party",
        "auditor",
        "material weakness",
        "restatement",
        "non-reliance",
        "investigation",
        "penalty",
        "resignation",
    ],
}


MANAGEMENT_EVIDENCE_CLAIMS = {
    "capital_allocation",
    "management_priorities_and_tone",
    "organization_and_people",
    "long_term_investment",
    "competition_and_pressure",
}


def build_right_people_analysis(state: ResearchState) -> dict[str, Any]:
    """Build a management-quality gate from already controlled sources.

    The agent is deliberately conservative: official filings and deterministic financial
    metrics get the highest weight; transcripts are used only for management
    communication and stated priorities.
    """

    company = state.get("canonical_company") or {}
    annual_report_evidence = annual_report_topic_evidence(
        state.get("documents", []),
        topic_terms=LEADERSHIP_TOPICS,
    )
    filing_cards = _official_filing_cards(state.get("documents", []))
    financial_signals = _financial_signals(state)
    transcript_signals = _management_transcript_signals(state)
    red_flags = _red_flags(state, filing_cards=filing_cards)
    control_map = _control_map(filing_cards, annual_report_evidence)
    incentive_map = _incentive_map(financial_signals, filing_cards)
    capital_allocation_ledger = _capital_allocation_ledger(state, financial_signals, filing_cards)
    communication_audit = _communication_audit(transcript_signals, financial_signals)
    red_flag_matrix = _red_flag_matrix(red_flags)

    subagents = [
        _governance_control_subagent(annual_report_evidence, filing_cards),
        _incentive_alignment_subagent(annual_report_evidence, financial_signals, filing_cards),
        _capital_allocation_subagent(financial_signals, filing_cards, transcript_signals),
        _management_communication_subagent(transcript_signals),
        _execution_track_record_subagent(financial_signals),
        _integrity_red_flag_subagent(red_flags, filing_cards),
    ]
    checklist = _right_people_checklist(subagents, red_flags)
    scorecard = _right_people_scorecard(
        control_map=control_map,
        incentive_map=incentive_map,
        capital_allocation_ledger=capital_allocation_ledger,
        communication_audit=communication_audit,
        red_flag_matrix=red_flag_matrix,
        financial_signals=financial_signals,
    )
    decision = _right_people_decision(scorecard=scorecard, red_flags=red_flags, checklist=checklist)

    return {
        "schema_version": RIGHT_PEOPLE_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "company_id": company.get("company_id"),
        "status": decision["status"],
        "principle": "right people",
        "overall_read": decision["current_read"],
        "right_people_decision": decision,
        "source_policy": {
            "financial_number_rule": "Use official filings and official financial reports for financial facts.",
            "transcript_rule": "Use earnings calls and executive interviews for management commentary only; reconcile with filings and outcomes.",
            "evidence_bucket_rule": "Every important observation should be kept separate as fact, management_claim, external_evidence, or inference.",
            "judgment_rule": "V1 may mark support/concern but must not infer integrity or skill beyond the evidence.",
        },
        "evidence_framework": {
            "buckets": EVIDENCE_BUCKETS,
            "source_hierarchy": SOURCE_HIERARCHY,
            "core_rule": "Never let a management claim masquerade as a fact.",
        },
        "source_coverage": {
            "annual_report_status": annual_report_evidence.get("status"),
            "official_filing_evidence_cards": len(filing_cards),
            "financial_signal_count": len(financial_signals),
            "management_transcript_signal_count": transcript_signals.get("signal_count", 0),
            "material_event_count": (state.get("material_event_scan") or {}).get("material_event_count", 0),
            "red_flag_count": len(red_flags),
        },
        "annual_report_evidence": annual_report_evidence,
        "financial_signals": financial_signals,
        "management_transcript_signals": transcript_signals,
        "official_filing_evidence_cards": filing_cards,
        "control_map": control_map,
        "incentive_map": incentive_map,
        "capital_allocation_ledger": capital_allocation_ledger,
        "communication_audit": communication_audit,
        "red_flag_matrix": red_flag_matrix,
        "scorecard": scorecard,
        "subagent_reports": subagents,
        "right_people_checklist": checklist,
        "red_flags": red_flags,
        "open_questions": _open_questions(subagents, red_flags),
        "limits": [
            "The current version does not yet run a full proxy-style compensation analysis for non-US issuers.",
            "The current version does not yet separate founder, board, and operating-team contributions when filings do not provide enough detail.",
            "Transcript evidence is management framing; it is not independent proof of execution quality.",
        ],
    }


def _control_map(
    filing_cards: list[dict[str, Any]],
    annual_report_evidence: dict[str, Any],
) -> dict[str, Any]:
    cards = _cards_by_group(filing_cards, "control_and_governance")
    matched_terms = sorted({term for card in cards for term in card.get("matched_terms", [])})
    issues = []
    if any(str(term).lower() in {"vie", "variable interest entity", "contractual arrangements"} for term in matched_terms):
        issues.append("VIE or contractual-arrangement language exists; legal ownership and accounting consolidation should be separated.")
    if any(str(term).lower() in {"voting power", "beneficial ownership", "dual-class"} for term in matched_terms):
        issues.append("Voting power / beneficial ownership language exists; controller economics versus votes requires table-level extraction.")
    if _topic_hits(annual_report_evidence, "leadership_disclosure"):
        issues.append("Annual report contains leadership/governance disclosure that should be mapped to named people and entities.")
    risk_level = "needs_review" if issues else "unknown"
    if not cards and not issues:
        risk_level = "not_evaluated"
    return {
        "status": "source_mapped" if cards or issues else "not_evaluated",
        "evidence_bucket": "fact",
        "source_quality": "official_filing_high",
        "risk_level": risk_level,
        "known_terms": matched_terms,
        "control_gap": "not_extracted",
        "controller_table_status": "pending_structured_extraction",
        "minority_owner_protection_status": "pending_review",
        "findings": issues or ["Control map cannot be judged until ownership/voting evidence is extracted."],
        "next_actions": [
            "Extract beneficial ownership and voting power by person/entity.",
            "Separate economic ownership from voting/control rights.",
            "Identify VIE, controlled-company, home-country, or minority-owner protection limitations.",
        ],
    }


def _incentive_map(
    financial_signals: list[dict[str, Any]],
    filing_cards: list[dict[str, Any]],
) -> dict[str, Any]:
    sbc = _signal_by_id(financial_signals, "sbc_burden")
    dilution = _signal_by_id(financial_signals, "diluted_share_growth")
    cards = _cards_by_group(filing_cards, "incentives_and_compensation")
    positives = []
    concerns = []
    if sbc:
        if sbc.get("tone") == "support":
            positives.append(str(sbc.get("read")))
        else:
            concerns.append(str(sbc.get("read")))
    if dilution:
        if dilution.get("tone") == "support":
            positives.append(str(dilution.get("read")))
        else:
            concerns.append(str(dilution.get("read")))
    if cards:
        positives.append("Official filings contain compensation / share-incentive evidence for review.")
    concerns.append("Named-executive pay metrics and pay-versus-performance alignment are not yet parsed.")
    return {
        "status": "partial_evidence" if sbc or dilution or cards else "not_evaluated",
        "evidence_bucket": "inference",
        "source_quality": "official_filing_high",
        "sbc_burden": sbc,
        "dilution": dilution,
        "positive_signals": positives,
        "concerns_or_unknowns": concerns,
        "pay_for_performance_status": "pending_structured_extraction",
        "per_share_value_alignment": "not_proven",
        "current_read": (
            "SBC and dilution are measurable and currently look supportive where calculated, but true pay-for-performance alignment is not proven."
            if positives
            else "Incentive alignment cannot be evaluated yet."
        ),
    }


def _capital_allocation_ledger(
    state: ResearchState,
    financial_signals: list[dict[str, Any]],
    filing_cards: list[dict[str, Any]],
) -> dict[str, Any]:
    facts = state.get("extracted_facts", [])
    metrics = state.get("metrics", [])
    years = sorted(
        {
            int(str(fact.get("end_date", ""))[:4])
            for fact in facts
            if str(fact.get("end_date", ""))[:4].isdigit()
            and fact.get("period_type") in {"annual", "year", "duration"}
        }
        | {
            int(row.get("year"))
            for metric in metrics
            for row in metric.get("annual_results", [])
            if row.get("status") == "calculated" and row.get("year") is not None
        }
    )
    rows = []
    for year in years[-6:]:
        margin = _metric_result_by_year(metrics, "margin_profile_v1", year)
        capex = _metric_result_by_year(metrics, "capital_intensity_v1", year)
        cash_conversion = _metric_result_by_year(metrics, "cash_conversion_ratio_v1", year)
        sbc = _metric_result_by_year(metrics, "share_based_compensation_burden_v1", year)
        owner = _metric_result_by_year(metrics, "owner_earnings_v1", year)
        roic = _metric_result_by_year(metrics, "unlevered_roic_v1", year)
        incremental_roic = _metric_result_by_year(metrics, "incremental_roic_proxy_v1", year)
        rows.append(
            {
                "year": year,
                "revenue": _annual_fact_value(facts, "revenue", year),
                "operating_cash_flow": _annual_fact_value(facts, "operating_cash_flow", year),
                "capex": _annual_fact_value(facts, "capex", year),
                "free_cash_flow": _annual_fact_value(facts, "free_cash_flow", year)
                or (margin or {}).get("free_cash_flow"),
                "owner_earnings_proxy": (owner or {}).get("value"),
                "sbc": _annual_fact_value(facts, "stock_based_compensation", year),
                "diluted_shares": _annual_fact_value(facts, "diluted_shares", year),
                "cash": _instant_fact_value(facts, "cash", year),
                "short_term_investments": _instant_fact_value(facts, "short_term_investments", year),
                "free_cash_flow_margin": (margin or {}).get("free_cash_flow_margin"),
                "capex_to_revenue": (capex or {}).get("capex_to_revenue"),
                "cash_conversion": (cash_conversion or {}).get("value"),
                "sbc_to_revenue": (sbc or {}).get("sbc_to_revenue"),
                "diluted_shares_yoy": (sbc or {}).get("diluted_shares_yoy"),
                "roic_proxy": (roic or {}).get("value"),
                "incremental_roic_proxy": (incremental_roic or {}).get("value"),
            }
        )
    signals = {
        signal.get("signal_id"): signal
        for signal in financial_signals
        if signal.get("signal_id")
        in {
            "free_cash_flow_margin",
            "capital_intensity",
            "cash_conversion",
            "roic_proxy",
            "incremental_roic_proxy",
            "incremental_operating_margin",
        }
    }
    concern_signals = [
        signal.get("read")
        for signal in signals.values()
        if signal.get("tone") == "concern" and signal.get("read")
    ]
    support_signals = [
        signal.get("read")
        for signal in signals.values()
        if signal.get("tone") == "support" and signal.get("read")
    ]
    return {
        "status": "ledger_built" if rows else "not_evaluated",
        "evidence_bucket": "inference",
        "source_quality": "official_financial_metrics_high",
        "row_count": len(rows),
        "rows": rows,
        "capital_allocation_terms": sorted(
            {term for card in _cards_by_group(filing_cards, "capital_allocation") for term in card.get("matched_terms", [])}
        ),
        "support_signals": support_signals,
        "concern_signals": concern_signals,
        "current_read": _capital_allocation_read(support_signals, concern_signals),
        "limitations": [
            "Maintenance versus growth reinvestment is still a proxy.",
            "Buyback/dividend/M&A and investment-asset decisions need a fuller cash-use bridge.",
        ],
    }


def _communication_audit(
    transcript_signals: dict[str, Any],
    financial_signals: list[dict[str, Any]],
) -> dict[str, Any]:
    claim_counts = transcript_signals.get("claim_counts") or {}
    timeline = transcript_signals.get("claim_timeline") or {}
    outcome_checks = []
    incremental_margin = _signal_by_id(financial_signals, "incremental_operating_margin")
    incremental_roic = _signal_by_id(financial_signals, "incremental_roic_proxy")
    operating_margin = _signal_by_id(financial_signals, "operating_margin")
    if claim_counts.get("long_term_investment"):
        outcome_checks.append(
            {
                "claim_theme": "long_term_investment",
                "claim_count": claim_counts.get("long_term_investment", 0),
                "later_outcome_signal": (incremental_margin or {}).get("read"),
                "verdict": (
                    "needs_review"
                    if (incremental_margin or {}).get("tone") == "concern"
                    else "partially_supported"
                ),
                "read": "Long-term investment language should be tested against later margins, cash flow, and incremental returns.",
            }
        )
    if claim_counts.get("competition_and_pressure"):
        outcome_checks.append(
            {
                "claim_theme": "competition_and_pressure",
                "claim_count": claim_counts.get("competition_and_pressure", 0),
                "later_outcome_signal": (operating_margin or {}).get("read"),
                "verdict": "needs_review",
                "read": "Competition/pressure commentary is present; check whether management explains margin changes directly.",
            }
        )
    if claim_counts.get("capital_allocation"):
        outcome_checks.append(
            {
                "claim_theme": "capital_allocation",
                "claim_count": claim_counts.get("capital_allocation", 0),
                "later_outcome_signal": (incremental_roic or {}).get("read"),
                "verdict": (
                    "needs_review"
                    if (incremental_roic or {}).get("tone") == "concern"
                    else "partially_supported"
                ),
                "read": "Capital-allocation language needs a promise-versus-outcome table before it can support right people.",
            }
        )
    return {
        "status": "audit_seeded" if claim_counts else "not_evaluated",
        "evidence_bucket": "management_claim",
        "source_quality": "official_or_provider_transcript_medium",
        "claim_counts": claim_counts,
        "claim_timeline": timeline,
        "outcome_checks": outcome_checks,
        "prepared_vs_qa_status": "not_yet_separated",
        "evasiveness_status": "not_yet_scored",
        "current_read": (
            "Management-priority claims are collected and linked to first-pass outcome checks, but evasiveness and promise fulfillment are not fully scored."
            if claim_counts
            else "No transcript claims available for communication audit."
        ),
    }


def _red_flag_matrix(red_flags: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for flag in red_flags:
        severity = str(flag.get("severity") or "medium")
        hard_override = severity == "high" or any(
            token in str(flag.get("flag_id") or "").lower()
            for token in ["non_reliance", "restatement", "material_weakness", "auditor_resignation"]
        )
        rows.append(
            {
                "flag_id": flag.get("flag_id"),
                "severity": severity,
                "hard_override": hard_override,
                "evidence_bucket": flag.get("evidence_bucket", "fact"),
                "source": flag.get("source"),
                "read": flag.get("read"),
            }
        )
    counts = Counter(str(row.get("severity")) for row in rows)
    return {
        "status": "review_items_found" if rows else "no_review_items_promoted",
        "row_count": len(rows),
        "severity_counts": dict(sorted(counts.items())),
        "hard_override_count": sum(1 for row in rows if row.get("hard_override")),
        "rows": rows,
        "current_read": (
            "Hard override exists; right-people gate cannot pass until reviewed."
            if any(row.get("hard_override") for row in rows)
            else "Review flags exist but no hard override was promoted by V1."
            if rows
            else "No promoted integrity/governance review flags."
        ),
    }


def _right_people_scorecard(
    *,
    control_map: dict[str, Any],
    incentive_map: dict[str, Any],
    capital_allocation_ledger: dict[str, Any],
    communication_audit: dict[str, Any],
    red_flag_matrix: dict[str, Any],
    financial_signals: list[dict[str, Any]],
) -> dict[str, Any]:
    dimensions = [
        _score_dimension(
            "integrity_and_candor",
            30,
            _integrity_score(red_flag_matrix, communication_audit),
            red_flag_matrix.get("current_read"),
            "Red flags, source separation, bad-news explanation, and future evasiveness review.",
        ),
        _score_dimension(
            "incentive_alignment",
            20,
            _incentive_score(incentive_map),
            incentive_map.get("current_read"),
            "SBC, dilution, ownership/pay metrics, and per-share orientation.",
        ),
        _score_dimension(
            "capital_allocation",
            20,
            _capital_allocation_score(capital_allocation_ledger),
            capital_allocation_ledger.get("current_read"),
            "Cash conversion, CapEx intensity, FCF, ROIC, incremental returns, buybacks/dividends/M&A.",
        ),
        _score_dimension(
            "control_and_governance",
            15,
            _control_score(control_map),
            "; ".join(control_map.get("findings", [])[:2]),
            "Control map, voting/economic ownership gap, VIE, board and minority-owner protections.",
        ),
        _score_dimension(
            "execution_quality",
            10,
            _execution_score(financial_signals),
            _execution_read(financial_signals),
            "Revenue quality, margin trend, cash conversion, ROIC and incremental returns.",
        ),
        _score_dimension(
            "behavior_in_stress",
            5,
            _stress_behavior_score(communication_audit),
            communication_audit.get("current_read"),
            "Competition/pressure language, Q&A directness, and promise-versus-outcome behavior.",
        ),
    ]
    weighted_score = sum(float(item["weighted_points"]) for item in dimensions)
    return {
        "status": "calculated",
        "scale": "-2 to +2 raw score per dimension; weighted score is normalized to 0-100.",
        "weighted_score": round(weighted_score, 1),
        "dimensions": dimensions,
        "limits": [
            "Scores are gatekeeping heuristics, not investment conclusions.",
            "A hard integrity override can block the gate even if the weighted score looks adequate.",
        ],
    }


def _right_people_decision(
    *,
    scorecard: dict[str, Any],
    red_flags: list[dict[str, Any]],
    checklist: list[dict[str, Any]],
) -> dict[str, Any]:
    high_flags = [flag for flag in red_flags if flag.get("severity") == "high"]
    weighted_score = float(scorecard.get("weighted_score") or 0)
    unresolved = [
        item.get("item")
        for item in checklist
        if item.get("status") in {"needs_review", "not_evaluated"}
    ]
    unresolved.extend(
        item.get("dimension_id")
        for item in scorecard.get("dimensions", [])
        if item.get("requires_analyst_review")
    )
    if high_flags:
        status = "does_not_pass_pending_red_flag_review"
        read = "does_not_pass_yet: high-severity governance, integrity, or verification flags must be resolved first."
    elif weighted_score >= 72 and not unresolved:
        status = "passes_v1_with_open_questions"
        read = "passes_v1: evidence is broadly supportive, but analyst review is still required before relying on the judgment."
    elif weighted_score >= 55:
        status = "partial_pass_needs_deeper_review"
        read = "partial_pass: financial outcomes and some incentive evidence are supportive, but control, pay-for-performance, communication fulfillment, and review flags are not resolved."
    else:
        status = "does_not_pass_v1_needs_review"
        read = "does_not_pass_yet: current evidence is too incomplete or cautionary to support right people."
    return {
        "status": status,
        "current_read": read,
        "weighted_score": weighted_score,
        "confidence": "medium" if weighted_score >= 55 and not high_flags else "low",
        "hard_overrides": [
            {
                "flag_id": flag.get("flag_id"),
                "severity": flag.get("severity"),
                "read": flag.get("read"),
            }
            for flag in high_flags
        ],
        "unresolved_gate_items": [item for item in dict.fromkeys(unresolved) if item],
        "not_buy_sell_recommendation": True,
    }


def _governance_control_subagent(
    annual_report_evidence: dict[str, Any],
    filing_cards: list[dict[str, Any]],
) -> dict[str, Any]:
    cards = _cards_by_group(filing_cards, "control_and_governance")
    total_hits = _topic_hits(annual_report_evidence, "leadership_disclosure")
    status = "functional_v1_official_filing_based" if cards or total_hits else "limited_no_source_evidence"
    concerns = []
    if _card_has_term(cards, "variable interest entity") or _card_has_term(cards, "VIE"):
        concerns.append("VIE / contractual-arrangement structure requires governance and cash-control review.")
    if _card_has_term(cards, "voting power"):
        concerns.append("Voting-power disclosure exists; shareholder-control rights should be reviewed.")
    return {
        "agent_id": "governance_control_reader",
        "name": "Governance / Control Reader",
        "status": status,
        "working_level": "functional_v1_for_annual_reports",
        "current_read": (
            "Official filings contain governance and control evidence; V1 maps the issues but does not yet score minority-shareholder protection."
            if status.startswith("functional")
            else "No useful governance/control evidence found yet."
        ),
        "evidence_records": len(cards),
        "findings": concerns or ["Governance/control section is source-mapped but needs issuer-specific review."],
        "source_quality": "official_filing_high",
        "limits": [
            "A term hit does not prove good or bad governance.",
            "Minority-shareholder rights require document-level review of voting power, VIE, and board structure.",
        ],
        "next_build": [
            "Extract named directors/officers and voting power into a structured table.",
            "Add year-over-year management and board-change history.",
        ],
    }


def _incentive_alignment_subagent(
    annual_report_evidence: dict[str, Any],
    financial_signals: list[dict[str, Any]],
    filing_cards: list[dict[str, Any]],
) -> dict[str, Any]:
    cards = _cards_by_group(filing_cards, "incentives_and_compensation")
    sbc = _signal_by_id(financial_signals, "sbc_burden")
    dilution = _signal_by_id(financial_signals, "diluted_share_growth")
    findings = []
    if sbc:
        findings.append(str(sbc.get("read")))
    if dilution:
        findings.append(str(dilution.get("read")))
    if cards:
        findings.append("Official filings contain share-incentive / compensation disclosures for source review.")
    total_hits = _topic_hits(annual_report_evidence, "incentives_and_ownership")
    status = "partially_supported" if findings or total_hits else "missing_key_inputs"
    return {
        "agent_id": "incentive_alignment_analyst",
        "name": "Incentive Alignment Analyst",
        "status": status,
        "working_level": "functional_v1_for_sbc_and_dilution",
        "current_read": (
            "SBC and dilution are measurable from official financial facts; full pay-for-performance alignment is still not proven."
            if status == "partially_supported"
            else "Incentive alignment cannot be evaluated yet."
        ),
        "evidence_records": len(cards) + len([x for x in [sbc, dilution] if x]),
        "findings": findings or ["Need ownership, compensation, and dilution data."],
        "source_quality": "official_filing_high",
        "limits": [
            "SBC ratio and dilution are necessary but not sufficient to prove alignment.",
            "V1 does not yet parse named-executive compensation metrics into a pay-for-performance table.",
        ],
        "next_build": [
            "Extract beneficial ownership and voting power by person/entity.",
            "Connect buybacks to diluted share-count changes.",
        ],
    }


def _capital_allocation_subagent(
    financial_signals: list[dict[str, Any]],
    filing_cards: list[dict[str, Any]],
    transcript_signals: dict[str, Any],
) -> dict[str, Any]:
    relevant = [
        signal
        for signal in financial_signals
        if signal.get("signal_id")
        in {
            "capital_intensity",
            "free_cash_flow_margin",
            "cash_conversion",
            "roic_proxy",
            "incremental_roic_proxy",
        }
    ]
    cards = _cards_by_group(filing_cards, "capital_allocation")
    transcript_count = transcript_signals.get("claim_counts", {}).get("capital_allocation", 0)
    findings = [str(signal.get("read")) for signal in relevant if signal.get("read")]
    if transcript_count:
        findings.append(f"Management transcript evidence includes {transcript_count} capital-allocation related matches.")
    status = "partially_supported" if relevant or cards or transcript_count else "missing_key_inputs"
    return {
        "agent_id": "capital_allocation_historian",
        "name": "Capital Allocation Historian",
        "status": status,
        "working_level": "functional_v1_for_financial_outcomes",
        "current_read": (
            "V1 connects reinvestment, cash conversion, ROIC proxy, and management capital-allocation language; causality still needs deeper review."
            if status == "partially_supported"
            else "Capital allocation history is not evaluable yet."
        ),
        "evidence_records": len(relevant) + len(cards) + int(bool(transcript_count)),
        "findings": findings or ["Need cash-use, buyback, dividend, investment, and M&A history."],
        "source_quality": "official_filing_high_plus_transcript_medium",
        "limits": [
            "ROIC and incremental ROIC are proxies and can be noisy for cash-heavy or investment-heavy companies.",
            "Management language about long-term investment must be tested against later margins, cash flow, and per-share value.",
        ],
        "next_build": [
            "Build a 5-year cash-use bridge: reinvestment, buybacks, dividends, acquisitions, investments, and cash build.",
            "Add a promise-versus-outcome timeline from transcripts and subsequent financial results.",
        ],
    }


def _management_communication_subagent(transcript_signals: dict[str, Any]) -> dict[str, Any]:
    signal_count = transcript_signals.get("signal_count", 0)
    claim_counts = transcript_signals.get("claim_counts", {})
    findings = []
    for claim_id, count in sorted(claim_counts.items(), key=lambda item: item[1], reverse=True)[:5]:
        findings.append(f"{claim_id}: {count} matched evidence items")
    status = "functional_v1_transcript_based" if signal_count else "pending_transcript_evidence"
    return {
        "agent_id": "management_communication_auditor",
        "name": "Management Communication Auditor",
        "status": status,
        "working_level": "functional_v1_for_cached_transcripts",
        "current_read": (
            "Cached transcripts provide management-priority evidence; V1 counts and samples claims but does not yet judge evasiveness."
            if signal_count
            else "No transcript evidence available for communication quality."
        ),
        "evidence_records": signal_count,
        "findings": findings or ["Need earnings-call or executive-interview transcript evidence."],
        "source_quality": "official_or_provider_transcript_medium",
        "limits": [
            "Prepared remarks are management framing.",
            "Q&A tone and consistency require a later promise-versus-outcome and evasiveness review.",
        ],
        "next_build": [
            "Separate prepared remarks from Q&A.",
            "Track repeated claims and whether later filings confirm or contradict them.",
        ],
    }


def _execution_track_record_subagent(financial_signals: list[dict[str, Any]]) -> dict[str, Any]:
    signal_ids = {
        "revenue_growth",
        "operating_margin",
        "incremental_operating_margin",
        "cash_conversion",
        "roic_proxy",
        "incremental_roic_proxy",
    }
    relevant = [signal for signal in financial_signals if signal.get("signal_id") in signal_ids]
    concerns = [signal for signal in relevant if signal.get("tone") == "concern"]
    support = [signal for signal in relevant if signal.get("tone") == "support"]
    status = "partially_supported" if relevant else "missing_financial_outcomes"
    read = "Financial outcomes support parts of execution quality but also show issues requiring review."
    if relevant and concerns and not support:
        read = "Financial outcome evidence is mostly cautionary for execution quality."
    elif relevant and support and not concerns:
        read = "Financial outcome evidence is broadly supportive of execution quality."
    return {
        "agent_id": "execution_track_record_analyst",
        "name": "Execution Track Record Analyst",
        "status": status,
        "working_level": "functional_v1_for_financial_metrics",
        "current_read": read if relevant else "Execution track record cannot be evaluated yet.",
        "evidence_records": len(relevant),
        "findings": [str(signal.get("read")) for signal in relevant if signal.get("read")]
        or ["Need multi-year revenue, margin, cash conversion, and ROIC history."],
        "source_quality": "official_financial_metrics_high",
        "limits": [
            "Strong financial outcomes can support execution skill but cannot identify which leader created the result.",
            "Weak margin or incremental-return signals require cause analysis before judging management quality.",
        ],
        "next_build": [
            "Add an explicit promise-versus-outcome table by management tenure.",
            "Separate operating execution from macro, competition, and accounting effects.",
        ],
    }


def _integrity_red_flag_subagent(
    red_flags: list[dict[str, Any]],
    filing_cards: list[dict[str, Any]],
) -> dict[str, Any]:
    cards = _cards_by_group(filing_cards, "integrity_red_flags")
    high = [flag for flag in red_flags if flag.get("severity") == "high"]
    status = "review_required" if high else "no_high_priority_red_flag_detected_v1"
    findings = [f"{flag.get('flag_id')}: {flag.get('read')}" for flag in red_flags[:6]]
    if cards and not findings:
        findings.append("Official filings contain integrity/red-flag search terms; review snippets before drawing conclusions.")
    return {
        "agent_id": "integrity_red_flag_scanner",
        "name": "Integrity / Red Flag Scanner",
        "status": status,
        "working_level": "functional_v1_for_existing_events_and_conflicts",
        "current_read": (
            "High-severity review items exist; they must be resolved before strong right-people support."
            if high
            else "No high-priority management/governance red flag was promoted by V1, but this is not a full forensic review."
        ),
        "evidence_records": len(red_flags) + len(cards),
        "findings": findings or ["No promoted red flags from existing material-event scan and verification results."],
        "source_quality": "official_filing_high",
        "limits": [
            "No detected red flag is not proof of integrity.",
            "V1 depends on existing material-event scanning and official filing text coverage.",
        ],
        "next_build": [
            "Add auditor-change, related-party, and management-turnover history tables.",
            "Add a dedicated related-party transaction reader.",
        ],
    }


def _official_filing_cards(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    document = latest_annual_report_document(documents)
    if not document or not document.get("local_path"):
        return []
    path = Path(str(document["local_path"]))
    if not path.exists():
        return []
    text = _read_text(path)
    cards: list[dict[str, Any]] = []
    for group_id, terms in OFFICIAL_FILING_TERM_GROUPS.items():
        snippets = _snippets_for_terms(text, terms, limit=6)
        if not snippets:
            continue
        cards.append(
            {
                "group_id": group_id,
                "evidence_bucket": "fact",
                "source_quality": "official_filing_high",
                "source_document": {
                    "document_id": document.get("document_id"),
                    "filing_date": document.get("filing_date"),
                    "local_path": document.get("local_path"),
                    "source_url": document.get("source_url"),
                },
                "matched_terms": sorted({snippet["matched_term"] for snippet in snippets}),
                "snippets": snippets,
                "limitation": "Term-level evidence card. It identifies where to review, not whether management is good or bad.",
            }
        )
    return cards


def _financial_signals(state: ResearchState) -> list[dict[str, Any]]:
    metrics = state.get("metrics", [])
    signals: list[dict[str, Any]] = []

    margin = _latest_metric_result(metrics, "margin_profile_v1")
    if margin:
        signals.append(
            {
                "signal_id": "revenue_growth",
                "evidence_bucket": "inference",
                "source": "financial_metrics",
                "value": margin.get("revenue_growth_yoy"),
                "unit": "ratio",
                "tone": "support" if _as_float(margin.get("revenue_growth_yoy"), 0) > 0 else "neutral",
                "read": f"Latest annual revenue growth is {_percent_text(margin.get('revenue_growth_yoy'))}.",
                "source_fact_ids": margin.get("source_fact_ids", []),
            }
        )
        signals.append(
            {
                "signal_id": "operating_margin",
                "evidence_bucket": "inference",
                "source": "financial_metrics",
                "value": margin.get("operating_margin"),
                "unit": "ratio",
                "tone": "support" if _as_float(margin.get("operating_margin"), 0) > 0.15 else "concern",
                "read": f"Latest annual operating margin is {_percent_text(margin.get('operating_margin'))}.",
                "source_fact_ids": margin.get("source_fact_ids", []),
            }
        )
        signals.append(
            {
                "signal_id": "free_cash_flow_margin",
                "evidence_bucket": "inference",
                "source": "financial_metrics",
                "value": margin.get("free_cash_flow_margin"),
                "unit": "ratio",
                "tone": "support" if _as_float(margin.get("free_cash_flow_margin"), 0) > 0.10 else "concern",
                "read": f"Latest annual FCF margin is {_percent_text(margin.get('free_cash_flow_margin'))}.",
                "source_fact_ids": margin.get("source_fact_ids", []),
            }
        )

    incremental_margin = _latest_metric_result(metrics, "incremental_margin_v1")
    if incremental_margin:
        value = incremental_margin.get("incremental_operating_margin")
        signals.append(
            {
                "signal_id": "incremental_operating_margin",
                "evidence_bucket": "inference",
                "source": "financial_metrics",
                "value": value,
                "unit": "ratio",
                "tone": "concern" if _as_float(value, 0) < 0 else "support",
                "read": f"Latest incremental operating margin is {_percent_text(value)}.",
                "source_fact_ids": incremental_margin.get("source_fact_ids", []),
            }
        )

    capital_intensity = _latest_metric_result(metrics, "capital_intensity_v1")
    if capital_intensity:
        value = capital_intensity.get("capex_to_revenue")
        signals.append(
            {
                "signal_id": "capital_intensity",
                "evidence_bucket": "inference",
                "source": "financial_metrics",
                "value": value,
                "unit": "ratio",
                "tone": "support" if _as_float(value, 1) < 0.05 else "concern",
                "read": f"Latest CapEx / revenue is {_percent_text(value)}.",
                "source_fact_ids": capital_intensity.get("source_fact_ids", []),
            }
        )

    cash_conversion = _latest_metric_result(metrics, "cash_conversion_ratio_v1")
    if cash_conversion:
        value = cash_conversion.get("value")
        signals.append(
            {
                "signal_id": "cash_conversion",
                "evidence_bucket": "inference",
                "source": "financial_metrics",
                "value": value,
                "unit": "ratio",
                "tone": "support" if _as_float(value, 0) >= 1 else "concern",
                "read": f"Latest CFO / net income is {_ratio_text(value)}.",
                "source_fact_ids": cash_conversion.get("source_fact_ids", []),
            }
        )

    sbc = _latest_metric_result(metrics, "share_based_compensation_burden_v1")
    if sbc:
        sbc_revenue = sbc.get("sbc_to_revenue")
        sbc_cfo = sbc.get("sbc_to_operating_cash_flow")
        diluted_yoy = sbc.get("diluted_shares_yoy")
        signals.extend(
            [
                {
                    "signal_id": "sbc_burden",
                    "evidence_bucket": "inference",
                    "source": "financial_metrics",
                    "value": sbc_revenue,
                    "unit": "ratio",
                    "tone": "support" if _as_float(sbc_revenue, 1) < 0.05 else "concern",
                    "read": (
                        f"Latest SBC / revenue is {_percent_text(sbc_revenue)} and "
                        f"SBC / CFO is {_percent_text(sbc_cfo)}."
                    ),
                    "source_fact_ids": sbc.get("source_fact_ids", []),
                },
                {
                    "signal_id": "diluted_share_growth",
                    "evidence_bucket": "inference",
                    "source": "financial_metrics",
                    "value": diluted_yoy,
                    "unit": "ratio",
                    "tone": "support" if _as_float(diluted_yoy, 1) < 0.02 else "concern",
                    "read": f"Latest diluted share-count growth is {_percent_text(diluted_yoy)}.",
                    "source_fact_ids": sbc.get("source_fact_ids", []),
                },
            ]
        )

    roic = _latest_metric_result(metrics, "unlevered_roic_v1")
    if roic:
        value = roic.get("value")
        signals.append(
            {
                "signal_id": "roic_proxy",
                "evidence_bucket": "inference",
                "source": "financial_metrics",
                "value": value,
                "unit": "ratio",
                "tone": "support" if _as_float(value, 0) > 0 else "neutral",
                "read": f"Latest unlevered ROIC proxy is {_percent_text(value)}.",
                "review_required": bool(roic.get("review_required")),
                "source_fact_ids": roic.get("source_fact_ids", []),
            }
        )

    incremental_roic = _latest_metric_result(metrics, "incremental_roic_proxy_v1")
    if incremental_roic:
        value = incremental_roic.get("value")
        signals.append(
            {
                "signal_id": "incremental_roic_proxy",
                "evidence_bucket": "inference",
                "source": "financial_metrics",
                "value": value,
                "unit": "ratio",
                "tone": "concern" if _as_float(value, 0) < 0 else "support",
                "read": f"Latest incremental ROIC proxy is {_percent_text(value)}.",
                "review_required": bool(incremental_roic.get("review_required")),
                "source_fact_ids": incremental_roic.get("source_fact_ids", []),
            }
        )

    return signals


def _management_transcript_signals(state: ResearchState) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for source_key in ("official_event_transcript_findings", "executive_transcript_findings"):
        findings = state.get(source_key) or {}
        for item in findings.get("evidence_items", []):
            claim_id = str(item.get("claim_id") or "")
            if claim_id in MANAGEMENT_EVIDENCE_CLAIMS:
                items.append({**item, "source_collection": source_key})
        for result in findings.get("source_results", []):
            for question in result.get("business_model_question_results", []):
                question_id = str(question.get("question_id") or "")
                if question_id in MANAGEMENT_EVIDENCE_CLAIMS and question.get("answer_status") == "evidence_found":
                    items.append({**question, "source_collection": source_key})

    claim_counts = Counter(str(item.get("claim_id") or item.get("question_id") or "unknown") for item in items)
    source_counts = Counter(str(item.get("source_collection") or "unknown") for item in items)
    timeline: dict[str, dict[str, Any]] = {}
    for item in items:
        claim_id = str(item.get("claim_id") or item.get("question_id") or "unknown")
        quarter = str(item.get("quarter") or item.get("period") or "unknown")
        bucket = timeline.setdefault(
            claim_id,
            {
                "claim_id": claim_id,
                "count": 0,
                "period_counts": Counter(),
                "first_period": None,
                "latest_period": None,
                "sample_excerpt": "",
            },
        )
        bucket["count"] += 1
        bucket["period_counts"][quarter] += 1
        if quarter != "unknown":
            periods = [p for p in bucket["period_counts"] if p != "unknown"]
            if periods:
                bucket["first_period"] = sorted(periods)[0]
                bucket["latest_period"] = sorted(periods)[-1]
        if not bucket["sample_excerpt"]:
            bucket["sample_excerpt"] = _trim_text(item.get("excerpt") or item.get("answer") or "", 220)
    timeline_output = []
    for claim_id, item in sorted(timeline.items()):
        timeline_output.append(
            {
                "claim_id": claim_id,
                "count": item["count"],
                "first_period": item["first_period"],
                "latest_period": item["latest_period"],
                "period_counts": dict(sorted(item["period_counts"].items())),
                "sample_excerpt": item["sample_excerpt"],
            }
        )
    samples = []
    for item in items[:8]:
        samples.append(
            {
                "claim_id": item.get("claim_id") or item.get("question_id"),
                "evidence_bucket": "management_claim",
                "source": item.get("source_name") or item.get("source_id") or item.get("source_collection"),
                "quarter": item.get("quarter"),
                "speaker": item.get("speaker"),
                "excerpt": _trim_text(item.get("excerpt") or item.get("answer") or "", 260),
                "source_quality_tier": item.get("source_quality_tier"),
                "limitation": item.get("limitation") or "Management transcript evidence; not independent proof.",
            }
        )
    return {
        "status": "evidence_collected" if items else "no_management_transcript_evidence",
        "signal_count": len(items),
        "claim_counts": dict(sorted(claim_counts.items())),
        "claim_timeline": timeline_output,
        "source_counts": dict(sorted(source_counts.items())),
        "samples": samples,
    }


def _red_flags(state: ResearchState, *, filing_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    scan = state.get("material_event_scan") or {}
    for event in scan.get("events", []):
        if event.get("severity") in {"high", "medium"}:
            flags.append(
                {
                    "flag_id": f"material_event_{event.get('event_type', 'unknown')}",
                    "evidence_bucket": "fact",
                    "severity": event.get("severity", "medium"),
                    "read": event.get("summary") or event.get("description") or "Material event requires review.",
                    "source": "material_event_scan",
                    "source_document": event.get("source_document"),
                }
            )
    for result in state.get("verification_results", []):
        if result.get("status") == "material_conflict":
            period = result.get("end_date") or result.get("instant") or result.get("period") or "unknown period"
            flags.append(
                {
                    "flag_id": "official_fact_material_conflict",
                    "evidence_bucket": "fact",
                    "severity": "medium",
                    "read": (
                        f"{result.get('metric')} conflict for {period} "
                        f"({result.get('mismatch_pct', 0) * 100:.1f}% mismatch)."
                    ),
                    "source": "financial_verification",
                    "metric": result.get("metric"),
                }
            )
    for card in _cards_by_group(filing_cards, "integrity_red_flags"):
        flags.append(
            {
                "flag_id": "official_filing_integrity_terms",
                "evidence_bucket": "fact",
                "severity": "medium",
                "read": "Official filing contains integrity/red-flag terms that should be reviewed in context.",
                "source": "official_filing_term_scan",
                "matched_terms": card.get("matched_terms", []),
                "source_document": card.get("source_document"),
            }
        )
    return flags


def _right_people_checklist(
    subagents: list[dict[str, Any]],
    red_flags: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = {item.get("agent_id"): item for item in subagents}
    high_flags = [flag for flag in red_flags if flag.get("severity") == "high"]
    return [
        {
            "item": "Understand who controls the company",
            "status": _support_status(by_id.get("governance_control_reader")),
            "basis": "Governance, board, ownership, voting-power, and VIE/control disclosures.",
            "limitation": "Needs structured ownership/voting table before final judgment.",
        },
        {
            "item": "Management incentives align with per-share value",
            "status": _support_status(by_id.get("incentive_alignment_analyst")),
            "basis": "SBC, dilution, ownership, and share-incentive disclosures.",
            "limitation": "V1 does not yet parse named-executive pay metrics or full beneficial ownership.",
        },
        {
            "item": "Capital allocation is rational and long-term",
            "status": _support_status(by_id.get("capital_allocation_historian")),
            "basis": "Cash conversion, CapEx intensity, ROIC proxy, reinvestment language, buyback/dividend terms.",
            "limitation": "Needs a 5-year cash-use bridge and promise-versus-outcome review.",
        },
        {
            "item": "Management communication is source-checkable",
            "status": _support_status(by_id.get("management_communication_auditor")),
            "basis": "Cached earnings-call and executive-transcript evidence.",
            "limitation": "V1 counts themes; it does not yet rate evasiveness or consistency in Q&A.",
        },
        {
            "item": "Execution record supports trust",
            "status": _support_status(by_id.get("execution_track_record_analyst")),
            "basis": "Revenue growth, margin trend, cash conversion, ROIC proxy, incremental-return evidence.",
            "limitation": "Financial outcomes support management assessment but do not prove individual skill.",
        },
        {
            "item": "No unresolved severe integrity/governance red flag",
            "status": "needs_review" if high_flags else "partially_supported",
            "basis": "Material-event scan, official filing red-flag terms, and official-fact verification conflicts.",
            "limitation": "No red flag detected is not proof of integrity.",
        },
    ]


def _capital_allocation_read(support_signals: list[Any], concern_signals: list[Any]) -> str:
    if support_signals and concern_signals:
        return "Mixed: strong cash-generation/capital-light signals exist, but incremental margin or incremental return concerns require review."
    if support_signals:
        return "Supportive: official financial outcomes show cash generation and capital efficiency, subject to cash-use review."
    if concern_signals:
        return "Cautionary: capital-allocation or incremental-return signals require review."
    return "Not enough capital-allocation evidence yet."


def _score_dimension(
    dimension_id: str,
    weight: int,
    raw_score: float,
    read: Any,
    evidence_basis: str,
) -> dict[str, Any]:
    raw = max(-2.0, min(2.0, float(raw_score)))
    weighted_points = ((raw + 2.0) / 4.0) * weight
    return {
        "dimension_id": dimension_id,
        "weight": weight,
        "raw_score": round(raw, 2),
        "weighted_points": round(weighted_points, 1),
        "current_read": _trim_text(str(read or ""), 320),
        "evidence_basis": evidence_basis,
        "requires_analyst_review": raw < 1.25,
    }


def _integrity_score(red_flag_matrix: dict[str, Any], communication_audit: dict[str, Any]) -> float:
    hard = int(red_flag_matrix.get("hard_override_count") or 0)
    rows = int(red_flag_matrix.get("row_count") or 0)
    if hard:
        return -2.0
    if rows >= 8:
        return -0.75
    if rows:
        return -0.35
    if communication_audit.get("status") == "audit_seeded":
        return 0.25
    return 0.0


def _incentive_score(incentive_map: dict[str, Any]) -> float:
    score = 0.0
    sbc = incentive_map.get("sbc_burden") or {}
    dilution = incentive_map.get("dilution") or {}
    if sbc.get("tone") == "support":
        score += 0.7
    elif sbc:
        score -= 0.7
    if dilution.get("tone") == "support":
        score += 0.7
    elif dilution:
        score -= 0.7
    if incentive_map.get("pay_for_performance_status") == "pending_structured_extraction":
        score -= 0.25
    return score


def _capital_allocation_score(ledger: dict[str, Any]) -> float:
    score = 0.0
    score += min(1.0, 0.25 * len(ledger.get("support_signals") or []))
    score -= min(1.25, 0.45 * len(ledger.get("concern_signals") or []))
    if not ledger.get("rows"):
        score -= 0.5
    return score


def _control_score(control_map: dict[str, Any]) -> float:
    if control_map.get("status") == "not_evaluated":
        return -0.5
    if control_map.get("risk_level") == "needs_review":
        return -0.5
    return 0.0


def _execution_score(financial_signals: list[dict[str, Any]]) -> float:
    relevant = [
        signal
        for signal in financial_signals
        if signal.get("signal_id")
        in {
            "revenue_growth",
            "operating_margin",
            "incremental_operating_margin",
            "cash_conversion",
            "roic_proxy",
            "incremental_roic_proxy",
        }
    ]
    if not relevant:
        return -0.5
    support = sum(1 for signal in relevant if signal.get("tone") == "support")
    concern = sum(1 for signal in relevant if signal.get("tone") == "concern")
    return ((support - concern) / max(1, len(relevant))) * 2


def _execution_read(financial_signals: list[dict[str, Any]]) -> str:
    reads = [
        str(signal.get("read"))
        for signal in financial_signals
        if signal.get("signal_id")
        in {
            "revenue_growth",
            "operating_margin",
            "incremental_operating_margin",
            "cash_conversion",
            "roic_proxy",
            "incremental_roic_proxy",
        }
        and signal.get("read")
    ]
    return "; ".join(reads[:4]) or "Execution evidence is not available."


def _stress_behavior_score(communication_audit: dict[str, Any]) -> float:
    checks = communication_audit.get("outcome_checks") or []
    if not checks:
        return 0.0
    concerns = sum(1 for check in checks if check.get("verdict") == "needs_review")
    partial = sum(1 for check in checks if check.get("verdict") == "partially_supported")
    return max(-1.0, min(0.5, (partial * 0.25) - (concerns * 0.35)))


def _open_questions(subagents: list[dict[str, Any]], red_flags: list[dict[str, Any]]) -> list[str]:
    questions = [
        "What is the exact beneficial ownership and voting-power table for current insiders and major shareholders?",
        "Are management incentives tied to per-share value, cash flow, ROIC, and durable growth, or mostly to scale?",
        "How much cash was used for reinvestment, buybacks, dividends, acquisitions, and investment assets over the last five years?",
        "Which management statements from earnings calls were later confirmed or contradicted by filings and financial outcomes?",
    ]
    if any(flag.get("severity") == "high" for flag in red_flags):
        questions.insert(0, "Resolve high-severity verification or governance review flags before upgrading right-people support.")
    for subagent in subagents:
        if str(subagent.get("status", "")).startswith("missing"):
            questions.append(f"{subagent.get('name')}: missing key input evidence.")
    return questions


def _overall_status(checklist: list[dict[str, Any]], subagents: list[dict[str, Any]]) -> str:
    if any(item.get("status") == "needs_review" for item in checklist):
        return "partial_v1_review_required"
    if any(item.get("status") in {"partially_supported", "supported"} for item in checklist):
        return "partial_v1_evidence_collected"
    if any(str(item.get("status", "")).startswith("functional") for item in subagents):
        return "partial_v1_evidence_collected"
    return "scaffolded_pending_source_research"


def _overall_read(checklist: list[dict[str, Any]], red_flags: list[dict[str, Any]]) -> str:
    if any(flag.get("severity") == "high" for flag in red_flags):
        return "needs_review: high-severity verification/governance flags exist, so V1 cannot support right people yet."
    supported = [item for item in checklist if item.get("status") in {"supported", "partially_supported"}]
    if len(supported) >= 4:
        return "partially_supported: V1 has official-filing, financial-outcome, and management-communication evidence, but final people judgment remains open."
    if supported:
        return "early_partial_support: some evidence exists, but key management-quality questions remain open."
    return "not_evaluated: source coverage is insufficient."


def _support_status(subagent: dict[str, Any] | None) -> str:
    if not subagent:
        return "not_evaluated"
    status = str(subagent.get("status") or "")
    if status in {"review_required"}:
        return "needs_review"
    if status.startswith("functional") or status.startswith("partially"):
        return "partially_supported"
    if status.startswith("no_high_priority"):
        return "partially_supported"
    return "not_evaluated"


def _cards_by_group(cards: list[dict[str, Any]], group_id: str) -> list[dict[str, Any]]:
    return [card for card in cards if card.get("group_id") == group_id]


def _card_has_term(cards: list[dict[str, Any]], term: str) -> bool:
    lower = term.lower()
    return any(lower == str(match).lower() for card in cards for match in card.get("matched_terms", []))


def _topic_hits(annual_report_evidence: dict[str, Any], topic: str) -> int:
    return int(((annual_report_evidence.get("topics") or {}).get(topic) or {}).get("total_hits") or 0)


def _signal_by_id(signals: list[dict[str, Any]], signal_id: str) -> dict[str, Any] | None:
    return next((signal for signal in signals if signal.get("signal_id") == signal_id), None)


def _latest_metric_result(metrics: list[dict[str, Any]], formula_id: str) -> dict[str, Any] | None:
    metric = next((item for item in metrics if item.get("formula_id") == formula_id), None)
    if not metric:
        return None
    rows = [
        row
        for row in metric.get("annual_results", [])
        if row.get("status") == "calculated" and row.get("year") is not None
    ]
    if not rows:
        result = metric.get("latest_interim_result")
        return result if isinstance(result, dict) else None
    return sorted(rows, key=lambda row: row.get("year"))[-1]


def _metric_result_by_year(metrics: list[dict[str, Any]], formula_id: str, year: int) -> dict[str, Any] | None:
    metric = next((item for item in metrics if item.get("formula_id") == formula_id), None)
    if not metric:
        return None
    for row in metric.get("annual_results", []):
        if row.get("status") == "calculated" and int(row.get("year") or 0) == int(year):
            return row
    return None


def _annual_fact_value(facts: list[dict[str, Any]], metric: str, year: int) -> Any:
    matches = [
        fact
        for fact in facts
        if fact.get("metric") == metric
        and str(fact.get("end_date") or "").startswith(str(year))
        and fact.get("period_type") in {"annual", "year", "duration"}
    ]
    if not matches:
        return None
    return _preferred_fact(matches).get("value")


def _instant_fact_value(facts: list[dict[str, Any]], metric: str, year: int) -> Any:
    matches = [
        fact
        for fact in facts
        if fact.get("metric") == metric
        and (
            str(fact.get("instant") or "").startswith(str(year))
            or str(fact.get("end_date") or "").startswith(str(year))
        )
        and fact.get("period_type") in {"instant", None}
    ]
    if not matches:
        return None
    return _preferred_fact(matches).get("value")


def _preferred_fact(matches: list[dict[str, Any]]) -> dict[str, Any]:
    def score(fact: dict[str, Any]) -> tuple[int, str]:
        unit = str(fact.get("unit") or "").upper()
        preferred_unit = 1 if any(token in unit for token in ["CNY", "RMB", "SHARE"]) else 0
        return (preferred_unit, str(fact.get("filing_date") or ""))

    return sorted(matches, key=score)[-1]


def _snippets_for_terms(text: str, terms: list[str], *, limit: int) -> list[dict[str, Any]]:
    snippets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for term in terms:
        pattern = re.compile(re.escape(term), flags=re.IGNORECASE)
        candidates: list[tuple[float, int, str]] = []
        for match in pattern.finditer(text):
            start = max(0, match.start() - 180)
            end = min(len(text), match.end() + 280)
            snippet = _trim_text(_snippet_window(text, start, end, match.start()), 480)
            key = re.sub(r"\W+", " ", snippet.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            candidates.append((_snippet_quality_score(snippet, term), match.start(), snippet))
            if len(candidates) >= 24:
                break
        if candidates:
            score, _, snippet = sorted(candidates, key=lambda item: (item[0], -item[1]))[-1]
            snippets.append({"matched_term": term, "text": snippet, "quality_score": round(score, 2)})
    snippets.sort(key=lambda snippet: snippet.get("quality_score", 0), reverse=True)
    return snippets[:limit]


def _snippet_quality_score(snippet: str, term: str) -> float:
    text = str(snippet or "")
    lower = text.lower()
    score = 0.0
    if term.lower() in lower:
        score += 2.0
    if len(text) >= 160:
        score += 1.0
    if re.search(r"\b20\d{2}\b", lower):
        score += 1.0
    signal_terms = [
        "as of",
        "december 31",
        "march 18",
        "table sets forth",
        "beneficial ownership",
        "directors and executive officers",
        "ordinary shares",
        "voting power",
        "vie",
        "principal subsidiaries and the vie",
        "contractual arrangements with the vie",
        "share incentive plan",
        "share-based compensation",
        "restricted share units",
        "options to purchase",
        "granted and were outstanding",
        "dividends",
        "repurchase",
        "capital expenditures",
        "investment commitments",
        "related party transactions",
        "auditor",
        "material weakness",
        "restatement",
    ]
    for signal in signal_terms:
        if signal in lower:
            score += 1.5
    noise_terms = [
        "table of contents",
        "forward-looking information",
        "offer statistics and expected timetable",
        "defaults, dividend arrearages and delinquencies",
        "identity of directors, senior management and advisers",
        "assessing the risk that a material weakness exists",
        "whether any of those error corrections are restatements",
        "item 1.",
        "item 2.",
        "item 3.",
        "item 4.",
        "part i",
        "part ii",
    ]
    for noise in noise_terms:
        if noise in lower:
            score -= 4.0
    if lower.count("item ") >= 2:
        score -= 3.0
    if "&#" in text:
        score -= 1.5
    if len(text) < 80:
        score -= 2.0
    return score


def _snippet_window(text: str, start: int, end: int, focus_start: int) -> str:
    adjusted_start = start
    if start > 0:
        prefix = text[start:focus_start]
        boundary = max(prefix.rfind(". "), prefix.rfind("; "), prefix.rfind("● "))
        if boundary >= 30:
            adjusted_start = start + boundary + 2
        else:
            while adjusted_start < focus_start and text[adjusted_start].isalnum():
                adjusted_start += 1
    return text[adjusted_start:end]


def _read_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    without_scripts = re.sub(
        r"<(script|style)\b.*?</\1>",
        " ",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )
    without_tags = re.sub(r"<[^>]+>", " ", without_scripts)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def _trim_text(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 3)].rstrip() + "..."


def _percent_text(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "n/a"


def _ratio_text(value: Any) -> str:
    try:
        return f"{float(value):.2f}x"
    except (TypeError, ValueError):
        return "n/a"


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
