from __future__ import annotations

from typing import Any

from stock_research.research_workflow.models import make_gap_request, stable_id


GAP_ROUTER_SCHEMA_VERSION = "research_gap_router_v1"


def build_research_backlog(
    *,
    filing_deep_read_pack: dict[str, Any],
    registry_gap_requests: list[dict[str, Any]] | None = None,
    feedback_loop_pack: dict[str, Any] | None = None,
    gap_decisions: list[dict[str, Any]] | None = None,
    unsupported_claims: list[dict[str, Any]] | None = None,
    confidence_caps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Route deep-read gaps and QA gaps into a concrete research backlog."""

    backlog = []
    for gap in filing_deep_read_pack.get("gap_requests") or []:
        backlog.append(_normalize_gap(gap))
    for gap in registry_gap_requests or []:
        backlog.append(_normalize_gap(gap))
    for decision in gap_decisions or []:
        backlog.append(_from_gap_decision(decision))
    for claim in unsupported_claims or []:
        backlog.append(
            make_gap_request(
                gap_id=stable_id("unsupported-claim", claim),
                question_id=str(claim.get("question_id") or "workflow"),
                gap_type="unsupported_claim",
                description=str(claim.get("claim") or "Question has no evidence-backed answer."),
                priority="P0" if str(claim.get("question_id") or "").startswith(("financial.", "people.", "risk.", "price.")) else "P1",
                route="official_filing_deep_read",
                owner_agent="filing_deep_read",
                required_source_types=["20-F", "6-K", "earnings_release"],
                depends_on_artifact="theme_workpaper_pack",
            )
        )
    for cap in confidence_caps or []:
        backlog.append(
            make_gap_request(
                gap_id=stable_id("confidence-cap", cap),
                question_id=str(cap.get("question_id") or "workflow"),
                gap_type="confidence_cap",
                description=str(cap.get("reason") or "Answer needs contradiction checks before confidence upgrade."),
                priority="P1",
                route="contradiction_matrix",
                owner_agent="filing_deep_read",
                depends_on_artifact="qa_gap_triage",
            )
        )
    for routed in _feedback_requests(feedback_loop_pack or {}):
        backlog.append(routed)

    backlog = _dedupe_backlog(backlog)
    route_counts: dict[str, int] = {}
    owner_counts: dict[str, int] = {}
    for item in backlog:
        route_counts[item.get("route", "unknown")] = route_counts.get(item.get("route", "unknown"), 0) + 1
        owner_counts[item.get("owner_agent", "unknown")] = owner_counts.get(item.get("owner_agent", "unknown"), 0) + 1

    return {
        "schema_version": GAP_ROUTER_SCHEMA_VERSION,
        "backlog_items": backlog,
        "summary": {
            "backlog_item_count": len(backlog),
            "route_counts": dict(sorted(route_counts.items())),
            "owner_agent_counts": dict(sorted(owner_counts.items())),
            "highest_priority": _highest_priority(backlog),
        },
    }


def _normalize_gap(gap: dict[str, Any]) -> dict[str, Any]:
    if all(key in gap for key in ["gap_id", "question_id", "route", "owner_agent"]):
        return gap
    return make_gap_request(
        gap_id=str(gap.get("gap_id") or stable_id("gap", gap)),
        question_id=str(gap.get("question_id") or "workflow"),
        gap_type=str(gap.get("gap_type") or "evidence_gap"),
        description=str(gap.get("description") or gap),
        priority=str(gap.get("priority") or "P2"),
        route=str(gap.get("route") or "human_review"),
        owner_agent=str(gap.get("owner_agent") or "research_workflow"),
        required_metrics=[str(item) for item in gap.get("required_metrics") or []],
        required_source_types=[str(item) for item in gap.get("required_source_types") or []],
        depends_on_artifact=gap.get("depends_on_artifact"),
    )


def _from_gap_decision(decision: dict[str, Any]) -> dict[str, Any]:
    next_action = str(decision.get("next_action") or "")
    route = {
        "collect_more_sources": "source_map",
        "extract_more_evidence": "official_filing_deep_read",
        "build_deeper_workpaper": "contradiction_matrix",
        "human_review_required": "human_review",
    }.get(next_action, "monitor")
    owner = {
        "source_map": "source_collection",
        "official_filing_deep_read": "filing_deep_read",
        "contradiction_matrix": "filing_deep_read",
        "human_review": "human",
    }.get(route, "research_workflow")
    return make_gap_request(
        gap_id=stable_id("gap-decision", decision),
        question_id=str(decision.get("question_id") or "workflow"),
        gap_type=str(decision.get("gap_type") or "qa_gap"),
        description=str(decision.get("reason") or decision),
        priority="P0" if next_action in {"collect_more_sources", "extract_more_evidence", "human_review_required"} else "P1",
        route=route,
        owner_agent=owner,
        depends_on_artifact="qa_gap_triage",
    )


def _feedback_requests(feedback_loop_pack: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    groups = [
        ("financial_extractor_requests", "financial_extractor"),
        ("metric_recalculation_requests", "metrics"),
        ("layer1_requery_requests", "layer1_question_pack"),
        ("evidence_communication_followups", "evidence_communication"),
        ("external_data_requests", "external_data"),
        ("human_review_requests", "human"),
    ]
    for key, owner in groups:
        for request in feedback_loop_pack.get(key) or []:
            results.append(
                make_gap_request(
                    gap_id=f"feedback_{request.get('request_id') or stable_id(key, request)}",
                    question_id=_linked_question(request),
                    gap_type=f"feedback_{key}",
                    description=str(request.get("request") or request.get("question") or request),
                    priority=str(request.get("priority") or "P2"),
                    route=str(request.get("route") or owner),
                    owner_agent=owner,
                    required_metrics=[str(item) for item in request.get("missing_metrics") or []],
                    required_source_types=[],
                    depends_on_artifact="feedback_loop_pack",
                )
            )
    return results


def _linked_question(request: dict[str, Any]) -> str:
    linked = request.get("linked_questions") or []
    if linked:
        return str(linked[0])
    text = " ".join(str(request.get(key) or "") for key in ["request", "question"]).casefold()
    if "cash" in text:
        return "financial.cash_conversion"
    if "margin" in text or "profit" in text:
        return "financial.margin_conversion"
    if "temu" in text or "segment" in text:
        return "pdd.temu_segment_opacity"
    if "governance" in text or "vie" in text:
        return "people.control_governance"
    return "workflow"


def _dedupe_backlog(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    deduped = []
    for item in items:
        key = (
            str(item.get("gap_id") or ""),
            str(item.get("question_id") or ""),
            str(item.get("description") or "")[:120],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _highest_priority(items: list[dict[str, Any]]) -> str:
    order = ["P0", "P1", "P2", "P3"]
    present = {str(item.get("priority") or "P3") for item in items}
    for priority in order:
        if priority in present:
            return priority
    return "none"
