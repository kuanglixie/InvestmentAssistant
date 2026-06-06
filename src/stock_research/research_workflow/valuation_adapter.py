from __future__ import annotations

from collections import Counter
from typing import Any

from stock_research.research_workflow.models import make_evidence_item, make_gap_request, make_source_ref, stable_id
from stock_research.state import ResearchState, utc_now_iso


VALUATION_ADAPTER_SCHEMA_VERSION = "valuation_workflow_adapter_v1"


def build_valuation_workflow_evidence(state: ResearchState) -> dict[str, Any]:
    """Expose valuation metrics as Right Price evidence only."""

    metrics = state.get("valuation_metrics") or []
    items = []
    gap_requests = []
    for metric in metrics:
        items.append(_metric_item(metric, len(items) + 1))
        if metric.get("status") != "calculated":
            gap_requests.append(_metric_gap(metric))

    question_counts = Counter()
    for item in items:
        for question_id in item.get("question_ids", []):
            question_counts[question_id] += 1

    return {
        "schema_version": VALUATION_ADAPTER_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "source_artifact": "valuation_metrics",
        "source_artifact_path": state.get("state_path"),
        "evidence_items": items,
        "source_refs": [
            make_source_ref(
                source_id="valuation_metrics",
                source_type="valuation_metrics",
                source_tier=1,
                locator="state.valuation_metrics",
                title="Valuation Metrics",
                reliability="derived_from_official_financials_and_market_inputs",
                metadata={
                    "metric_count": len(metrics),
                    "valuation_findings": state.get("valuation_findings") or {},
                },
            )
        ],
        "gap_requests": gap_requests,
        "quality_flags": _quality_flags(state, metrics),
        "summary": {
            "evidence_item_count": len(items),
            "source_ref_count": 1,
            "gap_request_count": len(gap_requests),
            "quality_flag_count": len(_quality_flags(state, metrics)),
            "question_evidence_counts": dict(sorted(question_counts.items())),
        },
    }


def _metric_item(metric: dict[str, Any], ordinal: int) -> dict[str, Any]:
    formula_id = str(metric.get("formula_id") or "")
    return make_evidence_item(
        evidence_id=f"VALUATION-METRIC-{ordinal:03d}",
        question_ids=["price.owner_return", "price.expectations"],
        source_id="valuation_metrics",
        source_tier=1,
        source_type="derived_valuation_metric",
        locator=formula_id,
        evidence_kind="system_inference",
        excerpt=str(metric.get("summary") or metric.get("note") or formula_id or metric.get("status") or "")[:1000],
        structured_fact=metric,
        confidence="medium" if metric.get("status") == "calculated" else "low",
        upstream_refs=[{"upstream_artifact": "valuation_metrics", "formula_id": formula_id}],
        requires_human_review=metric.get("status") != "calculated",
    )


def _metric_gap(metric: dict[str, Any]) -> dict[str, Any]:
    formula_id = str(metric.get("formula_id") or "valuation_metric")
    missing = [str(item) for item in metric.get("missing") or []]
    return make_gap_request(
        gap_id=stable_id("valuation-gap", metric),
        question_id="price.owner_return",
        gap_type="valuation_metric_not_calculated",
        description=str(metric.get("note") or f"{formula_id} was not calculated."),
        priority="P1",
        route="valuation",
        owner_agent="valuation",
        required_metrics=missing,
        depends_on_artifact="valuation_metrics",
    )


def _quality_flags(state: ResearchState, metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flags = []
    if not metrics:
        flags.append(
            {
                "flag_id": "valuation_metrics_absent",
                "severity": "medium",
                "message": "No valuation metrics were available for Right Price evidence.",
                "source_artifact": "valuation_metrics",
            }
        )
    findings = state.get("valuation_findings") or {}
    if findings.get("status") and findings.get("status") != "valuation_metrics_calculated":
        flags.append(
            {
                "flag_id": "valuation_findings_not_calculated",
                "severity": "medium",
                "message": f"Valuation findings status is {findings.get('status')}.",
                "source_artifact": "valuation_metrics",
            }
        )
    return flags
