from __future__ import annotations

from collections import Counter
from typing import Any

from stock_research.research_workflow.models import (
    make_evidence_item,
    make_gap_request,
    make_source_ref,
    question_ids_for_metric,
    stable_id,
)
from stock_research.state import ResearchState, utc_now_iso


FINANCIAL_ADAPTER_SCHEMA_VERSION = "financial_workflow_evidence_adapter_v1"


def build_financial_workflow_evidence(state: ResearchState) -> dict[str, Any]:
    """Convert FinancialReportPack internals into workflow evidence.

    This is intentionally code-level glue over the financial extraction pack:
    the research workflow should not manually rediscover fact-ledger, formula,
    verification, and human-review semantics inside artifacts.py.
    """

    pack = state.get("financial_report_pack") or {}
    items: list[dict[str, Any]] = []
    source_refs = _source_refs(pack)
    gap_requests = _gap_requests(pack)
    quality_flags = _quality_flags(pack)

    items.extend(_current_snapshot_cards(pack))
    items.extend(_metric_cards(pack))
    items.extend(_fact_ledger_cards(pack))
    items.extend(_verification_cards(pack))
    items.extend(_diagnostic_cards(pack))

    question_counts = Counter()
    for item in items:
        for question_id in item.get("question_ids", []):
            question_counts[question_id] += 1

    return {
        "schema_version": FINANCIAL_ADAPTER_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "source_artifact": "financial_report_pack",
        "source_artifact_path": state.get("financial_report_pack_path"),
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
            source_id="financial_report_pack",
            source_type="financial_report_pack",
            source_tier=1,
            locator="financial_report_pack.json",
            title="Financial Report Pack",
            reliability="derived_from_official_filings",
            metadata={
                "schema_version": pack.get("schema_version"),
                "fact_count": len(pack.get("fact_ledger") or []),
                "metric_family_count": len(pack.get("financial_metrics") or []),
            },
        )
    ]
    seen = {"financial_report_pack"}
    for fact in pack.get("fact_ledger") or []:
        source_id = str(fact.get("source_document") or fact.get("accession_number") or fact.get("local_path") or "")
        if not source_id or source_id in seen:
            continue
        seen.add(source_id)
        refs.append(
            make_source_ref(
                source_id=source_id,
                source_type=str(fact.get("source_document_type") or "official_financial_filing"),
                source_tier=1,
                locator=str(fact.get("local_path") or fact.get("source_table") or ""),
                title=source_id,
                reliability="official_filing_fact",
                metadata={
                    "accession_number": fact.get("accession_number"),
                    "filing_date": fact.get("filing_date"),
                    "report_date": fact.get("report_date"),
                },
            )
        )
    return refs


def _current_snapshot_cards(pack: dict[str, Any]) -> list[dict[str, Any]]:
    annual_rows = sorted(pack.get("annual_facts") or [], key=lambda row: row.get("year") or 0)
    quarterly_rows = sorted(pack.get("quarterly_facts") or [], key=lambda row: str(row.get("period_end") or row.get("quarter") or ""))
    if not annual_rows and not quarterly_rows:
        return []

    latest = annual_rows[-1] if annual_rows else {}
    prior = annual_rows[-2] if len(annual_rows) > 1 else {}
    latest_q = quarterly_rows[-1] if quarterly_rows else {}
    prior_q = _same_quarter_prior_year(latest_q, quarterly_rows)

    cards = [
        (
            "FA-SUPPORT-001",
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
            "FA-SUPPORT-002",
            ["financial.revenue_sources", "business.revenue_mechanism"],
            "latest_revenue_mix_snapshot",
            (
                f"FY{latest.get('year')} online marketing/services {_money_b(latest.get('online_marketing_services_revenue'))}; "
                f"transaction services {_money_b(latest.get('transaction_services_revenue'))}; "
                f"latest quarter online marketing/services {_money_b(latest_q.get('online_marketing_services_revenue'))}; "
                f"transaction services {_money_b(latest_q.get('transaction_services_revenue'))}."
            ),
            {
                "latest_annual": _pick_keys(latest, ["year", "revenue", "online_marketing_services_revenue", "transaction_services_revenue"]),
                "latest_quarter": _pick_keys(latest_q, ["quarter", "period_end", "revenue", "online_marketing_services_revenue", "transaction_services_revenue"]),
            },
        ),
        (
            "FA-SUPPORT-003",
            ["financial.margin_conversion", "business.unit_economics"],
            "latest_margin_snapshot",
            (
                f"FY{latest.get('year')} gross profit {_money_b(latest.get('gross_profit'))}; "
                f"operating income {_money_b(latest.get('operating_income'))}; latest quarter operating income {_money_b(latest_q.get('operating_income'))}."
            ),
            {
                "latest_annual": _pick_keys(latest, ["year", "revenue", "gross_profit", "operating_income", "net_income"]),
                "prior_annual": _pick_keys(prior, ["year", "revenue", "gross_profit", "operating_income", "net_income"]),
                "latest_quarter": _pick_keys(latest_q, ["quarter", "period_end", "revenue", "gross_profit", "operating_income", "net_income"]),
            },
        ),
        (
            "FA-SUPPORT-004",
            ["financial.cash_conversion", "price.owner_return"],
            "latest_cash_conversion_snapshot",
            (
                f"FY{latest.get('year')} operating cash flow {_money_b(latest.get('operating_cash_flow'))}; "
                f"FCF {_money_b(latest.get('free_cash_flow'))}; capex {_money_b(latest.get('capex'))}."
            ),
            {
                "latest_annual": _pick_keys(latest, ["year", "net_income", "operating_cash_flow", "free_cash_flow", "capex"]),
                "prior_annual": _pick_keys(prior, ["year", "net_income", "operating_cash_flow", "free_cash_flow", "capex"]),
                "latest_quarter": _pick_keys(latest_q, ["quarter", "period_end", "net_income", "operating_cash_flow"]),
            },
        ),
        (
            "FA-SUPPORT-005",
            ["financial.balance_sheet", "risk.regulatory_legal", "price.expectations"],
            "latest_balance_sheet_snapshot",
            (
                f"FY{latest.get('year')} cash {_money_b(latest.get('cash'))}; restricted cash {_money_b(latest.get('restricted_cash'))}; "
                f"short-term investments {_money_b(latest.get('short_term_investments'))}; debt {_money_b(latest.get('debt'))}."
            ),
            {
                "latest_annual": _pick_keys(
                    latest,
                    ["year", "cash", "restricted_cash", "short_term_investments", "current_assets", "current_liabilities", "total_assets", "total_liabilities", "debt"],
                ),
                "latest_quarter": _pick_keys(
                    latest_q,
                    ["quarter", "period_end", "cash", "restricted_cash", "short_term_investments", "current_assets", "current_liabilities", "total_assets", "total_liabilities"],
                ),
            },
        ),
        (
            "FA-SUPPORT-006",
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
    ]
    return [
        make_evidence_item(
            evidence_id=evidence_id,
            question_ids=question_ids,
            source_id="financial_report_pack",
            source_tier=1,
            source_type="financial_snapshot",
            locator=locator,
            evidence_kind="filed_fact",
            excerpt=excerpt,
            structured_fact=structured_fact,
            confidence="high",
            upstream_refs=[{"upstream_artifact": "financial_report_pack", "locator": locator}],
        )
        for evidence_id, question_ids, locator, excerpt, structured_fact in cards
    ]


def _metric_cards(pack: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    for metric in pack.get("financial_metrics") or []:
        formula_id = str(metric.get("formula_id") or metric.get("metric_id") or "")
        if not formula_id:
            continue
        latest = _latest_metric_result(metric)
        latest_interim = metric.get("latest_interim_result") or {}
        if not latest and not latest_interim:
            continue
        excerpt = _metric_excerpt(formula_id, latest, latest_interim)
        cards.append(
            make_evidence_item(
                evidence_id=f"FA-METRIC-{len(cards) + 1:03d}",
                question_ids=_questions_for_formula(formula_id),
                source_id="financial_report_pack",
                source_tier=1,
                source_type="deterministic_financial_metric",
                locator=formula_id,
                evidence_kind="system_inference",
                excerpt=excerpt,
                structured_fact={"formula_id": formula_id, "latest_annual_result": latest, "latest_interim_result": latest_interim},
                confidence="high" if metric.get("review_required") is not True else "medium",
                upstream_refs=[{"upstream_artifact": "financial_report_pack", "formula_id": formula_id}],
            )
        )
    return cards


def _fact_ledger_cards(pack: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    for fact in _prioritized_financial_facts(pack.get("fact_ledger") or [])[:500]:
        metric = str(fact.get("canonical_metric") or fact.get("metric") or "")
        fact_id = str(fact.get("fact_id") or stable_id("fact", fact))
        cards.append(
            make_evidence_item(
                evidence_id=f"FA-FACT-{len(cards) + 1:04d}",
                question_ids=question_ids_for_metric(metric),
                source_id=str(fact.get("source_document") or fact.get("accession_number") or "financial_report_pack"),
                source_tier=1,
                source_type=str(fact.get("source_document_type") or "official_financial_fact"),
                locator=str(fact.get("xbrl_tag") or fact.get("source_table") or fact.get("context_ref") or fact_id),
                evidence_kind=_fact_evidence_kind(fact),
                excerpt=_fact_excerpt(fact),
                structured_fact=fact,
                confidence="high" if fact.get("confidence") in {None, "high"} else "medium",
                upstream_refs=[
                    {
                        "upstream_artifact": "financial_report_pack",
                        "upstream_fact_id": fact.get("fact_id"),
                        "source_document": fact.get("source_document"),
                        "source_table": fact.get("source_table"),
                        "xbrl_tag": fact.get("xbrl_tag"),
                        "context_ref": fact.get("context_ref"),
                    }
                ],
            )
        )
    return cards


def _verification_cards(pack: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for record in pack.get("verification_results") or []:
        status = str(record.get("status") or "")
        if status not in {"material_conflict", "accepted_rounding_difference"}:
            continue
        items.append(
            make_evidence_item(
                evidence_id=f"FA-VERIFY-{len(items) + 1:03d}",
                question_ids=["financial.accounting_red_flags"],
                source_id="financial_report_pack",
                source_tier=1,
                source_type="financial_verification_record",
                locator=str(record.get("metric") or record.get("canonical_metric") or status),
                evidence_kind="system_inference",
                excerpt=f"Financial verification status {status}: {record.get('metric') or record.get('canonical_metric')}.",
                structured_fact=record,
                confidence="medium",
                upstream_refs=[{"upstream_artifact": "financial_report_pack", "verification_record_id": record.get("verification_id") or stable_id("verification", record)}],
                requires_human_review=status == "material_conflict",
            )
        )
    for flag in pack.get("human_review_flags") or []:
        items.append(
            make_evidence_item(
                evidence_id=f"FA-REVIEW-{len(items) + 1:03d}",
                question_ids=["financial.accounting_red_flags"],
                source_id="financial_report_pack",
                source_tier=1,
                source_type="financial_human_review_flag",
                locator=str(flag.get("metric") or flag.get("flag_id") or "human_review"),
                evidence_kind="unknown",
                excerpt=str(flag.get("message") or flag.get("warning") or flag)[:900],
                structured_fact=flag,
                confidence="medium",
                upstream_refs=[{"upstream_artifact": "financial_report_pack", "human_review_flag_id": flag.get("flag_id") or stable_id("review", flag)}],
                requires_human_review=True,
            )
        )
    return items


def _diagnostic_cards(pack: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    findings = pack.get("diagnostic_findings") or {}
    for question in findings.get("questions") or []:
        text = str(question.get("answer") or question.get("key_read") or question.get("question") or "")
        items.append(
            make_evidence_item(
                evidence_id=f"FA-DIAG-{len(items) + 1:03d}",
                question_ids=[_diagnostic_question_id(question)] or ["financial.growth"],
                source_id="financial_report_pack",
                source_tier=1,
                source_type="derived_financial_diagnostic",
                locator=str(question.get("question_id") or "diagnostic"),
                evidence_kind="system_inference",
                excerpt=text,
                structured_fact=question,
                confidence="medium",
                upstream_refs=[{"upstream_artifact": "financial_report_pack", "diagnostic_question_id": question.get("question_id")}],
            )
        )
    return items


def _gap_requests(pack: dict[str, Any]) -> list[dict[str, Any]]:
    gaps = []
    extraction = pack.get("fact_extraction_summary") or {}
    for gap in extraction.get("disclosure_gap_registry") or []:
        gap_id = str(gap.get("gap_id") or stable_id("financial-gap", gap))
        gaps.append(
            make_gap_request(
                gap_id=gap_id,
                question_id=_gap_question_id(gap_id, gap),
                gap_type="financial_disclosure_gap",
                description=str(gap.get("why_it_matters") or gap.get("status") or gap),
                priority="P0" if "temu" in gap_id or "cost" in gap_id else "P1",
                route="financial_extractor",
                owner_agent="financial_extractor",
                required_metrics=[str(item) for item in gap.get("missing_metrics") or []],
                required_source_types=["20-F", "6-K", "earnings_release"],
                depends_on_artifact="financial_report_pack",
            )
        )
    missing_facts = pack.get("missing_facts") or {}
    for category, values in missing_facts.items():
        if not values:
            continue
        gaps.append(
            make_gap_request(
                gap_id=f"missing_{category}",
                question_id="financial.accounting_red_flags",
                gap_type="missing_financial_fact",
                description=f"Missing financial facts in category {category}: {values}",
                priority="P1",
                route="financial_extractor",
                owner_agent="financial_extractor",
                required_metrics=[str(item) for item in values] if isinstance(values, list) else [str(values)],
                required_source_types=["20-F", "6-K", "earnings_release"],
                depends_on_artifact="financial_report_pack",
            )
        )
    return gaps


def _quality_flags(pack: dict[str, Any]) -> list[dict[str, Any]]:
    flags = []
    if not pack:
        flags.append({"flag_id": "missing_financial_report_pack", "severity": "high", "message": "FinancialReportPack is missing."})
        return flags
    if (pack.get("fact_quality_gate") or {}).get("status") not in {None, "", "pass", "passed"}:
        flags.append(
            {
                "flag_id": "financial_fact_quality_gate",
                "severity": "medium",
                "message": "Financial fact quality gate is not a clean pass.",
                "details": pack.get("fact_quality_gate"),
            }
        )
    conflicts = [
        flag
        for flag in pack.get("human_review_flags") or []
        if str(flag.get("severity") or "").casefold() == "high"
    ]
    if conflicts:
        flags.append(
            {
                "flag_id": "financial_human_review_conflicts",
                "severity": "medium",
                "message": f"{len(conflicts)} high-severity financial review flags require review.",
            }
        )
    return flags


def _prioritized_financial_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(fact: dict[str, Any]) -> tuple[Any, ...]:
        year = int(fact.get("period_year") or 0)
        source_type = str(fact.get("source_document_type") or fact.get("document_type") or "")
        currency = str(fact.get("currency") or "")
        confidence = str(fact.get("confidence") or "")
        official_priority = 1 if source_type.startswith(("20-F", "6-K", "10-K", "10-Q")) else 0
        currency_priority = 1 if currency in {"RMB", "CNY", "USD"} else 0
        confidence_priority = 1 if confidence in {"", "high"} else 0
        return (-year, -official_priority, -currency_priority, -confidence_priority, str(fact.get("fact_id") or ""))

    return sorted(facts, key=sort_key)


def _fact_evidence_kind(fact: dict[str, Any]) -> str:
    source_type = str(fact.get("source_document_type") or "")
    statement = str(fact.get("financial_statement") or "")
    if source_type == "20-F" and statement:
        return "audited_fact"
    if source_type in {"20-F", "10-K"}:
        return "filed_fact"
    if source_type in {"6-K", "10-Q"}:
        return "interim_fact"
    return "filed_fact"


def _fact_excerpt(fact: dict[str, Any]) -> str:
    value = fact.get("value")
    metric = fact.get("canonical_metric") or fact.get("metric")
    period = fact.get("period_label") or fact.get("period_year") or fact.get("end_date") or fact.get("instant")
    unit = fact.get("unit") or fact.get("currency")
    return f"{metric} = {value} {unit or ''} for {period}".strip()


def _metric_excerpt(formula_id: str, latest: dict[str, Any], latest_interim: dict[str, Any]) -> str:
    candidate = latest_interim or latest or {}
    pieces = [f"Formula {formula_id}"]
    for key in ["value", "result", "status", "current", "latest", "incremental_operating_margin", "fcf_margin", "roic", "owner_earnings"]:
        if key in candidate:
            pieces.append(f"{key}={candidate.get(key)}")
    return "; ".join(pieces)


def _questions_for_formula(formula_id: str) -> list[str]:
    mapping = {
        "source_of_growth_attribution_v1": ["financial.growth", "financial.revenue_sources", "business.revenue_mechanism"],
        "operating_profit_bridge_v1": ["financial.margin_conversion", "business.unit_economics"],
        "below_operating_bridge_v1": ["financial.accounting_red_flags", "financial.margin_conversion"],
        "working_capital_quality_v1": ["financial.cash_conversion", "financial.balance_sheet"],
        "balance_sheet_risk_v1": ["financial.balance_sheet", "risk.regulatory_legal"],
        "share_based_compensation_burden_v1": ["financial.dilution_sbc", "people.incentives"],
        "capital_intensity_v1": ["business.reinvestment_need", "price.expectations"],
        "unlevered_roic_v1": ["business.unit_economics", "people.capital_allocation", "price.expectations"],
        "incremental_roic_proxy_v1": ["business.unit_economics", "business.reinvestment_need", "people.capital_allocation"],
        "owner_earnings_v1": ["price.owner_return", "financial.cash_conversion"],
    }
    return mapping.get(formula_id, question_ids_for_metric(formula_id))


def _latest_metric_result(metric: dict[str, Any]) -> dict[str, Any]:
    if metric.get("latest_result"):
        return metric.get("latest_result") or {}
    results = metric.get("results") or metric.get("annual_results") or []
    if isinstance(results, list) and results:
        return results[-1]
    return {}


def _same_quarter_prior_year(latest_q: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    period = str(latest_q.get("period_end") or "")
    if len(period) < 4:
        return {}
    try:
        prior_year = str(int(period[:4]) - 1)
    except ValueError:
        return {}
    target = prior_year + period[4:]
    for row in rows:
        if str(row.get("period_end") or "") == target:
            return row
    return {}


def _pick_keys(row: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: row.get(key) for key in keys if key in row}


def _money_b(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "n/a"
    return f"RMB {value / 1_000_000_000:.1f}B"


def _diagnostic_question_id(question: dict[str, Any]) -> str:
    text = " ".join(str(question.get(key) or "") for key in ["question_id", "question", "key_read", "answer"]).casefold()
    if "cash" in text:
        return "financial.cash_conversion"
    if "balance" in text or "资产负债" in text:
        return "financial.balance_sheet"
    if "sbc" in text or "dilution" in text or "稀释" in text:
        return "financial.dilution_sbc"
    if "margin" in text or "利润率" in text:
        return "financial.margin_conversion"
    if "growth" in text or "收入" in text:
        return "financial.growth"
    return "financial.accounting_red_flags"


def _gap_question_id(gap_id: str, gap: dict[str, Any]) -> str:
    text = " ".join([gap_id, str(gap)]).casefold()
    if "temu" in text or "segment" in text:
        return "pdd.temu_segment_opacity"
    if "cost" in text or "fulfillment" in text:
        return "business.unit_economics"
    if "capex" in text:
        return "business.reinvestment_need"
    if "kpi" in text or "gmv" in text:
        return "business.unit_economics"
    return "financial.accounting_red_flags"
