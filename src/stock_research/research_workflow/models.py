from __future__ import annotations

import hashlib
from typing import Any


RELIABILITY_BY_EVIDENCE_KIND = {
    "audited_fact": "highest",
    "filed_fact": "high",
    "footnote_fact": "high",
    "interim_fact": "medium_high",
    "risk_disclosure": "medium_high",
    "management_explanation": "medium",
    "management_claim": "medium",
    "system_inference": "depends_on_chain",
    "inference": "depends_on_chain",
    "unknown": "gap_signal",
}


def normalize_confidence(value: Any) -> str:
    text = str(value or "medium").casefold()
    if text in {"high", "medium", "low"}:
        return text
    if text in {"highest", "strong"}:
        return "high"
    if text in {"weak", "needs_review"}:
        return "low"
    return "medium"


def stable_id(prefix: str, payload: Any) -> str:
    digest = hashlib.sha256(str(payload).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def make_evidence_item(
    *,
    evidence_id: str,
    question_ids: list[str],
    source_id: str,
    source_tier: int,
    source_type: str,
    locator: str = "",
    evidence_kind: str,
    excerpt: str = "",
    structured_fact: dict[str, Any] | None = None,
    confidence: str = "medium",
    upstream_refs: list[dict[str, Any]] | None = None,
    supports: list[str] | None = None,
    contradicts: list[str] | None = None,
    reliability: str | None = None,
    requires_human_review: bool | None = None,
) -> dict[str, Any]:
    normalized_questions = sorted({qid for qid in question_ids if qid})
    normalized_kind = evidence_kind or "inference"
    normalized_confidence = normalize_confidence(confidence)
    if requires_human_review is None:
        requires_human_review = normalized_kind in {"inference", "system_inference"} and normalized_confidence == "low"
    return {
        "evidence_id": evidence_id,
        "question_ids": normalized_questions,
        "source_id": source_id,
        "source_tier": source_tier,
        "source_type": source_type,
        "locator": locator,
        "evidence_kind": normalized_kind,
        "reliability": reliability or RELIABILITY_BY_EVIDENCE_KIND.get(normalized_kind, "unknown"),
        "excerpt": str(excerpt or "")[:1200],
        "structured_fact": structured_fact or {},
        "upstream_refs": upstream_refs or [],
        "supports": sorted(set(supports or normalized_questions)),
        "contradicts": sorted(set(contradicts or [])),
        "confidence": normalized_confidence,
        "requires_human_review": requires_human_review,
    }


def make_source_ref(
    *,
    source_id: str,
    source_type: str,
    source_tier: int,
    locator: str = "",
    title: str = "",
    reliability: str = "unknown",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "source_type": source_type,
        "source_tier": source_tier,
        "locator": locator,
        "title": title or source_id,
        "reliability": reliability,
        "metadata": metadata or {},
    }


def make_gap_request(
    *,
    gap_id: str,
    question_id: str,
    gap_type: str,
    description: str,
    priority: str = "P2",
    route: str = "human_review",
    owner_agent: str = "research_workflow",
    required_metrics: list[str] | None = None,
    required_source_types: list[str] | None = None,
    depends_on_artifact: str | None = None,
) -> dict[str, Any]:
    return {
        "gap_id": gap_id,
        "question_id": question_id,
        "gap_type": gap_type,
        "description": description,
        "priority": priority,
        "route": route,
        "owner_agent": owner_agent,
        "required_metrics": required_metrics or [],
        "required_source_types": required_source_types or [],
        "depends_on_artifact": depends_on_artifact,
        "status": "open",
    }


def question_ids_for_metric(metric: str) -> list[str]:
    text = str(metric or "").casefold()
    mapping = [
        ("revenue", ["financial.growth", "financial.revenue_sources", "business.revenue_mechanism"]),
        ("online_marketing", ["financial.revenue_sources", "business.revenue_mechanism"]),
        ("transaction_services", ["financial.revenue_sources", "business.revenue_mechanism"]),
        ("gross", ["financial.margin_conversion"]),
        ("operating_income", ["financial.margin_conversion"]),
        ("operating_expense", ["financial.margin_conversion"]),
        ("net_income", ["financial.margin_conversion", "financial.cash_conversion"]),
        ("operating_cash_flow", ["financial.cash_conversion"]),
        ("free_cash_flow", ["financial.cash_conversion", "price.owner_return"]),
        ("capex", ["financial.cash_conversion", "business.reinvestment_need", "price.expectations"]),
        ("cash", ["financial.balance_sheet", "price.owner_return"]),
        ("restricted_cash", ["financial.balance_sheet"]),
        ("investment", ["financial.balance_sheet", "price.owner_return"]),
        ("debt", ["financial.balance_sheet", "risk.regulatory_legal"]),
        ("liabilities", ["financial.balance_sheet"]),
        ("share_based", ["financial.dilution_sbc", "people.incentives"]),
        ("stock_based", ["financial.dilution_sbc", "people.incentives"]),
        ("diluted_shares", ["financial.dilution_sbc", "people.capital_allocation"]),
        ("merchant", ["financial.cash_conversion", "business.unit_economics"]),
        ("related_party", ["financial.accounting_red_flags", "people.control_governance"]),
        ("tax", ["financial.accounting_red_flags", "financial.margin_conversion"]),
    ]
    result: list[str] = []
    for needle, questions in mapping:
        if needle in text:
            result.extend(questions)
    return sorted(set(result or ["financial.accounting_red_flags"]))


def infer_question_ids_from_text(text: str) -> list[str]:
    lowered = str(text or "").casefold()
    keyword_map = [
        (["cash", "free cash", "operating cash", "working capital", "merchant deposit"], "financial.cash_conversion"),
        (["revenue", "growth", "online marketing", "transaction services"], "financial.revenue_sources"),
        (["margin", "profit", "expense", "cost"], "financial.margin_conversion"),
        (["restricted cash", "debt", "liabilit", "balance sheet"], "financial.balance_sheet"),
        (["sbc", "share-based", "dilution", "diluted share"], "financial.dilution_sbc"),
        (["auditor", "restatement", "material weakness", "related party"], "financial.accounting_red_flags"),
        (["business model", "unit economics", "take rate", "merchant", "customer"], "business.unit_economics"),
        (["competition", "moat", "competitor"], "business.competitive_position"),
        (["control", "governance", "vie", "voting"], "people.control_governance"),
        (["incentive", "compensation", "ownership"], "people.incentives"),
        (["capital allocation", "buyback", "dividend"], "people.capital_allocation"),
        (["regulatory", "legal", "risk", "lawsuit"], "risk.regulatory_legal"),
        (["valuation", "yield", "enterprise value", "market cap"], "price.owner_return"),
        (["temu", "segment"], "pdd.temu_segment_opacity"),
    ]
    result = []
    for keywords, question_id in keyword_map:
        if any(keyword in lowered for keyword in keywords):
            result.append(question_id)
    return sorted(set(result))
