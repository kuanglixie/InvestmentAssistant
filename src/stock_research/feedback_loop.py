from __future__ import annotations

import hashlib
from typing import Any

from stock_research.state import ResearchState, utc_now_iso


FEEDBACK_LOOP_PACK_SCHEMA_VERSION = "feedback_loop_pack_v1"


def build_feedback_loop_pack(state: ResearchState) -> dict[str, Any]:
    financial_pack = state.get("financial_report_pack") or {}
    layer1_pack = state.get("layer1_question_pack") or {}
    evidence_pack = state.get("evidence_communication_pack") or {}

    metric_catalog = _metric_catalog(financial_pack)
    fact_catalog = _fact_catalog(financial_pack)
    raw_requests = _collect_feedback_requests(layer1_pack, evidence_pack)

    financial_requests = []
    metric_requests = []
    layer1_requeries = []
    evidence_followups = []
    external_requests = []
    human_review = []

    for request in raw_requests:
        routed = _route_request(request, metric_catalog=metric_catalog, fact_catalog=fact_catalog)
        if routed["route"] == "financial_extractor":
            financial_requests.append(routed)
        elif routed["route"] == "metric_recalculation":
            metric_requests.append(routed)
        elif routed["route"] == "layer1_requery":
            layer1_requeries.append(routed)
        elif routed["route"] == "evidence_communication":
            evidence_followups.append(routed)
        elif routed["route"] == "external_data":
            external_requests.append(routed)
        else:
            human_review.append(routed)

    # Every new numeric fact request should flow back into Layer 1 after extraction.
    for item in financial_requests + metric_requests:
        layer1_requeries.append(_layer1_requery_from_routed_item(item))

    layer1_requeries = _unique_by_id(layer1_requeries)
    pack = {
        "schema_version": FEEDBACK_LOOP_PACK_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "agent_run": {
            "run_id": state.get("run_id"),
            "company_id": ((financial_pack.get("company") or {}).get("company_id") or state.get("company_query")),
            "company_name": ((financial_pack.get("company") or {}).get("legal_name") or state.get("company_query")),
            "status": "routed",
            "max_feedback_iterations": 2,
            "current_iteration": int(state.get("feedback_iteration") or 1),
            "auto_rerun_performed": False,
            "loop_policy": (
                "Feedback Router routes new evidence-layer questions back to financial extraction, "
                "metric recalculation, Layer-1 requery, evidence follow-up, external data, or human review. "
                "It does not invent missing facts."
            ),
        },
        "source_artifacts": {
            "financial_report_pack_path": state.get("financial_report_pack_path"),
            "layer1_question_pack_path": state.get("layer1_question_pack_path"),
            "evidence_communication_pack_path": state.get("evidence_communication_pack_path"),
        },
        "financial_extractor_requests": financial_requests,
        "metric_recalculation_requests": metric_requests,
        "layer1_requery_requests": layer1_requeries,
        "evidence_communication_followups": evidence_followups,
        "external_data_requests": external_requests,
        "human_review_requests": human_review,
        "closed_loop_status": _closed_loop_status(
            financial_requests=financial_requests,
            metric_requests=metric_requests,
            layer1_requeries=layer1_requeries,
            evidence_followups=evidence_followups,
        ),
        "summary": {
            "raw_feedback_request_count": len(raw_requests),
            "financial_extractor_request_count": len(financial_requests),
            "metric_recalculation_request_count": len(metric_requests),
            "layer1_requery_request_count": len(layer1_requeries),
            "evidence_communication_followup_count": len(evidence_followups),
            "external_data_request_count": len(external_requests),
            "human_review_request_count": len(human_review),
        },
    }
    return pack


def apply_feedback_to_layer1_question_pack(
    layer1_pack: dict[str, Any],
    feedback_pack: dict[str, Any],
) -> dict[str, Any]:
    updated = dict(layer1_pack or {})
    feedback_loop_path = (feedback_pack.get("source_artifacts") or {}).get("feedback_loop_pack_path")
    updated["feedback_requery_questions"] = feedback_pack.get("layer1_requery_requests") or []
    updated["feedback_loop_summary"] = feedback_pack.get("summary") or {}
    updated["feedback_loop_path"] = feedback_loop_path
    updated["feedback_loop_pack_path"] = feedback_loop_path
    return updated


def build_feedback_loop_report(pack: dict[str, Any]) -> str:
    agent_run = pack.get("agent_run") or {}
    summary = pack.get("summary") or {}
    lines = [
        f"# Feedback Router：{agent_run.get('company_name') or agent_run.get('company_id') or 'Unknown Company'}",
        "",
        "## 1. 闭环状态",
        "",
        f"- 状态：`{pack.get('closed_loop_status')}`",
        f"- 原始反馈请求：{summary.get('raw_feedback_request_count', 0)}",
        f"- 回 Financial Extractor：{summary.get('financial_extractor_request_count', 0)}",
        f"- 回 Metrics：{summary.get('metric_recalculation_request_count', 0)}",
        f"- 回 Layer 1：{summary.get('layer1_requery_request_count', 0)}",
        f"- 继续 Evidence / Communication：{summary.get('evidence_communication_followup_count', 0)}",
        f"- 外部数据：{summary.get('external_data_request_count', 0)}",
        f"- 人工复核：{summary.get('human_review_request_count', 0)}",
        "",
        "## 2. 回第一层的问题",
        "",
    ]
    for item in pack.get("layer1_requery_requests") or []:
        lines.extend(
            [
                f"### {item.get('request_id')}",
                "",
                f"- 问题：{item.get('question') or item.get('request')}",
                f"- 当前事实状态：`{item.get('current_financial_pack_status')}`",
                f"- 回流原因：{item.get('why_it_matters') or '未披露'}",
                f"- 关联问题：{_join(item.get('linked_questions'))}",
                "",
            ]
        )
    lines.extend(["## 3. 需要补抽的数字", ""])
    for item in pack.get("financial_extractor_requests") or []:
        lines.append(
            f"- `{item.get('priority') or 'P2'}` {item.get('request')}；缺口：{_join(item.get('missing_metrics'))}"
        )
    lines.extend(["", "## 4. 继续读文字证据的问题", ""])
    for item in pack.get("evidence_communication_followups") or []:
        lines.append(f"- {item.get('request') or item.get('question')}；来源：{item.get('source')}")
    return "\n".join(lines).strip() + "\n"


def _collect_feedback_requests(layer1_pack: dict[str, Any], evidence_pack: dict[str, Any]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for handoff in evidence_pack.get("handoff_to_financial_extractor") or []:
        requests.append(
            {
                "request_id": handoff.get("handoff_id") or _stable_id(handoff),
                "request": handoff.get("request") or handoff.get("handoff_id"),
                "missing_metrics": handoff.get("missing_metrics") or [],
                "why_it_matters": handoff.get("why_it_matters") or "",
                "linked_questions": handoff.get("linked_questions") or [],
                "priority": handoff.get("priority") or "P2",
                "source": handoff.get("source") or "evidence_communication_pack",
                "request_type": "numeric_or_metric_handoff",
            }
        )
    for item in evidence_pack.get("proactive_discoveries") or []:
        if not item.get("creates_new_question") and not item.get("unknowns"):
            continue
        requests.append(
            {
                "request_id": item.get("discovery_id") or _stable_id(item),
                "request": item.get("new_question_text") or item.get("title") or item.get("summary"),
                "missing_metrics": item.get("monitoring_metrics") or item.get("unknowns") or [],
                "why_it_matters": item.get("why_it_matters") or item.get("summary") or "",
                "linked_questions": item.get("linked_questions") or [],
                "priority": "P2",
                "source": "proactive_discovery",
                "request_type": "new_narrative_or_problem",
            }
        )
    for unknown in evidence_pack.get("unknowns") or []:
        requests.append(
            {
                "request_id": unknown.get("unknown_id") or _stable_id(unknown),
                "request": unknown.get("unknown"),
                "missing_metrics": [unknown.get("unknown")] if unknown.get("unknown") else [],
                "why_it_matters": f"Unresolved from {unknown.get('source') or 'evidence pack'}.",
                "linked_questions": [unknown.get("linked_question")] if unknown.get("linked_question") else [],
                "priority": "P3",
                "source": unknown.get("source") or "unknown_registry",
                "request_type": "unknown",
            }
        )
    for item in layer1_pack.get("handoff_to_financial_extractor") or []:
        requests.append(
            {
                "request_id": item.get("handoff_id") or _stable_id(item),
                "request": item.get("request") or item.get("handoff_id"),
                "missing_metrics": item.get("missing_metrics") or [],
                "why_it_matters": item.get("why_it_matters") or "",
                "linked_questions": item.get("linked_questions") or [],
                "priority": item.get("priority") or "P2",
                "source": "layer1_question_pack",
                "request_type": "layer1_numeric_handoff",
            }
        )
    return _unique_by_id(requests)


def _route_request(
    request: dict[str, Any],
    *,
    metric_catalog: set[str],
    fact_catalog: set[str],
) -> dict[str, Any]:
    missing_metrics = [str(item) for item in request.get("missing_metrics") or [] if item]
    statuses = [_metric_status(metric, metric_catalog=metric_catalog, fact_catalog=fact_catalog) for metric in missing_metrics]
    text = " ".join([str(request.get("request") or ""), " ".join(missing_metrics)]).lower()

    routed = {
        **request,
        "current_financial_pack_status": _combined_status(statuses),
        "metric_statuses": statuses,
        "route_reason": "",
    }
    if missing_metrics and all(status.get("status") in {"available_as_fact", "available_as_metric_family"} for status in statuses):
        return {**routed, "route": "layer1_requery", "route_reason": "Current financial pack already has relevant facts or metrics."}
    if any(_looks_like_external_data(metric) for metric in missing_metrics) or any(
        token in text for token in ["temu", "gmv", "active_buyers", "monthly_active", "retention", "获客", "留存"]
    ):
        return {**routed, "route": "external_data", "route_reason": "Question requires operating KPI or external validation beyond current official financial facts."}
    if any(_looks_like_metric_recalc(metric) for metric in missing_metrics):
        return {**routed, "route": "metric_recalculation", "route_reason": "Request is a formula or bridge that should be recalculated after inputs are available."}
    if any(_looks_like_numeric_fact(metric) for metric in missing_metrics):
        return {**routed, "route": "financial_extractor", "route_reason": "Request needs missing numeric facts from filings or tables."}
    if any(token in text for token in ["管理层", "解释", "战略", "叙事", "监管", "治理", "审计", "risk", "legal", "vie"]):
        return {**routed, "route": "evidence_communication", "route_reason": "Question needs more official text or management communication evidence."}
    return {**routed, "route": "human_review", "route_reason": "Router could not safely classify the request."}


def _layer1_requery_from_routed_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": f"layer1_requery_{item.get('request_id')}",
        "route": "layer1_requery",
        "request": item.get("request"),
        "question": f"补充事实后，第一层是否能回答：{item.get('request')}",
        "missing_metrics": item.get("missing_metrics") or [],
        "why_it_matters": item.get("why_it_matters") or item.get("route_reason") or "",
        "linked_questions": item.get("linked_questions") or [],
        "priority": item.get("priority") or "P2",
        "source": item.get("source") or "feedback_router",
        "current_financial_pack_status": item.get("current_financial_pack_status") or "pending_new_facts",
        "depends_on_route": item.get("route"),
    }


def _metric_catalog(financial_pack: dict[str, Any]) -> set[str]:
    catalog = set()
    for metric in financial_pack.get("financial_metrics") or []:
        if metric.get("formula_id"):
            catalog.add(str(metric["formula_id"]).lower())
    return catalog


def _fact_catalog(financial_pack: dict[str, Any]) -> set[str]:
    catalog = set()
    for fact in financial_pack.get("fact_ledger") or []:
        for key in ("canonical_metric", "label", "xbrl_tag"):
            if fact.get(key):
                catalog.add(str(fact[key]).lower())
    for row in (financial_pack.get("annual_facts") or []) + (financial_pack.get("quarterly_facts") or []):
        for key, value in row.items():
            if value is not None:
                catalog.add(str(key).lower())
    return catalog


def _metric_status(metric: str, *, metric_catalog: set[str], fact_catalog: set[str]) -> dict[str, str]:
    key = str(metric or "").lower().strip()
    if not key:
        return {"metric": metric, "status": "empty"}
    if key in metric_catalog:
        return {"metric": metric, "status": "available_as_metric_family"}
    if key in fact_catalog:
        return {"metric": metric, "status": "available_as_fact"}
    return {"metric": metric, "status": "missing_or_not_structured"}


def _combined_status(statuses: list[dict[str, str]]) -> str:
    if not statuses:
        return "no_metric_requested"
    values = {item.get("status") for item in statuses}
    if values <= {"available_as_fact", "available_as_metric_family"}:
        return "answerable_from_current_pack"
    if values & {"available_as_fact", "available_as_metric_family"}:
        return "partially_answerable_from_current_pack"
    return "requires_new_extraction_or_disclosure"


def _looks_like_numeric_fact(metric: str) -> bool:
    text = str(metric or "").lower()
    tokens = [
        "revenue",
        "income",
        "cost",
        "expense",
        "cash",
        "debt",
        "inventory",
        "capex",
        "share",
        "sbc",
        "tax",
        "receivable",
        "payable",
        "deposit",
        "margin",
        "投资",
        "收入",
        "利润",
        "成本",
        "费用",
        "现金",
        "债务",
        "存货",
        "税",
    ]
    return any(token in text for token in tokens)


def _looks_like_metric_recalc(metric: str) -> bool:
    text = str(metric or "").lower()
    return any(token in text for token in ["bridge", "ratio", "margin", "yoy", "qoq", "rate", "turnover", "recalc"])


def _looks_like_external_data(metric: str) -> bool:
    text = str(metric or "").lower()
    return any(
        token in text
        for token in [
            "gmv",
            "active_buyers",
            "monthly_active_users",
            "orders",
            "take_rate",
            "retention",
            "用户",
            "订单",
            "留存",
            "获客",
            "地区利润率",
        ]
    )


def _closed_loop_status(
    *,
    financial_requests: list[dict[str, Any]],
    metric_requests: list[dict[str, Any]],
    layer1_requeries: list[dict[str, Any]],
    evidence_followups: list[dict[str, Any]],
) -> str:
    if financial_requests:
        return "routed_to_financial_extraction_then_layer1"
    if metric_requests:
        return "routed_to_metrics_then_layer1"
    if layer1_requeries:
        return "routed_back_to_layer1"
    if evidence_followups:
        return "routed_back_to_evidence_communication"
    return "no_feedback_needed"


def _unique_by_id(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result = []
    for item in items:
        key = str(item.get("request_id") or item.get("handoff_id") or item.get("request") or item)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _stable_id(value: Any) -> str:
    return hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:10]


def _join(items: Any) -> str:
    values = [str(item) for item in (items or []) if item]
    return "；".join(values) if values else "未披露"
