from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from html import unescape
from pathlib import Path
from typing import Any

from stock_research.research_workflow.filing_deep_read import build_filing_deep_read_pack
from stock_research.research_workflow.gap_router import build_research_backlog
from stock_research.research_workflow.people_adapter import build_people_workflow_evidence
from stock_research.research_workflow.valuation_adapter import build_valuation_workflow_evidence
from stock_research.state import ResearchState, utc_now_iso


WORKFLOW_SCHEMA_VERSION = "decision_question_led_workflow_v1"
PROTOTYPE_VERSION = "v1.0_to_v1.25"


QUESTION_TEMPLATES: list[dict[str, Any]] = [
    {
        "question_id": "financial.growth",
        "pillar": "right_business",
        "theme": "financial_reality",
        "priority": "P0",
        "question": "Is the company growing, and is the recent trend improving or deteriorating?",
        "why_it_matters": "Growth is useful only if it is durable and economically valuable.",
        "expected_evidence_types": ["revenue", "quarterly_trend", "revenue_components"],
    },
    {
        "question_id": "financial.revenue_sources",
        "pillar": "right_business",
        "theme": "financial_reality",
        "priority": "P0",
        "question": "Where does revenue growth come from by business component?",
        "why_it_matters": "Revenue mix can reveal whether the business is changing or becoming more capital intensive.",
        "expected_evidence_types": ["transaction_services", "online_marketing", "segment_or_component_revenue"],
    },
    {
        "question_id": "financial.margin_conversion",
        "pillar": "right_business",
        "theme": "financial_reality",
        "priority": "P0",
        "question": "Does revenue growth convert into gross profit and operating profit?",
        "why_it_matters": "Operating leverage is one of the cleanest signs of business quality.",
        "expected_evidence_types": ["gross_profit", "operating_income", "expense_bridge"],
    },
    {
        "question_id": "financial.cash_conversion",
        "pillar": "right_business",
        "theme": "financial_reality",
        "priority": "P0",
        "question": "Does reported profit convert into operating cash flow and free cash flow?",
        "why_it_matters": "A value investor needs cash earnings, not only accounting earnings.",
        "expected_evidence_types": ["net_income", "operating_cash_flow", "capex", "working_capital_bridge"],
    },
    {
        "question_id": "financial.balance_sheet",
        "pillar": "right_risk",
        "theme": "financial_reality",
        "priority": "P0",
        "question": "Is the balance sheet safe, and how much cash is truly available?",
        "why_it_matters": "Cash, restricted cash, investments, debt, VIE restrictions, and transfer limits affect survival and owner value.",
        "expected_evidence_types": ["cash", "restricted_cash", "short_term_investments", "debt", "liabilities"],
    },
    {
        "question_id": "financial.dilution_sbc",
        "pillar": "right_people",
        "theme": "management_governance_capital_allocation",
        "priority": "P0",
        "question": "Are shareholders being diluted through SBC, share count growth, or weak capital return discipline?",
        "why_it_matters": "Per-share value can deteriorate even when company-level earnings grow.",
        "expected_evidence_types": ["sbc", "diluted_shares", "buybacks", "dividends", "equity_plans"],
    },
    {
        "question_id": "financial.accounting_red_flags",
        "pillar": "right_risk",
        "theme": "financial_reality",
        "priority": "P0",
        "question": "Are there accounting, auditor, restatement, or disclosure red flags?",
        "why_it_matters": "Accounting reliability is a hard gate before deeper valuation work.",
        "expected_evidence_types": ["auditor", "material_weakness", "restatement", "related_party", "material_events"],
    },
    {
        "question_id": "business.revenue_mechanism",
        "pillar": "right_business",
        "theme": "business_model_unit_economics",
        "priority": "P0",
        "question": "How does the business actually make money?",
        "why_it_matters": "The revenue mechanism must be understandable before judging moat or growth.",
        "expected_evidence_types": ["business_description", "revenue_streams", "merchant_or_customer_flows"],
    },
    {
        "question_id": "business.unit_economics",
        "pillar": "right_business",
        "theme": "business_model_unit_economics",
        "priority": "P0",
        "question": "What evidence exists for unit economics, take rate, fulfillment burden, and customer acquisition cost?",
        "why_it_matters": "Good aggregate margins can hide weak unit economics in a fast-changing business.",
        "expected_evidence_types": ["take_rate_proxy", "cost_structure", "marketing_intensity", "fulfillment_or_service_cost"],
    },
    {
        "question_id": "business.competitive_position",
        "pillar": "right_business",
        "theme": "business_model_unit_economics",
        "priority": "P1",
        "question": "What evidence supports or contradicts the competitive position?",
        "why_it_matters": "Moat should be earned from evidence, not asserted from scale language.",
        "expected_evidence_types": ["official_competition_language", "competitor_filings", "customer_or_merchant_evidence"],
    },
    {
        "question_id": "business.reinvestment_need",
        "pillar": "right_business",
        "theme": "business_model_unit_economics",
        "priority": "P1",
        "question": "How much reinvestment is required to grow?",
        "why_it_matters": "A growing business is more valuable when growth consumes little incremental capital.",
        "expected_evidence_types": ["capex", "working_capital", "sales_marketing", "rd", "merchant_support"],
    },
    {
        "question_id": "people.control_governance",
        "pillar": "right_people",
        "theme": "management_governance_capital_allocation",
        "priority": "P0",
        "question": "Who truly controls the company, and are minority-owner protections understandable?",
        "why_it_matters": "Power and economics can diverge through voting rights, VIEs, related parties, and board exemptions.",
        "expected_evidence_types": ["ownership", "voting_power", "vie", "board", "governance_documents"],
    },
    {
        "question_id": "people.incentives",
        "pillar": "right_people",
        "theme": "management_governance_capital_allocation",
        "priority": "P0",
        "question": "Do incentives reward per-share value, ROIC, cash generation, and long-term stewardship?",
        "why_it_matters": "Management usually does what the compensation and control structure rewards.",
        "expected_evidence_types": ["compensation", "sbc", "ownership", "clawback", "hedging", "pay_metrics"],
    },
    {
        "question_id": "people.capital_allocation",
        "pillar": "right_people",
        "theme": "management_governance_capital_allocation",
        "priority": "P0",
        "question": "Has capital allocation increased per-share owner value?",
        "why_it_matters": "The right people show up most clearly in reinvestment, buybacks, dividends, M&A, and dilution.",
        "expected_evidence_types": ["owner_earnings", "roic", "buybacks", "dividends", "m_and_a", "cash_retention"],
    },
    {
        "question_id": "people.candor",
        "pillar": "right_people",
        "theme": "management_governance_capital_allocation",
        "priority": "P1",
        "question": "Does management explain bad news directly, keep a stable scoreboard, and avoid evasive KPI shifts?",
        "why_it_matters": "Candor is tested by bad news, not by polished prepared remarks.",
        "expected_evidence_types": ["earnings_call_qna", "shareholder_letters", "promise_vs_outcome", "kpi_changes"],
    },
    {
        "question_id": "risk.regulatory_legal",
        "pillar": "right_risk",
        "theme": "risk_fragility",
        "priority": "P0",
        "question": "What legal, regulatory, and jurisdictional risks could impair the business model?",
        "why_it_matters": "A great business can still be a bad investment if the risk is unbounded or opaque.",
        "expected_evidence_types": ["risk_factors", "regulatory_filings", "court_records", "material_events"],
    },
    {
        "question_id": "price.owner_return",
        "pillar": "right_price",
        "theme": "valuation_assumptions",
        "priority": "P0",
        "question": "What owner-earnings yield and reinvestment-adjusted return does the current price imply?",
        "why_it_matters": "Right price should consume financial evidence but not be mixed into the Financial Evidence Agent.",
        "expected_evidence_types": ["owner_earnings", "enterprise_value", "market_cap", "fx", "roic", "growth_reinvestment"],
    },
    {
        "question_id": "price.expectations",
        "pillar": "right_price",
        "theme": "valuation_assumptions",
        "priority": "P1",
        "question": "What future growth and return assumptions are needed to justify the price?",
        "why_it_matters": "A high-quality company can still be unattractive if expectations are too high.",
        "expected_evidence_types": ["growth_scenarios", "margin_scenarios", "reinvestment_rate", "risk_adjustment"],
    },
]


def build_research_workflow_artifacts(state: ResearchState) -> dict[str, Any]:
    source_map = build_source_map(state)
    question_pack = build_decision_question_pack(state, source_map)
    evidence_plan = build_evidence_plan(source_map, question_pack)
    filing_deep_read_pack = build_filing_deep_read_pack(state, source_map, question_pack, evidence_plan)
    evidence_registry = build_evidence_registry(state, source_map, question_pack, filing_deep_read_pack)
    question_evidence_completion_pack = build_question_evidence_completion_pack(
        state=state,
        source_map=source_map,
        decision_question_pack=question_pack,
        evidence_plan=evidence_plan,
        filing_deep_read_pack=filing_deep_read_pack,
        evidence_registry=evidence_registry,
    )
    evidence_registry = build_augmented_evidence_registry(evidence_registry, question_evidence_completion_pack)
    theme_workpaper_pack = build_theme_workpaper_pack(state, question_pack, evidence_registry, filing_deep_read_pack)
    qa_gap_triage = build_qa_gap_triage(
        source_map,
        question_pack,
        evidence_registry,
        theme_workpaper_pack,
        filing_deep_read_pack,
        state.get("feedback_loop_pack") or {},
    )
    question_dossier_pack = build_question_dossier_pack(
        state=state,
        source_map=source_map,
        decision_question_pack=question_pack,
        evidence_plan=evidence_plan,
        filing_deep_read_pack=filing_deep_read_pack,
        evidence_registry=evidence_registry,
        question_evidence_completion_pack=question_evidence_completion_pack,
        theme_workpaper_pack=theme_workpaper_pack,
        qa_gap_triage=qa_gap_triage,
    )
    pillar_judgment_stub = build_pillar_judgment_stub(theme_workpaper_pack, qa_gap_triage)
    source_map = _english_safe_artifact(source_map)
    question_pack = _english_safe_artifact(question_pack)
    evidence_plan = _english_safe_artifact(evidence_plan)
    filing_deep_read_pack = _english_safe_artifact(filing_deep_read_pack)
    evidence_registry = _english_safe_artifact(evidence_registry)
    question_evidence_completion_pack = _english_safe_artifact(question_evidence_completion_pack)
    theme_workpaper_pack = _english_safe_artifact(theme_workpaper_pack)
    question_dossier_pack = _english_safe_artifact(question_dossier_pack)
    qa_gap_triage = _english_safe_artifact(qa_gap_triage)
    pillar_judgment_stub = _english_safe_artifact(pillar_judgment_stub)
    evidence_appendix = build_theme_workpaper_evidence_appendix(question_dossier_pack)
    report = build_research_workflow_report(
        source_map=source_map,
        decision_question_pack=question_pack,
        evidence_plan=evidence_plan,
        filing_deep_read_pack=filing_deep_read_pack,
        evidence_registry=evidence_registry,
        question_evidence_completion_pack=question_evidence_completion_pack,
        theme_workpaper_pack=theme_workpaper_pack,
        question_dossier_pack=question_dossier_pack,
        qa_gap_triage=qa_gap_triage,
        pillar_judgment_stub=pillar_judgment_stub,
    )
    return {
        "source_map": source_map,
        "decision_question_pack": question_pack,
        "evidence_plan": evidence_plan,
        "filing_deep_read_pack": filing_deep_read_pack,
        "evidence_registry": evidence_registry,
        "question_evidence_completion_pack": question_evidence_completion_pack,
        "theme_workpaper_pack": theme_workpaper_pack,
        "question_dossier_pack": question_dossier_pack,
        "theme_workpaper_evidence_appendix": evidence_appendix,
        "qa_gap_triage": qa_gap_triage,
        "pillar_judgment_stub": pillar_judgment_stub,
        "theme_workpaper_report": report,
    }


def build_source_map(state: ResearchState) -> dict[str, Any]:
    company = state.get("canonical_company") or {}
    company_context = {
        "raw_input": state.get("company_query"),
        "company_id": company.get("company_id") or state.get("company_query"),
        "legal_name": company.get("legal_name") or state.get("company_query"),
        "tickers": company.get("tickers", []),
        "market": state.get("market"),
        "listing_type": company.get("listing_type"),
        "sec_cik": company.get("sec_cik_padded") or company.get("sec_cik"),
        "official_ir_url": company.get("investor_relations_url"),
        "brands": company.get("brands", []),
        "business_aliases": company.get("aliases", []),
        "source_languages": company.get("source_languages", []),
    }
    inventory: list[dict[str, Any]] = []
    for source in state.get("source_candidates", []):
        inventory.append(_source_row_from_candidate(source, company_context))
    for document in state.get("documents", []):
        inventory.append(_source_row_from_document(document, company_context))

    seen = set()
    deduped = []
    for row in inventory:
        source_id = row["source_id"]
        if source_id in seen:
            continue
        seen.add(source_id)
        deduped.append(row)

    tier_counts = Counter(str(row.get("source_tier", "unknown")) for row in deduped)
    status_counts = Counter(str(row.get("collection_status", "unknown")) for row in deduped)
    type_counts = Counter(str(row.get("source_type", "unknown")) for row in deduped)
    official_rows = [row for row in deduped if row.get("source_tier") == 1]
    missing = _missing_source_log(company_context, deduped, state)
    return {
        "schema_version": "source_map_v1",
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "prototype_version": "v1.0",
        "generated_at": utc_now_iso(),
        "company_context": company_context,
        "source_inventory": deduped,
        "coverage_summary": {
            "source_count": len(deduped),
            "tier1_source_count": len(official_rows),
            "downloaded_or_cached_count": sum(
                1 for row in deduped if row.get("collection_status") in {"downloaded", "live_indexed", "live_fetched", "cached"}
            ),
            "parsed_count": sum(1 for row in deduped if row.get("parse_status") in {"parsed", "metadata_only"}),
            "missing_source_count": len(missing),
            "source_type_counts": dict(sorted(type_counts.items())),
            "collection_status_counts": dict(sorted(status_counts.items())),
        },
        "source_tier_mix": dict(sorted(tier_counts.items())),
        "missing_source_log": missing,
        "acquisition_log": _acquisition_log(state),
        "rights_constraints": _rights_constraints(deduped),
        "quality_flags": _source_quality_flags(deduped, missing),
    }


def build_decision_question_pack(state: ResearchState, source_map: dict[str, Any]) -> dict[str, Any]:
    company_id = (source_map.get("company_context") or {}).get("company_id")
    company_specific = _company_specific_questions(company_id)
    questions = [dict(template) for template in QUESTION_TEMPLATES]
    questions.extend(company_specific)
    theme_counts = Counter(question["theme"] for question in questions)
    pillar_counts = Counter(question["pillar"] for question in questions)
    return {
        "schema_version": "decision_question_pack_v1",
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "prototype_version": "v1.1",
        "generated_at": utc_now_iso(),
        "company_id": company_id,
        "source_map_path": state.get("source_map_path"),
        "questions": questions,
        "question_coverage_summary": {
            "question_count": len(questions),
            "p0_question_count": sum(1 for question in questions if question.get("priority") == "P0"),
            "theme_counts": dict(sorted(theme_counts.items())),
            "pillar_counts": dict(sorted(pillar_counts.items())),
        },
        "company_specific_questions": company_specific,
        "open_question_log": [
            {
                "status": "expected_in_mvp",
                "question": "Which questions remain unanswered after the first evidence registry pass?",
                "next_step": "qa_gap_triage",
            }
        ],
    }


def build_evidence_plan(source_map: dict[str, Any], question_pack: dict[str, Any]) -> dict[str, Any]:
    source_types = {row.get("source_type") for row in source_map.get("source_inventory", [])}
    plans = []
    for question in question_pack.get("questions", []):
        theme = question.get("theme")
        plan = {
            "question_id": question["question_id"],
            "preferred_source_tiers": [1],
            "preferred_source_types": _preferred_source_types(theme),
            "required_sections": _required_sections(question["question_id"], theme),
            "needed_evidence": question.get("expected_evidence_types", []),
            "support_tests": _support_tests(question["question_id"], theme),
            "contradiction_tests": _contradiction_tests(question["question_id"], theme),
            "gap_conditions": _gap_conditions(question["question_id"], theme),
            "available_source_type_overlap": sorted(
                source_type for source_type in _preferred_source_types(theme) if source_type in source_types
            ),
        }
        plans.append(plan)
    p0_without_overlap = [
        plan["question_id"]
        for plan in plans
        if _priority_for(question_pack, plan["question_id"]) == "P0" and not plan["available_source_type_overlap"]
    ]
    return {
        "schema_version": "evidence_plan_v1",
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "prototype_version": "v1.1",
        "generated_at": utc_now_iso(),
        "plans": plans,
        "plan_coverage_summary": {
            "plan_count": len(plans),
            "p0_plan_count": sum(1 for plan in plans if _priority_for(question_pack, plan["question_id"]) == "P0"),
            "p0_without_preferred_source_overlap": p0_without_overlap,
        },
        "source_gap_requests": [
            {
                "question_id": question_id,
                "request": "Add or parse preferred sources for this P0 question.",
                "route": "source_map",
            }
            for question_id in p0_without_overlap
        ],
    }


def build_evidence_registry(
    state: ResearchState,
    source_map: dict[str, Any],
    question_pack: dict[str, Any],
    filing_deep_read_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_aliases = _source_aliases(source_map)
    items: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    registry_gap_requests: list[dict[str, Any]] = []
    adapter_summaries: dict[str, Any] = {}
    _add_source_inventory_evidence(items, source_map)
    if filing_deep_read_pack:
        _add_deep_read_evidence(items, filing_deep_read_pack)
    else:
        _add_financial_fact_evidence(items, state, source_aliases)
        _add_layer1_diagnostic_evidence(items, state)
    _add_evidence_communication_items(items, state)
    if not filing_deep_read_pack:
        _add_business_model_items(items, state)
    for bundle in [build_people_workflow_evidence(state), build_valuation_workflow_evidence(state)]:
        _add_adapter_bundle_evidence(items, bundle)
        registry_gap_requests.extend(bundle.get("gap_requests") or [])
        adapter_summaries[str(bundle.get("source_artifact") or bundle.get("schema_version") or "adapter")] = bundle.get("summary") or {}
    unknowns.extend(_registry_unknowns(state, source_map, question_pack))
    if filing_deep_read_pack:
        unknowns.extend(
            {
                "type": "deep_read_gap",
                "question_id": gap.get("question_id"),
                "gap_id": gap.get("gap_id"),
                "unknown": gap.get("description"),
                "route": gap.get("route"),
            }
            for gap in filing_deep_read_pack.get("gap_requests", [])
        )
    unknowns.extend(
        {
            "type": "registry_adapter_gap",
            "question_id": gap.get("question_id"),
            "gap_id": gap.get("gap_id"),
            "unknown": gap.get("description"),
            "route": gap.get("route"),
        }
        for gap in registry_gap_requests
    )

    question_counts: dict[str, int] = defaultdict(int)
    kind_counts = Counter()
    source_tier_counts = Counter()
    for item in items:
        kind_counts[item.get("evidence_kind", "unknown")] += 1
        source_tier_counts[str(item.get("source_tier", "unknown"))] += 1
        for question_id in item.get("question_ids", []):
            question_counts[question_id] += 1

    return {
        "schema_version": "evidence_registry_v1",
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "prototype_version": "v1.2",
        "generated_at": utc_now_iso(),
        "evidence_items": items,
        "registry_summary": {
            "evidence_item_count": len(items),
            "question_coverage_count": len(question_counts),
            "question_evidence_counts": dict(sorted(question_counts.items())),
            "evidence_kind_counts": dict(sorted(kind_counts.items())),
            "source_tier_counts": dict(sorted(source_tier_counts.items())),
            "fact_claim_separation_status": "separated_by_evidence_kind",
        },
        "unknowns": unknowns,
        "registry_gap_requests": registry_gap_requests,
        "source_artifacts": {
            "filing_deep_read_pack": bool(filing_deep_read_pack),
            "adapter_summaries": adapter_summaries,
        },
    }


def build_question_evidence_completion_pack(
    *,
    state: ResearchState,
    source_map: dict[str, Any],
    decision_question_pack: dict[str, Any],
    evidence_plan: dict[str, Any],
    filing_deep_read_pack: dict[str, Any],
    evidence_registry: dict[str, Any],
) -> dict[str, Any]:
    """Run a question-level coverage gate and targeted source re-read pass.

    This is the first step that makes the question workflow more than a renderer:
    broad extraction remains the default source of evidence, but material gaps,
    contradictions, and high-priority mechanism questions trigger a targeted scan
    of already-collected official source files.
    """

    items_by_question: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in evidence_registry.get("evidence_items") or []:
        for question_id in item.get("question_ids") or []:
            items_by_question[str(question_id)].append(item)

    plan_by_question = {
        str(plan.get("question_id")): plan
        for plan in evidence_plan.get("plans") or []
        if plan.get("question_id")
    }
    gaps_by_question = _gaps_by_question(
        filing_deep_read_pack.get("gap_requests") or [],
        evidence_registry.get("registry_gap_requests") or [],
        [],
    )
    contradictions_by_question = _contradictions_by_question(filing_deep_read_pack)

    gates = []
    tasks = []
    supplemental_items = []
    for question in decision_question_pack.get("questions") or []:
        question_id = str(question.get("question_id") or "")
        question_items = items_by_question.get(question_id, [])
        gate = _question_completion_gate(
            question=question,
            items=question_items,
            gaps=gaps_by_question.get(question_id, []),
            contradictions=contradictions_by_question.get(question_id, []),
        )
        gates.append(gate)
        if gate["status"] not in {"targeted_read_required", "targeted_read_recommended"}:
            continue
        for spec in _targeted_read_specs(question_id, question.get("theme")):
            task, new_items = _run_targeted_read_task(
                question_id=question_id,
                question=question,
                spec=spec,
                source_map=source_map,
                plan=plan_by_question.get(question_id, {}),
                ordinal=len(tasks) + 1,
            )
            tasks.append(task)
            supplemental_items.extend(new_items)

    for item in supplemental_items:
        item.setdefault("upstream_refs", []).append(
            {
                "upstream_artifact": "question_evidence_completion_pack",
                "completion_type": "targeted_source_read",
            }
        )

    question_ids_with_supplemental = {
        question_id
        for item in supplemental_items
        for question_id in item.get("question_ids", [])
    }
    return {
        "schema_version": "question_evidence_completion_pack_v1",
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "prototype_version": "v1.45",
        "generated_at": utc_now_iso(),
        "purpose": "Question coverage gate plus targeted source re-read against already-collected official files.",
        "source_policy": {
            "uses_network": False,
            "source_scope": "already_collected_local_sources",
            "note": "This pass does not replace the broad extractor; it only supplements questions whose evidence is incomplete, conflicted, or mechanism-sensitive.",
        },
        "coverage_gates": gates,
        "targeted_read_tasks": tasks,
        "supplemental_evidence_items": supplemental_items,
        "summary": {
            "question_count": len(decision_question_pack.get("questions") or []),
            "targeted_read_question_count": len({task.get("question_id") for task in tasks}),
            "targeted_read_task_count": len(tasks),
            "supplemental_evidence_count": len(supplemental_items),
            "questions_with_supplemental_evidence": len(question_ids_with_supplemental),
            "questions_requiring_targeted_read": sum(1 for gate in gates if gate["status"] == "targeted_read_required"),
            "questions_recommended_for_targeted_read": sum(1 for gate in gates if gate["status"] == "targeted_read_recommended"),
            "unresolved_after_targeted_read": sum(1 for task in tasks if task.get("status") != "evidence_found"),
        },
    }


def build_augmented_evidence_registry(
    evidence_registry: dict[str, Any],
    question_evidence_completion_pack: dict[str, Any],
) -> dict[str, Any]:
    supplemental = question_evidence_completion_pack.get("supplemental_evidence_items") or []
    if not supplemental:
        augmented = dict(evidence_registry)
        augmented["prototype_version"] = "v1.2+v1.45"
        augmented["registry_summary"] = {
            **(evidence_registry.get("registry_summary") or {}),
            "supplemental_evidence_count": 0,
            "question_evidence_completion_status": "coverage_gated_without_supplemental_reads",
        }
        augmented.setdefault("source_artifacts", {})["question_evidence_completion_pack"] = (
            question_evidence_completion_pack.get("summary") or {}
        )
        return augmented

    items = list(evidence_registry.get("evidence_items") or [])
    existing_ids = {str(item.get("evidence_id")) for item in items}
    for item in supplemental:
        evidence_id = str(item.get("evidence_id") or "")
        if evidence_id and evidence_id in existing_ids:
            continue
        items.append(item)
        if evidence_id:
            existing_ids.add(evidence_id)

    question_counts: dict[str, int] = defaultdict(int)
    kind_counts = Counter()
    source_tier_counts = Counter()
    for item in items:
        kind_counts[item.get("evidence_kind", "unknown")] += 1
        source_tier_counts[str(item.get("source_tier", "unknown"))] += 1
        for question_id in item.get("question_ids", []):
            question_counts[question_id] += 1

    augmented = dict(evidence_registry)
    augmented["prototype_version"] = "v1.2+v1.45"
    augmented["evidence_items"] = items
    augmented["registry_summary"] = {
        **(evidence_registry.get("registry_summary") or {}),
        "evidence_item_count": len(items),
        "question_coverage_count": len(question_counts),
        "question_evidence_counts": dict(sorted(question_counts.items())),
        "evidence_kind_counts": dict(sorted(kind_counts.items())),
        "source_tier_counts": dict(sorted(source_tier_counts.items())),
        "supplemental_evidence_count": len(supplemental),
        "question_evidence_completion_status": "augmented_with_targeted_source_reads",
    }
    augmented.setdefault("source_artifacts", {})["question_evidence_completion_pack"] = (
        question_evidence_completion_pack.get("summary") or {}
    )
    return augmented


def _question_completion_gate(
    *,
    question: dict[str, Any],
    items: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    contradictions: list[dict[str, Any]],
) -> dict[str, Any]:
    question_id = str(question.get("question_id") or "")
    kind_counts = Counter(str(item.get("evidence_kind") or "unknown") for item in items)
    source_tier_counts = Counter(str(item.get("source_tier") or "unknown") for item in items)
    fact_count = sum(kind_counts.get(kind, 0) for kind in ["audited_fact", "filed_fact", "footnote_fact", "fact", "interim_fact"])
    management_claim_count = kind_counts.get("management_claim", 0) + kind_counts.get("management_explanation", 0)
    inference_count = kind_counts.get("system_inference", 0) + kind_counts.get("inference", 0)
    conditions = []
    if not items:
        conditions.append("no_reusable_evidence")
    if source_tier_counts.get("1", 0) == 0:
        conditions.append("no_tier1_source")
    if fact_count == 0:
        conditions.append("no_filed_fact_anchor")
    if management_claim_count and not fact_count:
        conditions.append("only_management_claim_without_fact_anchor")
    if contradictions:
        conditions.append("material_tension_present")
    if gaps:
        conditions.append("open_gap_present")
    if question_id in _targeted_read_question_ids() and question.get("priority") == "P0":
        conditions.append("p0_mechanism_question_needs_targeted_source_check")

    if not conditions:
        status = "sufficient_after_broad_extraction"
    elif any(condition in conditions for condition in ["no_reusable_evidence", "no_tier1_source", "no_filed_fact_anchor", "only_management_claim_without_fact_anchor"]):
        status = "targeted_read_required"
    else:
        status = "targeted_read_recommended"
    return {
        "question_id": question_id,
        "priority": question.get("priority"),
        "theme": question.get("theme"),
        "status": status,
        "conditions": conditions,
        "broad_evidence_counts": {
            "total": len(items),
            "tier1": source_tier_counts.get("1", 0),
            "fact": fact_count,
            "management_claim_or_explanation": management_claim_count,
            "inference": inference_count,
            "gaps": len(gaps),
            "contradictions": len(contradictions),
        },
        "next_action": _completion_next_action(question_id, status, conditions),
    }


def _targeted_read_question_ids() -> set[str]:
    return set(_TARGETED_READ_SPECS)


_TARGETED_READ_SPECS: dict[str, list[dict[str, Any]]] = {
    "financial.growth": [
        {
            "task_type": "latest_revenue_driver_read",
            "source_types": ["20-F", "6-K"],
            "sections": ["md&a", "financial_results", "business"],
            "keywords": ["revenue", "transaction services", "online marketing", "Temu", "Pinduoduo", "growth"],
            "evidence_kind": "management_explanation",
        }
    ],
    "financial.revenue_sources": [
        {
            "task_type": "revenue_component_note_read",
            "source_types": ["20-F", "6-K"],
            "sections": ["financial_statements", "footnotes", "business"],
            "keywords": ["transaction services", "online marketing services", "third-party merchants", "revenue"],
            "evidence_kind": "footnote_fact",
        }
    ],
    "financial.margin_conversion": [
        {
            "task_type": "expense_mechanism_read",
            "source_types": ["20-F", "6-K"],
            "sections": ["md&a", "financial_results", "footnotes"],
            "keywords": ["cost of revenues", "sales and marketing", "fulfillment", "payment processing", "server", "bandwidth", "gross profit", "operating profit"],
            "evidence_kind": "management_explanation",
        }
    ],
    "financial.cash_conversion": [
        {
            "task_type": "cash_conversion_and_working_capital_read",
            "source_types": ["20-F", "6-K"],
            "sections": ["financial_statements", "footnotes", "md&a"],
            "keywords": ["net cash provided by operating activities", "restricted cash", "merchant deposits", "accounts payable", "working capital", "settlement"],
            "evidence_kind": "footnote_fact",
        }
    ],
    "financial.balance_sheet": [
        {
            "task_type": "cash_availability_and_restriction_read",
            "source_types": ["20-F"],
            "sections": ["footnotes", "risk_factors", "financial_statements"],
            "keywords": ["restricted cash", "short-term investments", "VIE", "PRC", "transfer", "merchant deposits", "cash and cash equivalents"],
            "evidence_kind": "footnote_fact",
        }
    ],
    "financial.dilution_sbc": [
        {
            "task_type": "sbc_and_share_count_read",
            "source_types": ["20-F", "6-K"],
            "sections": ["footnotes", "governance", "financial_statements"],
            "keywords": ["share-based compensation", "diluted", "ADS", "ordinary shares", "equity incentive", "repurchase", "dividend"],
            "evidence_kind": "footnote_fact",
        }
    ],
    "financial.accounting_red_flags": [
        {
            "task_type": "accounting_quality_note_read",
            "source_types": ["20-F", "6-K"],
            "sections": ["footnotes", "financial_statements", "risk_factors"],
            "keywords": ["independent registered public accounting firm", "internal control", "material weakness", "related party", "investment income", "other income", "tax"],
            "evidence_kind": "footnote_fact",
        }
    ],
    "business.unit_economics": [
        {
            "task_type": "unit_economics_source_gap_read",
            "source_types": ["20-F", "6-K"],
            "sections": ["business", "md&a", "financial_results"],
            "keywords": ["merchant", "marketing", "transaction services", "Temu", "supply chain", "fulfillment"],
            "evidence_kind": "management_explanation",
        }
    ],
    "pdd.temu_segment_opacity": [
        {
            "task_type": "temu_segment_disclosure_gap_read",
            "source_types": ["20-F", "6-K"],
            "sections": ["business", "md&a", "financial_statements"],
            "keywords": ["Temu", "segment", "CODM", "disaggregated", "geographic", "global"],
            "evidence_kind": "management_explanation",
        }
    ],
}


def _targeted_read_specs(question_id: str, theme: str | None) -> list[dict[str, Any]]:
    if question_id in _TARGETED_READ_SPECS:
        return _TARGETED_READ_SPECS[question_id]
    if str(theme or "").startswith("management") or question_id.startswith("people."):
        return [
            {
                "task_type": "governance_targeted_read",
                "source_types": ["20-F", "proxy", "annual_report"],
                "sections": ["governance", "footnotes"],
                "keywords": ["directors", "senior management", "beneficial ownership", "voting power", "share-based compensation", "related party"],
                "evidence_kind": "footnote_fact",
            }
        ]
    return []


def _completion_next_action(question_id: str, status: str, conditions: list[str]) -> str:
    if status == "sufficient_after_broad_extraction":
        return "Use broad extraction evidence; no targeted re-read was triggered."
    if "material_tension_present" in conditions:
        return "Read the original source around the tension before upgrading confidence."
    if "open_gap_present" in conditions:
        return "Run targeted source read for the open gap and preserve unresolved items in the dossier."
    if question_id.startswith("financial."):
        return "Read the relevant financial statement, MD&A, and footnote areas for this question."
    return "Run a targeted read of the preferred Tier-1 source sections."


def _run_targeted_read_task(
    *,
    question_id: str,
    question: dict[str, Any],
    spec: dict[str, Any],
    source_map: dict[str, Any],
    plan: dict[str, Any],
    ordinal: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sources = _candidate_sources_for_targeted_read(source_map, spec, plan)
    task_id = f"QEC-TASK-{ordinal:03d}"
    read_results = []
    supplemental = []
    for row in sources[:2]:
        snippets = _targeted_snippets_from_source(row, spec)
        read_results.append(
            {
                "source_id": row.get("source_id"),
                "source_type": row.get("source_type"),
                "period": row.get("period"),
                "local_path": row.get("local_path"),
                "matched_snippet_count": len(snippets),
                "matched_keywords": sorted({snippet.get("matched_keyword") for snippet in snippets if snippet.get("matched_keyword")}),
            }
        )
        for snippet in snippets[:3]:
            payload = {
                "question_id": question_id,
                "task_id": task_id,
                "task_type": spec.get("task_type"),
                "source_id": row.get("source_id"),
                "source_type": row.get("source_type"),
                "period": row.get("period"),
                "section_targets": spec.get("sections") or [],
                "matched_keyword": snippet.get("matched_keyword"),
                "completion_role": "supplemental_targeted_read",
            }
            supplemental.append(
                _evidence_item(
                    evidence_id=f"QEC-EV-{_stable_id(str(payload))}",
                    question_ids=[question_id],
                    source_id=str(row.get("source_id") or "question_evidence_completion_pack"),
                    source_tier=int(row.get("source_tier") or 1),
                    source_type="targeted_source_read",
                    locator=f"{row.get('local_path') or row.get('url') or row.get('source_id')} | {spec.get('task_type')} | keyword={snippet.get('matched_keyword')}",
                    evidence_kind=str(spec.get("evidence_kind") or "footnote_fact"),
                    excerpt=str(snippet.get("excerpt") or ""),
                    structured_fact=payload,
                    confidence="medium",
                )
            )
    task_status = "evidence_found" if supplemental else "no_matching_excerpt_found"
    return (
        {
            "task_id": task_id,
            "question_id": question_id,
            "question": question.get("question"),
            "task_type": spec.get("task_type"),
            "status": task_status,
            "source_types": spec.get("source_types") or [],
            "section_targets": spec.get("sections") or [],
            "keywords": spec.get("keywords") or [],
            "source_count_read": len(sources[:2]),
            "read_results": read_results,
            "supplemental_evidence_count": len(supplemental),
            "remaining_gap": None if supplemental else "No matching local excerpt found; this needs a stronger section parser or manual review.",
        },
        supplemental,
    )


def _candidate_sources_for_targeted_read(
    source_map: dict[str, Any],
    spec: dict[str, Any],
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    preferred_types = set(spec.get("source_types") or plan.get("preferred_source_types") or [])
    rows = []
    for row in source_map.get("source_inventory") or []:
        if row.get("source_tier") != 1:
            continue
        if row.get("collection_status") not in {"downloaded", "cached"}:
            continue
        if not row.get("local_path"):
            continue
        if preferred_types and row.get("source_type") not in preferred_types:
            continue
        if not Path(str(row.get("local_path"))).exists():
            continue
        rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("period") or ""),
            str(row.get("filing_date") or ""),
            str(row.get("source_id") or ""),
        ),
        reverse=True,
    )


def _targeted_snippets_from_source(row: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    path = Path(str(row.get("local_path") or ""))
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    text = _plain_text_from_raw_source(raw)
    lowered = text.casefold()
    snippets = []
    seen_windows: set[tuple[int, int]] = set()
    for keyword in spec.get("keywords") or []:
        needle = str(keyword or "").casefold()
        if not needle:
            continue
        start_at = 0
        while len(snippets) < 6:
            idx = lowered.find(needle, start_at)
            if idx < 0:
                break
            start, end = _readable_excerpt_window(text, idx, before=420, after=720)
            window_key = (start // 100, end // 100)
            start_at = idx + len(needle)
            if window_key in seen_windows:
                continue
            seen_windows.add(window_key)
            snippets.append(
                {
                    "matched_keyword": keyword,
                    "excerpt": _truncate(text[start:end], 900),
                    "char_start": start,
                    "char_end": end,
                }
            )
            break
    return snippets


def _readable_excerpt_window(text: str, idx: int, *, before: int, after: int) -> tuple[int, int]:
    rough_start = max(0, idx - before)
    rough_end = min(len(text), idx + after)
    prefix = text.rfind(".", rough_start, idx)
    prefix = max(prefix, text.rfind(";", rough_start, idx), text.rfind(":", rough_start, idx))
    suffix_candidates = [
        position
        for position in [
            text.find(".", idx, rough_end),
            text.find(";", idx, rough_end),
        ]
        if position >= 0
    ]
    start = prefix + 1 if prefix >= 0 and idx - prefix < before else rough_start
    end = min(suffix_candidates) + 1 if suffix_candidates else rough_end
    while start < idx and start < len(text) and text[start].isspace():
        start += 1
    return start, end


def _plain_text_from_raw_source(raw: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>", " ", raw)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_theme_workpaper_pack(
    state: ResearchState,
    question_pack: dict[str, Any],
    evidence_registry: dict[str, Any],
    filing_deep_read_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    answer_context = _answer_context(state)
    items_by_question: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in evidence_registry.get("evidence_items", []):
        for question_id in item.get("question_ids", []):
            items_by_question[question_id].append(item)

    workpapers = []
    for theme in [
        "financial_reality",
        "business_model_unit_economics",
        "management_governance_capital_allocation",
        "risk_fragility",
        "valuation_assumptions",
    ]:
        theme_questions = [question for question in question_pack.get("questions", []) if question.get("theme") == theme]
        answers = [
            _workpaper_answer(theme, question, items_by_question.get(question["question_id"], []), answer_context)
            for question in theme_questions
        ]
        workpapers.append(
            {
                "theme": theme,
                "questions_answered": [answer for answer in answers if answer["status"] != "no_evidence"],
                "questions_without_evidence": [answer for answer in answers if answer["status"] == "no_evidence"],
                "evidence_used": sorted(
                    {
                        evidence_id
                        for answer in answers
                        for evidence_id in answer.get("evidence_ids", [])
                    }
                ),
                "answers": answers,
                "mechanism_explanations": _mechanism_explanations(theme, answers),
                "contradiction_checks": _theme_contradiction_checks(theme, answers),
                "unknowns": _theme_unknowns(theme, answers, evidence_registry.get("unknowns", [])),
                "handoff_questions": _theme_handoff_questions(theme, answers),
                "preliminary_read": _theme_preliminary_read(theme, answers),
            }
        )

    return {
        "schema_version": "theme_workpaper_pack_v1",
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "prototype_version": "v1.3",
        "generated_at": utc_now_iso(),
        "theme": "multi_theme_mvp",
        "workpapers": workpapers,
        "questions_answered": [
            question_id
            for workpaper in workpapers
            for question_id in [answer["question_id"] for answer in workpaper["questions_answered"]]
        ],
        "evidence_used": sorted({item["evidence_id"] for item in evidence_registry.get("evidence_items", [])}),
        "answers": [answer for workpaper in workpapers for answer in workpaper["answers"]],
        "mechanism_explanations": [
            explanation for workpaper in workpapers for explanation in workpaper["mechanism_explanations"]
        ],
        "contradiction_checks": [
            check for workpaper in workpapers for check in workpaper["contradiction_checks"]
        ],
        "unknowns": [unknown for workpaper in workpapers for unknown in workpaper["unknowns"]],
        "handoff_questions": [
            question for workpaper in workpapers for question in workpaper["handoff_questions"]
        ],
        "source_artifacts": {
            "financial_report_pack_path": state.get("financial_report_pack_path"),
            "business_model_unit_economics_pack_path": state.get("business_model_unit_economics_pack_path"),
            "right_people_report_path": state.get("right_people_report_path"),
            "filing_deep_read_pack_path": state.get("filing_deep_read_pack_path"),
        },
        "deep_read_summary": (filing_deep_read_pack or {}).get("summary", {}),
    }


def build_question_dossier_pack(
    *,
    state: ResearchState,
    source_map: dict[str, Any],
    decision_question_pack: dict[str, Any],
    evidence_plan: dict[str, Any],
    filing_deep_read_pack: dict[str, Any],
    evidence_registry: dict[str, Any],
    question_evidence_completion_pack: dict[str, Any],
    theme_workpaper_pack: dict[str, Any],
    qa_gap_triage: dict[str, Any],
) -> dict[str, Any]:
    evidence_items = evidence_registry.get("evidence_items") or []
    items_by_question: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in evidence_items:
        for question_id in item.get("question_ids") or []:
            items_by_question[str(question_id)].append(item)

    answers_by_question = {
        str(answer.get("question_id")): answer
        for answer in theme_workpaper_pack.get("answers", [])
        if answer.get("question_id")
    }
    coverage_by_question = {
        str(row.get("question_id")): row
        for row in filing_deep_read_pack.get("question_coverage") or []
        if row.get("question_id")
    }
    plan_by_question = {
        str(plan.get("question_id")): plan
        for plan in evidence_plan.get("plans") or []
        if plan.get("question_id")
    }
    contradictions_by_question = _contradictions_by_question(filing_deep_read_pack)
    gaps_by_question = _gaps_by_question(
        filing_deep_read_pack.get("gap_requests") or [],
        evidence_registry.get("registry_gap_requests") or [],
        ((qa_gap_triage.get("research_backlog") or {}).get("backlog_items") or []),
    )
    numeric_refs_by_question = _numeric_refs_by_question(
        filing_deep_read_pack.get("numeric_fact_refs") or [],
        evidence_items,
    )
    management_explanations_by_question = _management_explanations_by_question(
        filing_deep_read_pack.get("management_explanations") or []
    )
    completion_gate_by_question = {
        str(gate.get("question_id")): gate
        for gate in question_evidence_completion_pack.get("coverage_gates") or []
        if gate.get("question_id")
    }
    completion_tasks_by_question: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in question_evidence_completion_pack.get("targeted_read_tasks") or []:
        completion_tasks_by_question[str(task.get("question_id") or "")].append(task)
    supplemental_by_question: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in question_evidence_completion_pack.get("supplemental_evidence_items") or []:
        for question_id in item.get("question_ids") or []:
            supplemental_by_question[str(question_id)].append(item)

    dossiers = []
    for question in decision_question_pack.get("questions") or []:
        question_id = str(question.get("question_id") or "")
        question_items = sorted(
            items_by_question.get(question_id, []),
            key=lambda item: (-_materiality_score(item), str(item.get("evidence_id") or "")),
        )
        answer = answers_by_question.get(question_id) or {}
        contradictions = sorted(
            contradictions_by_question.get(question_id, []),
            key=lambda item: (-_gap_or_tension_severity_score(item), str(item.get("contradiction_id") or "")),
        )
        gaps = sorted(
            gaps_by_question.get(question_id, []),
            key=lambda item: (-_gap_or_tension_severity_score(item), str(item.get("gap_id") or "")),
        )
        dossier = {
            "question_id": question_id,
            "pillar": question.get("pillar"),
            "theme": question.get("theme"),
            "priority": question.get("priority"),
            "question": question.get("question"),
            "why_it_matters": question.get("why_it_matters"),
            "answer": {
                "status": answer.get("status", "no_evidence"),
                "confidence": answer.get("confidence", "low"),
                "current_answer": answer.get("current_answer", ""),
                "key_points": answer.get("key_points") or [],
                "evidence_ids_from_workpaper": answer.get("evidence_ids") or [],
                "contradiction_checked": bool(answer.get("contradiction_checked")),
                "what_could_be_wrong": answer.get("what_could_be_wrong"),
                "next_step": answer.get("next_step"),
            },
            "evidence_plan": plan_by_question.get(question_id, {}),
            "evidence_coverage": _evidence_coverage(question_items, coverage_by_question.get(question_id, {})),
            "source_coverage": _source_coverage_for_items(question_items),
            "supporting_evidence": [_compact_evidence_row(item) for item in question_items],
            "materiality_ranking": [_compact_evidence_row(item, include_score=True) for item in question_items[:15]],
            "contradictions_and_tensions": contradictions,
            "numeric_facts": numeric_refs_by_question.get(question_id, [])[:80],
            "management_explanations": management_explanations_by_question.get(question_id, [])[:40],
            "financial_bridge_tables": _financial_bridge_tables_for_question(question_id, state),
            "question_completion": {
                "coverage_gate": completion_gate_by_question.get(question_id, {}),
                "targeted_read_tasks": completion_tasks_by_question.get(question_id, []),
                "supplemental_evidence": [
                    _compact_evidence_row(item, include_score=True)
                    for item in sorted(
                        supplemental_by_question.get(question_id, []),
                        key=lambda item: (-_materiality_score(item), str(item.get("evidence_id") or "")),
                    )
                ],
                "machine_contract": _question_completion_machine_contract(
                    question_id=question_id,
                    coverage=_evidence_coverage(question_items, coverage_by_question.get(question_id, {})),
                    gaps=gaps,
                    gate=completion_gate_by_question.get(question_id, {}),
                    tasks=completion_tasks_by_question.get(question_id, []),
                    supplemental=supplemental_by_question.get(question_id, []),
                ),
            },
            "gap_severity_ranking": gaps,
            "audit_notes": _question_audit_notes(question_items, contradictions, gaps),
        }
        dossiers.append(dossier)

    total_evidence_links = sum(len(dossier.get("supporting_evidence") or []) for dossier in dossiers)
    return {
        "schema_version": "question_dossier_pack_v1",
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "prototype_version": "v1.35",
        "generated_at": utc_now_iso(),
        "company_id": (source_map.get("company_context") or {}).get("company_id"),
        "source_artifacts": {
            "source_map": True,
            "decision_question_pack": True,
            "evidence_plan": True,
            "filing_deep_read_pack": True,
            "evidence_registry": True,
            "theme_workpaper_pack": True,
            "qa_gap_triage": True,
        },
        "dossiers": dossiers,
        "summary": {
            "question_count": len(dossiers),
            "questions_with_evidence": sum(1 for dossier in dossiers if dossier["evidence_coverage"]["total_evidence_items"] > 0),
            "questions_with_tensions": sum(1 for dossier in dossiers if dossier.get("contradictions_and_tensions")),
            "questions_with_open_gaps": sum(1 for dossier in dossiers if dossier.get("gap_severity_ranking")),
            "total_evidence_links": total_evidence_links,
            "questions_with_supplemental_evidence": (
                question_evidence_completion_pack.get("summary") or {}
            ).get("questions_with_supplemental_evidence", 0),
        },
    }


def build_theme_workpaper_evidence_appendix(question_dossier_pack: dict[str, Any]) -> str:
    summary = question_dossier_pack.get("summary") or {}
    lines = [
        "# Theme Workpaper Evidence Appendix",
        "",
        "This appendix lists the full question-level evidence trail used by the theme workpaper. The main report stays readable; this appendix is for audit.",
        "",
        "## Summary",
        "",
        f"- Questions: {summary.get('question_count', 0)}",
        f"- Questions with evidence: {summary.get('questions_with_evidence', 0)}",
        f"- Questions with contradictions / tensions: {summary.get('questions_with_tensions', 0)}",
        f"- Questions with open gaps: {summary.get('questions_with_open_gaps', 0)}",
        f"- Total question-evidence links: {summary.get('total_evidence_links', 0)}",
        "",
    ]
    for dossier in question_dossier_pack.get("dossiers") or []:
        coverage = dossier.get("evidence_coverage") or {}
        source_coverage = dossier.get("source_coverage") or {}
        lines.extend(
            [
                f"## {dossier.get('question_id')}",
                "",
                f"Question: {_report_md(dossier.get('question'))}",
                "",
                "Evidence base summary:",
                "",
                f"- Total evidence items: {coverage.get('total_evidence_items', 0)}",
                f"- Evidence kind mix: {_report_md(coverage.get('evidence_kind_counts', {}))}",
                f"- Source count: {source_coverage.get('source_count', 0)}",
                f"- Top source types: {_report_md(source_coverage.get('top_source_types', []))}",
                f"- Remaining evidence gaps after official-report review: {coverage.get('gap_count', 0)}",
                "",
            ]
        )
        if dossier.get("contradictions_and_tensions"):
            lines.extend(["Contradictions / tensions:", ""])
            for tension in dossier["contradictions_and_tensions"][:10]:
                lines.append(
                    f"- [{_report_md(tension.get('severity'))}] {_report_md(tension.get('summary'))} (`{_report_md(tension.get('contradiction_type'))}`)"
                )
            lines.append("")
        if dossier.get("gap_severity_ranking"):
            lines.extend(["Remaining official-disclosure / extraction gaps:", ""])
            completion_contract = ((dossier.get("question_completion") or {}).get("machine_contract") or {})
            lines.append(_remaining_gap_summary(dossier, completion_contract))
            lines.append("")
            for gap in dossier["gap_severity_ranking"][:10]:
                lines.append(
                    f"- [{_report_md(gap.get('priority'))}] {_report_md(gap.get('description'))} Route: `{_report_md(gap.get('route'))}`"
                )
            lines.append("")
        completion = dossier.get("question_completion") or {}
        gate = completion.get("coverage_gate") or {}
        contract = completion.get("machine_contract") or {}
        if gate:
            lines.extend(
                [
                    "Evidence completion attempt:",
                    "",
                    f"- Status: {_report_md(contract.get('completion_status'))}",
                    f"- Why triggered: {_report_md(contract.get('trigger_summary'))}",
                    f"- Targeted source reads completed: {len(completion.get('targeted_read_tasks') or [])}",
                    f"- Supplemental evidence found: {len(completion.get('supplemental_evidence') or [])}",
                    f"- Remaining gap status: `{_report_md(contract.get('remaining_gap_status'))}`",
                    f"- Remaining gap type: `{_report_md(contract.get('remaining_gap_type'))}`",
                    "",
                ]
            )
        if completion.get("supplemental_evidence"):
            lines.extend(
                [
                    "Targeted source evidence:",
                    "",
                    "| Evidence ID | Kind | Source | Confidence | Excerpt |",
                    "|---|---|---|---|---|",
                ]
            )
            for item in completion.get("supplemental_evidence") or []:
                lines.append(
                    "| `{evidence_id}` | {kind} | `{source}` | {confidence} | {excerpt} |".format(
                        evidence_id=_report_md(item.get("evidence_id")),
                        kind=_report_md(item.get("evidence_kind")),
                        source=_report_md(item.get("source_id")),
                        confidence=_report_md(item.get("confidence")),
                        excerpt=_report_md(_truncate(item.get("excerpt"), 220)),
                    )
                )
            lines.append("")
        lines.extend(
            [
                "Material evidence ranking:",
                "",
                "| Rank | Evidence ID | Kind | Source | Confidence | Materiality | Excerpt |",
                "|---:|---|---|---|---|---:|---|",
            ]
        )
        for rank, item in enumerate(dossier.get("materiality_ranking") or [], start=1):
            lines.append(
                "| {rank} | `{evidence_id}` | {kind} | `{source}` | {confidence} | {score} | {excerpt} |".format(
                    rank=rank,
                    evidence_id=_report_md(item.get("evidence_id")),
                    kind=_report_md(item.get("evidence_kind")),
                    source=_report_md(item.get("source_id")),
                    confidence=_report_md(item.get("confidence")),
                    score=item.get("materiality_score"),
                    excerpt=_report_md(_truncate(item.get("excerpt"), 220)),
                )
            )
        lines.append("")
        supporting = [
            item
            for item in dossier.get("supporting_evidence") or []
            if item.get("source_type") != "source_metadata"
        ]
        omitted_metadata_count = len(dossier.get("supporting_evidence") or []) - len(supporting)
        lines.extend(
            [
                "All non-metadata supporting evidence:",
                "",
                "| Evidence ID | Kind | Source Type | Source | Confidence | Excerpt |",
                "|---|---|---|---|---|---|",
            ]
        )
        for item in supporting:
            lines.append(
                "| `{evidence_id}` | {kind} | {source_type} | `{source}` | {confidence} | {excerpt} |".format(
                    evidence_id=_report_md(item.get("evidence_id")),
                    kind=_report_md(item.get("evidence_kind")),
                    source_type=_report_md(item.get("source_type")),
                    source=_report_md(item.get("source_id")),
                    confidence=_report_md(item.get("confidence")),
                    excerpt=_report_md(_truncate(item.get("excerpt"), 220)),
                )
            )
        if omitted_metadata_count:
            lines.append("")
            lines.append(f"Generic source-metadata evidence omitted from this table: {omitted_metadata_count}. It remains counted in `question_dossier_pack.json`.")
        lines.append("")
    return _ensure_english_report("\n".join(lines))


def _contradictions_by_question(filing_deep_read_pack: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for contradiction in filing_deep_read_pack.get("contradiction_matrix") or []:
        question_id = str(contradiction.get("question_id") or "")
        if question_id:
            grouped[question_id].append(contradiction)
    return grouped


def _gaps_by_question(*gap_groups: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen = set()
    for gaps in gap_groups:
        for gap in gaps or []:
            question_id = str(gap.get("question_id") or "workflow")
            gap_id = str(gap.get("gap_id") or _stable_id(str(gap)))
            description_key = _normalized_gap_description(gap.get("description"))
            key = (question_id, description_key or gap_id)
            if key in seen:
                continue
            seen.add(key)
            grouped[question_id].append({**gap, "gap_id": gap_id})
    return grouped


def _normalized_gap_description(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip().casefold()
    text = re.sub(r"`[^`]+`", "`field`", text)
    text = re.sub(r"\bfa-[a-z0-9-]+\b", "fa-id", text)
    text = re.sub(r"\b[a-f0-9]{8,}\b", "hash", text)
    return text[:180]


def _numeric_refs_by_question(
    numeric_fact_refs: list[dict[str, Any]],
    evidence_items: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    questions_by_evidence_id = {
        str(item.get("evidence_id")): [str(qid) for qid in item.get("question_ids") or []]
        for item in evidence_items
        if item.get("evidence_id")
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ref in numeric_fact_refs:
        for question_id in questions_by_evidence_id.get(str(ref.get("evidence_id")), []):
            grouped[question_id].append(ref)
    return grouped


def _management_explanations_by_question(explanations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for explanation in explanations:
        for question_id in explanation.get("question_ids") or []:
            grouped[str(question_id)].append(explanation)
    return grouped


def _evidence_coverage(items: list[dict[str, Any]], deep_coverage: dict[str, Any]) -> dict[str, Any]:
    kind_counts = Counter(str(item.get("evidence_kind") or "unknown") for item in items)
    source_type_counts = Counter(str(item.get("source_type") or "unknown") for item in items)
    confidence_counts = Counter(str(item.get("confidence") or "unknown") for item in items)
    tier_counts = Counter(str(item.get("source_tier") or "unknown") for item in items)
    return {
        "total_evidence_items": len(items),
        "evidence_kind_counts": dict(sorted(kind_counts.items())),
        "source_type_counts": dict(sorted(source_type_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "source_tier_counts": dict(sorted(tier_counts.items())),
        "filed_or_audited_fact_count": sum(kind_counts.get(kind, 0) for kind in ["audited_fact", "filed_fact", "footnote_fact", "fact"]),
        "management_claim_count": kind_counts.get("management_claim", 0),
        "management_explanation_count": kind_counts.get("management_explanation", 0),
        "system_inference_count": kind_counts.get("system_inference", 0) + kind_counts.get("inference", 0),
        "gap_count": int(deep_coverage.get("gap_count") or 0),
        "contradiction_count": int(deep_coverage.get("contradiction_count") or 0),
        "deep_read_coverage_status": deep_coverage.get("coverage_status"),
    }


def _source_coverage_for_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    source_ids = [str(item.get("source_id") or "unknown") for item in items]
    source_types = [str(item.get("source_type") or "unknown") for item in items]
    source_tiers = [str(item.get("source_tier") or "unknown") for item in items]
    return {
        "source_count": len(set(source_ids)),
        "source_id_counts": dict(Counter(source_ids).most_common(20)),
        "top_source_types": Counter(source_types).most_common(10),
        "source_tier_counts": dict(sorted(Counter(source_tiers).items())),
    }


def _question_completion_machine_contract(
    *,
    question_id: str,
    coverage: dict[str, Any],
    gaps: list[dict[str, Any]],
    gate: dict[str, Any],
    tasks: list[dict[str, Any]],
    supplemental: list[dict[str, Any]],
) -> dict[str, Any]:
    completion_status = _completion_status(gate, tasks, supplemental)
    remaining_gap_status = (
        "unresolved_after_official_report_review"
        if gaps or coverage.get("gap_count", 0)
        else "no_material_gap_logged_after_current_pass"
    )
    remaining_gap_type = _remaining_gap_type(question_id, gaps)
    return {
        "schema_version": "question_completion_machine_contract_v1",
        "completion_status": completion_status,
        "trigger_status": gate.get("status") or "not_gated",
        "trigger_conditions": gate.get("conditions") or [],
        "trigger_summary": _completion_trigger_summary(gate),
        "targeted_read_task_count": len(tasks),
        "supplemental_evidence_count": len(supplemental),
        "remaining_gap_status": remaining_gap_status,
        "remaining_gap_type": remaining_gap_type,
        "downstream_rule": "Treat supplemental targeted-read evidence as support for the current answer, not as proof that all gaps are closed.",
    }


def _completion_status(
    gate: dict[str, Any],
    tasks: list[dict[str, Any]],
    supplemental: list[dict[str, Any]],
) -> str:
    if tasks and supplemental:
        return "targeted_read_completed_with_supplemental_evidence"
    if tasks:
        return "targeted_read_completed_without_matching_evidence"
    if (gate.get("status") or "") == "sufficient_after_broad_extraction":
        return "broad_extraction_sufficient_no_targeted_read"
    return "not_completed_or_not_triggered"


def _completion_trigger_summary(gate: dict[str, Any]) -> str:
    conditions = set(gate.get("conditions") or [])
    if not conditions:
        return "Broad extraction was sufficient; no targeted source read was triggered."
    reasons = []
    if "p0_mechanism_question_needs_targeted_source_check" in conditions:
        reasons.append("this is a P0 mechanism question")
    if "open_gap_present" in conditions:
        reasons.append("official-report review still left evidence gaps")
    if "material_tension_present" in conditions:
        reasons.append("the evidence base contains a material tension")
    if "no_filed_fact_anchor" in conditions:
        reasons.append("the broad evidence lacked a filed fact anchor")
    if "only_management_claim_without_fact_anchor" in conditions:
        reasons.append("the broad evidence relied on management claims without a filed fact anchor")
    if "no_reusable_evidence" in conditions:
        reasons.append("no reusable evidence existed after broad extraction")
    if "no_tier1_source" in conditions:
        reasons.append("no Tier-1 source evidence was linked")
    return "; ".join(reasons) + "."


def _remaining_gap_type(question_id: str, gaps: list[dict[str, Any]]) -> str:
    if not gaps:
        return "none_logged"
    if question_id in {"financial.growth", "financial.revenue_sources", "business.unit_economics", "pdd.temu_segment_opacity"}:
        return "insufficient_official_disaggregation"
    if question_id.startswith("financial."):
        return "financial_disclosure_or_extraction_gap"
    if question_id.startswith("people."):
        return "governance_disclosure_or_extraction_gap"
    if question_id.startswith("risk."):
        return "risk_disclosure_or_external_evidence_gap"
    if question_id.startswith("price."):
        return "valuation_input_gap"
    return "official_disclosure_or_extraction_gap"


def _remaining_gap_summary(dossier: dict[str, Any], contract: dict[str, Any]) -> str:
    question_id = str(dossier.get("question_id") or "")
    gap_status = str(contract.get("remaining_gap_status") or "unknown")
    gap_type = str(contract.get("remaining_gap_type") or "official_disclosure_or_extraction_gap")
    if gap_status == "no_material_gap_logged_after_current_pass":
        return "No material remaining gap is logged after the current official-report review."
    if gap_type == "insufficient_official_disaggregation":
        return (
            "The current official reports support the broad answer, but they do not disclose enough detail to fully close the economic-quality question. "
            "The unresolved pieces include business-line split, geography, volume versus pricing/take-rate, merchant-fee mechanics, and cost/subsidy burden. "
            f"Downstream status: `{gap_status}`."
        )
    if gap_type == "financial_disclosure_or_extraction_gap":
        return (
            "The current official reports support parts of the financial answer, but some line-item bridge or footnote detail remains unresolved. "
            f"Downstream status: `{gap_status}`."
        )
    if gap_type == "governance_disclosure_or_extraction_gap":
        return (
            "The current official reports support parts of the governance answer, but control, incentive, or related-party evidence is still incomplete. "
            f"Downstream status: `{gap_status}`."
        )
    if gap_type == "risk_disclosure_or_external_evidence_gap":
        return (
            "The official-report risk evidence is not enough to fully close the risk question; external official records or later filings may be needed. "
            f"Downstream status: `{gap_status}`."
        )
    if question_id.startswith("price."):
        return (
            "The valuation answer still depends on unresolved or review-sensitive inputs, so downstream valuation agents should keep the confidence capped. "
            f"Downstream status: `{gap_status}`."
        )
    return (
        "The current official-report review leaves a remaining evidence gap. Downstream agents should keep this item open rather than treating supplemental evidence as gap closure. "
        f"Downstream status: `{gap_status}`."
    )


def _compact_evidence_row(item: dict[str, Any], *, include_score: bool = False) -> dict[str, Any]:
    row = {
        "evidence_id": item.get("evidence_id"),
        "question_ids": item.get("question_ids") or [],
        "source_id": item.get("source_id"),
        "source_type": item.get("source_type"),
        "source_tier": item.get("source_tier"),
        "locator": item.get("locator"),
        "evidence_kind": item.get("evidence_kind"),
        "reliability": item.get("reliability"),
        "confidence": item.get("confidence"),
        "requires_human_review": item.get("requires_human_review"),
        "excerpt": item.get("excerpt"),
        "upstream_refs": item.get("upstream_refs") or [],
    }
    if include_score:
        row["materiality_score"] = _materiality_score(item)
    return row


def _materiality_score(item: dict[str, Any]) -> int:
    kind = str(item.get("evidence_kind") or "")
    source_type = str(item.get("source_type") or "")
    score = {
        "audited_fact": 100,
        "filed_fact": 95,
        "footnote_fact": 90,
        "fact": 80,
        "interim_fact": 75,
        "risk_disclosure": 70,
        "system_inference": 58,
        "inference": 52,
        "management_explanation": 48,
        "management_claim": 35,
        "unknown": 25,
    }.get(kind, 40)
    if item.get("source_tier") == 1:
        score += 8
    if item.get("confidence") == "high":
        score += 8
    elif item.get("confidence") == "medium":
        score += 4
    if source_type in {"contradiction_matrix", "right_people_red_flag"}:
        score += 15
    if item.get("requires_human_review"):
        score += 4
    if item.get("upstream_refs"):
        score += 3
    return score


def _gap_or_tension_severity_score(item: dict[str, Any]) -> int:
    severity = str(item.get("severity") or "").casefold()
    priority = str(item.get("priority") or "").upper()
    if severity == "high" or priority == "P0":
        return 100
    if severity == "medium" or priority == "P1":
        return 70
    if severity == "low" or priority == "P2":
        return 40
    return 20


def _financial_bridge_tables_for_question(question_id: str, state: ResearchState) -> list[dict[str, Any]]:
    metrics = {
        str(metric.get("formula_id")): metric
        for metric in ((state.get("financial_report_pack") or {}).get("financial_metrics") or [])
        if metric.get("formula_id")
    }
    formula_map = {
        "financial.growth": ["latest_interim_trend_v1", "source_of_growth_attribution_v1"],
        "financial.revenue_sources": ["source_of_growth_attribution_v1"],
        "financial.margin_conversion": ["margin_profile_v1", "operating_profit_bridge_v1", "incremental_margin_v1"],
        "financial.cash_conversion": ["cash_conversion_ratio_v1", "capital_intensity_v1", "working_capital_quality_v1"],
        "financial.balance_sheet": ["balance_sheet_risk_v1", "working_capital_quality_v1"],
        "financial.dilution_sbc": ["share_based_compensation_burden_v1"],
        "financial.accounting_red_flags": ["below_operating_bridge_v1", "tax_non_gaap_accounting_quality_v1"],
        "business.reinvestment_need": ["capital_intensity_v1", "incremental_roic_proxy_v1"],
        "business.unit_economics": ["unlevered_roic_v1", "incremental_roic_proxy_v1", "working_capital_quality_v1"],
        "price.owner_return": ["owner_earnings_v1", "cash_conversion_ratio_v1", "capital_intensity_v1"],
        "price.expectations": ["unlevered_roic_v1", "incremental_roic_proxy_v1", "capital_intensity_v1"],
    }
    tables = []
    for formula_id in formula_map.get(question_id, []):
        metric = metrics.get(formula_id)
        if metric:
            tables.append(_bridge_table_from_metric(metric))
    return tables


def _bridge_table_from_metric(metric: dict[str, Any]) -> dict[str, Any]:
    latest_annual = _latest_metric_result(metric)
    latest_interim = metric.get("latest_interim_result") or {}
    bridge_rows = latest_interim.get("bridge_rows") or latest_annual.get("bridge_rows") or []
    return {
        "formula_id": metric.get("formula_id"),
        "status": metric.get("status"),
        "latest_annual": _compact_metric_result(latest_annual),
        "latest_interim": _compact_metric_result(latest_interim),
        "bridge_rows": [_compact_bridge_row(row) for row in bridge_rows[:12]],
    }


def _compact_metric_result(result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict) or not result:
        return {}
    preferred_keys = [
        "status",
        "year",
        "period",
        "period_end",
        "value",
        "revenue_growth",
        "operating_income_growth",
        "incremental_operating_margin",
        "free_cash_flow_margin",
        "free_cash_flow_to_operating_cash_flow",
        "capex_to_revenue",
        "cash_conversion_ratio",
        "working_capital_cash_tailwind_to_revenue",
        "restricted_cash_to_cash",
        "current_ratio",
        "liquid_assets_to_total_liabilities",
        "sbc_to_revenue",
        "sbc_to_operating_cash_flow",
        "diluted_shares_yoy",
        "maintenance_capex_proxy",
    ]
    compact = {key: result.get(key) for key in preferred_keys if key in result}
    if result.get("top_component"):
        compact["top_component"] = result.get("top_component")
    if result.get("warning_flags"):
        compact["warning_flags"] = result.get("warning_flags")
    return compact


def _compact_bridge_row(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    return {
        key: row.get(key)
        for key in [
            "metric",
            "label",
            "current",
            "prior",
            "delta",
            "effect_on_operating_income",
            "share_of_revenue",
            "yoy_growth",
            "revenue_growth_contribution",
            "comment",
        ]
        if key in row
    }


def _question_audit_notes(
    items: list[dict[str, Any]],
    contradictions: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
) -> list[str]:
    notes = []
    if not items:
        notes.append("No reusable evidence registered for this question.")
    if contradictions:
        notes.append("Contradictions or tensions require explicit analyst review before confidence is upgraded.")
    if gaps:
        notes.append("Open gaps remain in the research backlog.")
    if not any(item.get("evidence_kind") in {"audited_fact", "filed_fact", "fact"} for item in items):
        notes.append("No filed/audited fact anchors were found in the question evidence set.")
    return notes


def _truncate(value: Any, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _bridge_result_summary(result: dict[str, Any]) -> str:
    if not result:
        return "n/a"
    parts = []
    for key in [
        "status",
        "year",
        "period",
        "period_end",
        "value",
        "revenue_growth",
        "incremental_operating_margin",
        "free_cash_flow_margin",
        "capex_to_revenue",
        "cash_conversion_ratio",
        "restricted_cash_to_cash",
        "sbc_to_revenue",
    ]:
        if key in result and result.get(key) is not None:
            value = result.get(key)
            if isinstance(value, float):
                value = round(value, 4)
            parts.append(f"{key}={value}")
    if not parts and result.get("top_component"):
        parts.append(f"top_component={result.get('top_component')}")
    return "; ".join(parts[:5]) or "available"


def build_qa_gap_triage(
    source_map: dict[str, Any],
    question_pack: dict[str, Any],
    evidence_registry: dict[str, Any],
    theme_workpaper_pack: dict[str, Any],
    filing_deep_read_pack: dict[str, Any] | None = None,
    feedback_loop_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_aliases = _source_aliases(source_map)
    citation_checks = []
    for item in evidence_registry.get("evidence_items", []):
        source_id = str(item.get("source_id") or "")
        has_upstream_ref = bool(item.get("upstream_refs"))
        citation_pass = source_id in source_aliases or (item.get("source_tier") == 1 and has_upstream_ref)
        citation_checks.append(
            {
                "evidence_id": item.get("evidence_id"),
                "source_id": source_id,
                "status": "pass" if citation_pass else "source_not_in_source_map",
            }
        )
    unsupported_claims = [
        {
            "question_id": answer.get("question_id"),
            "claim": answer.get("current_answer"),
            "status": "unsupported_or_no_evidence",
        }
        for answer in theme_workpaper_pack.get("answers", [])
        if not answer.get("evidence_ids")
    ]
    missing_contradiction_checks = [
        {
            "question_id": answer.get("question_id"),
            "theme": answer.get("theme"),
            "reason": "High-confidence answers require explicit contradiction checks.",
        }
        for answer in theme_workpaper_pack.get("answers", [])
        if answer.get("confidence") == "high" and not answer.get("contradiction_checked")
    ]
    confidence_caps = [
        {
            "question_id": answer.get("question_id"),
            "cap": "medium",
            "reason": "Answer has evidence but no contradiction check.",
        }
        for answer in theme_workpaper_pack.get("answers", [])
        if answer.get("evidence_ids") and not answer.get("contradiction_checked")
    ]
    p0_questions = [question for question in question_pack.get("questions", []) if question.get("priority") == "P0"]
    covered_question_ids = {
        question_id
        for item in evidence_registry.get("evidence_items", [])
        for question_id in item.get("question_ids", [])
    }
    quality_flags = []
    missing_p0 = [question["question_id"] for question in p0_questions if question["question_id"] not in covered_question_ids]
    if missing_p0:
        quality_flags.append(
            {
                "flag_id": "missing_p0_evidence",
                "severity": "medium",
                "question_ids": missing_p0,
                "message": "Some P0 decision questions do not yet have registry evidence.",
            }
        )
    failed_citations = [check for check in citation_checks if check["status"] != "pass"]
    if failed_citations:
        quality_flags.append(
            {
                "flag_id": "source_map_mismatch",
                "severity": "medium",
                "count": len(failed_citations),
                "message": "Some evidence source ids are not present in the source map aliases.",
            }
        )
    gap_decisions = _gap_decisions(missing_p0, unsupported_claims, missing_contradiction_checks)
    research_backlog = build_research_backlog(
        filing_deep_read_pack=filing_deep_read_pack or {},
        registry_gap_requests=evidence_registry.get("registry_gap_requests") or [],
        feedback_loop_pack=feedback_loop_pack or {},
        gap_decisions=gap_decisions,
        unsupported_claims=unsupported_claims,
        confidence_caps=confidence_caps,
    )
    return {
        "schema_version": "qa_gap_triage_v1",
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "prototype_version": "v1.4",
        "generated_at": utc_now_iso(),
        "citation_checks": citation_checks,
        "source_tier_checks": _source_tier_checks(evidence_registry),
        "unsupported_claims": unsupported_claims,
        "missing_contradiction_checks": missing_contradiction_checks,
        "confidence_caps": confidence_caps,
        "quality_flags": quality_flags,
        "gap_decisions": gap_decisions,
        "research_backlog": research_backlog,
        "triage_summary": {
            "citation_check_count": len(citation_checks),
            "failed_citation_count": len(failed_citations),
            "unsupported_claim_count": len(unsupported_claims),
            "missing_contradiction_check_count": len(missing_contradiction_checks),
            "confidence_cap_count": len(confidence_caps),
            "quality_flag_count": len(quality_flags),
            "research_backlog_count": (research_backlog.get("summary") or {}).get("backlog_item_count", 0),
            "next_action": _overall_next_action(gap_decisions),
        },
    }


def build_pillar_judgment_stub(theme_workpaper_pack: dict[str, Any], qa_gap_triage: dict[str, Any]) -> dict[str, Any]:
    flags = qa_gap_triage.get("quality_flags", [])
    answers = theme_workpaper_pack.get("answers", [])
    answer_by_id = {str(answer.get("question_id")): answer for answer in answers if answer.get("question_id")}
    readiness = {
        "right_business": _pillar_status(
            answer_by_id,
            ["financial.growth", "financial.margin_conversion", "financial.cash_conversion", "business.revenue_mechanism"],
            flags,
        ),
        "right_people": _pillar_status(
            answer_by_id,
            ["people.control_governance", "people.incentives", "people.capital_allocation", "financial.dilution_sbc"],
            flags,
        ),
        "right_risk": _pillar_status(
            answer_by_id,
            ["financial.balance_sheet", "financial.accounting_red_flags", "risk.regulatory_legal"],
            flags,
        ),
        "right_price": _pillar_status(
            answer_by_id,
            ["price.owner_return", "price.expectations"],
            flags,
        ),
    }
    blocking_gaps = [
        decision
        for decision in qa_gap_triage.get("gap_decisions", [])
        if decision.get("next_action") in {"collect_more_sources", "extract_more_evidence", "human_review_required"}
    ]
    return {
        "schema_version": "pillar_judgment_stub_v1",
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "prototype_version": "v1.4",
        "generated_at": utc_now_iso(),
        "pillar_readiness": readiness,
        "blocking_gaps": blocking_gaps,
        "required_workpapers": [
            "financial_reality",
            "business_model_unit_economics",
            "management_governance_capital_allocation",
            "risk_fragility",
            "valuation_assumptions",
        ],
        "scope_limit": "Readiness stub only. No buy/sell/hold, target price, or final CIO memo.",
    }


def build_research_workflow_report(
    *,
    source_map: dict[str, Any],
    decision_question_pack: dict[str, Any],
    evidence_plan: dict[str, Any],
    filing_deep_read_pack: dict[str, Any],
    evidence_registry: dict[str, Any],
    question_evidence_completion_pack: dict[str, Any],
    theme_workpaper_pack: dict[str, Any],
    question_dossier_pack: dict[str, Any],
    qa_gap_triage: dict[str, Any],
    pillar_judgment_stub: dict[str, Any],
) -> str:
    company = source_map.get("company_context") or {}
    coverage = source_map.get("coverage_summary") or {}
    deep_summary = filing_deep_read_pack.get("summary") or {}
    registry_summary = evidence_registry.get("registry_summary") or {}
    completion_summary = question_evidence_completion_pack.get("summary") or {}
    qa_summary = qa_gap_triage.get("triage_summary") or {}
    evidence_by_id = {
        item.get("evidence_id"): item
        for item in evidence_registry.get("evidence_items", [])
        if item.get("evidence_id")
    }
    dossier_by_question = {
        str(dossier.get("question_id")): dossier
        for dossier in question_dossier_pack.get("dossiers") or []
        if dossier.get("question_id")
    }
    source_rows = [
        "| Source | Type | Tier | Status | Period / date |",
        "|---|---|---:|---|---|",
    ]
    for row in source_map.get("source_inventory", [])[:18]:
        source_rows.append(
            "| {source} | {source_type} | {tier} | {status} | {period} |".format(
                source=_md(row.get("source_id")),
                source_type=_md(row.get("source_type")),
                tier=row.get("source_tier"),
                status=_md(row.get("collection_status")),
                period=_md(row.get("period") or row.get("filing_date") or ""),
            )
        )
    question_rows = [
        "| Question ID | Pillar | Theme | Priority | Question | Evidence count |",
        "|---|---|---|---|---|---:|",
    ]
    question_counts = registry_summary.get("question_evidence_counts") or {}
    for question in decision_question_pack.get("questions", []):
        question_rows.append(
            "| {question_id} | {pillar} | {theme} | {priority} | {question} | {count} |".format(
                question_id=_md(question.get("question_id")),
                pillar=_md(question.get("pillar")),
                theme=_md(question.get("theme")),
                priority=_md(question.get("priority")),
                question=_md(question.get("question")),
                count=question_counts.get(question.get("question_id"), 0),
            )
        )
    workpaper_rows = [
        "| Theme | Answers with evidence | Questions without evidence | Evidence used | Preliminary read |",
        "|---|---:|---:|---:|---|",
    ]
    detail_sections: list[str] = []
    for workpaper in theme_workpaper_pack.get("workpapers", []):
        workpaper_rows.append(
            "| {theme} | {answered} | {missing} | {evidence} | {read} |".format(
                theme=workpaper.get("theme"),
                answered=len(workpaper.get("questions_answered", [])),
                missing=len(workpaper.get("questions_without_evidence", [])),
                evidence=len(workpaper.get("evidence_used", [])),
                read=_md(workpaper.get("preliminary_read")),
            )
        )
        detail_sections.extend(_workpaper_detail_lines(workpaper, evidence_by_id, dossier_by_question))
    readiness_rows = [
        "| Pillar | Readiness |",
        "|---|---|",
        *[
            f"| {pillar} | {status} |"
            for pillar, status in (pillar_judgment_stub.get("pillar_readiness") or {}).items()
        ],
    ]
    report = "\n".join(
        [
            f"# Decision-Question-Led Evidence Workflow: {_report_md(company.get('legal_name') or company.get('company_id'))}",
            "",
            "This is the v1.0-v1.25 artifact-first report. It is generated from the new workflow artifacts only: source map, decision questions, evidence plan, filing deep read, evidence registry, theme workpapers, QA/gap triage, and pillar-readiness stub.",
            "",
            "It is not the legacy `final_report.md`, and it does not make a buy/sell recommendation.",
            "",
            "## Version Map",
            "",
            "| Version | Artifact | Status |",
            "|---|---|---|",
            f"| v1.0 | source_map.json | {coverage.get('source_count', 0)} sources mapped |",
            f"| v1.1 | decision_question_pack.json / evidence_plan.json | {len(decision_question_pack.get('questions', []))} questions / {len(evidence_plan.get('plans', []))} plans |",
            f"| v1.25 | filing_deep_read_pack.json | {deep_summary.get('evidence_card_count', 0)} evidence cards / {deep_summary.get('contradiction_count', 0)} contradictions |",
            f"| v1.2 | evidence_registry.json | {registry_summary.get('evidence_item_count', 0)} evidence items |",
            f"| v1.3 | theme_workpaper_pack.json | {len(theme_workpaper_pack.get('workpapers', []))} workpapers |",
            f"| v1.35 | question_dossier_pack.json / theme_workpaper_evidence_appendix.md | {(question_dossier_pack.get('summary') or {}).get('question_count', 0)} question dossiers |",
            f"| v1.45 | question_evidence_completion_pack.json | {completion_summary.get('targeted_read_task_count', 0)} targeted reads / {completion_summary.get('supplemental_evidence_count', 0)} supplemental evidence items |",
            f"| v1.4 | qa_gap_triage.json / pillar_judgment_stub.json | next action: {qa_summary.get('next_action')} |",
            "",
            "## Source Coverage",
            "",
            f"- Tier-1 sources: {coverage.get('tier1_source_count', 0)}",
            f"- Downloaded or cached sources: {coverage.get('downloaded_or_cached_count', 0)}",
            f"- Missing source logs: {coverage.get('missing_source_count', 0)}",
            "",
            *source_rows,
            "",
            "## Decision Questions",
            "",
            *question_rows,
            "",
            "## Evidence Registry",
            "",
            f"- Evidence items: {registry_summary.get('evidence_item_count', 0)}",
            f"- Questions with evidence: {registry_summary.get('question_coverage_count', 0)}",
            f"- Supplemental targeted-read evidence: {registry_summary.get('supplemental_evidence_count', 0)}",
            f"- Evidence kinds: {registry_summary.get('evidence_kind_counts', {})}",
            "",
            "## Filing Deep Read",
            "",
            f"- Section rows: {deep_summary.get('section_count', 0)}",
            f"- Evidence cards: {deep_summary.get('evidence_card_count', 0)}",
            f"- Numeric fact refs: {deep_summary.get('numeric_fact_ref_count', 0)}",
            f"- Claims / inferences: {deep_summary.get('claim_count', 0)}",
            f"- Gap requests: {deep_summary.get('gap_request_count', 0)}",
            f"- Contradictions: {deep_summary.get('contradiction_count', 0)}",
            "",
            "## Workpapers",
            "",
            *workpaper_rows,
            "",
            "## Question-Led Workpaper Detail",
            "",
            *detail_sections,
            "",
            "## QA / Gap Triage",
            "",
            f"- Failed citations: {qa_summary.get('failed_citation_count', 0)}",
            f"- Unsupported claims: {qa_summary.get('unsupported_claim_count', 0)}",
            f"- Missing contradiction checks: {qa_summary.get('missing_contradiction_check_count', 0)}",
            f"- Confidence caps: {qa_summary.get('confidence_cap_count', 0)}",
            f"- Quality flags: {qa_summary.get('quality_flag_count', 0)}",
            "",
            "## Pillar Readiness Stub",
            "",
            *readiness_rows,
            "",
            "## Scope Limit",
            "",
            "This artifact does not make an investment decision. It decides whether the evidence base is organized enough for later Right Business / Right People / Right Risk / Right Price judgment agents.",
        ]
    )
    return _ensure_english_report(report)


def _workpaper_detail_lines(
    workpaper: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
    dossier_by_question: dict[str, dict[str, Any]],
) -> list[str]:
    lines = [
        f"### {_title_from_theme(str(workpaper.get('theme') or 'unknown'))}",
        "",
        f"Preliminary read: {_report_md(workpaper.get('preliminary_read'))}",
        "",
    ]
    for explanation in workpaper.get("mechanism_explanations", []):
        lines.extend(
            [
                f"- Mechanism: `{_report_md(explanation.get('mechanism'))}`",
                f"- Why it matters: {_report_md(explanation.get('summary'))}",
                "",
            ]
        )
    for answer in workpaper.get("answers", []):
        lines.extend(_answer_detail_lines(answer, evidence_by_id, dossier_by_question.get(str(answer.get("question_id")) or "")))
    unknowns = workpaper.get("unknowns", [])
    if unknowns:
        lines.extend(["#### Open Gaps", ""])
        for unknown in unknowns[:8]:
            lines.append(
                "- {question_or_type}: {unknown} Next: {next_action}".format(
                    question_or_type=_report_md(unknown.get("question_id") or unknown.get("type") or "unknown"),
                    unknown=_report_md(unknown.get("unknown") or unknown.get("description") or unknown.get("source_type")),
                    next_action=_report_md(unknown.get("next_action")),
                )
            )
        lines.append("")
    return lines


def _answer_detail_lines(
    answer: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
    dossier: dict[str, Any] | None = None,
) -> list[str]:
    evidence_ids = answer.get("evidence_ids", [])
    lines = [
        f"#### {_report_md(answer.get('question_id'))}",
        "",
        f"Question: {_report_md(answer.get('question'))}",
        "",
        "Answer:",
        "",
        _report_md(answer.get("current_answer")),
        "",
        "Evidence quality:",
        "",
        f"- Answer status: {_report_md(answer.get('status'))}",
        f"- Confidence: {_report_md(answer.get('confidence'))}",
        f"- Evidence mix: {answer.get('fact_count', 0)} facts, {answer.get('management_claim_count', 0)} management claims, {answer.get('inference_count', 0)} inferences",
        f"- Contradiction check: {'done' if answer.get('contradiction_checked') else 'pending'}",
        f"- Important caveat: {_report_md(answer.get('what_could_be_wrong'))}",
        "",
    ]
    if dossier:
        coverage = dossier.get("evidence_coverage") or {}
        source_coverage = dossier.get("source_coverage") or {}
        lines.extend(
            [
                "Evidence base summary:",
                "",
                f"- Total evidence items: {coverage.get('total_evidence_items', 0)}",
                f"- Filed/audited fact anchors: {coverage.get('filed_or_audited_fact_count', 0)}",
                f"- Evidence kind mix: {_report_md(coverage.get('evidence_kind_counts', {}))}",
                f"- Source count: {source_coverage.get('source_count', 0)}",
                f"- Top source types: {_report_md(source_coverage.get('top_source_types', []))}",
                f"- Remaining evidence gaps after official-report review: {coverage.get('gap_count', 0)}",
                f"- Contradictions/tensions logged: {coverage.get('contradiction_count', 0)}",
                "",
            ]
        )
        tensions = dossier.get("contradictions_and_tensions") or []
        if tensions:
            lines.extend(["Contradictions / tensions:", ""])
            for tension in tensions[:5]:
                lines.append(
                    f"- [{_report_md(tension.get('severity'))}] {_report_md(tension.get('summary'))} (`{_report_md(tension.get('contradiction_type'))}`)"
                )
            lines.append("")
        completion = dossier.get("question_completion") or {}
        gate = completion.get("coverage_gate") or {}
        if gate:
            supplemental = completion.get("supplemental_evidence") or []
            tasks = completion.get("targeted_read_tasks") or []
            contract = completion.get("machine_contract") or {}
            lines.extend(
                [
                    "Evidence completion attempt:",
                    "",
                    f"- Status: {_report_md(contract.get('completion_status'))}",
                    f"- Why triggered: {_report_md(contract.get('trigger_summary'))}",
                    f"- Targeted source reads completed: {len(tasks)}",
                    f"- Supplemental evidence found: {len(supplemental)}",
                    f"- Remaining gap status: `{_report_md(contract.get('remaining_gap_status'))}`",
                    f"- Remaining gap type: `{_report_md(contract.get('remaining_gap_type'))}`",
                    "",
                ]
            )
            if supplemental:
                lines.extend(["Targeted source evidence:", ""])
                for item in supplemental[:3]:
                    lines.append(
                        "- `{evidence_id}` [{kind}, source `{source}`]: {excerpt}".format(
                            evidence_id=_report_md(item.get("evidence_id")),
                            kind=_report_md(item.get("evidence_kind")),
                            source=_report_md(item.get("source_id")),
                            excerpt=_report_md(_truncate(item.get("excerpt"), 240)),
                        )
                    )
                lines.append("")
        gaps = dossier.get("gap_severity_ranking") or []
        if gaps:
            lines.extend(["Remaining official-disclosure gap:", ""])
            lines.append(_remaining_gap_summary(dossier, completion.get("machine_contract") or {}))
            lines.append("")
        bridge_tables = dossier.get("financial_bridge_tables") or []
        if bridge_tables:
            lines.extend(
                [
                    "Financial bridge snapshot:",
                    "",
                    "| Formula | Annual snapshot | Interim snapshot | Bridge rows |",
                    "|---|---|---|---:|",
                ]
            )
            for table in bridge_tables[:4]:
                lines.append(
                    "| {formula} | {annual} | {interim} | {rows} |".format(
                        formula=_report_md(table.get("formula_id")),
                        annual=_report_md(_bridge_result_summary(table.get("latest_annual") or {})),
                        interim=_report_md(_bridge_result_summary(table.get("latest_interim") or {})),
                        rows=len(table.get("bridge_rows") or []),
                    )
                )
            lines.append("")
    key_points = answer.get("key_points") or []
    if key_points:
        lines.extend(["Key points:", ""])
        for point in key_points[:6]:
            lines.append(f"- {_report_md(point)}")
        lines.append("")
    examples = [evidence_by_id.get(evidence_id) for evidence_id in evidence_ids]
    examples = [example for example in examples if example]
    if examples:
        lines.extend(["Evidence examples:", ""])
        for item in _select_evidence_examples(examples):
            lines.append(
                "- `{evidence_id}` [{kind}, tier {tier}, source `{source}`]: {excerpt}".format(
                    evidence_id=_report_md(item.get("evidence_id")),
                    kind=_report_md(item.get("evidence_kind")),
                    tier=item.get("source_tier"),
                    source=_report_md(item.get("source_id")),
                    excerpt=_report_md(item.get("excerpt")),
                )
            )
        lines.append("")
    return lines


def _select_evidence_examples(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts = [
        item
        for item in items
        if item.get("evidence_kind") == "fact" and item.get("source_type") != "source_metadata"
    ]
    claims = [item for item in items if item.get("evidence_kind") == "management_claim"]
    inferences = [item for item in items if item.get("evidence_kind") == "inference"]
    metadata_facts = [
        item
        for item in items
        if item.get("evidence_kind") == "fact" and item.get("source_type") == "source_metadata"
    ]
    selected = []
    selected.extend(facts[:2])
    selected.extend(claims[:1])
    selected.extend(inferences[:1])
    if not selected:
        selected = metadata_facts[:2] or items[:3]
    seen = set()
    deduped = []
    for item in selected:
        evidence_id = item.get("evidence_id")
        if evidence_id in seen:
            continue
        seen.add(evidence_id)
        deduped.append(item)
    return deduped[:4]


def _title_from_theme(theme: str) -> str:
    return {
        "financial_reality": "Financial Reality & Accounting Quality",
        "business_model_unit_economics": "Business Model & Unit Economics",
        "management_governance_capital_allocation": "Management / Governance / Capital Allocation",
        "risk_fragility": "Risk & Fragility",
        "valuation_assumptions": "Valuation Assumptions",
    }.get(theme, theme.replace("_", " ").title())


def _source_row_from_candidate(source: dict[str, Any], company_context: dict[str, Any]) -> dict[str, Any]:
    source_id = str(source.get("source_id") or _stable_id(source.get("name") or "source"))
    source_type = _normalize_source_type(source.get("type"))
    return {
        "source_id": source_id,
        "source_type": source_type,
        "source_group": _source_group(source_type),
        "source_tier": int(source.get("trust_tier") or 2),
        "issuer": company_context.get("legal_name"),
        "period": source.get("period"),
        "publication_date": source.get("publication_date"),
        "filing_date": source.get("filing_date"),
        "url": source.get("url"),
        "local_path": source.get("local_path"),
        "content_hash": source.get("checksum") or source.get("sha256"),
        "collection_status": source.get("status") or "registered",
        "parse_status": "metadata_only",
        "sections": [],
        "parent_source_id": None,
        "alias_source_ids": [source_id],
        "source_name": source.get("name"),
        "rights_status": _rights_status(int(source.get("trust_tier") or 2), source_type),
    }


def _source_row_from_document(document: dict[str, Any], company_context: dict[str, Any]) -> dict[str, Any]:
    document_id = str(document.get("document_id") or document.get("downloaded_file") or _stable_id(str(document)))
    source_type = _normalize_source_type(document.get("document_type"))
    local_path = document.get("local_path")
    content_hash = document.get("checksum") or document.get("sha256")
    if not content_hash and local_path and Path(str(local_path)).exists():
        content_hash = _file_sha256(Path(str(local_path)))
    alias_ids = {
        document_id,
        str(document.get("downloaded_file") or ""),
        str(document.get("primary_document") or ""),
        str(document.get("source_id") or ""),
    }
    return {
        "source_id": document_id,
        "source_type": source_type,
        "source_group": _source_group(source_type),
        "source_tier": 1 if _is_official_document(document) else 2,
        "issuer": company_context.get("legal_name"),
        "period": document.get("report_date") or document.get("period"),
        "publication_date": document.get("publication_date"),
        "filing_date": document.get("filing_date"),
        "url": document.get("source_url") or document.get("url"),
        "local_path": local_path,
        "content_hash": content_hash,
        "collection_status": document.get("status") or ("downloaded" if local_path else "registered"),
        "parse_status": "parsed" if document.get("status") == "downloaded" else "metadata_only",
        "sections": _sections_for_document(document),
        "parent_source_id": document.get("source_id"),
        "alias_source_ids": sorted(alias for alias in alias_ids if alias),
        "source_name": document.get("primary_doc_description") or document.get("downloaded_file"),
        "rights_status": "official_source_cached_for_research",
    }


def _missing_source_log(company_context: dict[str, Any], inventory: list[dict[str, Any]], state: ResearchState) -> list[dict[str, Any]]:
    source_types = {row.get("source_type") for row in inventory}
    missing = []
    if not any(source_type in source_types for source_type in {"20-F", "10-K", "annual_report"}):
        missing.append(
            {
                "source_type": "annual_report",
                "status": "missing_or_not_classified",
                "priority": "P0",
                "reason": "Annual official filing is the baseline for financial and governance research.",
            }
        )
    if not state.get("official_event_transcript_findings"):
        missing.append(
            {
                "source_type": "earnings_call_transcript",
                "status": "not_collected_in_this_artifact_pass",
                "priority": "P1",
                "reason": "Management communication should be separated from filed facts.",
            }
        )
    if company_context.get("market") == "us-adr" and not any(row.get("source_type") == "CORRESP" for row in inventory):
        missing.append(
            {
                "source_type": "sec_correspondence",
                "status": "optional_deep_stack_gap",
                "priority": "P1",
                "reason": "SEC correspondence is useful for disclosure-friction evidence.",
            }
        )
    return missing


def _acquisition_log(state: ResearchState) -> list[dict[str, Any]]:
    discovery = state.get("source_discovery") or {}
    return [
        {
            "step": "source_discovery",
            "status": "completed" if discovery else "placeholder_or_offline",
            "downloaded_documents": len(state.get("documents", [])),
            "download_errors": len(discovery.get("download_errors", [])) if isinstance(discovery, dict) else 0,
        }
    ]


def _rights_constraints(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    constraints = []
    for row in inventory:
        if row.get("source_tier") and int(row.get("source_tier")) >= 3:
            constraints.append(
                {
                    "source_id": row.get("source_id"),
                    "constraint": "lower_tier_source_for_leads_only",
                    "rule": "Do not let this source override official financial facts.",
                }
            )
    return constraints


def _source_quality_flags(inventory: list[dict[str, Any]], missing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flags = []
    if not inventory:
        flags.append({"flag_id": "empty_source_map", "severity": "high", "message": "No sources registered."})
    if any(item.get("priority") == "P0" for item in missing):
        flags.append(
            {
                "flag_id": "missing_p0_source",
                "severity": "high",
                "message": "At least one P0 source is missing or not classified.",
            }
        )
    return flags


def _company_specific_questions(company_id: str | None) -> list[dict[str, Any]]:
    if str(company_id).casefold() != "pdd":
        return []
    return [
        {
            "question_id": "pdd.temu_segment_opacity",
            "pillar": "right_business",
            "theme": "business_model_unit_economics",
            "priority": "P0",
            "question": "Can the system separate Pinduoduo domestic economics from Temu/global expansion economics?",
            "why_it_matters": "Consolidated reporting may hide materially different unit economics.",
            "expected_evidence_types": ["segment_disclosure", "sec_correspondence", "management_explanation", "financial_cross_check"],
        }
    ]


def _preferred_source_types(theme: str | None) -> list[str]:
    if theme == "financial_reality":
        return ["20-F", "10-K", "10-Q", "6-K", "earnings_release", "annual_report"]
    if theme == "business_model_unit_economics":
        return ["20-F", "10-K", "annual_report", "earnings_call_transcript", "investor_presentation"]
    if theme == "management_governance_capital_allocation":
        return ["20-F", "10-K", "annual_report", "proxy", "6-K", "earnings_call_transcript"]
    if theme == "risk_fragility":
        return ["20-F", "10-K", "annual_report", "CORRESP", "court_or_regulatory_record"]
    if theme == "valuation_assumptions":
        return ["20-F", "10-K", "annual_report", "market_input", "manual_market_input"]
    return ["annual_report"]


def _required_sections(question_id: str, theme: str | None) -> list[str]:
    if question_id.startswith("financial."):
        return ["financial_statements", "footnotes", "md&a", "risk_factors"]
    if question_id.startswith("business."):
        return ["business_overview", "revenue_discussion", "segment_discussion", "risk_factors"]
    if question_id.startswith("people."):
        return ["governance", "related_party_transactions", "share_based_compensation", "capital_allocation"]
    if question_id.startswith("price."):
        return ["financial_statements", "share_count", "cash_and_debt", "market_inputs"]
    if theme == "risk_fragility":
        return ["risk_factors", "legal_proceedings", "regulatory_correspondence"]
    return ["source_metadata"]


def _support_tests(question_id: str, theme: str | None) -> list[str]:
    if question_id == "financial.cash_conversion":
        return ["CFO >= net income over a relevant period", "FCF remains positive after capex"]
    if question_id == "financial.margin_conversion":
        return ["operating margin expands or remains resilient as revenue grows"]
    if question_id == "people.capital_allocation":
        return ["retained earnings produce attractive ROIC or shareholder returns"]
    if theme == "business_model_unit_economics":
        return ["official business description aligns with financial line items"]
    return ["source-backed evidence exists"]


def _contradiction_tests(question_id: str, theme: str | None) -> list[str]:
    if question_id.startswith("financial."):
        return ["Check whether profit growth diverges from cash flow or working capital."]
    if question_id.startswith("business."):
        return ["Check whether management claims are contradicted by margins, capex, or source gaps."]
    if question_id.startswith("people."):
        return ["Check whether ownership, SBC, related parties, or capital allocation contradict owner-oriented language."]
    if question_id.startswith("price."):
        return ["Check whether return estimate depends on aggressive growth or excess-cash assumptions."]
    return ["Search for opposing evidence before assigning high confidence."]


def _gap_conditions(question_id: str, theme: str | None) -> list[str]:
    gaps = ["No Tier-1 source", "No source-linked evidence item", "Only management claim without filed fact"]
    if question_id.startswith("people."):
        gaps.append("No structured control or incentive extraction")
    if question_id.startswith("business."):
        gaps.append("No unit-economics or segment disclosure")
    if question_id.startswith("price."):
        gaps.append("No reviewed market cap / FX input")
    return gaps


def _priority_for(question_pack: dict[str, Any], question_id: str) -> str:
    for question in question_pack.get("questions", []):
        if question.get("question_id") == question_id:
            return str(question.get("priority") or "")
    return ""


def _add_financial_fact_evidence(items: list[dict[str, Any]], state: ResearchState, source_aliases: set[str]) -> None:
    financial_pack = state.get("financial_report_pack") or {}
    _add_current_financial_support_evidence(items, financial_pack)
    for fact in _prioritized_financial_facts(financial_pack.get("fact_ledger", []))[:500]:
        metric = str(fact.get("canonical_metric") or fact.get("metric") or "")
        source_id = _best_source_id(
            [
                fact.get("source_document"),
                fact.get("accession_number"),
                fact.get("local_path"),
                fact.get("fact_id"),
                "financial_report_pack",
            ],
            source_aliases,
        )
        items.append(
            _evidence_item(
                evidence_id=f"ev_fin_fact_{len(items) + 1:04d}",
                question_ids=_question_ids_for_metric(metric),
                source_id=source_id,
                source_tier=1,
                source_type=str(fact.get("source_document_type") or "official_financial_fact"),
                locator=fact.get("xbrl_tag") or fact.get("source_table") or fact.get("context_ref") or "",
                evidence_kind="fact",
                excerpt=_fact_excerpt(fact),
                structured_fact=fact,
                confidence="high" if fact.get("confidence") in {None, "high"} else "medium",
            )
        )


def _add_current_financial_support_evidence(items: list[dict[str, Any]], financial_pack: dict[str, Any]) -> None:
    annual_rows = sorted(financial_pack.get("annual_facts", []), key=lambda row: row.get("year") or 0)
    quarterly_rows = sorted(
        financial_pack.get("quarterly_facts", []),
        key=lambda row: str(row.get("period_end") or row.get("quarter") or ""),
    )
    latest = annual_rows[-1] if annual_rows else {}
    prior = annual_rows[-2] if len(annual_rows) >= 2 else {}
    latest_q = quarterly_rows[-1] if quarterly_rows else {}
    prior_q = _same_quarter_prior_year(latest_q, quarterly_rows)
    if not latest and not latest_q:
        return

    metrics_by_id = {
        str(metric.get("formula_id")): metric
        for metric in financial_pack.get("financial_metrics", [])
        if metric.get("formula_id")
    }
    support_cards = [
        (
            ["financial.growth"],
            "latest_growth_snapshot",
            f"FY{latest.get('year')} revenue {_money_b(latest.get('revenue'))}; latest quarter revenue {_money_b(latest_q.get('revenue'))}.",
            {
                "latest_annual": _pick_keys(latest, ["year", "revenue", "operating_income", "net_income"]),
                "prior_annual": _pick_keys(prior, ["year", "revenue", "operating_income", "net_income"]),
                "latest_quarter": _pick_keys(latest_q, ["quarter", "period_end", "revenue", "operating_income", "net_income"]),
                "prior_year_quarter": _pick_keys(prior_q, ["quarter", "period_end", "revenue", "operating_income", "net_income"]),
            },
        ),
        (
            ["financial.revenue_sources", "business.revenue_mechanism"],
            "latest_revenue_mix_snapshot",
            (
                f"FY{latest.get('year')} online marketing/services {_money_b(latest.get('online_marketing_services_revenue'))}; "
                f"transaction services {_money_b(latest.get('transaction_services_revenue'))}; "
                f"latest quarter online marketing/services {_money_b(latest_q.get('online_marketing_services_revenue'))}; "
                f"transaction services {_money_b(latest_q.get('transaction_services_revenue'))}."
            ),
            {
                "latest_annual": _pick_keys(
                    latest,
                    ["year", "revenue", "online_marketing_services_revenue", "transaction_services_revenue"],
                ),
                "latest_quarter": _pick_keys(
                    latest_q,
                    ["quarter", "period_end", "revenue", "online_marketing_services_revenue", "transaction_services_revenue"],
                ),
            },
        ),
        (
            ["financial.margin_conversion", "business.unit_economics"],
            "latest_margin_snapshot",
            (
                f"FY{latest.get('year')} gross profit {_money_b(latest.get('gross_profit'))}; "
                f"operating income {_money_b(latest.get('operating_income'))}; "
                f"latest quarter operating income {_money_b(latest_q.get('operating_income'))}."
            ),
            {
                "latest_annual": _pick_keys(latest, ["year", "revenue", "gross_profit", "operating_income", "net_income"]),
                "prior_annual": _pick_keys(prior, ["year", "revenue", "gross_profit", "operating_income", "net_income"]),
                "latest_quarter": _pick_keys(latest_q, ["quarter", "period_end", "revenue", "gross_profit", "operating_income", "net_income"]),
            },
        ),
        (
            ["financial.cash_conversion", "price.owner_return"],
            "latest_cash_conversion_snapshot",
            (
                f"FY{latest.get('year')} operating cash flow {_money_b(latest.get('operating_cash_flow'))}; "
                f"FCF {_money_b(latest.get('free_cash_flow'))}; capex {_money_b(latest.get('capex'))}."
            ),
            {
                "latest_annual": _pick_keys(
                    latest,
                    ["year", "net_income", "operating_cash_flow", "free_cash_flow", "capex"],
                ),
                "prior_annual": _pick_keys(prior, ["year", "net_income", "operating_cash_flow", "free_cash_flow", "capex"]),
                "latest_quarter": _pick_keys(latest_q, ["quarter", "period_end", "net_income", "operating_cash_flow"]),
            },
        ),
        (
            ["financial.balance_sheet", "risk.regulatory_legal", "price.expectations"],
            "latest_balance_sheet_snapshot",
            (
                f"FY{latest.get('year')} cash {_money_b(latest.get('cash'))}; restricted cash {_money_b(latest.get('restricted_cash'))}; "
                f"short-term investments {_money_b(latest.get('short_term_investments'))}; debt {_money_b(latest.get('debt'))}."
            ),
            {
                "latest_annual": _pick_keys(
                    latest,
                    [
                        "year",
                        "cash",
                        "restricted_cash",
                        "short_term_investments",
                        "current_assets",
                        "current_liabilities",
                        "total_assets",
                        "total_liabilities",
                        "debt",
                    ],
                ),
                "latest_quarter": _pick_keys(
                    latest_q,
                    [
                        "quarter",
                        "period_end",
                        "cash",
                        "restricted_cash",
                        "short_term_investments",
                        "current_assets",
                        "current_liabilities",
                        "total_assets",
                        "total_liabilities",
                    ],
                ),
            },
        ),
        (
            ["financial.dilution_sbc", "people.incentives", "people.capital_allocation"],
            "latest_sbc_dilution_snapshot",
            (
                f"FY{latest.get('year')} SBC {_money_b(latest.get('stock_based_compensation'))}; "
                f"diluted shares {latest.get('diluted_shares')}; prior year diluted shares {prior.get('diluted_shares')}."
            ),
            {
                "latest_annual": _pick_keys(latest, ["year", "stock_based_compensation", "diluted_shares"]),
                "prior_annual": _pick_keys(prior, ["year", "stock_based_compensation", "diluted_shares"]),
                "latest_quarter": _pick_keys(latest_q, ["quarter", "period_end", "diluted_shares"]),
            },
        ),
        (
            ["financial.accounting_red_flags"],
            "financial_extraction_quality_snapshot",
            (
                f"Financial extraction records {len(financial_pack.get('human_review_flags') or [])} human-review flags, "
                f"{len(financial_pack.get('verification_results') or [])} verification records, "
                f"and material-event scan status {(financial_pack.get('material_event_scan') or {}).get('status', 'unknown')}."
            ),
            {
                "human_review_flag_count": len(financial_pack.get("human_review_flags") or []),
                "verification_record_count": len(financial_pack.get("verification_results") or []),
                "material_event_scan": financial_pack.get("material_event_scan") or {},
            },
        ),
    ]
    support_cards.extend(_financial_metric_support_cards(metrics_by_id))

    for question_ids, locator, excerpt, structured_fact in support_cards:
        items.append(
            _evidence_item(
                evidence_id=f"ev_fin_support_{len(items) + 1:04d}",
                question_ids=question_ids,
                source_id="financial_report_pack",
                source_tier=1,
                source_type="current_financial_summary",
                locator=locator,
                evidence_kind="fact",
                excerpt=excerpt,
                structured_fact=structured_fact,
                confidence="high",
            )
        )


def _financial_metric_support_cards(metrics_by_id: dict[str, dict[str, Any]]) -> list[tuple[list[str], str, str, dict[str, Any]]]:
    source_growth = metrics_by_id.get("source_of_growth_attribution_v1") or {}
    annual_growth = _latest_metric_result(source_growth)
    interim_growth = source_growth.get("latest_interim_result") or {}
    op_bridge = metrics_by_id.get("operating_profit_bridge_v1") or {}
    annual_op_bridge = _latest_metric_result(op_bridge)
    interim_op_bridge = op_bridge.get("latest_interim_result") or {}
    below_bridge = metrics_by_id.get("below_operating_bridge_v1") or {}
    interim_below_bridge = below_bridge.get("latest_interim_result") or {}
    working_capital = _latest_metric_result(metrics_by_id.get("working_capital_quality_v1") or {})
    balance_sheet = _latest_metric_result(metrics_by_id.get("balance_sheet_risk_v1") or {})
    sbc = _latest_metric_result(metrics_by_id.get("share_based_compensation_burden_v1") or {})
    capital_intensity = _latest_metric_result(metrics_by_id.get("capital_intensity_v1") or {})
    roic = _latest_metric_result(metrics_by_id.get("unlevered_roic_v1") or {})
    incremental_roic = _latest_metric_result(metrics_by_id.get("incremental_roic_proxy_v1") or {})
    owner_earnings = _latest_metric_result(metrics_by_id.get("owner_earnings_v1") or {})

    cards: list[tuple[list[str], str, str, dict[str, Any]]] = []
    if annual_growth or interim_growth:
        top_annual = (annual_growth or {}).get("top_component") or {}
        top_interim = (interim_growth or {}).get("top_component") or {}
        cards.append(
            (
                ["financial.growth", "financial.revenue_sources", "business.revenue_mechanism"],
                "source_of_growth_attribution_v1",
                (
                    "Source-of-growth attribution from existing metrics: "
                    f"annual top component {top_annual.get('metric', 'n/a')} at {_pct(top_annual.get('share_of_revenue'))}; "
                    f"latest-interim top component {top_interim.get('metric', 'n/a')} at {_pct(top_interim.get('share_of_revenue'))}."
                ),
                {
                    "formula_id": "source_of_growth_attribution_v1",
                    "latest_annual_result": annual_growth,
                    "latest_interim_result": interim_growth,
                },
            )
        )
    if annual_op_bridge or interim_op_bridge:
        cards.append(
            (
                ["financial.margin_conversion", "business.unit_economics"],
                "operating_profit_bridge_v1",
                (
                    "Operating-profit bridge from existing metrics: "
                    f"annual incremental operating margin {_pct((annual_op_bridge or {}).get('incremental_operating_margin'))}; "
                    f"latest-interim incremental operating margin {_pct((interim_op_bridge or {}).get('incremental_operating_margin'))}."
                ),
                {
                    "formula_id": "operating_profit_bridge_v1",
                    "latest_annual_result": annual_op_bridge,
                    "latest_interim_result": interim_op_bridge,
                },
            )
        )
    if interim_below_bridge:
        cards.append(
            (
                ["financial.accounting_red_flags"],
                "below_operating_bridge_v1",
                (
                    "Below-operating bridge from existing metrics: "
                    f"operating-income delta {_money_b(interim_below_bridge.get('operating_income_delta'))}; "
                    f"net-income delta {_money_b(interim_below_bridge.get('net_income_delta'))}; "
                    f"below-operating delta {_money_b(interim_below_bridge.get('below_operating_delta'))}."
                ),
                {
                    "formula_id": "below_operating_bridge_v1",
                    "latest_interim_result": interim_below_bridge,
                },
            )
        )
    if working_capital:
        cards.append(
            (
                ["financial.cash_conversion", "financial.balance_sheet", "business.unit_economics"],
                "working_capital_quality_v1",
                (
                    "Working-capital quality from existing metrics: "
                    f"cash tailwind / revenue {_pct(working_capital.get('working_capital_cash_tailwind_to_revenue'))}; "
                    f"source-liability delta {_money_b(working_capital.get('cash_source_liability_delta'))}; "
                    f"use-asset delta {_money_b(working_capital.get('cash_use_asset_delta'))}."
                ),
                {
                    "formula_id": "working_capital_quality_v1",
                    "latest_annual_result": working_capital,
                },
            )
        )
    if balance_sheet:
        cards.append(
            (
                ["financial.balance_sheet", "risk.regulatory_legal"],
                "balance_sheet_risk_v1",
                (
                    "Balance-sheet risk from existing metrics: "
                    f"current ratio {_ratio(balance_sheet.get('current_ratio'))}; "
                    f"restricted cash / cash {_pct(balance_sheet.get('restricted_cash_to_cash'))}; "
                    f"liquid assets / liabilities {_ratio(balance_sheet.get('liquid_assets_to_total_liabilities'))}."
                ),
                {
                    "formula_id": "balance_sheet_risk_v1",
                    "latest_annual_result": balance_sheet,
                },
            )
        )
    if sbc:
        cards.append(
            (
                ["financial.dilution_sbc", "people.incentives", "people.capital_allocation"],
                "share_based_compensation_burden_v1",
                (
                    "SBC/dilution burden from existing metrics: "
                    f"SBC / revenue {_pct(sbc.get('sbc_to_revenue'))}; "
                    f"SBC / CFO {_pct(sbc.get('sbc_to_operating_cash_flow'))}; "
                    f"diluted shares YoY {_pct(sbc.get('diluted_shares_yoy'))}."
                ),
                {
                    "formula_id": "share_based_compensation_burden_v1",
                    "latest_annual_result": sbc,
                },
            )
        )
    if capital_intensity:
        cards.append(
            (
                ["financial.cash_conversion", "business.reinvestment_need", "price.owner_return"],
                "capital_intensity_v1",
                (
                    "Capital-intensity metrics from existing metrics: "
                    f"capex / revenue {_pct(capital_intensity.get('capex_to_revenue'))}; "
                    f"FCF margin {_pct(capital_intensity.get('free_cash_flow_margin'))}; "
                    f"FCF / CFO {_pct(capital_intensity.get('free_cash_flow_to_operating_cash_flow'))}."
                ),
                {
                    "formula_id": "capital_intensity_v1",
                    "latest_annual_result": capital_intensity,
                },
            )
        )
    if roic or incremental_roic:
        cards.append(
            (
                ["business.unit_economics", "business.reinvestment_need", "people.capital_allocation", "price.expectations"],
                "roic_and_incremental_roic_v1",
                (
                    "ROIC metrics from existing metrics: "
                    f"unlevered ROIC {_pct((roic or {}).get('value'))}; "
                    f"incremental ROIC proxy {_pct((incremental_roic or {}).get('value'))}."
                ),
                {
                    "formula_ids": ["unlevered_roic_v1", "incremental_roic_proxy_v1"],
                    "latest_roic_result": roic,
                    "latest_incremental_roic_result": incremental_roic,
                },
            )
        )
    if owner_earnings:
        cards.append(
            (
                ["price.owner_return"],
                "owner_earnings_v1",
                (
                    "Owner-earnings proxy from existing metrics: "
                    f"owner earnings {_money_b(owner_earnings.get('value'))}; "
                    f"maintenance capex proxy {_money_b(owner_earnings.get('maintenance_capex_proxy'))}."
                ),
                {
                    "formula_id": "owner_earnings_v1",
                    "latest_annual_result": owner_earnings,
                },
            )
        )
    return cards


def _pick_keys(row: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: row.get(key) for key in keys if key in row}


def _latest_metric_result(metric: dict[str, Any], result_key: str = "annual_results") -> dict[str, Any]:
    rows = [row for row in metric.get(result_key, []) if isinstance(row, dict)]
    calculated = [row for row in rows if row.get("status") == "calculated"]
    if calculated:
        return calculated[-1]
    return rows[-1] if rows else {}


def _component_points(result: dict[str, Any]) -> list[str]:
    points = []
    for component in result.get("component_details", [])[:4]:
        metric = component.get("metric", "component")
        parts = [
            f"{metric}: {_money_b(component.get('value'))}",
            f"share {_pct(component.get('share_of_revenue'))}",
        ]
        if "revenue_growth_contribution" in component:
            parts.append(f"growth contribution {_pct(component.get('revenue_growth_contribution'))}")
        if "yoy_growth" in component:
            parts.append(f"YoY {_pct(component.get('yoy_growth'))}")
        points.append("; ".join(parts) + ".")
    return points


def _bridge_metric_row(result: dict[str, Any], metric: str) -> dict[str, Any]:
    for row in result.get("bridge_rows", []):
        if row.get("metric") == metric:
            return row
    return {}


def _warning_points(warnings: Any) -> list[str]:
    if not isinstance(warnings, list):
        return []
    return [f"Warning: {_clean(warning)}." for warning in warnings if warning]


def _prioritized_financial_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(fact: dict[str, Any]) -> tuple[int, int, int, str]:
        year = int(_num(fact.get("period_year")) or _row_year(fact) or 0)
        source_type = str(fact.get("source_document_type") or "")
        currency = str(fact.get("currency") or fact.get("display_unit") or "")
        confidence = str(fact.get("confidence") or "")
        official_priority = 1 if source_type.startswith(("20-F", "6-K")) else 0
        currency_priority = 1 if currency in {"RMB", "CNY"} else 0
        confidence_priority = 1 if confidence in {"", "high"} else 0
        return (-year, -official_priority, -currency_priority, -confidence_priority, str(fact.get("fact_id") or ""))

    return sorted(facts, key=sort_key)


def _add_source_inventory_evidence(items: list[dict[str, Any]], source_map: dict[str, Any]) -> None:
    for row in source_map.get("source_inventory", [])[:80]:
        if row.get("collection_status") == "not_used_phase_2":
            continue
        source_type = str(row.get("source_type") or "")
        question_ids = ["financial.accounting_red_flags"]
        if source_type in {"20-F", "10-K", "annual_report", "6-K", "earnings_release"}:
            question_ids.extend(["financial.growth", "financial.cash_conversion", "financial.balance_sheet"])
        if source_type in {"annual_report", "investor_presentation", "earnings_call_transcript"}:
            question_ids.append("business.revenue_mechanism")
        if source_type in {"20-F", "10-K", "annual_report", "proxy"}:
            question_ids.append("people.control_governance")
        items.append(
            _evidence_item(
                evidence_id=f"ev_source_{len(items) + 1:04d}",
                question_ids=question_ids,
                source_id=str(row.get("source_id") or "source_map"),
                source_tier=int(row.get("source_tier") or 2),
                source_type="source_metadata",
                locator=str(row.get("local_path") or row.get("url") or row.get("source_name") or ""),
                evidence_kind="fact",
                excerpt=(
                    f"Source mapped: {row.get('source_id')} | type={row.get('source_type')} | "
                    f"status={row.get('collection_status')} | tier={row.get('source_tier')}"
                ),
                structured_fact=row,
                confidence="high" if row.get("source_tier") == 1 else "medium",
            )
        )


def _add_deep_read_evidence(items: list[dict[str, Any]], filing_deep_read_pack: dict[str, Any]) -> None:
    for card in filing_deep_read_pack.get("evidence_cards", []):
        copied = dict(card)
        if not copied.get("evidence_id"):
            copied["evidence_id"] = f"ev_deep_{len(items) + 1:04d}"
        items.append(copied)
    for contradiction in filing_deep_read_pack.get("contradiction_matrix", []):
        question_id = str(contradiction.get("question_id") or "workflow")
        if question_id == "workflow":
            continue
        items.append(
            _evidence_item(
                evidence_id=f"ev_contradiction_{len(items) + 1:04d}",
                question_ids=[question_id],
                source_id="filing_deep_read_pack",
                source_tier=1,
                source_type="contradiction_matrix",
                locator=str(contradiction.get("contradiction_id") or ""),
                evidence_kind="inference",
                excerpt=str(contradiction.get("summary") or ""),
                structured_fact=contradiction,
                confidence="high" if contradiction.get("severity") == "high" else "medium",
            )
        )


def _add_adapter_bundle_evidence(items: list[dict[str, Any]], bundle: dict[str, Any]) -> None:
    for card in bundle.get("evidence_items", []):
        copied = dict(card)
        if not copied.get("evidence_id"):
            copied["evidence_id"] = f"ev_adapter_{len(items) + 1:04d}"
        items.append(copied)


def _add_layer1_diagnostic_evidence(items: list[dict[str, Any]], state: ResearchState) -> None:
    pack = state.get("layer1_question_pack") or {}
    for answer in pack.get("standard_question_answers", []):
        question_ids = _legacy_question_refs_to_decision_questions(answer.get("related_research_questions", []))
        if not question_ids:
            question_ids = ["financial.growth"]
        items.append(
            _evidence_item(
                evidence_id=f"ev_layer1_{len(items) + 1:04d}",
                question_ids=question_ids,
                source_id="layer1_question_pack",
                source_tier=1,
                source_type="derived_financial_diagnostic",
                locator=str(answer.get("question_id") or ""),
                evidence_kind="inference",
                excerpt=str(answer.get("answer") or answer.get("current_read") or ""),
                structured_fact=answer,
                confidence="medium",
            )
        )


def _add_evidence_communication_items(items: list[dict[str, Any]], state: ResearchState) -> None:
    pack = state.get("evidence_communication_pack") or {}
    for answer in pack.get("question_answers", [])[:80]:
        question_ids = _infer_questions_from_text(
            " ".join(str(answer.get(key) or "") for key in ["question", "current_answer", "answer", "topic"])
        )
        items.append(
            _evidence_item(
                evidence_id=f"ev_comm_{len(items) + 1:04d}",
                question_ids=question_ids or ["financial.accounting_red_flags"],
                source_id=str(answer.get("source_id") or "evidence_communication_pack"),
                source_tier=1,
                source_type="official_filing_or_management_communication",
                locator=str(answer.get("locator") or answer.get("question_id") or ""),
                evidence_kind="management_claim" if _looks_like_management_claim(answer) else "inference",
                excerpt=str(answer.get("current_answer") or answer.get("answer") or answer.get("summary") or "")[:900],
                structured_fact=answer,
                confidence=str(answer.get("confidence") or "medium"),
            )
        )
    for discovery in pack.get("proactive_discoveries", [])[:80]:
        items.append(
            _evidence_item(
                evidence_id=f"ev_discovery_{len(items) + 1:04d}",
                question_ids=_infer_questions_from_text(str(discovery)) or ["financial.accounting_red_flags"],
                source_id=str(discovery.get("source_id") or "evidence_communication_pack"),
                source_tier=1,
                source_type="official_filing_discovery",
                locator=str(discovery.get("locator") or discovery.get("theme") or ""),
                evidence_kind="fact" if discovery.get("evidence_kind") == "fact" else "inference",
                excerpt=str(discovery.get("finding") or discovery.get("summary") or discovery)[:900],
                structured_fact=discovery,
                confidence=str(discovery.get("confidence") or "medium"),
            )
        )


def _add_business_model_items(items: list[dict[str, Any]], state: ResearchState) -> None:
    unit_pack = state.get("business_model_unit_economics_pack") or {}
    for answer in unit_pack.get("question_answers", [])[:120]:
        question_ids = _business_question_ids(answer)
        items.append(
            _evidence_item(
                evidence_id=f"ev_bmue_{len(items) + 1:04d}",
                question_ids=question_ids,
                source_id=str(answer.get("source_id") or "business_model_unit_economics_pack"),
                source_tier=1,
                source_type="business_model_workpaper",
                locator=str(answer.get("question_id") or answer.get("id") or ""),
                evidence_kind="inference",
                excerpt=str(answer.get("current_answer") or answer.get("answer") or answer.get("summary") or "")[:900],
                structured_fact=answer,
                confidence=str(answer.get("confidence") or answer.get("evidence_grade") or "medium"),
            )
        )
    bm_pack = state.get("business_model_evidence_pack") or {}
    for question in bm_pack.get("questions", [])[:40]:
        items.append(
            _evidence_item(
                evidence_id=f"ev_bme_{len(items) + 1:04d}",
                question_ids=_business_question_ids(question),
                source_id="business_model_evidence_pack",
                source_tier=1,
                source_type="business_model_evidence_pack",
                locator=str(question.get("question_id") or question.get("id") or ""),
                evidence_kind="inference",
                excerpt=str(question.get("answer") or question.get("current_read") or question.get("summary") or "")[:900],
                structured_fact=question,
                confidence=str(question.get("confidence") or "medium"),
            )
        )


def _add_right_people_items(items: list[dict[str, Any]], state: ResearchState) -> None:
    findings = state.get("leadership_findings") or {}
    for card in findings.get("official_filing_evidence_cards", [])[:80]:
        items.append(
            _evidence_item(
                evidence_id=f"ev_people_card_{len(items) + 1:04d}",
                question_ids=_infer_questions_from_text(str(card)) or ["people.control_governance"],
                source_id=str(card.get("source_id") or card.get("document_id") or "leadership_findings"),
                source_tier=1,
                source_type="official_filing_governance_evidence",
                locator=str(card.get("locator") or card.get("theme") or ""),
                evidence_kind="fact",
                excerpt=str(card.get("evidence") or card.get("excerpt") or card.get("finding") or card)[:900],
                structured_fact=card,
                confidence=str(card.get("confidence") or "medium"),
            )
        )
    for signal in findings.get("financial_signals", [])[:60]:
        items.append(
            _evidence_item(
                evidence_id=f"ev_people_signal_{len(items) + 1:04d}",
                question_ids=_infer_questions_from_text(str(signal)) or ["people.capital_allocation"],
                source_id="leadership_findings",
                source_tier=1,
                source_type="derived_people_financial_signal",
                locator=str(signal.get("signal_id") or ""),
                evidence_kind="inference",
                excerpt=str(signal.get("read") or signal.get("summary") or signal)[:900],
                structured_fact=signal,
                confidence=str(signal.get("confidence") or "medium"),
            )
        )
    decision = findings.get("right_people_decision") or {}
    if decision:
        items.append(
            _evidence_item(
                evidence_id=f"ev_people_decision_{len(items) + 1:04d}",
                question_ids=["people.control_governance", "people.incentives", "people.capital_allocation", "people.candor"],
                source_id="leadership_findings",
                source_tier=1,
                source_type="right_people_analysis",
                locator="right_people_decision",
                evidence_kind="inference",
                excerpt=str(decision.get("current_read") or decision.get("status") or "")[:900],
                structured_fact=decision,
                confidence="medium",
            )
        )


def _add_valuation_items(items: list[dict[str, Any]], state: ResearchState) -> None:
    for metric in state.get("valuation_metrics", [])[:30]:
        items.append(
            _evidence_item(
                evidence_id=f"ev_price_{len(items) + 1:04d}",
                question_ids=["price.owner_return", "price.expectations"],
                source_id="valuation_metrics",
                source_tier=1,
                source_type="derived_valuation_metric",
                locator=str(metric.get("formula_id") or ""),
                evidence_kind="inference",
                excerpt=str(metric.get("summary") or metric.get("formula_id") or metric.get("status") or "")[:900],
                structured_fact=metric,
                confidence="medium" if metric.get("status") == "calculated" else "low",
            )
        )


def _registry_unknowns(state: ResearchState, source_map: dict[str, Any], question_pack: dict[str, Any]) -> list[dict[str, Any]]:
    unknowns = []
    for missing in source_map.get("missing_source_log", []):
        unknowns.append(
            {
                "unknown_id": f"unknown_source_{len(unknowns) + 1:03d}",
                "type": "missing_source",
                "source_type": missing.get("source_type"),
                "priority": missing.get("priority"),
                "description": missing.get("reason"),
                "next_action": "collect_more_sources" if missing.get("priority") == "P0" else "monitor",
            }
        )
    for gap in ((state.get("financial_report_pack") or {}).get("fact_extraction_summary") or {}).get(
        "disclosure_gap_registry",
        [],
    ):
        unknowns.append(
            {
                "unknown_id": f"unknown_disclosure_{len(unknowns) + 1:03d}",
                "type": "disclosure_gap",
                "description": gap.get("description") or gap.get("metric") or str(gap),
                "structured_gap": gap,
                "next_action": "extract_more_evidence",
            }
        )
    return unknowns


def _workpaper_answer(
    theme: str,
    question: dict[str, Any],
    evidence_items: list[dict[str, Any]],
    answer_context: dict[str, Any],
) -> dict[str, Any]:
    evidence_ids = _answer_evidence_ids(evidence_items)
    facts = [item for item in evidence_items if item.get("evidence_kind") == "fact"]
    claims = [item for item in evidence_items if item.get("evidence_kind") == "management_claim"]
    inferences = [item for item in evidence_items if item.get("evidence_kind") == "inference"]
    status = _answer_status(question["question_id"], facts, claims, inferences, answer_context)
    contradiction_checked = bool(facts and (claims or inferences) and len(evidence_items) >= 2)
    confidence = "high" if status == "answered" and contradiction_checked else "medium" if evidence_items else "low"
    current_answer, key_points = _current_answer(question, facts, claims, inferences, answer_context)
    return {
        "theme": theme,
        "question_id": question["question_id"],
        "question": question.get("question"),
        "status": status,
        "current_answer": current_answer,
        "key_points": key_points,
        "evidence_ids": evidence_ids,
        "fact_count": len(facts),
        "management_claim_count": len(claims),
        "inference_count": len(inferences),
        "confidence": confidence,
        "contradiction_checked": contradiction_checked,
        "what_could_be_wrong": _what_could_be_wrong(question["question_id"], status, contradiction_checked),
        "next_step": _answer_next_step(question["question_id"], status, contradiction_checked),
    }


def _current_answer(
    question: dict[str, Any],
    facts: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    inferences: list[dict[str, Any]],
    answer_context: dict[str, Any],
) -> tuple[str, list[str]]:
    question_id = question["question_id"]
    if not facts and not claims and not inferences:
        return "No reusable evidence has been registered yet.", [
            "Collect or parse the preferred sources in the evidence plan."
        ]
    if question_id.startswith("financial."):
        return _financial_current_answer(question_id, answer_context)
    if question_id.startswith("business.") or question_id.startswith("pdd."):
        return _business_current_answer(question_id, answer_context)
    if question_id.startswith("people."):
        return _people_current_answer(question_id, answer_context)
    if question_id.startswith("risk."):
        return _risk_current_answer(question_id, answer_context)
    if question_id.startswith("price."):
        return _price_current_answer(question_id, answer_context)
    return "Evidence exists, but the answer should stay provisional until contradiction checks are complete.", [
        "Run contradiction checks before raising confidence."
    ]


def _answer_context(state: ResearchState) -> dict[str, Any]:
    financial_pack = state.get("financial_report_pack") or {}
    annual_rows = sorted(
        financial_pack.get("annual_facts", []),
        key=lambda row: row.get("year") or 0,
    )
    quarterly_rows = sorted(
        financial_pack.get("quarterly_facts", []),
        key=lambda row: str(row.get("period_end") or row.get("quarter") or ""),
    )
    latest_annual = annual_rows[-1] if annual_rows else {}
    prior_annual = annual_rows[-2] if len(annual_rows) >= 2 else {}
    latest_quarter = quarterly_rows[-1] if quarterly_rows else {}
    same_quarter_prior_year = _same_quarter_prior_year(latest_quarter, quarterly_rows)
    metrics_by_id = {
        str(metric.get("formula_id")): metric
        for metric in financial_pack.get("financial_metrics", [])
        if metric.get("formula_id")
    }
    valuation_by_id = {
        str(metric.get("formula_id")): metric
        for metric in state.get("valuation_metrics", [])
        if metric.get("formula_id")
    }
    return {
        "financial_pack": financial_pack,
        "annual_rows": annual_rows,
        "quarterly_rows": quarterly_rows,
        "latest_annual": latest_annual,
        "prior_annual": prior_annual,
        "latest_quarter": latest_quarter,
        "same_quarter_prior_year": same_quarter_prior_year,
        "metrics_by_id": metrics_by_id,
        "financial_health": financial_pack.get("financial_health") or {},
        "business_model_unit_economics_pack": state.get("business_model_unit_economics_pack") or {},
        "business_model_evidence_pack": state.get("business_model_evidence_pack") or {},
        "leadership_findings": state.get("leadership_findings") or {},
        "valuation_metrics_by_id": valuation_by_id,
        "market_inputs": state.get("market_inputs") or {},
    }


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"n/a", "na", "none", "null"}:
            return None
        negative = text.startswith("(") and text.endswith(")")
        cleaned = (
            text.replace(",", "")
            .replace("RMB", "")
            .replace("USD", "")
            .replace("HKD", "")
            .replace("$", "")
            .replace("%", "")
            .replace("x", "")
            .replace("X", "")
            .strip("() ")
        )
        try:
            parsed = float(cleaned)
        except ValueError:
            return None
        return -parsed if negative else parsed
    return None


def _safe_div(numerator: Any, denominator: Any) -> float | None:
    num = _num(numerator)
    den = _num(denominator)
    if num is None or den in {None, 0.0}:
        return None
    return num / den


def _growth(current: Any, prior: Any) -> float | None:
    current_num = _num(current)
    prior_num = _num(prior)
    if current_num is None or prior_num in {None, 0.0}:
        return None
    return (current_num - prior_num) / abs(prior_num)


def _money_b(value: Any, currency: str = "RMB") -> str:
    num = _num(value)
    if num is None:
        return "n/a"
    return f"{currency} {num / 1_000_000_000:.1f}B"


def _pct(value: Any) -> str:
    num = _num(value)
    if num is None:
        return "n/a"
    display = num * 100 if abs(num) <= 1.5 else num
    return f"{display:.1f}%"


def _ratio(value: Any) -> str:
    num = _num(value)
    if num is None:
        return "n/a"
    return f"{num:.2f}x"


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _same_quarter_prior_year(
    latest_quarter: dict[str, Any],
    quarterly_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    latest_year = _row_year(latest_quarter)
    latest_quarter_num = _row_quarter(latest_quarter)
    if latest_year is None or latest_quarter_num is None:
        return {}
    for row in quarterly_rows:
        if _row_year(row) == latest_year - 1 and _row_quarter(row) == latest_quarter_num:
            return row
    return {}


def _row_year(row: dict[str, Any]) -> int | None:
    for key in ["year", "fiscal_year"]:
        value = _num(row.get(key))
        if value is not None:
            return int(value)
    for key in ["period_end", "quarter", "period"]:
        text = str(row.get(key) or "")
        if len(text) >= 4 and text[:4].isdigit():
            return int(text[:4])
    return None


def _row_quarter(row: dict[str, Any]) -> int | None:
    quarter = str(row.get("quarter") or row.get("period") or "").upper()
    for idx in range(1, 5):
        if f"Q{idx}" in quarter:
            return idx
    period_end = str(row.get("period_end") or "")
    if len(period_end) >= 7 and period_end[5:7].isdigit():
        month = int(period_end[5:7])
        return ((month - 1) // 3) + 1
    return None


def _financial_current_answer(question_id: str, ctx: dict[str, Any]) -> tuple[str, list[str]]:
    latest = ctx.get("latest_annual") or {}
    prior = ctx.get("prior_annual") or {}
    latest_q = ctx.get("latest_quarter") or {}
    prior_q = ctx.get("same_quarter_prior_year") or {}
    metrics = ctx.get("metrics_by_id") or {}
    health = ctx.get("financial_health") or {}

    if question_id == "financial.growth":
        annual_growth = _growth(latest.get("revenue"), prior.get("revenue"))
        q_growth = _growth(latest_q.get("revenue"), prior_q.get("revenue"))
        trend = metrics.get("latest_interim_trend_v1") or {}
        source_growth = metrics.get("source_of_growth_attribution_v1") or {}
        interim_growth = source_growth.get("latest_interim_result") or {}
        interim_top = interim_growth.get("top_component") or {}
        answer = (
            f"Yes, PDD is still growing, but the latest annual picture is mixed. "
            f"FY{latest.get('year')} revenue was {_money_b(latest.get('revenue'))}, "
            f"up {_pct(annual_growth)} YoY; latest quarter revenue was {_money_b(latest_q.get('revenue'))}, "
            f"up {_pct(q_growth)} YoY. The upstream current-run latest-interim trend metric is `{trend.get('overall_status', 'unknown')}` "
            f"with direction `{trend.get('direction', 'unknown')}`; the financial-health status is `{health.get('status', 'unknown')}` because profit and return metrics weakened versus the prior annual period."
        )
        return answer, [
            f"FY revenue: {_money_b(latest.get('revenue'))}; YoY {_pct(annual_growth)}.",
            f"Latest quarter revenue: {_money_b(latest_q.get('revenue'))}; YoY {_pct(q_growth)}.",
            f"Latest-quarter top revenue component: {interim_top.get('metric', 'n/a')} at {_pct(interim_top.get('share_of_revenue'))} of revenue.",
            _clean(health.get("main_negative_evidence")) or "Profit conversion needs follow-up.",
        ]

    if question_id == "financial.revenue_sources":
        source_growth = metrics.get("source_of_growth_attribution_v1") or {}
        annual_source = _latest_metric_result(source_growth)
        interim_source = source_growth.get("latest_interim_result") or {}
        online_share = _safe_div(latest.get("online_marketing_services_revenue"), latest.get("revenue"))
        transaction_share = _safe_div(latest.get("transaction_services_revenue"), latest.get("revenue"))
        q_online_share = _safe_div(latest_q.get("online_marketing_services_revenue"), latest_q.get("revenue"))
        q_transaction_share = _safe_div(latest_q.get("transaction_services_revenue"), latest_q.get("revenue"))
        annual_components = _component_points(annual_source)
        interim_components = _component_points(interim_source)
        answer = (
            f"Revenue is now roughly split between online marketing/services and transaction services. "
            f"In FY{latest.get('year')}, online marketing services and others were {_money_b(latest.get('online_marketing_services_revenue'))} "
            f"({_pct(online_share)} of revenue), while transaction services were {_money_b(latest.get('transaction_services_revenue'))} "
            f"({_pct(transaction_share)}). In the latest quarter, transaction services were the larger component at {_pct(q_transaction_share)} of revenue. "
            "This uses the existing `source_of_growth_attribution_v1` metric, so the component split remains tied to official revenue-line facts."
        )
        return answer, [
            f"FY online marketing/services: {_money_b(latest.get('online_marketing_services_revenue'))} ({_pct(online_share)}).",
            f"FY transaction services: {_money_b(latest.get('transaction_services_revenue'))} ({_pct(transaction_share)}).",
            f"Latest quarter mix: transaction {_pct(q_transaction_share)}, online marketing {_pct(q_online_share)}.",
            *(annual_components[:2] or []),
            *(interim_components[:2] or []),
        ]

    if question_id == "financial.margin_conversion":
        op_bridge = ((metrics.get("operating_profit_bridge_v1") or {}).get("latest_interim_result") or {})
        annual_op_bridge = _latest_metric_result(metrics.get("operating_profit_bridge_v1") or {})
        annual_op_growth = _growth(latest.get("operating_income"), prior.get("operating_income"))
        annual_gross_margin = _safe_div(latest.get("gross_profit"), latest.get("revenue"))
        annual_op_margin = _safe_div(latest.get("operating_income"), latest.get("revenue"))
        q_op_margin = _safe_div(latest_q.get("operating_income"), latest_q.get("revenue"))
        annual_cost_row = _bridge_metric_row(annual_op_bridge, "cost_of_revenue")
        annual_snm_row = _bridge_metric_row(annual_op_bridge, "sales_and_marketing_expense")
        answer = (
            f"Growth did not fully convert into annual operating profit. FY{latest.get('year')} gross margin was {_pct(annual_gross_margin)} "
            f"and operating margin was {_pct(annual_op_margin)}, but operating income declined {_pct(annual_op_growth)} YoY. "
            f"The existing operating-profit bridge shows annual incremental operating margin of {_pct(annual_op_bridge.get('incremental_operating_margin'))}; "
            f"the latest quarter looks better at the operating line, with operating margin {_pct(q_op_margin)} and incremental operating margin {_pct(op_bridge.get('incremental_operating_margin'))}."
        )
        return answer, [
            f"FY operating income YoY: {_pct(annual_op_growth)}.",
            f"FY gross / operating margin: {_pct(annual_gross_margin)} / {_pct(annual_op_margin)}.",
            f"FY incremental operating margin: {_pct(annual_op_bridge.get('incremental_operating_margin'))}.",
            f"Latest-quarter incremental operating margin: {_pct(op_bridge.get('incremental_operating_margin'))}.",
            f"FY cost-of-revenue delta: {_money_b(annual_cost_row.get('delta'))}; sales-and-marketing delta: {_money_b(annual_snm_row.get('delta'))}.",
        ]

    if question_id == "financial.cash_conversion":
        cap_intensity = _latest_metric_result(metrics.get("capital_intensity_v1") or {})
        working_capital = _latest_metric_result(metrics.get("working_capital_quality_v1") or {})
        cash_conversion = _safe_div(latest.get("operating_cash_flow"), latest.get("net_income"))
        fcf_margin = _safe_div(latest.get("free_cash_flow"), latest.get("revenue"))
        fcf_growth = _growth(latest.get("free_cash_flow"), prior.get("free_cash_flow"))
        answer = (
            f"Reported profit still converts into cash, but cash flow is no longer accelerating. "
            f"FY{latest.get('year')} operating cash flow was {_money_b(latest.get('operating_cash_flow'))}, "
            f"FCF was {_money_b(latest.get('free_cash_flow'))}, CFO / net income was {_ratio(cash_conversion)}, "
            f"and FCF margin was {_pct(fcf_margin)}. FCF declined {_pct(fcf_growth)} YoY. "
            f"Upstream current-run working-capital metrics show a cash tailwind of {_pct(working_capital.get('working_capital_cash_tailwind_to_revenue'))} of revenue, so the next workpaper should keep separating real owner cash from working-capital float."
        )
        return answer, [
            f"CFO / net income: {_ratio(cash_conversion)}.",
            f"FCF: {_money_b(latest.get('free_cash_flow'))}; FCF margin {_pct(fcf_margin)}.",
            f"FCF YoY: {_pct(fcf_growth)}.",
            f"CapEx / revenue: {_pct(cap_intensity.get('capex_to_revenue'))}; FCF / CFO: {_pct(cap_intensity.get('free_cash_flow_to_operating_cash_flow'))}.",
            f"Working-capital cash tailwind / revenue: {_pct(working_capital.get('working_capital_cash_tailwind_to_revenue'))}.",
            *(_warning_points(working_capital.get("warning_flags"))[:2]),
        ]

    if question_id == "financial.balance_sheet":
        balance_metric = _latest_metric_result(metrics.get("balance_sheet_risk_v1") or {})
        broad_cash = sum(
            value or 0
            for value in [
                latest.get("cash"),
                latest.get("restricted_cash"),
                latest.get("short_term_investments"),
            ]
        )
        restricted_to_cash = _safe_div(latest.get("restricted_cash"), latest.get("cash"))
        current_ratio = _safe_div(latest.get("current_assets"), latest.get("current_liabilities"))
        liabilities_to_assets = _safe_div(latest.get("total_liabilities"), latest.get("total_assets"))
        answer = (
            f"The balance sheet looks strong, but not all cash should be treated as freely distributable owner cash. "
            f"FY{latest.get('year')} broad cash and short-term investments were {_money_b(broad_cash)}; "
            f"restricted cash was {_money_b(latest.get('restricted_cash'))}, or {_pct(restricted_to_cash)} of cash. "
            f"The current ratio was {_ratio(current_ratio)} and liabilities / assets were {_pct(liabilities_to_assets)}. "
            f"The existing balance-sheet-risk metric also shows liquid assets / liabilities at {_ratio(balance_metric.get('liquid_assets_to_total_liabilities'))}."
        )
        return answer, [
            f"Broad cash + restricted cash + short-term investments: {_money_b(broad_cash)}.",
            f"Restricted cash / cash: {_pct(restricted_to_cash)}.",
            f"Current ratio: {_ratio(current_ratio)}; liabilities / assets: {_pct(liabilities_to_assets)}.",
            f"Liquid assets / total liabilities: {_ratio(balance_metric.get('liquid_assets_to_total_liabilities'))}.",
        ]

    if question_id == "financial.dilution_sbc":
        sbc_metric = _latest_metric_result(metrics.get("share_based_compensation_burden_v1") or {})
        sbc_to_revenue = _safe_div(latest.get("stock_based_compensation"), latest.get("revenue"))
        sbc_to_cfo = _safe_div(latest.get("stock_based_compensation"), latest.get("operating_cash_flow"))
        dilution = _growth(latest.get("diluted_shares"), prior.get("diluted_shares"))
        answer = (
            f"Dilution and SBC are visible but not the main financial pressure in the latest annual data. "
            f"FY{latest.get('year')} SBC was {_money_b(latest.get('stock_based_compensation'))}, "
            f"equal to {_pct(sbc_to_revenue)} of revenue and {_pct(sbc_to_cfo)} of operating cash flow. "
            f"Diluted shares increased {_pct(dilution)} YoY. This now borrows `share_based_compensation_burden_v1`; per-share dilution looks contained, while pay-metric alignment still needs governance extraction."
        )
        return answer, [
            f"SBC / revenue: {_pct(sbc_metric.get('sbc_to_revenue') if sbc_metric else sbc_to_revenue)}.",
            f"SBC / CFO: {_pct(sbc_metric.get('sbc_to_operating_cash_flow') if sbc_metric else sbc_to_cfo)}.",
            f"Diluted shares YoY: {_pct(sbc_metric.get('diluted_shares_yoy') if sbc_metric else dilution)}.",
        ]

    if question_id == "financial.accounting_red_flags":
        verification_count = len((ctx.get("financial_pack") or {}).get("verification_results") or [])
        human_flags = len((ctx.get("financial_pack") or {}).get("human_review_flags") or [])
        material_events = ((ctx.get("financial_pack") or {}).get("material_event_scan") or {}).get("material_event_count")
        below_bridge = ((metrics.get("below_operating_bridge_v1") or {}).get("latest_interim_result") or {})
        investment_row = _bridge_metric_row(below_bridge, "investment_income")
        other_row = _bridge_metric_row(below_bridge, "other_income_net")
        tax_row = _bridge_metric_row(below_bridge, "tax_expense")
        answer = (
            f"No material event was promoted by the material-event scanner, but the report is not clean enough to skip review. "
            f"The pack records {human_flags} human-review flags and {verification_count} verification records. "
            f"In the latest quarter, operating income increased {_money_b(below_bridge.get('operating_income_delta'))}, "
            f"but net income decreased {_money_b(below_bridge.get('net_income_delta'))}; the upstream current-run below-operating bridge attributes the divergence mainly to below-operating items, especially other income/loss and investment income swings."
        )
        return answer, [
            f"Material events promoted: {material_events}.",
            f"Human-review flags: {human_flags}; verification records: {verification_count}.",
            f"Latest-quarter operating-income delta {_money_b(below_bridge.get('operating_income_delta'))} vs net-income delta {_money_b(below_bridge.get('net_income_delta'))}.",
            f"Investment-income delta: {_money_b(investment_row.get('delta'))}; other-income-net delta: {_money_b(other_row.get('delta'))}; tax-expense delta: {_money_b(tax_row.get('delta'))}.",
        ]

    return "Financial evidence exists, but no specific renderer has been configured for this question yet.", [
        "Add a question-specific financial renderer."
    ]


def _business_current_answer(question_id: str, ctx: dict[str, Any]) -> tuple[str, list[str]]:
    pack = ctx.get("business_model_unit_economics_pack") or {}
    summary = pack.get("summary") or {}
    revenue_streams = pack.get("revenue_streams") or []
    unit_proxies = pack.get("unit_economics_proxies") or []
    metrics = ctx.get("metrics_by_id") or {}
    if question_id == "business.competitive_position":
        return (
            "The new workflow does not yet have enough source-backed evidence to answer competitive position. "
            "This should route to competitor filings, public voice, app/traffic evidence, and merchant economics before any moat confidence is upgraded."
        ), [
            "Evidence count is currently zero for this question.",
            "Next action: collect competitor and external validation sources.",
        ]
    if question_id == "business.revenue_mechanism":
        streams = ", ".join(stream.get("stream_name", "unknown") for stream in revenue_streams[:3])
        return (
            f"{summary.get('preliminary_read') or 'The business model workpaper is partially available.'} "
            f"The current revenue-stream map identifies: {streams or 'not enough structured revenue streams'}."
        ), [
            f"Revenue streams mapped: {streams or 'none'}.",
            f"Coverage: {summary.get('coverage', 'unknown')}; confidence: {summary.get('confidence', 'unknown')}.",
        ]
    if question_id == "business.unit_economics":
        proxy = unit_proxies[0] if unit_proxies else {}
        roic = _latest_metric_result(metrics.get("unlevered_roic_v1") or {})
        incremental_roic = _latest_metric_result(metrics.get("incremental_roic_proxy_v1") or {})
        working_capital = _latest_metric_result(metrics.get("working_capital_quality_v1") or {})
        return (
            f"Direct unit economics remain limited. The current proxy is `{proxy.get('metric_name', 'not available')}`: "
            f"{_clean(proxy.get('summary')) or 'no proxy summary available'} "
            f"Upstream current-run metrics add an ROIC proxy of {_pct(roic.get('value'))}, an incremental ROIC proxy of {_pct(incremental_roic.get('value'))}, "
            f"and a working-capital cash tailwind of {_pct(working_capital.get('working_capital_cash_tailwind_to_revenue'))} of revenue."
        ), [
            f"Proxy quality: {proxy.get('quality', 'unknown')}.",
            f"ROIC proxy: {_pct(roic.get('value'))}; incremental ROIC proxy: {_pct(incremental_roic.get('value'))}.",
            f"Working-capital cash tailwind / revenue: {_pct(working_capital.get('working_capital_cash_tailwind_to_revenue'))}.",
            _clean(proxy.get("interpretation_limit")) or "Direct merchant/order economics still need source collection.",
        ]
    if question_id == "business.reinvestment_need":
        latest = ctx.get("latest_annual") or {}
        cap_intensity = _latest_metric_result(metrics.get("capital_intensity_v1") or {})
        incremental_roic = _latest_metric_result(metrics.get("incremental_roic_proxy_v1") or {})
        capex_to_revenue = cap_intensity.get("capex_to_revenue")
        if capex_to_revenue is None:
            capex_to_revenue = _safe_div(latest.get("capex"), latest.get("revenue"))
        return (
            f"Reported capex intensity is very low at company level: FY{latest.get('year')} capex was {_money_b(latest.get('capex'))}, "
            f"or {_pct(capex_to_revenue)} of revenue. Existing metrics also show FCF margin of {_pct(cap_intensity.get('free_cash_flow_margin'))} "
            f"and incremental ROIC proxy of {_pct(incremental_roic.get('value'))}. That supports an asset-light headline, but the negative incremental ROIC proxy means 2025 reinvestment quality should not be treated as proven."
        ), [
            f"Capex / revenue: {_pct(capex_to_revenue)}.",
            f"FCF margin: {_pct(cap_intensity.get('free_cash_flow_margin'))}; FCF / CFO: {_pct(cap_intensity.get('free_cash_flow_to_operating_cash_flow'))}.",
            f"Incremental ROIC proxy: {_pct(incremental_roic.get('value'))}.",
            "Maintenance versus growth capex is not disclosed as a structured fact.",
        ]
    if question_id == "pdd.temu_segment_opacity":
        return (
            "The workflow cannot yet separate Pinduoduo domestic economics from Temu/global expansion economics. "
            "That is a core disclosure gap, not a conclusion: Temu revenue, operating income, GMV and fulfillment cost are not available as structured standalone facts."
        ), [
            "Temu standalone economics remain a P0 gap.",
            "Do not treat consolidated margins as proof of Temu unit economics.",
        ]
    return (
        f"{summary.get('preliminary_read') or 'Business-model evidence exists, but this question needs a deeper workpaper.'}"
    ), ["Use BMUE evidence cards before converting this into a judgment."]


def _people_current_answer(question_id: str, ctx: dict[str, Any]) -> tuple[str, list[str]]:
    findings = ctx.get("leadership_findings") or {}
    decision = findings.get("right_people_decision") or {}
    control = findings.get("control_map") or {}
    incentive = findings.get("incentive_map") or {}
    capalloc = findings.get("capital_allocation_ledger") or {}
    communication = findings.get("communication_audit") or {}
    if question_id == "people.control_governance":
        return (
            f"Control and governance need review, not a pass. {', '.join(control.get('findings', [])[:2]) or 'Control map is not complete.'} "
            f"Controller table status: `{control.get('controller_table_status', 'unknown')}`."
        ), [
            f"Risk level: {control.get('risk_level', 'unknown')}.",
            f"Control gap: {control.get('control_gap', 'not extracted')}.",
        ]
    if question_id == "people.incentives":
        return (
            f"Incentive evidence is partial. {incentive.get('current_read') or 'SBC/dilution evidence exists but pay metrics are not fully parsed.'}"
        ), [
            *(incentive.get("positive_signals", [])[:2] or ["Positive signals not extracted."]),
            *(incentive.get("concerns_or_unknowns", [])[:1] or []),
        ]
    if question_id == "people.capital_allocation":
        return (
            f"Capital allocation is mixed. {capalloc.get('current_read') or 'The ledger exists but still needs analyst review.'}"
        ), [
            f"Ledger status: {capalloc.get('status', 'unknown')}.",
            f"Right-people gate status: {decision.get('status', 'unknown')}.",
        ]
    if question_id == "people.candor":
        return (
            f"Candor is not fully scored yet. {communication.get('current_read') or 'Promise-vs-outcome and Q&A evasiveness review are still incomplete.'}"
        ), [
            f"Communication audit status: {communication.get('status', 'unknown')}.",
            "Do not infer integrity from prepared remarks alone.",
        ]
    if question_id == "financial.dilution_sbc":
        return _financial_current_answer(question_id, ctx)
    return (
        f"Right People status is `{decision.get('status', 'unknown')}` with weighted score {decision.get('weighted_score', 'n/a')}."
    ), [
        decision.get("current_read", "Needs analyst review.")
    ]


def _risk_current_answer(question_id: str, ctx: dict[str, Any]) -> tuple[str, list[str]]:
    financial_pack = ctx.get("financial_pack") or {}
    material_scan = financial_pack.get("material_event_scan") or {}
    return (
        "Risk evidence is partially organized but not decision-ready. The material-event scanner found no promoted post-annual material events, "
        "but legal/regulatory risk still needs deeper source collection beyond the current financial/source-map pass."
    ), [
        f"Material event status: {material_scan.get('status', 'unknown')}.",
        f"High-priority events: {material_scan.get('high_priority_event_count', 0)}.",
        "Regulatory/legal workpaper should collect official external sources before confidence is upgraded.",
    ]


def _price_current_answer(question_id: str, ctx: dict[str, Any]) -> tuple[str, list[str]]:
    market = ctx.get("market_inputs") or {}
    metrics = ctx.get("metrics_by_id") or {}
    valuation = ctx.get("valuation_metrics_by_id") or {}
    enterprise = valuation.get("enterprise_value_v1") or {}
    owner_earnings = _latest_metric_result(metrics.get("owner_earnings_v1") or {})
    cap_intensity = _latest_metric_result(metrics.get("capital_intensity_v1") or {})
    if market.get("status") == "input_incomplete" or enterprise.get("status") != "calculated":
        missing = ", ".join(market.get("missing", []) or enterprise.get("missing", []) or [])
        return (
            f"Right Price is not ready in this run because reviewed market inputs are missing: {missing or 'market inputs'}. "
            f"The workflow has prepared owner-earnings and cash-flow facts, including owner earnings {_money_b(owner_earnings.get('value'))} "
            f"and FCF margin {_pct(cap_intensity.get('free_cash_flow_margin'))}, but it should not estimate return without market cap and FX."
        ), [
            f"Market input status: {market.get('status', 'unknown')}.",
            f"Enterprise value status: {enterprise.get('status', 'not run')}.",
            f"Owner earnings proxy: {_money_b(owner_earnings.get('value'))}; maintenance capex proxy: {_money_b(owner_earnings.get('maintenance_capex_proxy'))}.",
            f"FCF margin: {_pct(cap_intensity.get('free_cash_flow_margin'))}; capex / revenue: {_pct(cap_intensity.get('capex_to_revenue'))}.",
        ]
    return (
        "Valuation inputs are available, but scenario assumptions still need a dedicated Right Price workpaper."
    ), [
        f"Enterprise value status: {enterprise.get('status')}.",
    ]


def _answer_status(
    question_id: str,
    facts: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    inferences: list[dict[str, Any]],
    ctx: dict[str, Any],
) -> str:
    if not facts and not claims and not inferences:
        return "no_evidence"
    if question_id == "business.competitive_position":
        return "partial"
    if question_id in {"risk.regulatory_legal", "price.owner_return", "price.expectations", "pdd.temu_segment_opacity"}:
        return "partial"
    market = ctx.get("market_inputs") or {}
    if question_id.startswith("price.") and market.get("status") == "input_incomplete":
        return "partial"
    return "answered" if facts and inferences else "partial"


def _answer_evidence_ids(evidence_items: list[dict[str, Any]]) -> list[str]:
    def rank(item: dict[str, Any]) -> tuple[int, str]:
        source_type = str(item.get("source_type") or "")
        kind = str(item.get("evidence_kind") or "")
        if kind == "fact" and source_type == "current_financial_summary":
            return (-1, str(item.get("evidence_id")))
        if kind == "fact" and source_type != "source_metadata":
            return (0, str(item.get("evidence_id")))
        if kind == "inference":
            return (1, str(item.get("evidence_id")))
        if kind == "management_claim":
            return (2, str(item.get("evidence_id")))
        if kind == "fact":
            return (3, str(item.get("evidence_id")))
        return (4, str(item.get("evidence_id")))

    return [
        str(item["evidence_id"])
        for item in sorted(evidence_items, key=rank)
        if item.get("evidence_id")
    ][:12]


def _mechanism_explanations(theme: str, answers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if theme == "financial_reality":
        return [
            {
                "mechanism": "profit_to_cash_chain",
                "summary": "Connect revenue growth to margin, operating profit, working capital, and free cash flow before using valuation metrics.",
                "covered_question_ids": [answer["question_id"] for answer in answers if answer.get("evidence_ids")],
            }
        ]
    if theme == "business_model_unit_economics":
        return [
            {
                "mechanism": "business_model_to_financials_chain",
                "summary": "Connect how the company makes money to revenue mix, cost burden, merchant/customer economics, and reinvestment need.",
                "covered_question_ids": [answer["question_id"] for answer in answers if answer.get("evidence_ids")],
            }
        ]
    if theme == "risk_fragility":
        return [
            {
                "mechanism": "risk_source_to_survivability_chain",
                "summary": "Separate filed risk factors, material events, regulatory sources, litigation, and balance-sheet survivability before judging risk.",
                "covered_question_ids": [answer["question_id"] for answer in answers if answer.get("evidence_ids")],
            }
        ]
    if theme == "valuation_assumptions":
        return [
            {
                "mechanism": "owner_earnings_to_expected_return_chain",
                "summary": "Use financial evidence as inputs, then require reviewed market cap, FX, reinvestment, growth, and risk assumptions before estimating return.",
                "covered_question_ids": [answer["question_id"] for answer in answers if answer.get("evidence_ids")],
            }
        ]
    return [
        {
            "mechanism": "control_incentive_capital_allocation_chain",
            "summary": "Connect who controls the company to incentives, dilution, related-party risk, and per-share capital allocation.",
            "covered_question_ids": [answer["question_id"] for answer in answers if answer.get("evidence_ids")],
        }
    ]


def _theme_contradiction_checks(theme: str, answers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "question_id": answer["question_id"],
            "status": "checked" if answer.get("contradiction_checked") else "pending",
            "check": "Verify that facts, claims, and inferences do not point in opposite directions.",
            "reason": answer.get("what_could_be_wrong"),
        }
        for answer in answers
    ]


def _theme_unknowns(theme: str, answers: list[dict[str, Any]], registry_unknowns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unknowns = [
        {
            "question_id": answer["question_id"],
            "unknown": "No registry evidence yet.",
            "next_action": answer.get("next_step"),
        }
        for answer in answers
        if not answer.get("evidence_ids")
    ]
    if theme == "financial_reality":
        unknowns.extend([unknown for unknown in registry_unknowns if unknown.get("type") == "disclosure_gap"][:8])
    return unknowns


def _theme_handoff_questions(theme: str, answers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "question_id": answer["question_id"],
            "route": "source_map" if answer["status"] == "no_evidence" else "evidence_registry",
            "question": answer.get("next_step"),
        }
        for answer in answers
        if answer["status"] != "answered"
    ]


def _theme_preliminary_read(theme: str, answers: list[dict[str, Any]]) -> str:
    answered = sum(1 for answer in answers if answer["status"] == "answered")
    partial = sum(1 for answer in answers if answer["status"] == "partial")
    missing = sum(1 for answer in answers if answer["status"] == "no_evidence")
    return f"{answered} answered, {partial} partial, {missing} missing; not a final investment judgment."


def _source_tier_checks(evidence_registry: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    by_question: dict[str, set[int]] = defaultdict(set)
    for item in evidence_registry.get("evidence_items", []):
        for question_id in item.get("question_ids", []):
            tier = item.get("source_tier")
            if isinstance(tier, int):
                by_question[question_id].add(tier)
    for question_id, tiers in sorted(by_question.items()):
        checks.append(
            {
                "question_id": question_id,
                "source_tiers": sorted(tiers),
                "status": "pass" if 1 in tiers else "needs_tier1_source",
            }
        )
    return checks


def _gap_decisions(
    missing_p0: list[str],
    unsupported_claims: list[dict[str, Any]],
    missing_contradiction_checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    decisions = []
    for question_id in missing_p0:
        decisions.append(
            {
                "question_id": question_id,
                "gap_type": "missing_p0_evidence",
                "next_action": "extract_more_evidence",
                "reason": "P0 question lacks reusable evidence.",
            }
        )
    for claim in unsupported_claims[:20]:
        decisions.append(
            {
                "question_id": claim.get("question_id"),
                "gap_type": "unsupported_claim",
                "next_action": "collect_more_sources",
                "reason": "Question has no evidence-backed answer yet.",
            }
        )
    for check in missing_contradiction_checks[:20]:
        decisions.append(
            {
                "question_id": check.get("question_id"),
                "gap_type": "missing_contradiction_check",
                "next_action": "build_deeper_workpaper",
                "reason": "Contradiction checks are required before high confidence.",
            }
        )
    if not decisions:
        decisions.append(
            {
                "question_id": "workflow",
                "gap_type": "none_material_in_mvp",
                "next_action": "ready_for_pillar_judgment",
                "reason": "MVP evidence registry and QA checks are sufficient for a preliminary pillar stub.",
            }
        )
    return decisions


def _overall_next_action(decisions: list[dict[str, Any]]) -> str:
    priority = [
        "human_review_required",
        "collect_more_sources",
        "extract_more_evidence",
        "build_deeper_workpaper",
        "ready_for_pillar_judgment",
        "monitor",
        "stop",
    ]
    actions = {decision.get("next_action") for decision in decisions}
    for action in priority:
        if action in actions:
            return action
    return "monitor"


def _pillar_status(answer_by_id: dict[str, dict[str, Any]], required: list[str], flags: list[dict[str, Any]]) -> str:
    if any(flag.get("severity") == "high" for flag in flags):
        return "needs_more_work"
    required_answers = [answer_by_id.get(question_id) for question_id in required]
    answered = [answer for answer in required_answers if answer and answer.get("status") == "answered"]
    partial = [answer for answer in required_answers if answer and answer.get("status") == "partial"]
    if len(answered) == len(required):
        return "ready"
    if answered or partial:
        return "needs_more_work"
    return "not_ready"


def _evidence_item(
    *,
    evidence_id: str,
    question_ids: list[str],
    source_id: str,
    source_tier: int,
    source_type: str,
    locator: str,
    evidence_kind: str,
    excerpt: str,
    structured_fact: dict[str, Any],
    confidence: str,
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "question_ids": sorted(set(question_ids)),
        "source_id": source_id,
        "source_tier": source_tier,
        "source_type": source_type,
        "locator": locator,
        "evidence_kind": evidence_kind,
        "excerpt": excerpt,
        "structured_fact": structured_fact,
        "supports": sorted(set(question_ids)),
        "contradicts": [],
        "confidence": _normalize_confidence(confidence),
        "requires_human_review": evidence_kind == "inference" and _normalize_confidence(confidence) == "low",
    }


def _question_ids_for_metric(metric: str) -> list[str]:
    text = metric.casefold()
    mapping = [
        ("revenue", ["financial.growth", "financial.revenue_sources", "business.revenue_mechanism"]),
        ("gross", ["financial.margin_conversion"]),
        ("operating_income", ["financial.margin_conversion"]),
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
    ]
    result: list[str] = []
    for needle, questions in mapping:
        if needle in text:
            result.extend(questions)
    return sorted(set(result or ["financial.accounting_red_flags"]))


def _legacy_question_refs_to_decision_questions(refs: list[Any]) -> list[str]:
    mapping = {
        "Q1": "financial.margin_conversion",
        "Q2": "financial.margin_conversion",
        "Q3": "financial.cash_conversion",
        "Q4": "financial.balance_sheet",
        "Q5": "business.reinvestment_need",
        "Q6": "financial.revenue_sources",
        "Q7": "business.unit_economics",
        "Q8": "financial.accounting_red_flags",
        "Q9": "financial.dilution_sbc",
    }
    return sorted({mapping.get(str(ref), str(ref)) for ref in refs if mapping.get(str(ref), str(ref))})


def _infer_questions_from_text(text: str) -> list[str]:
    lowered = text.casefold()
    result = []
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
    for keywords, question_id in keyword_map:
        if any(keyword in lowered for keyword in keywords):
            result.append(question_id)
    return sorted(set(result))


def _business_question_ids(answer: dict[str, Any]) -> list[str]:
    text = " ".join(
        str(answer.get(key) or "")
        for key in ["question_id", "id", "question", "answer", "current_answer", "summary", "topic"]
    )
    inferred = _infer_questions_from_text(text)
    business = [question_id for question_id in inferred if question_id.startswith("business.") or question_id.startswith("pdd.")]
    return business or ["business.revenue_mechanism"]


def _looks_like_management_claim(answer: dict[str, Any]) -> bool:
    text = str(answer).casefold()
    return any(token in text for token in ["management", "ceo", "cfo", "said", "claim", "believe", "expect"])


def _fact_excerpt(fact: dict[str, Any]) -> str:
    value = fact.get("value")
    metric = fact.get("canonical_metric") or fact.get("metric")
    period = fact.get("period_label") or fact.get("period_year") or fact.get("end_date") or fact.get("instant")
    unit = fact.get("unit") or fact.get("currency")
    return f"{metric} = {value} {unit or ''} for {period}".strip()


def _what_could_be_wrong(question_id: str, status: str, contradiction_checked: bool) -> str:
    if status == "no_evidence":
        return "The answer may be absent because the source was not collected or the extractor did not map this field yet."
    if not contradiction_checked:
        return "The evidence exists, but opposing evidence has not been checked enough for high confidence."
    financial_caveats = {
        "financial.growth": (
            "The growth answer can overstate business quality because it uses consolidated revenue. It may miss whether growth came from "
            "Pinduoduo, Temu, pricing, order volume, merchant fees, or geography because those drivers are not always separately disclosed in tagged tables."
        ),
        "financial.revenue_sources": (
            "The revenue-source answer can identify online marketing and transaction-services mix, but it may not explain the true economic source of growth. "
            "The missing checks are segment/geography split, Temu versus domestic platform contribution, GMV or order-volume drivers, and merchant take-rate changes."
        ),
        "financial.margin_conversion": (
            "The margin answer may be too coarse because cost of revenue and operating expenses are aggregated. The items to check manually are fulfillment, "
            "payment processing, server and bandwidth, merchant support, platform governance, advertising subsidy, and any reclassification in the expense footnotes."
        ),
        "financial.cash_conversion": (
            "The cash-conversion answer may treat working-capital float as owner cash. The key manual checks are merchant deposits, payables to merchants, "
            "settlement timing, restricted cash, deferred revenue, and whether free cash flow would weaken if supplier or merchant payment terms normalize."
        ),
        "financial.balance_sheet": (
            "The balance-sheet answer may overstate distributable cash. The key manual checks are restricted cash purpose, funds held for merchant settlement, "
            "cash trapped in PRC or VIE entities, short-term investment liquidity, transfer restrictions, and any pledge or guarantee footnotes."
        ),
        "financial.dilution_sbc": (
            "The dilution/SBC answer may miss off-table dilution. The key manual checks are ADS-to-ordinary-share conversion, unvested awards, equity-plan reserve, "
            "new grants after period end, repurchase offset, and whether SBC is excluded from non-GAAP profit while diluted shares still rise."
        ),
        "financial.accounting_red_flags": (
            "The accounting-red-flag answer may miss issues that do not appear as a material event. The key manual checks are below-operating-line swings, "
            "investment income, other income/loss, tax rate changes, related-party notes, auditor language, internal-control disclosures, and recurring non-GAAP adjustments."
        ),
    }
    if question_id in financial_caveats:
        return financial_caveats[question_id]
    if question_id.startswith("financial."):
        return "The financial answer may be incomplete until the relevant footnotes, non-tagged tables, and management discussion are mapped to this question."
    if question_id.startswith("business."):
        return "Management's description may not reveal segment-level unit economics."
    if question_id.startswith("people."):
        return "Governance evidence may require ownership and compensation tables not yet parsed."
    return "Assumptions may depend on later source collection."


def _answer_next_step(question_id: str, status: str, contradiction_checked: bool) -> str:
    if status == "no_evidence":
        return "Collect or parse the preferred source types from the evidence plan."
    if not contradiction_checked:
        return "Run contradiction checks before upgrading confidence."
    if question_id.startswith("price."):
        return "Route to Right Price / Valuation Agent for scenario work."
    return "Ready for deeper theme workpaper review."


def _source_aliases(source_map: dict[str, Any]) -> set[str]:
    aliases = {
        "financial_report_pack",
        "filing_deep_read_pack",
        "financial_metrics",
        "financial_verification",
        "layer1_question_pack",
        "evidence_communication_pack",
        "business_model_unit_economics_pack",
        "business_model_evidence_pack",
        "official_report_evidence_pack",
        "leadership_findings",
        "valuation_metrics",
    }
    for row in source_map.get("source_inventory", []):
        aliases.add(str(row.get("source_id")))
        aliases.update(str(alias) for alias in row.get("alias_source_ids", []) if alias)
        if row.get("local_path"):
            aliases.add(str(row.get("local_path")))
        if row.get("parent_source_id"):
            aliases.add(str(row.get("parent_source_id")))
    return aliases


def _best_source_id(candidates: list[Any], source_aliases: set[str]) -> str:
    for candidate in candidates:
        if not candidate:
            continue
        value = str(candidate)
        if value in source_aliases:
            return value
        name = Path(value).name
        if name in source_aliases:
            return name
    for candidate in candidates:
        if candidate:
            return str(candidate)
    return "unknown_source"


def _normalize_source_type(value: Any) -> str:
    text = str(value or "unknown")
    upper = text.upper()
    for form in ["20-F", "10-K", "10-Q", "6-K", "8-K", "CORRESP", "F-1", "424B4"]:
        if form in upper:
            return form
    if "ANNUAL" in upper:
        return "annual_report"
    if "EARNINGS" in upper:
        return "earnings_release"
    if "INVESTOR" in upper:
        return "investor_presentation"
    if "SEC" in upper:
        return "sec_filing"
    if "HKEX" in upper:
        return "hkex_disclosure"
    return text.lower().replace(" ", "_")


def _source_group(source_type: str) -> str:
    if source_type in {"20-F", "10-K", "10-Q", "6-K", "8-K", "annual_report", "earnings_release", "sec_filing", "hkex_disclosure"}:
        return "official_company_or_regulator"
    if source_type in {"CORRESP", "court_or_regulatory_record"}:
        return "official_external"
    if source_type in {"google_trends", "youtube", "reddit", "app_store", "ecommerce_crawler"}:
        return "market_alternative_data"
    return "third_party_or_other"


def _rights_status(source_tier: int, source_type: str) -> str:
    if source_tier == 1:
        return "official_source_for_research"
    if source_tier == 2:
        return "official_external_or_sanity_check"
    if source_tier == 3:
        return "alternative_data_lead_only"
    return "third_party_opinion_lead_only"


def _is_official_document(document: dict[str, Any]) -> bool:
    text = " ".join(str(document.get(key) or "") for key in ["source_id", "document_type", "source_url"]).casefold()
    return any(token in text for token in ["sec", "edgar", "investor", "ir", "hkex", "20-f", "10-k", "6-k"])


def _sections_for_document(document: dict[str, Any]) -> list[str]:
    source_type = _normalize_source_type(document.get("document_type"))
    if source_type in {"20-F", "10-K", "annual_report"}:
        return ["business", "risk_factors", "md&a", "financial_statements", "footnotes", "governance"]
    if source_type in {"6-K", "10-Q", "earnings_release"}:
        return ["financial_results", "management_commentary", "financial_statements"]
    if source_type == "CORRESP":
        return ["regulatory_correspondence"]
    return ["metadata"]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_id(value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"src_{digest}"


def _normalize_confidence(value: str) -> str:
    text = str(value or "medium").casefold()
    if "high" in text:
        return "high"
    if "low" in text or "weak" in text:
        return "low"
    return "medium"


def _md(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ")


ENGLISH_REPORT_TRANSLATIONS = {
    "增量经营利润率为负，新增收入没有带来新增经营利润。": (
        "Incremental operating margin is negative; incremental revenue did not translate into incremental operating profit."
    ),
    "官方数字显示交易服务已成为最新季度最大收入组件，这会改变对收入来源的读法，但不能单独证明增长质量。": (
        "Official figures show transaction services became the largest latest-quarter revenue component; this changes the reading of revenue sources but does not by itself prove growth quality."
    ),
    "官方文件中出现相关叙事，V1 将其登记为需要后续跟踪的决策相关信息。": (
        "Official filings contain this narrative; V1 registers it as decision-relevant information that needs follow-up tracking."
    ),
    "供应链和商家支持叙事可解释部分利润率压力，但需要用费用率、现金流和后续季度结果继续验证。": (
        "Supply-chain and merchant-support narratives may explain part of the margin pressure, but expense ratios, cash flow, and later quarterly results still need verification."
    ),
    "受限现金和 VIE 叙事会影响现金安全垫读法，账面现金不能自动视为可自由分配现金。": (
        "Restricted cash and VIE disclosures affect the cash-buffer reading; reported cash should not be treated automatically as freely distributable cash."
    ),
    "AGM / proxy 材料提供治理事实：它能说明董事重选和 ADS 投票机制，但不能单独证明治理质量。": (
        "AGM / proxy materials provide governance facts about director reelection and ADS voting mechanics, but they do not by themselves prove governance quality."
    ),
    "股权计划期限延长会拉长激励工具的可用期；当前还需要和 SBC、稀释、回购抵消情况一起判断。": (
        "The equity-plan term extension lengthens the period during which incentive instruments can be used; it still needs to be evaluated together with SBC, dilution, and buyback offsets."
    ),
    "自营品牌业务是官方叙事中的战略举措，可能改变平台轻重和供应链控制深度；投入回报仍需验证。": (
        "The first-party brand business is a strategic initiative in official communication; it may change asset intensity and supply-chain control depth, while investment returns remain unverified."
    ),
    "管理层把安全、合规和社会责任称为一切工作的前提，并具体提到第一季度推出 20 多项食品安全治理措施，包括资质审核、食品广告和直播监测、食品数据库、举报渠道和自动/人工巡检。": (
        "Management describes safety, compliance, and social responsibility as prerequisites, and cites more than 20 food-safety governance measures launched in Q1, including qualification reviews, ad and livestream monitoring, food databases, reporting channels, and automated/manual inspections."
    ),
    "管理层把 2026Q1 定义为三年战略的第一个完整季度，核心抓手是 first-party brand、供应链投入和 RMB 100B 支持计划。这说明 2025 年以来的利润率压力不是单季偶发，而是管理层主动选择的投入周期。": (
        "Management frames 2026Q1 as the first full quarter of the three-year strategy, centered on first-party brands, supply-chain investment, and the RMB 100B support program; this suggests margin pressure since 2025 is an intentional investment cycle rather than a single-quarter accident."
    ),
    "管理层反复把 PDD 的下一阶段竞争优势定义为供应链能力，而不是单纯流量、营销或用户增长。first-party brand 被描述为平台更主动参与产品开发、标准、质量、履约、合规和客服的机制。": (
        "Management repeatedly defines PDD's next-stage competitive advantage as supply-chain capability rather than only traffic, marketing, or user growth; first-party brands are described as a mechanism for deeper platform participation in product development, standards, quality, fulfillment, compliance, and customer service."
    ),
    "在被直接问到长期稳定利润率时，CFO 没有给出利润率区间或时间表，而是强调季节性、投资周期、长期内在价值和供应链能力积累。": (
        "When directly asked about long-term stable margins, the CFO did not provide a margin range or timeline, and instead emphasized seasonality, the investment cycle, long-term intrinsic value, and supply-chain capability building."
    ),
    "管理层用中山灯具到甘肃的运费案例、河南县域进村配送案例和远程地区物流补贴解释增长机制：平台通过承担转运成本，把部分偏远地区纳入包邮区，从而扩大需求和商家订单。": (
        "Management explains the growth mechanism through examples such as Zhongshan lighting shipped to Gansu, county-level delivery in Henan, and remote-region logistics subsidies: the platform absorbs some transfer costs to expand free-shipping coverage, demand, and merchant orders."
    ),
}


def _report_md(value: Any) -> str:
    text = _english_report_text(value)
    return _md(text)


def _english_report_text(value: Any) -> str:
    text = str(value if value is not None else "")
    return _apply_known_english_translations(text)


def _apply_known_english_translations(text: str) -> str:
    translated = text
    for source, replacement in ENGLISH_REPORT_TRANSLATIONS.items():
        translated = translated.replace(source, replacement)
    for source, replacement in ENGLISH_TERM_TRANSLATIONS.items():
        translated = translated.replace(source, replacement)
    return translated


ENGLISH_TERM_TRANSLATIONS = {
    "收入增长来自哪里？增长质量好吗？": "Where does revenue growth come from, and is the growth quality good?",
    "增长需要消耗多少资本？资本效率有没有变差？": "How much capital does growth consume, and is capital efficiency deteriorating?",
    "这个公司赚的钱是真钱吗？现金流质量好不好？": "Are the company's earnings real cash earnings, and is cash-flow quality good?",
    "规模变大以后利润率是上升还是下降？": "Do margins rise or fall as the company scales?",
    "增长有没有被股权激励和稀释吃掉？": "Is growth being consumed by share-based compensation and dilution?",
    "税率、非 GAAP 调整和会计项目有没有让利润看起来更好？": "Do tax rate, non-GAAP adjustments, or accounting items make profit look better?",
    "资产负债表风险大不大？公司能不能扛住坏年份？": "How large is balance-sheet risk, and can the company withstand bad years?",
    "下个季度先看增量经营利润率是否从负转正，并拆费用率、商家支持和供应链投入。": (
        "Next quarter, first check whether incremental operating margin turns positive, and break down expense ratios, merchant support, and supply-chain investment."
    ),
    "商家分群 / 单商家经济性": "merchant segmentation / single-merchant economics",
    "继续验证收入结构、商家经济性和投入回报是否改善。": "Continue verifying whether revenue mix, merchant economics, and investment returns improve.",
    "把费用率、成本率和官方投入叙事连续跟踪到下一期。": "Track expense ratios, cost ratios, and official investment narratives into the next period.",
    "应收账款": "accounts receivable",
    "存货": "inventory",
    "拆营运资本来源，确认现金流是否依赖商家相关负债和结算周期。": "Break down working-capital sources to determine whether cash flow depends on merchant-related liabilities and settlement timing.",
    "维护性资本开支与增长性资本开支拆分": "maintenance capex versus growth capex split",
    "区分维护性资本开支、增长性投入、供应链投入和品牌投入。": "Separate maintenance capex, growth investment, supply-chain investment, and brand investment.",
    "长期债务": "long-term debt",
    "回查受限现金、VIE 资金转移、债务到期和可用现金口径。": "Review restricted cash, VIE fund transferability, debt maturities, and usable-cash definitions.",
    "回购是否抵消股权激励稀释": "whether buybacks offset equity-incentive dilution",
    "完整 ADS / 普通股稀释桥": "complete ADS / ordinary-share dilution bridge",
    "确认回购是否抵消股权激励稀释，并补完整 ADS / 普通股桥。": "Verify whether repurchases offset equity-incentive dilution and complete the ADS / ordinary-share bridge.",
    "现金纳税": "cash taxes paid",
    "减值项目": "impairment items",
    "拆非 GAAP 调整、投资收益、税率调节和关键会计估计。": "Break down non-GAAP adjustments, investment income, tax-rate reconciliation, and critical accounting estimates.",
    "全年业务线结构是否稳定披露": "whether full-year business-line structure is consistently disclosed",
    "交易服务收入增长的价格/量/服务拆分": "price / volume / service split for transaction-services revenue growth",
    "继续跟踪交易服务与在线营销收入占比。": "Continue tracking transaction-services and online-marketing revenue mix.",
    "是否承担库存风险": "whether inventory risk is assumed",
    "单独收入、利润和投入回收期": "standalone revenue, profit, and investment payback period",
    "在业绩电话会和后续 6-K 中追问自营品牌业务的资本需求和利润影响。": "Ask in earnings calls and later 6-Ks about the capital needs and profit impact of the first-party brand business.",
    "商家支持的金额与持续性": "amount and durability of merchant support",
    "投入能否转化为利润率修复": "whether investment can translate into margin recovery",
    "跟踪费用率、履约成本、商家支持和经营现金流是否随投入改善。": "Track whether expense ratios, fulfillment costs, merchant support, and operating cash flow improve with investment.",
    "Temu 单独收入、利润、GMV 和履约成本": "Temu standalone revenue, profit, GMV, and fulfillment costs",
    "全球业务 / Temu": "global business / Temu",
    "需要第三层跟踪管理层对海外业务、合规和履约成本的解释。": "Layer 3 should track management explanations of overseas business, compliance, and fulfillment costs.",
    "现金可转移性和 VIE 结构下的实际分配能力": "cash transferability and actual distribution capacity under the VIE structure",
    "回到年报附注和 VIE 风险因素，确认现金可用性和资金转移限制。": "Return to annual-report notes and VIE risk factors to verify cash availability and fund-transfer restrictions.",
    "变化对执行质量和资本配置纪律的影响": "impact of changes on execution quality and capital-allocation discipline",
    "检查相关 6-K / 代理声明 / 股东会文件是否披露职责、薪酬或控制权变化。": "Check relevant 6-K / proxy / shareholder-meeting documents for changes in responsibilities, compensation, or control.",
    "ADS 持有人实际投票参与情况": "actual ADS-holder voting participation",
    "下一次 AGM 是否继续出现较高反对票": "whether the next AGM still shows high opposition votes",
    "是否出现治理争议": "whether governance disputes appear",
    "跟踪 AGM 投票结果、董事重选反对率和 ADS voting instruction 机制是否影响少数股东权利。": "Track AGM voting results, director-reelection opposition rates, and whether ADS voting-instruction mechanics affect minority-owner rights.",
    "剩余可授予股份": "remaining shares available for grants",
    "未来 SBC 强度": "future SBC intensity",
    "回购是否抵消激励稀释": "whether buybacks offset incentive dilution",
    "把股权计划期限延长与 SBC / 收入、SBC / 经营现金流、稀释股数和回购桥表一起跟踪。": "Track the equity-plan term extension together with SBC / revenue, SBC / operating cash flow, diluted shares, and the buyback bridge.",
    "关键审计事项的敏感性和后续变化": "sensitivity and subsequent changes in key audit matters",
    "跟踪审计师、ICFR、关键审计事项和会计估计是否变化。": "Track changes in the auditor, ICFR, key audit matters, and accounting estimates.",
    "补自营品牌单位经济性和库存风险。": "Add first-party brand unit economics and inventory-risk evidence.",
    "补成本细项抽取。": "Add detailed cost-line extraction.",
    "补维护性/增长性资本开支拆分。": "Add maintenance / growth capex split.",
    "补充 usable_cash_and_vie_transferability。": "Add usable_cash_and_vie_transferability.",
    "如果官方后续披露，补充：": "If later official disclosures provide it, add: ",
    "履约成本": "fulfillment costs",
    "品牌业务的收入和利润披露": "brand-business revenue and profit disclosure",
    "三年后利润率框架": "three-year margin framework",
    "利润率底部": "margin floor",
    "投资强度峰值": "peak investment intensity",
    "交易服务收入与收入结构": "transaction-services revenue and revenue mix",
    "自营品牌业务": "first-party brand business",
    "供应链投入与商家支持": "supply-chain investment and merchant support",
    "受限现金、VIE 与资金可转移性": "restricted cash, VIE, and fund transferability",
    "2015 Global Share Plan 期限延长": "2015 Global Share Plan term extension",
    "从轻平台叙事转向更深供应链组织者": "shift from an asset-light platform narrative to a deeper supply-chain organizer",
    "库存风险": "inventory risk",
    "三年“再造一个拼多多”进入执行期": "three-year 'build another Pinduoduo' plan entering execution",
    "投入回收期": "investment payback period",
    "投入项目的 KPI": "investment-project KPIs",
    "管理层没有给稳定利润率目标": "management did not provide a stable-margin target",
    "恢复时间表": "recovery timeline",
    "商家广告投资回报": "merchant advertising ROI",
    "费用化节奏": "expense-recognition timing",
    "投资回报": "investment return",
    "利润率是否有内部目标或底部": "whether margins have an internal target or floor",
    "利润压力中有多少来自竞争、有多少来自主动投入": "how much margin pressure comes from competition versus intentional investment",
    "应收、预付、存货、应付、商家保证金、递延收入完整桥": "complete working-capital bridge across receivables, prepayments, inventory, payables, merchant deposits, and deferred revenue",
    "受限现金性质": "restricted-cash nature",
    "在线营销收入拆分": "online-marketing revenue breakdown",
    "履约/退货成本": "fulfillment / return costs",
    "投资收益": "investment income",
    "税项": "tax items",
    "权益法投资": "equity-method investments",
    "回购是否抵消 SBC": "whether buybacks offset SBC",
    "补经营利润桥和费用率完整桥。": "Add operating-profit bridge and complete expense-ratio bridge.",
    "补充 working_capital_bridge。": "Add working_capital_bridge.",
    "补充 below_operating_bridge。": "Add below_operating_bridge.",
    "补充 share_count_and_capital_return_bridge。": "Add share_count_and_capital_return_bridge.",
    "广告 take-rate": "advertising take rate",
}


def _english_safe_artifact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _english_safe_artifact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_english_safe_artifact(item) for item in value]
    if isinstance(value, tuple):
        return [_english_safe_artifact(item) for item in value]
    if isinstance(value, str):
        translated = _apply_known_english_translations(value)
        if not _contains_cjk(translated):
            return translated
        digest = hashlib.sha1(translated.encode("utf-8")).hexdigest()[:10]
        return f"Non-English generated free text omitted from English workflow artifact. original_text_sha1={digest}"
    return value


def _ensure_english_report(report: str) -> str:
    translated = _apply_known_english_translations(report)
    lines = []
    previous_line = None
    for line in translated.splitlines():
        if _contains_cjk(line):
            if line.startswith("- `") and ": " in line:
                prefix = line.split(": ", 1)[0]
                line = (
                    f"{prefix}: Non-English generated excerpt omitted from the English report; "
                    "see the structured JSON artifact for the original text."
                )
            elif line.startswith("- "):
                line = "- Non-English generated text omitted from the English report; see the structured JSON artifact for the original text."
            else:
                line = "Non-English generated text omitted from the English report; see the structured JSON artifact for the original text."
        if line == previous_line and "Non-English generated" in line:
            continue
        lines.append(line)
        previous_line = line
    return "\n".join(lines)


def _contains_cjk(text: str) -> bool:
    return any("\u3400" <= char <= "\u9fff" for char in str(text))
