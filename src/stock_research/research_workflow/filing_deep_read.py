from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from stock_research.research_workflow.bmue_adapter import build_bmue_workflow_evidence
from stock_research.research_workflow.financial_adapter import build_financial_workflow_evidence
from stock_research.research_workflow.models import make_gap_request, stable_id
from stock_research.research_workflow.official_evidence_adapter import build_official_report_workflow_evidence
from stock_research.state import ResearchState, utc_now_iso


FILING_DEEP_READ_SCHEMA_VERSION = "filing_deep_read_pack_v1"


def build_filing_deep_read_pack(
    state: ResearchState,
    source_map: dict[str, Any],
    question_pack: dict[str, Any],
    evidence_plan: dict[str, Any],
) -> dict[str, Any]:
    """Build the official-filing-only evidence-mining layer.

    This layer sits between evidence planning and theme workpapers. It is not a
    report writer. It organizes source sections, evidence cards, claim ledgers,
    unknowns, contradictions, and gap requests so the Theme Workpaper consumes a
    deeper evidence base.
    """

    financial_bundle = build_financial_workflow_evidence(state)
    bmue_bundle = build_bmue_workflow_evidence(state)
    official_bundle = build_official_report_workflow_evidence(state)
    evidence_cards = []
    evidence_cards.extend(financial_bundle.get("evidence_items") or [])
    evidence_cards.extend(bmue_bundle.get("evidence_items") or [])
    evidence_cards.extend(official_bundle.get("evidence_items") or [])

    source_refs = []
    source_refs.extend(financial_bundle.get("source_refs") or [])
    source_refs.extend(bmue_bundle.get("source_refs") or [])
    source_refs.extend(official_bundle.get("source_refs") or [])
    source_refs.extend(_source_map_refs(source_map))
    source_refs = _dedupe_source_refs(source_refs)

    gap_requests = []
    gap_requests.extend(financial_bundle.get("gap_requests") or [])
    gap_requests.extend(bmue_bundle.get("gap_requests") or [])
    gap_requests.extend(official_bundle.get("gap_requests") or [])
    gap_requests.extend(_source_plan_gap_requests(source_map, question_pack, evidence_plan))
    gap_requests = _dedupe_gap_requests(gap_requests)

    contradiction_matrix = _contradiction_matrix(state, evidence_cards, gap_requests)
    question_coverage = _question_coverage(question_pack, evidence_cards, gap_requests, contradiction_matrix)
    section_map = _section_map(source_map)

    return {
        "schema_version": FILING_DEEP_READ_SCHEMA_VERSION,
        "workflow_schema_version": "decision_question_led_workflow_v1",
        "prototype_version": "v1.25",
        "generated_at": utc_now_iso(),
        "scope": {
            "source_policy": "official_filing_and_existing_official_evidence_only",
            "allowed_source_tiers": [1],
            "purpose": "Deep evidence mining layer between evidence plan and theme workpapers.",
        },
        "section_map": section_map,
        "source_refs": source_refs,
        "evidence_cards": evidence_cards,
        "claim_ledger": _claim_ledger(evidence_cards),
        "numeric_fact_refs": _numeric_fact_refs(evidence_cards),
        "management_explanations": _management_explanations(evidence_cards),
        "risk_disclosures": _risk_disclosures(evidence_cards, section_map),
        "unknowns": _unknowns(gap_requests),
        "contradiction_matrix": contradiction_matrix,
        "question_coverage": question_coverage,
        "gap_requests": gap_requests,
        "adapter_summaries": {
            "financial": financial_bundle.get("summary") or {},
            "business_model_unit_economics": bmue_bundle.get("summary") or {},
            "official_report_evidence": official_bundle.get("summary") or {},
        },
        "quality_flags": (
            (financial_bundle.get("quality_flags") or [])
            + (bmue_bundle.get("quality_flags") or [])
            + (official_bundle.get("quality_flags") or [])
        ),
        "summary": {
            "section_count": len(section_map),
            "source_ref_count": len(source_refs),
            "evidence_card_count": len(evidence_cards),
            "claim_count": len(_claim_ledger(evidence_cards)),
            "numeric_fact_ref_count": len(_numeric_fact_refs(evidence_cards)),
            "gap_request_count": len(gap_requests),
            "contradiction_count": len(contradiction_matrix),
            "questions_with_evidence": sum(1 for row in question_coverage if row.get("evidence_count", 0) > 0),
            "question_count": len(question_pack.get("questions") or []),
        },
    }


def _source_map_refs(source_map: dict[str, Any]) -> list[dict[str, Any]]:
    refs = []
    for row in source_map.get("source_inventory") or []:
        refs.append(
            {
                "source_id": str(row.get("source_id") or ""),
                "source_type": str(row.get("source_type") or "unknown"),
                "source_tier": int(row.get("source_tier") or 2),
                "locator": str(row.get("local_path") or row.get("url") or ""),
                "title": str(row.get("source_name") or row.get("source_id") or ""),
                "reliability": "official_or_regulator" if row.get("source_tier") == 1 else "lower_tier",
                "metadata": row,
            }
        )
    return refs


def _section_map(source_map: dict[str, Any]) -> list[dict[str, Any]]:
    sections = []
    for row in source_map.get("source_inventory") or []:
        if row.get("source_tier") != 1:
            continue
        source_type = str(row.get("source_type") or "")
        if source_type not in {"20-F", "10-K", "10-Q", "6-K", "annual_report", "earnings_release", "sec_filing"}:
            continue
        available_sections = row.get("sections") or []
        sections.append(
            {
                "source_id": row.get("source_id"),
                "source_type": source_type,
                "period": row.get("period"),
                "filing_date": row.get("filing_date"),
                "publication_date": row.get("publication_date"),
                "local_path": row.get("local_path"),
                "collection_status": row.get("collection_status"),
                "parse_status": row.get("parse_status"),
                "sections": available_sections,
                "question_routes": _section_question_routes(available_sections, source_type),
                "reliability_tier": _source_reliability(source_type),
            }
        )
    return sections


def _section_question_routes(sections: list[str], source_type: str) -> list[str]:
    routes = set()
    for section in sections:
        text = str(section).casefold()
        if "financial" in text or "statement" in text:
            routes.update(["financial.growth", "financial.margin_conversion", "financial.cash_conversion", "financial.balance_sheet"])
        if "md&a" in text or "management" in text:
            routes.update(["financial.growth", "financial.margin_conversion", "people.candor"])
        if "risk" in text:
            routes.update(["risk.regulatory_legal", "financial.accounting_red_flags"])
        if "footnote" in text:
            routes.update(["financial.cash_conversion", "financial.balance_sheet", "financial.accounting_red_flags"])
        if "governance" in text:
            routes.update(["people.control_governance", "people.incentives"])
        if "business" in text:
            routes.update(["business.revenue_mechanism", "business.unit_economics"])
    if source_type in {"6-K", "earnings_release"}:
        routes.update(["financial.growth", "financial.margin_conversion", "financial.cash_conversion"])
    return sorted(routes)


def _source_reliability(source_type: str) -> str:
    if source_type in {"20-F", "10-K"}:
        return "audited_annual_filing"
    if source_type in {"10-Q", "6-K", "earnings_release"}:
        return "official_interim_filing"
    if source_type == "sec_filing":
        return "official_regulator_index"
    return "official_source"


def _claim_ledger(evidence_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims = []
    for item in evidence_cards:
        if item.get("evidence_kind") not in {"management_claim", "management_explanation", "system_inference", "inference"}:
            continue
        claims.append(
            {
                "claim_id": f"CLAIM-{len(claims) + 1:04d}",
                "evidence_id": item.get("evidence_id"),
                "claim_type": item.get("evidence_kind"),
                "question_ids": item.get("question_ids") or [],
                "text": item.get("excerpt"),
                "source_id": item.get("source_id"),
                "confidence": item.get("confidence"),
                "reliability": item.get("reliability"),
                "upstream_refs": item.get("upstream_refs") or [],
            }
        )
    return claims


def _numeric_fact_refs(evidence_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs = []
    for item in evidence_cards:
        fact = item.get("structured_fact") or {}
        upstream_refs = item.get("upstream_refs") or []
        if not any(ref.get("upstream_fact_id") for ref in upstream_refs) and "value" not in fact:
            continue
        refs.append(
            {
                "evidence_id": item.get("evidence_id"),
                "metric": fact.get("canonical_metric") or fact.get("metric") or fact.get("label"),
                "value": fact.get("value"),
                "period": fact.get("period_label") or fact.get("period_year") or fact.get("end_date") or fact.get("instant"),
                "source_document": fact.get("source_document"),
                "source_table": fact.get("source_table"),
                "upstream_refs": upstream_refs,
            }
        )
    return refs


def _management_explanations(evidence_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "evidence_id": item.get("evidence_id"),
            "question_ids": item.get("question_ids"),
            "explanation": item.get("excerpt"),
            "source_id": item.get("source_id"),
            "confidence": item.get("confidence"),
        }
        for item in evidence_cards
        if item.get("evidence_kind") in {"management_claim", "management_explanation"}
    ]


def _risk_disclosures(evidence_cards: list[dict[str, Any]], section_map: list[dict[str, Any]]) -> list[dict[str, Any]]:
    disclosures = [
        {
            "evidence_id": item.get("evidence_id"),
            "question_ids": item.get("question_ids"),
            "risk_text": item.get("excerpt"),
            "source_id": item.get("source_id"),
            "confidence": item.get("confidence"),
        }
        for item in evidence_cards
        if "risk.regulatory_legal" in (item.get("question_ids") or []) or item.get("evidence_kind") == "risk_disclosure"
    ]
    for section in section_map:
        if any(str(name).casefold() == "risk_factors" for name in section.get("sections") or []):
            disclosures.append(
                {
                    "evidence_id": None,
                    "question_ids": ["risk.regulatory_legal", "financial.accounting_red_flags"],
                    "risk_text": "Risk factors section available for deeper extraction.",
                    "source_id": section.get("source_id"),
                    "confidence": "medium",
                }
            )
    return disclosures


def _unknowns(gap_requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "unknown_id": gap.get("gap_id"),
            "question_id": gap.get("question_id"),
            "unknown": gap.get("description"),
            "route": gap.get("route"),
            "priority": gap.get("priority"),
            "owner_agent": gap.get("owner_agent"),
        }
        for gap in gap_requests
    ]


def _contradiction_matrix(
    state: ResearchState,
    evidence_cards: list[dict[str, Any]],
    gap_requests: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pack = state.get("financial_report_pack") or {}
    annual_rows = sorted(pack.get("annual_facts") or [], key=lambda row: row.get("year") or 0)
    quarterly_rows = sorted(pack.get("quarterly_facts") or [], key=lambda row: str(row.get("period_end") or row.get("quarter") or ""))
    matrix = []
    if len(annual_rows) >= 2:
        prior = annual_rows[-2]
        latest = annual_rows[-1]
        revenue_growth = _growth(latest.get("revenue"), prior.get("revenue"))
        op_growth = _growth(latest.get("operating_income"), prior.get("operating_income"))
        fcf_growth = _growth(latest.get("free_cash_flow"), prior.get("free_cash_flow"))
        if revenue_growth is not None and revenue_growth > 0 and op_growth is not None and op_growth < 0:
            matrix.append(
                _contradiction(
                    "financial.margin_conversion",
                    "revenue_growth_without_operating_profit_growth",
                    "Revenue increased while operating income declined.",
                    {"revenue_growth": revenue_growth, "operating_income_growth": op_growth},
                    "high",
                )
            )
        if revenue_growth is not None and revenue_growth > 0 and fcf_growth is not None and fcf_growth < 0:
            matrix.append(
                _contradiction(
                    "financial.cash_conversion",
                    "revenue_growth_without_fcf_growth",
                    "Revenue increased while free cash flow declined.",
                    {"revenue_growth": revenue_growth, "fcf_growth": fcf_growth},
                    "high",
                )
            )
        restricted = latest.get("restricted_cash")
        cash = latest.get("cash")
        if isinstance(restricted, (int, float)) and isinstance(cash, (int, float)) and cash:
            ratio = restricted / cash
            if ratio > 0.25:
                matrix.append(
                    _contradiction(
                        "financial.balance_sheet",
                        "headline_cash_vs_restricted_cash",
                        "Headline cash strength must be adjusted for restricted cash.",
                        {"restricted_cash_to_cash": ratio},
                        "medium",
                    )
                )
    if quarterly_rows:
        latest_q = quarterly_rows[-1]
        below_items = _below_operating_gap(latest_q)
        if below_items:
            matrix.append(
                _contradiction(
                    "financial.accounting_red_flags",
                    "operating_profit_vs_net_income_divergence",
                    "Operating performance and net income may diverge because below-operating items moved against reported profit.",
                    below_items,
                    "medium",
                )
            )
    for gap in gap_requests:
        if gap.get("question_id") == "pdd.temu_segment_opacity":
            matrix.append(
                _contradiction(
                    "pdd.temu_segment_opacity",
                    "consolidated_margin_vs_temu_standalone_gap",
                    "Consolidated margins cannot prove Temu standalone unit economics.",
                    {"gap_id": gap.get("gap_id"), "missing_metrics": gap.get("required_metrics") or []},
                    "high",
                )
            )
            break
    if not matrix:
        matrix.append(
            _contradiction(
                "workflow",
                "no_material_contradiction_detected_by_v1",
                "No material contradiction was detected by the deterministic v1 rules; this is not proof no contradiction exists.",
                {},
                "low",
            )
        )
    return matrix


def _question_coverage(
    question_pack: dict[str, Any],
    evidence_cards: list[dict[str, Any]],
    gap_requests: list[dict[str, Any]],
    contradiction_matrix: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence_counts = Counter()
    kind_counts: dict[str, Counter[str]] = defaultdict(Counter)
    gap_counts = Counter(gap.get("question_id") for gap in gap_requests)
    contradiction_counts = Counter(row.get("question_id") for row in contradiction_matrix)
    for item in evidence_cards:
        for question_id in item.get("question_ids") or []:
            evidence_counts[question_id] += 1
            kind_counts[question_id][str(item.get("evidence_kind") or "unknown")] += 1
    rows = []
    for question in question_pack.get("questions") or []:
        qid = question.get("question_id")
        rows.append(
            {
                "question_id": qid,
                "pillar": question.get("pillar"),
                "theme": question.get("theme"),
                "priority": question.get("priority"),
                "evidence_count": evidence_counts[qid],
                "evidence_kind_counts": dict(sorted(kind_counts[qid].items())),
                "gap_count": gap_counts[qid],
                "contradiction_count": contradiction_counts[qid],
                "coverage_status": _coverage_status(evidence_counts[qid], gap_counts[qid], contradiction_counts[qid]),
            }
        )
    return rows


def _source_plan_gap_requests(
    source_map: dict[str, Any],
    question_pack: dict[str, Any],
    evidence_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    available_types = {row.get("source_type") for row in source_map.get("source_inventory") or []}
    questions_by_id = {question.get("question_id"): question for question in question_pack.get("questions") or []}
    gaps = []
    for plan in evidence_plan.get("plans") or []:
        question = questions_by_id.get(plan.get("question_id")) or {}
        if question.get("priority") != "P0":
            continue
        preferred = [source_type for source_type in plan.get("preferred_source_types") or [] if source_type]
        if preferred and not any(source_type in available_types for source_type in preferred):
            gaps.append(
                make_gap_request(
                    gap_id=f"source_gap_{plan.get('question_id')}",
                    question_id=str(plan.get("question_id")),
                    gap_type="missing_preferred_source_type",
                    description=f"No available source type overlaps preferred sources: {preferred}",
                    priority="P0",
                    route="source_map",
                    owner_agent="source_collection",
                    required_source_types=preferred,
                    depends_on_artifact="source_map",
                )
            )
    return gaps


def _coverage_status(evidence_count: int, gap_count: int, contradiction_count: int) -> str:
    if evidence_count <= 0:
        return "missing"
    if gap_count or contradiction_count:
        return "partial_with_gaps_or_contradictions"
    return "evidence_available"


def _contradiction(question_id: str, contradiction_type: str, summary: str, data: dict[str, Any], severity: str) -> dict[str, Any]:
    return {
        "contradiction_id": stable_id("CONTRA", [question_id, contradiction_type, data]),
        "question_id": question_id,
        "contradiction_type": contradiction_type,
        "summary": summary,
        "supporting_data": data,
        "severity": severity,
        "status": "requires_workpaper_attention",
    }


def _growth(latest: Any, prior: Any) -> float | None:
    if not isinstance(latest, (int, float)) or not isinstance(prior, (int, float)) or not prior:
        return None
    return (latest - prior) / abs(prior)


def _below_operating_gap(latest_q: dict[str, Any]) -> dict[str, Any]:
    # The current quarterly row may not carry every below-operating detail. Keep
    # this deterministic and conservative.
    op = latest_q.get("operating_income")
    net = latest_q.get("net_income")
    if not isinstance(op, (int, float)) or not isinstance(net, (int, float)):
        return {}
    gap = net - op
    if abs(gap) < abs(op) * 0.2:
        return {}
    return {"operating_income": op, "net_income": net, "net_minus_operating_income": gap}


def _dedupe_source_refs(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    deduped = []
    for ref in refs:
        source_id = str(ref.get("source_id") or "")
        if not source_id or source_id in seen:
            continue
        seen.add(source_id)
        deduped.append(ref)
    return deduped


def _dedupe_gap_requests(gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    deduped = []
    for gap in gaps:
        gap_id = str(gap.get("gap_id") or stable_id("gap", gap))
        if gap_id in seen:
            continue
        seen.add(gap_id)
        deduped.append({**gap, "gap_id": gap_id})
    return deduped
