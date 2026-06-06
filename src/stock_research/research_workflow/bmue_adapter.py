from __future__ import annotations

from collections import Counter
from typing import Any

from stock_research.research_workflow.models import (
    infer_question_ids_from_text,
    make_evidence_item,
    make_gap_request,
    make_source_ref,
    stable_id,
)
from stock_research.state import ResearchState, utc_now_iso


BMUE_ADAPTER_SCHEMA_VERSION = "bmue_workflow_evidence_adapter_v1"


def build_bmue_workflow_evidence(state: ResearchState) -> dict[str, Any]:
    pack = state.get("business_model_unit_economics_pack") or {}
    items: list[dict[str, Any]] = []
    source_refs = _source_refs(pack)
    items.extend(_evidence_card_items(pack))
    items.extend(_answer_items(pack))
    items.extend(_contradiction_items(pack))
    gap_requests = _gap_requests(pack)
    quality_flags = _quality_flags(pack)

    question_counts = Counter()
    for item in items:
        for question_id in item.get("question_ids", []):
            question_counts[question_id] += 1

    return {
        "schema_version": BMUE_ADAPTER_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "source_artifact": "business_model_unit_economics_pack",
        "source_artifact_path": state.get("business_model_unit_economics_pack_path"),
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


def _source_refs(pack: dict[str, Any]) -> list[dict[str, Any]]:
    refs = [
        make_source_ref(
            source_id="business_model_unit_economics_pack",
            source_type="business_model_unit_economics_pack",
            source_tier=1,
            locator="business_model_unit_economics_pack.json",
            title="Business Model Unit Economics Pack",
            reliability="derived_from_official_and_financial_evidence",
            metadata={
                "schema_version": pack.get("schema_version"),
                "evidence_card_count": len(pack.get("evidence_cards") or []),
                "question_answer_count": len(pack.get("question_answers") or []),
            },
        )
    ]
    for source in pack.get("source_inventory") or []:
        refs.append(
            make_source_ref(
                source_id=str(source.get("source_id") or stable_id("bmue-source", source)),
                source_type=str(source.get("document_type") or "bmue_source"),
                source_tier=1 if source.get("source_scope") in {"official_filing", "official_report"} else 2,
                locator=str(source.get("citation") or source.get("locator") or ""),
                title=str(source.get("title") or source.get("source_name") or source.get("source_id") or "BMUE source"),
                reliability=str(source.get("reliability") or "unknown"),
                metadata=source,
            )
        )
    return refs


def _evidence_card_items(pack: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for card in pack.get("evidence_cards") or []:
        source = ((card.get("evidence") or [{}])[0] or {})
        question_ids = _decision_questions_for_bmue(card, fallback=["business.revenue_mechanism"])
        assertion_class = str(card.get("assertion_class") or "")
        evidence_kind = _kind_from_assertion(assertion_class, card)
        items.append(
            make_evidence_item(
                evidence_id=f"BMUE-CARD-{len(items) + 1:03d}",
                question_ids=question_ids,
                source_id=str(source.get("source_id") or "business_model_unit_economics_pack"),
                source_tier=1,
                source_type="bmue_evidence_card",
                locator=str(source.get("locator") or card.get("card_id") or ""),
                evidence_kind=evidence_kind,
                excerpt=str(source.get("excerpt") or card.get("claim_text") or card.get("claim_normalized") or "")[:1000],
                structured_fact=card,
                confidence=_confidence_from_score(card.get("confidence")),
                upstream_refs=[
                    {
                        "upstream_artifact": "business_model_unit_economics_pack",
                        "upstream_card_id": card.get("card_id"),
                        "source_id": source.get("source_id"),
                        "locator": source.get("locator"),
                    }
                ],
                requires_human_review=str(card.get("status") or "").casefold() in {"partial", "unknown", "needs_review"},
            )
        )
    return items


def _answer_items(pack: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for answer in pack.get("question_answers") or []:
        status = str(answer.get("status") or answer.get("answer_status") or "")
        text = str(answer.get("current_answer") or answer.get("answer") or answer.get("summary") or "")
        if not text:
            continue
        items.append(
            make_evidence_item(
                evidence_id=f"BMUE-ANSWER-{len(items) + 1:03d}",
                question_ids=_decision_questions_for_bmue(answer),
                source_id="business_model_unit_economics_pack",
                source_tier=1,
                source_type="bmue_question_answer",
                locator=str(answer.get("question_id") or answer.get("id") or ""),
                evidence_kind="system_inference",
                excerpt=text[:1000],
                structured_fact=answer,
                confidence=str(answer.get("confidence") or ("medium" if status != "missing" else "low")),
                upstream_refs=[
                    {
                        "upstream_artifact": "business_model_unit_economics_pack",
                        "upstream_question_id": answer.get("question_id") or answer.get("id"),
                        "evidence_card_ids": answer.get("evidence_card_ids") or [],
                    }
                ],
                requires_human_review=status in {"partial", "missing", "unknown"},
            )
        )
    return items


def _contradiction_items(pack: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for contradiction in pack.get("contradictions") or []:
        text = str(contradiction.get("issue") or contradiction.get("summary") or contradiction)
        items.append(
            make_evidence_item(
                evidence_id=f"BMUE-CONTRA-{len(items) + 1:03d}",
                question_ids=infer_question_ids_from_text(text) or ["business.unit_economics"],
                source_id="business_model_unit_economics_pack",
                source_tier=1,
                source_type="bmue_contradiction",
                locator=str(contradiction.get("contradiction_id") or stable_id("bmue-contradiction", contradiction)),
                evidence_kind="system_inference",
                excerpt=text[:1000],
                structured_fact=contradiction,
                confidence=str(contradiction.get("confidence") or "medium"),
                upstream_refs=[{"upstream_artifact": "business_model_unit_economics_pack", "contradiction_id": contradiction.get("contradiction_id")}],
                requires_human_review=True,
            )
        )
    return items


def _gap_requests(pack: dict[str, Any]) -> list[dict[str, Any]]:
    gaps = []
    for unknown in pack.get("unknowns") or []:
        text = str(unknown.get("unknown") or unknown.get("question") or unknown)
        gaps.append(
            make_gap_request(
                gap_id=str(unknown.get("unknown_id") or stable_id("bmue-gap", unknown)),
                question_id=(infer_question_ids_from_text(text) or ["business.unit_economics"])[0],
                gap_type="business_model_unknown",
                description=text,
                priority=str(unknown.get("priority") or "P1"),
                route="official_filing_deep_read",
                owner_agent="business_model_unit_economics",
                required_metrics=[str(item) for item in unknown.get("missing_metrics") or []],
                required_source_types=["20-F", "6-K", "earnings_release"],
                depends_on_artifact="business_model_unit_economics_pack",
            )
        )
    for handoff in pack.get("handoff") or []:
        text = str(handoff.get("question") or handoff.get("request") or handoff)
        gaps.append(
            make_gap_request(
                gap_id=str(handoff.get("handoff_id") or stable_id("bmue-handoff", handoff)),
                question_id=(infer_question_ids_from_text(text) or ["business.unit_economics"])[0],
                gap_type="business_model_handoff",
                description=text,
                priority=str(handoff.get("priority") or "P2"),
                route=str(handoff.get("route") or "evidence_registry"),
                owner_agent=str(handoff.get("owner_agent") or "business_model_unit_economics"),
                required_metrics=[str(item) for item in handoff.get("missing_metrics") or []],
                required_source_types=["20-F", "6-K", "earnings_release"],
                depends_on_artifact="business_model_unit_economics_pack",
            )
        )
    return gaps


def _quality_flags(pack: dict[str, Any]) -> list[dict[str, Any]]:
    flags = []
    for flag in pack.get("quality_flags") or []:
        if not isinstance(flag, dict):
            flag = {"message": str(flag), "severity": "medium"}
        flags.append(
            {
                "flag_id": str(flag.get("flag_id") or stable_id("bmue-quality", flag)),
                "severity": str(flag.get("severity") or "medium"),
                "message": str(flag.get("message") or flag),
                "source_artifact": "business_model_unit_economics_pack",
            }
        )
    return flags


def _decision_questions_for_bmue(payload: dict[str, Any], fallback: list[str] | None = None) -> list[str]:
    raw_ids = [str(item) for item in payload.get("question_ids") or [] if item]
    qid = str(payload.get("question_id") or payload.get("id") or "")
    if qid:
        raw_ids.append(qid)
    mapped: list[str] = []
    mapping = {
        "BMQ-01": ["business.revenue_mechanism"],
        "BMQ-02": ["business.revenue_mechanism"],
        "BMQ-03": ["business.revenue_mechanism"],
        "BMQ-04": ["business.revenue_mechanism"],
        "BMQ-05": ["business.unit_economics"],
        "BMQ-06": ["business.unit_economics"],
        "BMQ-07": ["business.unit_economics"],
        "BMQ-08": ["pdd.temu_segment_opacity", "business.unit_economics"],
        "BMQ-09": ["business.unit_economics", "financial.margin_conversion"],
        "BMQ-10": ["business.reinvestment_need"],
        "BMQ-11": ["business.reinvestment_need"],
        "BMQ-12": ["business.competitive_position"],
        "BMQ-13": ["business.competitive_position"],
        "BMQ-14": ["business.unit_economics"],
        "BMQ-15": ["pdd.temu_segment_opacity"],
        "BMQ-16": ["business.unit_economics"],
        "BMQ-17": ["business.competitive_position"],
        "BMQ-18": ["business.reinvestment_need"],
        "Q1": ["financial.margin_conversion"],
        "Q2": ["financial.margin_conversion"],
        "Q3": ["financial.cash_conversion"],
        "Q4": ["financial.balance_sheet"],
        "Q5": ["business.reinvestment_need"],
        "Q6": ["financial.revenue_sources"],
        "Q7": ["business.unit_economics"],
        "Q8": ["financial.accounting_red_flags"],
        "Q9": ["financial.dilution_sbc"],
    }
    for raw_id in raw_ids:
        mapped.extend(mapping.get(raw_id, []))
    text = " ".join(str(payload.get(key) or "") for key in ["claim_text", "claim_normalized", "question", "answer", "current_answer", "summary"])
    mapped.extend(infer_question_ids_from_text(text))
    business_or_pdd = [item for item in mapped if item.startswith("business.") or item.startswith("pdd.") or item.startswith("financial.")]
    return sorted(set(business_or_pdd or fallback or ["business.revenue_mechanism"]))


def _kind_from_assertion(assertion_class: str, card: dict[str, Any]) -> str:
    text = " ".join([assertion_class, str(card.get("source_scope") or ""), str(card.get("audited_scope") or "")]).casefold()
    if "audited" in text:
        return "audited_fact"
    if "management" in text or "claim" in text:
        return "management_claim"
    if "official" in text or "filing" in text:
        return "filed_fact"
    return "system_inference"


def _confidence_from_score(value: Any) -> str:
    if isinstance(value, (int, float)):
        if value >= 0.75:
            return "high"
        if value <= 0.35:
            return "low"
    text = str(value or "medium").casefold()
    if text in {"high", "medium", "low"}:
        return text
    return "medium"
