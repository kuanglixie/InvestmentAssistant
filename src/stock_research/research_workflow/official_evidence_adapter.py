from __future__ import annotations

from collections import Counter
from typing import Any

from stock_research.research_workflow.models import make_evidence_item, make_gap_request, make_source_ref, stable_id
from stock_research.state import ResearchState, utc_now_iso


OFFICIAL_EVIDENCE_ADAPTER_SCHEMA_VERSION = "official_evidence_workflow_adapter_v1"


QUESTION_MAP = {
    "growth_quality": ["financial.growth", "financial.revenue_sources"],
    "profitability_with_scale": ["financial.margin_conversion", "business.unit_economics"],
    "cash_profit_quality": ["financial.cash_conversion"],
    "capital_needed_for_growth": ["business.reinvestment_need", "financial.cash_conversion"],
    "balance_sheet_resilience": ["financial.balance_sheet", "risk.regulatory_legal"],
    "sbc_and_per_share_quality": ["financial.dilution_sbc", "people.incentives"],
    "tax_non_gaap_accounting_quality": ["financial.accounting_red_flags"],
}


NARRATIVE_MAP = {
    "transaction_services_revenue_mix": ["financial.revenue_sources", "business.revenue_mechanism"],
    "first_party_brand": ["business.unit_economics", "business.reinvestment_need"],
    "supply_chain_investment": ["business.reinvestment_need", "financial.margin_conversion"],
    "global_business_temu": ["pdd.temu_segment_opacity", "business.unit_economics", "risk.regulatory_legal"],
    "restricted_cash_vie": ["financial.balance_sheet", "people.control_governance", "risk.regulatory_legal"],
    "management_governance_change": ["people.control_governance", "people.candor"],
    "agm_ads_voting_board": ["people.control_governance"],
    "share_plan_extension": ["financial.dilution_sbc", "people.incentives"],
    "audit_accounting_reliability": ["financial.accounting_red_flags"],
}


def build_official_report_workflow_evidence(state: ResearchState) -> dict[str, Any]:
    """Convert the official report evidence pack into reusable evidence items."""

    pack = state.get("official_report_evidence_pack") or {}
    items: list[dict[str, Any]] = []
    gap_requests: list[dict[str, Any]] = []
    source_refs = _source_refs(pack, state)

    seen_bundle_ids: set[str] = set()
    for answer in pack.get("question_answers") or []:
        question_ids = _question_ids_for_answer(answer)
        for bundle in answer.get("evidence_bundle") or []:
            evidence_key = str(bundle.get("evidence_id") or stable_id("official-bundle", bundle))
            if evidence_key not in seen_bundle_ids:
                seen_bundle_ids.add(evidence_key)
                items.append(_bundle_item(bundle, question_ids, len(items) + 1))
        items.append(_answer_item(answer, question_ids, len(items) + 1))
        gap_requests.extend(_gaps_from_payload(answer, question_ids, "official_question"))

    for narrative in pack.get("decision_relevant_narratives") or []:
        question_ids = _question_ids_for_narrative(narrative)
        for bundle in narrative.get("evidence_bundle") or []:
            evidence_key = str(bundle.get("evidence_id") or stable_id("official-narrative-bundle", bundle))
            if evidence_key not in seen_bundle_ids:
                seen_bundle_ids.add(evidence_key)
                items.append(_bundle_item(bundle, question_ids, len(items) + 1))
        items.append(_narrative_item(narrative, question_ids, len(items) + 1))
        gap_requests.extend(_gaps_from_payload(narrative, question_ids, "official_narrative"))

    quality_flags = [
        {
            "flag_id": str(flag.get("flag_id") or stable_id("official-quality", flag)),
            "severity": str(flag.get("severity") or "medium"),
            "message": str(flag.get("message") or flag),
            "source_artifact": "official_report_evidence_pack",
        }
        if isinstance(flag, dict)
        else {
            "flag_id": stable_id("official-quality", flag),
            "severity": "medium",
            "message": str(flag),
            "source_artifact": "official_report_evidence_pack",
        }
        for flag in pack.get("quality_flags") or []
    ]

    question_counts = Counter()
    for item in items:
        for question_id in item.get("question_ids", []):
            question_counts[question_id] += 1

    return {
        "schema_version": OFFICIAL_EVIDENCE_ADAPTER_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "source_artifact": "official_report_evidence_pack",
        "source_artifact_path": state.get("official_report_evidence_pack_path"),
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


def _source_refs(pack: dict[str, Any], state: ResearchState) -> list[dict[str, Any]]:
    refs = [
        make_source_ref(
            source_id="official_report_evidence_pack",
            source_type="official_report_evidence_pack",
            source_tier=1,
            locator="official_report_evidence_pack.json",
            title="Official Report Evidence Pack",
            reliability="derived_from_official_filings",
            metadata={
                "schema_version": pack.get("schema_version"),
                "path": state.get("official_report_evidence_pack_path"),
            },
        )
    ]
    seen = {"official_report_evidence_pack"}
    for source in pack.get("source_catalog") or []:
        source_id = str(source.get("document_id") or source.get("source_url") or source.get("local_file_path") or "")
        if not source_id or source_id in seen:
            continue
        seen.add(source_id)
        refs.append(
            make_source_ref(
                source_id=source_id,
                source_type=str(source.get("document_type") or "official_report_source"),
                source_tier=1,
                locator=str(source.get("local_file_path") or source.get("source_url") or ""),
                title=source_id,
                reliability="official_report_source",
                metadata=source,
            )
        )
    return refs


def _bundle_item(bundle: dict[str, Any], question_ids: list[str], ordinal: int) -> dict[str, Any]:
    evidence_type = str(bundle.get("evidence_type") or "")
    return make_evidence_item(
        evidence_id=f"OFFICIAL-EVIDENCE-{ordinal:03d}",
        question_ids=question_ids or _question_ids_for_bundle(bundle),
        source_id=str(bundle.get("source_document") or "official_report_evidence_pack"),
        source_tier=1,
        source_type=str(bundle.get("source_document_type") or "official_report_evidence"),
        locator=str(bundle.get("source_section") or bundle.get("evidence_id") or ""),
        evidence_kind=_kind_from_evidence_type(evidence_type),
        excerpt=str(bundle.get("quote_or_summary") or ""),
        structured_fact=bundle,
        confidence="high" if bundle.get("cross_validation_status") == "matched" else "medium",
        upstream_refs=[
            {
                "upstream_artifact": "official_report_evidence_pack",
                "upstream_evidence_id": bundle.get("evidence_id"),
                "local_file_path": bundle.get("local_file_path"),
                "source_section": bundle.get("source_section"),
            }
        ],
    )


def _answer_item(answer: dict[str, Any], question_ids: list[str], ordinal: int) -> dict[str, Any]:
    inference = answer.get("our_inference") or {}
    inference_text = inference.get("text") if isinstance(inference, dict) else str(inference or "")
    excerpt = inference_text or str(answer.get("short_answer") or answer.get("rendered_answer") or "")
    return make_evidence_item(
        evidence_id=f"OFFICIAL-ANSWER-{ordinal:03d}",
        question_ids=question_ids,
        source_id="official_report_evidence_pack",
        source_tier=1,
        source_type="official_report_question_answer",
        locator=str(answer.get("question_id") or ""),
        evidence_kind="system_inference",
        excerpt=excerpt,
        structured_fact=answer,
        confidence=str(inference.get("confidence") or "medium") if isinstance(inference, dict) else "medium",
        upstream_refs=[
            {
                "upstream_artifact": "official_report_evidence_pack",
                "official_question_id": answer.get("question_id"),
                "evidence_ids": [item.get("evidence_id") for item in answer.get("evidence_bundle") or []],
            }
        ],
        requires_human_review=bool(answer.get("still_unknown") or answer.get("warning_flags")),
    )


def _narrative_item(narrative: dict[str, Any], question_ids: list[str], ordinal: int) -> dict[str, Any]:
    return make_evidence_item(
        evidence_id=f"OFFICIAL-NARRATIVE-{ordinal:03d}",
        question_ids=question_ids,
        source_id="official_report_evidence_pack",
        source_tier=1,
        source_type="official_report_narrative",
        locator=str(narrative.get("narrative_id") or ""),
        evidence_kind="system_inference",
        excerpt=str(narrative.get("our_inference") or narrative.get("impact_on_investment_judgment") or ""),
        structured_fact=narrative,
        confidence="medium",
        upstream_refs=[
            {
                "upstream_artifact": "official_report_evidence_pack",
                "narrative_id": narrative.get("narrative_id"),
                "evidence_ids": [item.get("evidence_id") for item in narrative.get("evidence_bundle") or []],
            }
        ],
        requires_human_review=bool(narrative.get("still_unknown")),
    )


def _gaps_from_payload(payload: dict[str, Any], question_ids: list[str], gap_type: str) -> list[dict[str, Any]]:
    gaps = []
    qid = question_ids[0] if question_ids else "workflow"
    for unknown in payload.get("still_unknown") or []:
        gaps.append(
            make_gap_request(
                gap_id=stable_id("official-gap", [payload.get("question_id") or payload.get("narrative_id"), unknown]),
                question_id=qid,
                gap_type=f"{gap_type}_unknown",
                description=str(unknown),
                priority="P1",
                route="official_filing_deep_read",
                owner_agent="official_report_evidence",
                required_source_types=["20-F", "6-K", "earnings_release"],
                depends_on_artifact="official_report_evidence_pack",
            )
        )
    for follow_up in payload.get("follow_up_needed") or []:
        gaps.append(
            make_gap_request(
                gap_id=stable_id("official-followup", [payload.get("question_id") or payload.get("narrative_id"), follow_up]),
                question_id=qid,
                gap_type=f"{gap_type}_follow_up",
                description=str(follow_up),
                priority="P2",
                route="official_filing_deep_read",
                owner_agent="official_report_evidence",
                required_source_types=["20-F", "6-K", "earnings_release"],
                depends_on_artifact="official_report_evidence_pack",
            )
        )
    return gaps


def _question_ids_for_answer(answer: dict[str, Any]) -> list[str]:
    return QUESTION_MAP.get(str(answer.get("question_id") or ""), ["financial.accounting_red_flags"])


def _question_ids_for_narrative(narrative: dict[str, Any]) -> list[str]:
    return NARRATIVE_MAP.get(str(narrative.get("narrative_id") or ""), ["business.revenue_mechanism"])


def _question_ids_for_bundle(bundle: dict[str, Any]) -> list[str]:
    if bundle.get("question_id"):
        return QUESTION_MAP.get(str(bundle.get("question_id")), ["financial.accounting_red_flags"])
    if bundle.get("narrative_id"):
        return NARRATIVE_MAP.get(str(bundle.get("narrative_id")), ["business.revenue_mechanism"])
    return ["financial.accounting_red_flags"]


def _kind_from_evidence_type(evidence_type: str) -> str:
    if evidence_type == "filing_fact":
        return "filed_fact"
    if evidence_type == "management_explanation":
        return "management_explanation"
    if evidence_type == "management_claim":
        return "management_claim"
    return "system_inference"
