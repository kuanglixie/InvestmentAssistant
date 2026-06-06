from __future__ import annotations

from collections import Counter
from typing import Any

from stock_research.research_workflow.models import infer_question_ids_from_text, make_evidence_item, make_gap_request, make_source_ref, stable_id
from stock_research.state import ResearchState, utc_now_iso


PEOPLE_ADAPTER_SCHEMA_VERSION = "people_workflow_adapter_v1"


GROUP_MAP = {
    "control_and_governance": ["people.control_governance"],
    "incentives_and_compensation": ["people.incentives", "financial.dilution_sbc"],
    "capital_allocation": ["people.capital_allocation", "price.owner_return"],
    "integrity_red_flags": ["financial.accounting_red_flags", "people.control_governance", "risk.regulatory_legal"],
}


SIGNAL_MAP = {
    "revenue_growth": ["financial.growth"],
    "operating_margin": ["financial.margin_conversion"],
    "free_cash_flow_margin": ["financial.cash_conversion"],
    "incremental_operating_margin": ["financial.margin_conversion"],
    "capital_intensity": ["business.reinvestment_need", "price.expectations"],
    "cash_conversion": ["financial.cash_conversion"],
    "sbc_burden": ["financial.dilution_sbc", "people.incentives"],
    "diluted_share_growth": ["financial.dilution_sbc", "people.capital_allocation"],
    "roic_proxy": ["people.capital_allocation", "price.expectations"],
    "incremental_roic_proxy": ["people.capital_allocation", "price.expectations"],
}


SUBAGENT_MAP = {
    "governance_control_reader": ["people.control_governance"],
    "incentive_alignment_analyst": ["people.incentives", "financial.dilution_sbc"],
    "capital_allocation_historian": ["people.capital_allocation", "price.owner_return"],
    "management_communication_auditor": ["people.candor"],
    "execution_track_record_analyst": ["financial.growth", "financial.margin_conversion"],
    "integrity_red_flag_scanner": ["financial.accounting_red_flags", "people.control_governance"],
}


def build_people_workflow_evidence(state: ResearchState) -> dict[str, Any]:
    """Convert Right People analysis into structured workflow evidence."""

    findings = state.get("leadership_findings") or {}
    items: list[dict[str, Any]] = []
    source_refs = _source_refs(findings, state)
    gap_requests = _gap_requests(findings)
    quality_flags = _quality_flags(findings)

    for card in findings.get("official_filing_evidence_cards") or []:
        items.append(_official_card_item(card, len(items) + 1))
    for signal in findings.get("financial_signals") or []:
        items.append(_financial_signal_item(signal, len(items) + 1))
    for red_flag in findings.get("red_flags") or []:
        items.append(_red_flag_item(red_flag, len(items) + 1))
    for subagent in findings.get("subagent_reports") or []:
        items.append(_subagent_item(subagent, len(items) + 1))
    decision = findings.get("right_people_decision") or {}
    if decision:
        items.append(_decision_item(decision, len(items) + 1))

    question_counts = Counter()
    for item in items:
        for question_id in item.get("question_ids", []):
            question_counts[question_id] += 1

    return {
        "schema_version": PEOPLE_ADAPTER_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "source_artifact": "leadership_findings",
        "source_artifact_path": state.get("state_path"),
        "evidence_items": items,
        "source_refs": source_refs,
        "gap_requests": gap_requests,
        "quality_flags": quality_flags,
        "summary": {
            "evidence_item_count": len(items),
            "source_ref_count": len(source_refs),
            "gap_request_count": len(gap_requests),
            "quality_flag_count": len(quality_flags),
            "question_evidence_counts": dict(sorted(question_counts.items())),
        },
    }


def _source_refs(findings: dict[str, Any], state: ResearchState) -> list[dict[str, Any]]:
    refs = [
        make_source_ref(
            source_id="leadership_findings",
            source_type="right_people_analysis",
            source_tier=1,
            locator="state.leadership_findings",
            title="Right People Analysis",
            reliability="derived_from_official_filings_and_financial_metrics",
            metadata={
                "schema_version": findings.get("schema_version"),
                "state_path": state.get("state_path"),
            },
        )
    ]
    seen = {"leadership_findings"}
    for card in findings.get("official_filing_evidence_cards") or []:
        source_id = str(card.get("source_document") or card.get("source_id") or "")
        if not source_id or source_id in seen:
            continue
        seen.add(source_id)
        refs.append(
            make_source_ref(
                source_id=source_id,
                source_type="official_filing_governance_evidence",
                source_tier=1,
                locator=str(card.get("locator") or card.get("source_document") or ""),
                title=source_id,
                reliability=str(card.get("source_quality") or "official_filing_high"),
                metadata=card,
            )
        )
    return refs


def _official_card_item(card: dict[str, Any], ordinal: int) -> dict[str, Any]:
    question_ids = GROUP_MAP.get(str(card.get("group_id") or ""), infer_question_ids_from_text(str(card)) or ["people.control_governance"])
    snippets = card.get("snippets") or []
    excerpt = str(card.get("evidence") or card.get("excerpt") or card.get("finding") or snippets[:2] or "")
    return make_evidence_item(
        evidence_id=f"PEOPLE-CARD-{ordinal:03d}",
        question_ids=question_ids,
        source_id=str(card.get("source_document") or card.get("source_id") or "leadership_findings"),
        source_tier=1,
        source_type="official_filing_governance_evidence",
        locator=str(card.get("locator") or card.get("group_id") or ""),
        evidence_kind=str(card.get("evidence_bucket") or "filed_fact"),
        excerpt=excerpt,
        structured_fact=card,
        confidence="high" if "official" in str(card.get("source_quality") or "").casefold() else "medium",
        upstream_refs=[{"upstream_artifact": "leadership_findings", "group_id": card.get("group_id"), "source_document": card.get("source_document")}],
    )


def _financial_signal_item(signal: dict[str, Any], ordinal: int) -> dict[str, Any]:
    signal_id = str(signal.get("signal_id") or "")
    return make_evidence_item(
        evidence_id=f"PEOPLE-SIGNAL-{ordinal:03d}",
        question_ids=SIGNAL_MAP.get(signal_id, infer_question_ids_from_text(str(signal)) or ["people.capital_allocation"]),
        source_id=str(signal.get("source") or "leadership_findings"),
        source_tier=1,
        source_type="derived_people_financial_signal",
        locator=signal_id,
        evidence_kind=str(signal.get("evidence_bucket") or "system_inference"),
        excerpt=str(signal.get("read") or signal.get("summary") or signal)[:1000],
        structured_fact=signal,
        confidence="medium",
        upstream_refs=[
            {
                "upstream_artifact": "leadership_findings",
                "signal_id": signal_id,
                "source_fact_ids": signal.get("source_fact_ids") or [],
            }
        ],
        requires_human_review=signal.get("tone") == "concern",
    )


def _red_flag_item(red_flag: dict[str, Any], ordinal: int) -> dict[str, Any]:
    severity = str(red_flag.get("severity") or "medium").casefold()
    question_ids = infer_question_ids_from_text(str(red_flag)) or ["financial.accounting_red_flags", "people.control_governance"]
    return make_evidence_item(
        evidence_id=f"PEOPLE-REDFLAG-{ordinal:03d}",
        question_ids=question_ids,
        source_id=str(red_flag.get("source") or "leadership_findings"),
        source_tier=1,
        source_type="right_people_red_flag",
        locator=str(red_flag.get("flag_id") or ""),
        evidence_kind=str(red_flag.get("evidence_bucket") or "system_inference"),
        excerpt=str(red_flag.get("read") or red_flag.get("summary") or red_flag)[:1000],
        structured_fact=red_flag,
        confidence="high" if severity == "high" else "medium",
        upstream_refs=[{"upstream_artifact": "leadership_findings", "flag_id": red_flag.get("flag_id")}],
        requires_human_review=True,
    )


def _subagent_item(subagent: dict[str, Any], ordinal: int) -> dict[str, Any]:
    agent_id = str(subagent.get("agent_id") or "")
    return make_evidence_item(
        evidence_id=f"PEOPLE-SUBAGENT-{ordinal:03d}",
        question_ids=SUBAGENT_MAP.get(agent_id, infer_question_ids_from_text(str(subagent)) or ["people.control_governance"]),
        source_id="leadership_findings",
        source_tier=1,
        source_type="right_people_subagent_read",
        locator=agent_id,
        evidence_kind="system_inference",
        excerpt=str(subagent.get("current_read") or subagent.get("status") or "")[:1000],
        structured_fact=subagent,
        confidence="medium",
        upstream_refs=[{"upstream_artifact": "leadership_findings", "agent_id": agent_id}],
        requires_human_review=str(subagent.get("status") or "").casefold() not in {"supportive", "complete"},
    )


def _decision_item(decision: dict[str, Any], ordinal: int) -> dict[str, Any]:
    return make_evidence_item(
        evidence_id=f"PEOPLE-DECISION-{ordinal:03d}",
        question_ids=["people.control_governance", "people.incentives", "people.capital_allocation", "people.candor"],
        source_id="leadership_findings",
        source_tier=1,
        source_type="right_people_decision_read",
        locator="right_people_decision",
        evidence_kind="system_inference",
        excerpt=str(decision.get("current_read") or decision.get("status") or "")[:1000],
        structured_fact=decision,
        confidence="medium",
        upstream_refs=[{"upstream_artifact": "leadership_findings", "decision_status": decision.get("status")}],
        requires_human_review=True,
    )


def _gap_requests(findings: dict[str, Any]) -> list[dict[str, Any]]:
    gaps = []
    for question in findings.get("open_questions") or []:
        text = str(question.get("question") if isinstance(question, dict) else question)
        qids = infer_question_ids_from_text(text) or ["people.control_governance"]
        gaps.append(
            make_gap_request(
                gap_id=stable_id("people-open-question", text),
                question_id=qids[0],
                gap_type="right_people_open_question",
                description=text,
                priority="P1",
                route="official_filing_deep_read",
                owner_agent="right_people",
                required_source_types=["20-F", "6-K", "governance_document", "ownership_filing"],
                depends_on_artifact="leadership_findings",
            )
        )
    for limit in findings.get("limits") or []:
        text = str(limit)
        gaps.append(
            make_gap_request(
                gap_id=stable_id("people-limit", text),
                question_id=(infer_question_ids_from_text(text) or ["people.control_governance"])[0],
                gap_type="right_people_limit",
                description=text,
                priority="P2",
                route="human_review",
                owner_agent="right_people",
                depends_on_artifact="leadership_findings",
            )
        )
    return gaps


def _quality_flags(findings: dict[str, Any]) -> list[dict[str, Any]]:
    flags = []
    coverage = findings.get("source_coverage") or {}
    if coverage.get("official_filing_evidence_cards", 0) <= 0:
        flags.append(
            {
                "flag_id": "people_no_official_filing_cards",
                "severity": "medium",
                "message": "Right People analysis has no official filing governance cards.",
                "source_artifact": "leadership_findings",
            }
        )
    if findings.get("status") in {"blocked", "not_evaluated"}:
        flags.append(
            {
                "flag_id": "people_status_not_ready",
                "severity": "medium",
                "message": f"Right People status is {findings.get('status')}.",
                "source_artifact": "leadership_findings",
            }
        )
    return flags
