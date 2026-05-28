from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_PDD_EXTERNAL_MOAT_REGISTRY = Path(
    "config/qualitative/pdd_external_moat_sources.v1.json"
)


def load_external_moat_registry(
    company_id: str,
    *,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    if registry_path is None:
        if company_id == "pdd":
            registry_path = DEFAULT_PDD_EXTERNAL_MOAT_REGISTRY
        else:
            return _empty_registry(company_id)

    path = Path(registry_path)
    if not path.exists():
        return _empty_registry(company_id, missing_path=str(path))
    registry = json.loads(path.read_text(encoding="utf-8"))
    registry["registry_path"] = str(path)
    return registry


def build_external_moat_validation_plan(
    *,
    company: dict[str, Any],
    business_model_findings: dict[str, Any],
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    company_id = str(company.get("company_id") or "").lower()
    if company_id != "pdd":
        return {
            "status": "not_configured_for_company_v1",
            "company_id": company_id or "unknown",
            "scope": "External moat validation is currently prototyped for PDD only.",
            "source_lines": [],
            "hypotheses": [],
            "quality_tiers": [],
            "review_needed_decisions": [],
            "auditor_rules": [
                "Do not use external sources for official financial numbers.",
                "Do not make final moat conclusions from unverified public discussion.",
            ],
        }

    registry = load_external_moat_registry(company_id, registry_path=registry_path)
    source_lines = registry.get("source_lines", [])
    hypotheses = registry.get("hypotheses", [])
    review_decisions = registry.get("review_needed_decisions", [])
    status_counts = Counter(str(line.get("status", "unknown")) for line in source_lines)
    tier_counts = Counter(str(line.get("quality_tier", "unknown")) for line in source_lines)
    collector_groups = _controlled_collector_groups(source_lines)
    collector_status_counts = Counter(
        str(group.get("status", "unknown")) for group in collector_groups
    )

    official_gaps = business_model_findings.get("missing_evidence") or []
    official_analysis = business_model_findings.get("official_report_analysis") or {}
    official_subagents = official_analysis.get("subagent_reports") or []
    official_hypotheses = _official_moat_hypotheses(official_subagents)

    return {
        "status": "source_plan_ready_pending_collection",
        "company_id": company_id,
        "registry_path": registry.get("registry_path"),
        "scope": registry.get("scope"),
        "planned_only": True,
        "hypotheses": hypotheses,
        "source_lines": source_lines,
        "collector_groups": collector_groups,
        "collector_status_counts": dict(sorted(collector_status_counts.items())),
        "quality_tiers": registry.get("quality_tiers", []),
        "auditor_rules": registry.get("auditor_rules", []),
        "review_needed_decisions": review_decisions,
        "review_needed_decision_count": sum(
            1 for decision in review_decisions if decision.get("needs_user_review")
        ),
        "status_counts": dict(sorted(status_counts.items())),
        "tier_counts": dict(sorted(tier_counts.items())),
        "official_report_gaps": official_gaps,
        "official_moat_hypotheses": official_hypotheses,
        "evidence_output_schema": {
            "hypothesis_id": "Required. Link evidence to a specific moat hypothesis.",
            "source_line_id": "Required. Identify the source line used.",
            "source_name": "Required. Name the exact source/page/video/thread/report.",
            "source_url_or_locator": "Required. URL or search locator.",
            "source_quality_tier": "Required. Tier 1-4.",
            "language": "Required. English, Chinese, or other.",
            "claim": "The specific claim being supported, contradicted, or questioned.",
            "evidence_direction": "supporting, contradicting, mixed, or lead_only.",
            "confidence": "low, medium, or high, based on source quality and triangulation.",
            "requires_human_review": "True for important claims relying on low-quality sources.",
        },
        "next_collection_steps": _next_collection_steps(source_lines),
    }


def _empty_registry(company_id: str, *, missing_path: str | None = None) -> dict[str, Any]:
    return {
        "company_id": company_id,
        "status": "missing_registry",
        "registry_path": missing_path,
        "source_lines": [],
        "hypotheses": [],
        "quality_tiers": [],
        "review_needed_decisions": [],
        "auditor_rules": [],
    }


def _official_moat_hypotheses(subagent_reports: list[dict[str, Any]]) -> list[str]:
    hypotheses: list[str] = []
    for report in subagent_reports:
        if report.get("name") != "Moat Hypothesis Analyst":
            continue
        for finding in report.get("findings", []):
            if isinstance(finding, str):
                hypotheses.append(finding)
            elif isinstance(finding, dict):
                hypothesis = finding.get("hypothesis") or finding.get("claim")
                if hypothesis:
                    hypotheses.append(str(hypothesis))
    return hypotheses


def _next_collection_steps(source_lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps = []
    for line in source_lines:
        planned_sources = line.get("planned_sources", [])
        steps.append(
            {
                "source_line_id": line.get("source_line_id"),
                "name": line.get("name"),
                "status": "ready_to_collect",
                "first_locator": planned_sources[0].get("locator") if planned_sources else None,
                "quality_tier": line.get("quality_tier"),
                "validation_role": line.get("validation_role"),
            }
        )
    return steps


def _controlled_collector_groups(source_lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collector_profiles = {
        "regulatory_trade_reputation": {
            "collector_id": "regulatory_official_collector",
            "collector_type": "regulatory_sources",
            "status": "ready_pending_live_source_fetch",
            "allowed_adapters": ["official_search_locator", "web_reader_public_page", "manual_url_ingestion"],
            "collection_rule": "Start from government/regulator pages; social or media sources may only add context.",
        },
        "customer_app_reviews": {
            "collector_id": "app_review_and_review_site_collector",
            "collector_type": "app_store_and_review_sources",
            "status": "partially_collectable_v1",
            "allowed_adapters": ["web_reader_public_page", "manual_app_store_snapshot", "manual_url_ingestion"],
            "collection_rule": "Separate aggregate ratings/review volume from selected review excerpts.",
        },
        "merchant_seller_feedback": {
            "collector_id": "merchant_feedback_collector",
            "collector_type": "merchant_feedback",
            "status": "ready_pending_source_specific_collectors",
            "allowed_adapters": ["official_seller_page", "reddit_public_json", "manual_url_ingestion"],
            "collection_rule": "Official seller pages support rules; forums only create seller-economics leads.",
        },
        "customer_public_discussion": {
            "collector_id": "customer_forum_collector",
            "collector_type": "customer_forums",
            "status": "partially_collectable_v1",
            "allowed_adapters": ["reddit_public_json", "web_reader_public_page", "manual_url_ingestion"],
            "collection_rule": "Forum evidence is pattern/lead evidence and needs triangulation.",
        },
        "competitor_public_materials": {
            "collector_id": "competitor_official_material_collector",
            "collector_type": "competitor_official_materials",
            "status": "ready_pending_competitor_document_pipeline",
            "allowed_adapters": ["official_ir_download", "sec_or_exchange_filing", "manual_url_ingestion"],
            "collection_rule": "Competitor claims should come from official filings/IR before media or forum comparisons.",
        },
        "independent_business_reporting": {
            "collector_id": "business_reporting_collector",
            "collector_type": "independent_business_reporting",
            "status": "ready_pending_live_source_fetch",
            "allowed_adapters": ["web_reader_public_page", "manual_url_ingestion"],
            "collection_rule": "Use only as context unless the article provides visible methodology or direct source attribution.",
        },
    }
    groups: list[dict[str, Any]] = []
    for line in source_lines:
        source_line_id = str(line.get("source_line_id") or "")
        profile = collector_profiles.get(
            source_line_id,
            {
                "collector_id": f"{source_line_id}_collector",
                "collector_type": "generic_external_source_line",
                "status": "ready_pending_adapter",
                "allowed_adapters": ["manual_url_ingestion"],
                "collection_rule": "Preserve source quality, language, evidence direction, and human-review flags.",
            },
        )
        planned_sources = line.get("planned_sources") or []
        groups.append(
            {
                **profile,
                "source_line_id": source_line_id,
                "source_line_name": line.get("name"),
                "quality_tier": line.get("quality_tier"),
                "hypothesis_ids": line.get("hypothesis_ids", []),
                "source_types": line.get("source_types", []),
                "planned_source_count": len(planned_sources),
                "first_locator": planned_sources[0].get("locator") if planned_sources else None,
                "audit_notes": line.get("audit_notes", []),
                "output_schema": {
                    "source_line_id": "Source-line group that produced the evidence.",
                    "collector_id": "Controlled collector that produced or registered the evidence.",
                    "source_quality_tier": "Tier 1-4 source-quality label.",
                    "evidence_direction": "supporting, contradicting, mixed, or lead_only.",
                    "confidence": "low, medium, or high after source-quality and triangulation checks.",
                    "requires_human_review": "True for important claims from low-quality or conflicting sources.",
                },
            }
        )
    return groups
