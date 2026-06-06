from __future__ import annotations

from collections import defaultdict
from typing import Any

from stock_research.valuation.market_inputs import market_cap_in_cny


REVENUE_COMPONENT_METRICS = [
    "online_marketing_services_revenue",
    "transaction_services_revenue",
    "product_revenue",
    "service_revenue",
    "subscription_revenue",
    "advertising_revenue",
    "marketplace_services_revenue",
]

REVENUE_COMPONENT_EXCLUDE = {
    "cost_of_revenue",
    "deferred_revenue",
    "change_in_deferred_revenue",
}

WORKING_CAPITAL_COMPONENTS = [
    ("accounts_receivable", "cash_use_asset"),
    ("receivables_from_online_payment_platforms", "cash_use_asset"),
    ("inventory", "cash_use_asset"),
    ("prepayments_and_other_current_assets", "cash_use_asset"),
    ("accounts_payable", "cash_source_liability"),
    ("accounts_payable_and_accrued_expenses", "cash_source_liability"),
    ("payable_to_merchants", "cash_source_liability"),
    ("merchant_deposits", "cash_source_liability"),
    ("deferred_revenue", "cash_source_liability"),
    ("accrued_expenses", "cash_source_liability"),
]

NON_GAAP_ADJUSTMENT_METRICS = [
    "non_gaap_adjustment_share_based_compensation",
    "non_gaap_adjustment_fair_value_changes",
    "non_gaap_adjustment_amortization",
    "non_gaap_adjustment_tax_effect",
]


def calculate_v1_metrics(
    extracted_facts: list[dict[str, Any]],
    *,
    market_inputs: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    financial_metrics = calculate_v1_financial_metrics(extracted_facts)
    valuation_metrics = calculate_v1_valuation_metrics(
        extracted_facts,
        market_inputs=market_inputs,
        financial_metrics=financial_metrics,
    )
    return financial_metrics + valuation_metrics


def calculate_v1_financial_metrics(extracted_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annual = _annual_cny_fact_map(extracted_facts)
    quarterly = _quarterly_fact_map(extracted_facts)
    owner_earnings = _owner_earnings(annual)
    margin_profile = _margin_profile(annual)
    incremental_margin = _incremental_margin(annual)
    capital_intensity = _capital_intensity(annual)
    balance_sheet_risk = _balance_sheet_risk(annual)
    sbc_burden = _share_based_compensation_burden(annual)
    cash_conversion = _cash_conversion(annual)
    working_capital_quality = _working_capital_quality(annual)
    tax_non_gaap_accounting_quality = _tax_non_gaap_accounting_quality(annual, quarterly)
    source_of_growth = _source_of_growth_attribution(annual, quarterly)
    operating_profit_bridge = _operating_profit_bridge(annual, quarterly)
    below_operating_bridge = _below_operating_bridge(annual, quarterly)
    latest_interim_trend = _latest_interim_trend(annual, quarterly)
    roic = _unlevered_roic(annual)
    incremental_roic = _incremental_roic_proxy(annual)
    metrics = [
        margin_profile,
        incremental_margin,
        source_of_growth,
        capital_intensity,
        working_capital_quality,
        tax_non_gaap_accounting_quality,
        latest_interim_trend,
        operating_profit_bridge,
        below_operating_bridge,
        balance_sheet_risk,
        sbc_burden,
        owner_earnings,
        cash_conversion,
        roic,
        incremental_roic,
    ]
    return metrics


def calculate_v1_valuation_metrics(
    extracted_facts: list[dict[str, Any]],
    *,
    market_inputs: dict[str, Any] | None = None,
    financial_metrics: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    annual = _annual_cny_fact_map(extracted_facts)
    owner_earnings = _metric_by_id(financial_metrics or [], "owner_earnings_v1") or _owner_earnings(
        annual
    )
    enterprise_value = _enterprise_value(annual, market_inputs or {})
    return [
        enterprise_value,
        _true_yield(owner_earnings, enterprise_value),
        _free_cash_flow_yield(annual, enterprise_value),
        _investment_adjusted_operating_yield(
            annual,
            owner_earnings,
            enterprise_value,
        ),
        _one_dollar_test(),
    ]


def annual_fact_rows(extracted_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annual = _annual_cny_fact_map(extracted_facts)
    rows = []
    for year in sorted(annual):
        by_metric = annual[year]
        rows.append(
            {
                "year": year,
                "revenue": _value(by_metric, "revenue"),
                "gross_profit": _value(by_metric, "gross_profit"),
                "operating_income": _value(by_metric, "operating_income"),
                "net_income": _value(by_metric, "net_income"),
                "operating_cash_flow": _value(by_metric, "operating_cash_flow"),
                "capex": _value(by_metric, "capex"),
                "free_cash_flow": _value(by_metric, "free_cash_flow"),
                "cash": _value(by_metric, "cash"),
                "restricted_cash": _value(by_metric, "restricted_cash"),
                "short_term_investments": _value(by_metric, "short_term_investments"),
                "online_marketing_services_revenue": _value(by_metric, "online_marketing_services_revenue"),
                "transaction_services_revenue": _value(by_metric, "transaction_services_revenue"),
                "sales_and_marketing_expense": _value(by_metric, "sales_and_marketing_expense"),
                "research_and_development_expense": _value(by_metric, "research_and_development_expense"),
                "general_and_administrative_expense": _value(by_metric, "general_and_administrative_expense"),
                "investment_income": _value(by_metric, "investment_income"),
                "interest_expense": _value(by_metric, "interest_expense"),
                "foreign_exchange_gain_loss": _value(by_metric, "foreign_exchange_gain_loss"),
                "other_income_net": _value(by_metric, "other_income_net"),
                "tax_expense": _value(by_metric, "tax_expense"),
                "equity_method_income": _value(by_metric, "equity_method_income"),
                "debt": _value(by_metric, "debt"),
                "debt_current": _value(by_metric, "debt_current"),
                "debt_noncurrent": _value(by_metric, "debt_noncurrent"),
                "convertible_debt_current": _value(by_metric, "convertible_debt_current"),
                "lease_liabilities_current": _value(by_metric, "lease_liabilities_current"),
                "lease_liabilities_noncurrent": _value(by_metric, "lease_liabilities_noncurrent"),
                "lease_liabilities": _value(by_metric, "lease_liabilities"),
                "investment_portfolio": _value(by_metric, "investment_portfolio"),
                "stock_based_compensation": _value(by_metric, "stock_based_compensation"),
                "diluted_shares": _value(by_metric, "diluted_shares"),
                "current_assets": _value(by_metric, "current_assets"),
                "current_liabilities": _value(by_metric, "current_liabilities"),
                "total_assets": _value(by_metric, "total_assets"),
                "total_liabilities": _value(by_metric, "total_liabilities"),
            }
        )
    return rows


def quarterly_fact_rows(extracted_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    quarterly = _quarterly_fact_map(extracted_facts)
    rows = []
    for period_end in sorted(quarterly):
        by_metric = quarterly[period_end]
        rows.append(
            {
                "quarter": _quarter_label(period_end),
                "period_end": period_end,
                "revenue": _value(by_metric, "revenue"),
                "gross_profit": _value(by_metric, "gross_profit"),
                "operating_income": _value(by_metric, "operating_income"),
                "net_income": _value(by_metric, "net_income"),
                "operating_cash_flow": _value(by_metric, "operating_cash_flow"),
                "online_marketing_services_revenue": _value(by_metric, "online_marketing_services_revenue"),
                "transaction_services_revenue": _value(by_metric, "transaction_services_revenue"),
                "investment_income": _value(by_metric, "investment_income"),
                "foreign_exchange_gain_loss": _value(by_metric, "foreign_exchange_gain_loss"),
                "other_income_net": _value(by_metric, "other_income_net"),
                "tax_expense": _value(by_metric, "tax_expense"),
                "equity_method_income": _value(by_metric, "equity_method_income"),
                "cash": _value(by_metric, "cash"),
                "short_term_investments": _value(by_metric, "short_term_investments"),
                "restricted_cash": _value(by_metric, "restricted_cash"),
                "receivables_from_online_payment_platforms": _value(by_metric, "receivables_from_online_payment_platforms"),
                "prepayments_and_other_current_assets": _value(by_metric, "prepayments_and_other_current_assets"),
                "payable_to_merchants": _value(by_metric, "payable_to_merchants"),
                "merchant_deposits": _value(by_metric, "merchant_deposits"),
                "deferred_revenue": _value(by_metric, "deferred_revenue"),
                "lease_liabilities_current": _value(by_metric, "lease_liabilities_current"),
                "lease_liabilities_noncurrent": _value(by_metric, "lease_liabilities_noncurrent"),
                "current_assets": _value(by_metric, "current_assets"),
                "current_liabilities": _value(by_metric, "current_liabilities"),
                "total_assets": _value(by_metric, "total_assets"),
                "total_liabilities": _value(by_metric, "total_liabilities"),
                "diluted_shares": _value(by_metric, "diluted_shares"),
            }
        )
    return rows


def annual_fact_source_rows(extracted_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annual = _annual_cny_fact_map(extracted_facts)
    metrics = [
        "revenue",
        "gross_profit",
        "operating_income",
        "net_income",
        "operating_cash_flow",
        "capex",
        "free_cash_flow",
        "cash",
        "investment_portfolio",
        "total_assets",
        "total_liabilities",
        "diluted_shares",
    ]
    rows = []
    for year in sorted(annual):
        for metric in metrics:
            fact = annual[year].get(metric)
            if not fact:
                continue
            rows.append(
                {
                    "year": year,
                    "metric": metric,
                    "value": fact.get("value"),
                    "unit": fact.get("unit"),
                    "filing_date": fact.get("filing_date"),
                    "document_id": fact.get("document_id"),
                    "local_path": fact.get("local_path"),
                    "tag_or_method": fact.get("xbrl_tag") or fact.get("extraction_method"),
                    "fact_id": fact.get("fact_id"),
                    "source_fact_ids": fact.get("source_fact_ids", []),
                }
            )
    return rows


def _annual_cny_fact_map(extracted_facts: list[dict[str, Any]]) -> dict[int, dict[str, dict[str, Any]]]:
    by_year: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for fact in extracted_facts:
        unit = fact.get("unit")
        metric = fact.get("metric")
        if unit not in {"CNY", "shares"}:
            continue
        end_date = fact.get("end_date") or fact.get("instant")
        if not isinstance(end_date, str) or not end_date.endswith("-12-31"):
            continue
        if fact.get("period_type") not in {"annual", "instant"}:
            continue
        if fact.get("period_type") == "annual" and not str(fact.get("start_date", "")).endswith("-01-01"):
            continue
        year = int(end_date[:4])
        current = by_year[year].get(metric)
        if current is None or (fact.get("filing_date") or "") >= (current.get("filing_date") or ""):
            by_year[year][metric] = fact
    return dict(by_year)


def _quarterly_fact_map(extracted_facts: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    by_period: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for fact in extracted_facts:
        unit = fact.get("unit")
        metric = fact.get("metric")
        if unit not in {"CNY", "shares"}:
            continue
        end_date = fact.get("end_date") or fact.get("instant")
        if not isinstance(end_date, str):
            continue
        if fact.get("period_type") == "quarter":
            if not fact.get("start_date"):
                continue
        else:
            continue
        current = by_period[end_date].get(metric)
        if current is None or _fact_preference_key(fact) >= _fact_preference_key(current):
            by_period[end_date][metric] = fact
    for fact in extracted_facts:
        unit = fact.get("unit")
        metric = fact.get("metric")
        if unit not in {"CNY", "shares"} or metric not in {
            "cash",
            "cash_and_short_term_investments",
            "short_term_investments",
            "restricted_cash",
            "current_assets",
            "total_assets",
            "current_liabilities",
            "total_liabilities",
            "debt",
            "debt_current",
            "debt_noncurrent",
        }:
            continue
        end_date = fact.get("end_date") or fact.get("instant")
        if not isinstance(end_date, str) or end_date not in by_period:
            continue
        if fact.get("period_type") != "instant":
            continue
        current = by_period[end_date].get(metric)
        if current is None or _fact_preference_key(fact) >= _fact_preference_key(current):
            by_period[end_date][metric] = fact
    return dict(by_period)


def _metric_by_id(metrics: list[dict[str, Any]], formula_id: str) -> dict[str, Any] | None:
    for metric in metrics:
        if metric.get("formula_id") == formula_id:
            return metric
    return None


def _owner_earnings(annual: dict[int, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    results = []
    for year, facts in sorted(annual.items()):
        required = ["operating_cash_flow", "stock_based_compensation", "depreciation_and_amortization"]
        missing = [metric for metric in required if metric not in facts]
        if missing:
            results.append({"year": year, "status": "missing_required_facts", "missing": missing})
            continue
        value = (
            facts["operating_cash_flow"]["value"]
            - facts["stock_based_compensation"]["value"]
            - facts["depreciation_and_amortization"]["value"]
        )
        results.append(
            {
                "year": year,
                "status": "calculated",
                "value": value,
                "unit": "CNY",
                "display_name": "owner earnings proxy",
                "formula": "operating_cash_flow - stock_based_compensation - maintenance_capex_proxy",
                "maintenance_capex_proxy": facts["depreciation_and_amortization"]["value"],
                "assumption": "V1 uses D&A as the maintenance CapEx approximation.",
                "review_required": True,
                "limitations": [
                    "This is an owner-earnings proxy, not a precise Buffett owner-earnings calculation.",
                    "Maintenance CapEx is not separately estimated from growth CapEx in V1.",
                ],
                "source_fact_ids": [facts[metric]["fact_id"] for metric in required],
            }
        )
    return {
        "formula_id": "owner_earnings_v1",
        "status": "calculated" if any(row.get("status") == "calculated" for row in results) else "missing_required_facts",
        "annual_results": results,
    }


def _enterprise_value(
    annual: dict[int, dict[str, dict[str, Any]]],
    market_inputs: dict[str, Any],
) -> dict[str, Any]:
    market_cap = market_cap_in_cny(market_inputs)
    if market_cap.get("status") != "calculated":
        return {
            "formula_id": "enterprise_value_v1",
            "status": "pending_manual_market_data",
            "note": "Requires validated market capitalization and FX inputs.",
            "market_inputs_status": market_inputs.get("status", "not_loaded"),
            "missing": market_cap.get("missing") or market_inputs.get("missing", []),
        }

    latest_cash = _latest_fact(annual, "cash")
    if latest_cash is None:
        return {
            "formula_id": "enterprise_value_v1",
            "status": "missing_required_facts",
            "missing": ["cash"],
            "note": "Requires latest official cash balance to subtract cash from market capitalization.",
        }

    year, cash_fact = latest_cash
    debt_fact = annual.get(year, {}).get("debt")
    debt = debt_fact["value"] if debt_fact else 0
    value = market_cap["value"] + debt - cash_fact["value"]
    source_fact_ids = [cash_fact["fact_id"]]
    if debt_fact:
        source_fact_ids.append(debt_fact["fact_id"])
    else:
        source_fact_ids.append("assumption:no_interest_bearing_debt_fact_found")

    return {
        "formula_id": "enterprise_value_v1",
        "status": "calculated",
        "annual_results": [
            {
                "year": year,
                "status": "calculated",
                "value": value,
                "unit": "CNY",
                "formula": "market_cap + interest_bearing_debt - cash",
                "market_cap_cny": market_cap["value"],
                "market_cap_input": market_cap["market_cap"],
                "market_cap_currency": market_cap["currency"],
                "fx_rate": market_cap["fx_rate"],
                "fx_field": market_cap["fx_field"],
                "as_of_date": market_cap.get("as_of_date"),
                "source": market_cap.get("source"),
                "cash": cash_fact["value"],
                "debt": debt,
                "used_zero_debt_assumption": debt_fact is None,
                "source_fact_ids": source_fact_ids,
                "review_required": market_cap.get("review_required", True),
                "review_status": market_cap.get("review_status"),
                "limitations": [
                    "V1 subtracts all cash rather than estimating excess operating cash.",
                    "Market capitalization and FX are market-data inputs, not official filing facts.",
                ],
            }
        ],
    }


def _true_yield(owner_earnings: dict[str, Any], enterprise_value: dict[str, Any]) -> dict[str, Any]:
    owner_result = _latest_calculated_result(owner_earnings)
    if owner_result is None:
        return {
            "formula_id": "true_yield_v1",
            "status": "missing_owner_earnings",
            "note": "Requires calculated owner earnings.",
        }
    ev_result = _latest_calculated_result(enterprise_value)
    if ev_result is None:
        return {
            "formula_id": "true_yield_v1",
            "status": "pending_enterprise_value",
            "note": "Requires enterprise value.",
        }
    if ev_result["value"] <= 0:
        return {
            "formula_id": "true_yield_v1",
            "status": "not_calculable_nonpositive_enterprise_value",
        }
    return {
        "formula_id": "true_yield_v1",
        "status": "calculated",
        "annual_results": [
            {
                "year": owner_result["year"],
                "status": "calculated",
                "value": owner_result["value"] / ev_result["value"],
                "unit": "ratio",
                "display_name": "owner earnings proxy yield on enterprise value",
                "formula": "owner_earnings / enterprise_value",
                "owner_earnings": owner_result["value"],
                "enterprise_value": ev_result["value"],
                "enterprise_value_year": ev_result.get("year"),
                "as_of_date": ev_result.get("as_of_date"),
                "review_required": owner_result.get("review_required", True)
                or ev_result.get("review_required", True),
                "limitations": [
                    "Uses owner_earnings_v1, which is a proxy because maintenance CapEx is not independently estimated.",
                    "Uses enterprise_value_v1, which subtracts all cash rather than estimating excess operating cash.",
                ],
                "source_fact_ids": owner_result.get("source_fact_ids", [])
                + ev_result.get("source_fact_ids", []),
            }
        ],
    }


def _free_cash_flow_yield(
    annual: dict[int, dict[str, dict[str, Any]]],
    enterprise_value: dict[str, Any],
) -> dict[str, Any]:
    latest_fcf = _latest_fact(annual, "free_cash_flow")
    if latest_fcf is None:
        return {
            "formula_id": "free_cash_flow_yield_v1",
            "status": "missing_free_cash_flow",
            "note": "Requires official free cash flow or capex facts.",
        }
    ev_result = _latest_calculated_result(enterprise_value)
    if ev_result is None:
        return {
            "formula_id": "free_cash_flow_yield_v1",
            "status": "pending_enterprise_value",
            "note": "Requires enterprise value.",
        }
    if ev_result["value"] <= 0:
        return {
            "formula_id": "free_cash_flow_yield_v1",
            "status": "not_calculable_nonpositive_enterprise_value",
        }
    year, fcf_fact = latest_fcf
    return {
        "formula_id": "free_cash_flow_yield_v1",
        "status": "calculated",
        "annual_results": [
            {
                "year": year,
                "status": "calculated",
                "value": fcf_fact["value"] / ev_result["value"],
                "unit": "ratio",
                "display_name": "free cash flow yield on enterprise value",
                "formula": "free_cash_flow / enterprise_value",
                "free_cash_flow": fcf_fact["value"],
                "enterprise_value": ev_result["value"],
                "enterprise_value_year": ev_result.get("year"),
                "as_of_date": ev_result.get("as_of_date"),
                "review_required": ev_result.get("review_required", True),
                "limitations": [
                    "Uses the V1 free-cash-flow definition from official operating cash flow and CapEx facts.",
                    "FCF definitions can vary across companies and non-GAAP presentations.",
                ],
                "source_fact_ids": [fcf_fact["fact_id"]] + ev_result.get("source_fact_ids", []),
            }
        ],
    }


def _investment_adjusted_operating_yield(
    annual: dict[int, dict[str, dict[str, Any]]],
    owner_earnings: dict[str, Any],
    enterprise_value: dict[str, Any],
) -> dict[str, Any]:
    owner_result = _latest_calculated_result(owner_earnings)
    if owner_result is None:
        return {
            "formula_id": "investment_adjusted_operating_yield_v1",
            "status": "missing_owner_earnings",
            "note": "Requires calculated owner earnings.",
        }
    ev_result = _latest_calculated_result(enterprise_value)
    if ev_result is None:
        return {
            "formula_id": "investment_adjusted_operating_yield_v1",
            "status": "pending_enterprise_value",
            "note": "Requires enterprise value.",
        }
    latest_portfolio = _latest_fact(annual, "investment_portfolio")
    if latest_portfolio is None:
        return {
            "formula_id": "investment_adjusted_operating_yield_v1",
            "status": "missing_investment_portfolio",
            "note": "Requires official investment portfolio carrying amount. This is mainly needed for investment-heavy companies such as Tencent.",
        }
    latest_fcf = _latest_fact(annual, "free_cash_flow")
    year, portfolio_fact = latest_portfolio
    operating_enterprise_value = ev_result["value"] - portfolio_fact["value"]
    if operating_enterprise_value <= 0:
        return {
            "formula_id": "investment_adjusted_operating_yield_v1",
            "status": "not_calculable_nonpositive_operating_enterprise_value",
            "enterprise_value": ev_result["value"],
            "investment_portfolio": portfolio_fact["value"],
        }
    fcf_fact = latest_fcf[1] if latest_fcf else None
    source_fact_ids = (
        owner_result.get("source_fact_ids", [])
        + ev_result.get("source_fact_ids", [])
        + [portfolio_fact["fact_id"]]
    )
    if fcf_fact:
        source_fact_ids.append(fcf_fact["fact_id"])
    return {
        "formula_id": "investment_adjusted_operating_yield_v1",
        "status": "calculated",
        "annual_results": [
            {
                "year": owner_result["year"],
                "status": "calculated",
                "value": owner_result["value"] / operating_enterprise_value,
                "unit": "ratio",
                "formula": "owner_earnings / (enterprise_value - official_investment_portfolio_carrying_value)",
                "owner_earnings_yield": owner_result["value"] / operating_enterprise_value,
                "free_cash_flow_yield": _safe_div(fcf_fact["value"], operating_enterprise_value) if fcf_fact else None,
                "owner_earnings": owner_result["value"],
                "free_cash_flow": fcf_fact["value"] if fcf_fact else None,
                "enterprise_value": ev_result["value"],
                "investment_portfolio": portfolio_fact["value"],
                "operating_enterprise_value": operating_enterprise_value,
                "investment_portfolio_year": year,
                "enterprise_value_year": ev_result.get("year"),
                "as_of_date": ev_result.get("as_of_date"),
                "review_required": ev_result.get("review_required", True),
                "source_fact_ids": source_fact_ids,
                "limitations": [
                    "Uses Tencent's official investment-portfolio carrying amount, not an independent market-value sum-of-the-parts.",
                    "No tax haircut, liquidity haircut, control premium, or trapped-cash adjustment is applied in V1.",
                    "Assumes owner earnings and FCF primarily represent consolidated operating cash generation rather than look-through investee cash earnings.",
                ],
            }
        ],
        "note": "Tencent-specific operating yield approximation: subtracts official investment portfolio carrying value from EV before calculating cash earnings yield.",
    }


def _cash_conversion(annual: dict[int, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    results = []
    for year, facts in sorted(annual.items()):
        required = ["operating_cash_flow", "net_income"]
        missing = [metric for metric in required if metric not in facts]
        if missing:
            results.append({"year": year, "status": "missing_required_facts", "missing": missing})
            continue
        net_income = facts["net_income"]["value"]
        if net_income == 0:
            results.append({"year": year, "status": "not_calculable_zero_net_income"})
            continue
        results.append(
            {
                "year": year,
                "status": "calculated",
                "value": facts["operating_cash_flow"]["value"] / net_income,
                "unit": "ratio",
                "display_name": "CFO / net income",
                "formula": "operating_cash_flow / net_income",
                "source_fact_ids": [facts[metric]["fact_id"] for metric in required],
            }
        )
    return {
        "formula_id": "cash_conversion_ratio_v1",
        "status": "calculated" if any(row.get("status") == "calculated" for row in results) else "missing_required_facts",
        "annual_results": results,
    }


def _working_capital_quality(annual: dict[int, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    results = []
    all_component_metrics = [metric for metric, _role in WORKING_CAPITAL_COMPONENTS]
    for year, facts in sorted(annual.items()):
        previous = annual.get(year - 1, {})
        component_specs = _working_capital_component_specs(facts, previous)
        component_metrics = [metric for metric, _role in component_specs]
        missing_required = [metric for metric in ["revenue"] if metric not in facts]
        available_components = [metric for metric in component_metrics if metric in facts]
        if missing_required:
            results.append(
                {"year": year, "status": "missing_required_facts", "missing": missing_required}
            )
            continue
        if not available_components and not {"current_assets", "current_liabilities"} <= facts.keys():
            results.append(
                {
                    "year": year,
                    "status": "missing_required_facts",
                    "missing": all_component_metrics + ["current_assets", "current_liabilities"],
                }
            )
            continue
        revenue = facts["revenue"]["value"]
        if revenue == 0:
            results.append({"year": year, "status": "not_calculable_zero_revenue"})
            continue

        previous_revenue = _value(previous, "revenue")
        revenue_growth = _growth_rate(revenue, previous_revenue)
        component_details = []
        source_delta = 0.0
        use_delta = 0.0
        has_delta = False
        for metric, role in component_specs:
            current_value = _value(facts, metric)
            if current_value is None:
                continue
            prior_value = _value(previous, metric)
            yoy_growth = _growth_rate(current_value, prior_value)
            delta = current_value - prior_value if prior_value is not None else None
            if delta is not None:
                has_delta = True
                if role == "cash_source_liability":
                    source_delta += delta
                else:
                    use_delta += delta
            component_details.append(
                _compact_values(
                    {
                        "metric": metric,
                        "role": role,
                        "value": current_value,
                        "to_revenue": _safe_div(current_value, revenue),
                        "yoy_growth": yoy_growth,
                        "growth_minus_revenue_growth": yoy_growth - revenue_growth
                        if yoy_growth is not None and revenue_growth is not None
                        else None,
                        "delta": delta,
                    }
                )
            )

        current_assets = _value(facts, "current_assets")
        current_liabilities = _value(facts, "current_liabilities")
        net_working_capital = (
            current_assets - current_liabilities
            if current_assets is not None and current_liabilities is not None
            else None
        )
        working_capital_cash_tailwind = _safe_div(source_delta - use_delta, revenue) if has_delta else None
        result = {
            "year": year,
            "status": "calculated",
            "value": working_capital_cash_tailwind
            if working_capital_cash_tailwind is not None
            else _safe_div(net_working_capital, revenue),
            "unit": "ratio",
            "formula": "working-capital component deltas / revenue when prior-year components exist; otherwise net working capital / revenue",
            "revenue_growth_yoy": revenue_growth,
            "current_ratio": _safe_div(current_assets, current_liabilities),
            "net_working_capital_to_revenue": _safe_div(net_working_capital, revenue),
            "working_capital_cash_tailwind_to_revenue": working_capital_cash_tailwind,
            "cash_source_liability_delta": source_delta if has_delta else None,
            "cash_use_asset_delta": use_delta if has_delta else None,
            "component_details": component_details,
            "warning_flags": _working_capital_warnings(component_details, working_capital_cash_tailwind),
            "missing_optional": [metric for metric in component_metrics if metric not in facts],
            "source_fact_ids": [facts["revenue"]["fact_id"]]
            + _source_fact_ids_for(facts, component_metrics + ["current_assets", "current_liabilities"])
            + _source_fact_ids_for(previous, component_metrics + ["revenue"]),
        }
        results.append(result)
    return {
        "formula_id": "working_capital_quality_v1",
        "status": "calculated" if any(row.get("status") == "calculated" for row in results) else "missing_required_facts",
        "annual_results": results,
        "note": "Checks whether cash conversion is supported by receivables, inventory, payables, merchant deposits, accrued expenses, deferred revenue, and current balance-sheet items.",
    }


def _tax_non_gaap_accounting_quality(
    annual: dict[int, dict[str, dict[str, Any]]],
    quarterly: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    results = []
    for year, facts in sorted(annual.items()):
        pretax_metric = "pretax_income" if "pretax_income" in facts else "pretax_income_after_equity_method"
        required = [pretax_metric, "tax_expense"]
        missing = [metric for metric in required if metric not in facts]
        if missing:
            results.append({"year": year, "status": "missing_required_facts", "missing": missing})
            continue
        pretax_income = facts[pretax_metric]["value"]
        if pretax_income == 0:
            results.append({"year": year, "status": "not_calculable_zero_pretax_income"})
            continue
        tax_expense = facts["tax_expense"]["value"]
        effective_tax_rate = tax_expense / pretax_income
        cash_paid_for_taxes = _value(facts, "cash_paid_for_taxes")
        investment_income = _value(facts, "investment_income")
        equity_method_income = _value(facts, "equity_method_income")
        impairment = _value(facts, "impairment")
        revenue = _value(facts, "revenue")
        result = {
            "year": year,
            "status": "calculated",
            "value": effective_tax_rate,
            "unit": "ratio",
            "formula": "tax_expense / pretax_income",
            "pretax_metric_used": pretax_metric,
            "effective_tax_rate": effective_tax_rate,
            "cash_tax_to_tax_expense": _safe_div(cash_paid_for_taxes, tax_expense),
            "cash_tax_to_pretax_income": _safe_div(cash_paid_for_taxes, pretax_income),
            "investment_income_to_pretax": _safe_div(investment_income, pretax_income),
            "equity_method_income_to_pretax": _safe_div(equity_method_income, pretax_income),
            "impairment_to_revenue": _safe_div(impairment, revenue),
            "warning_flags": _tax_accounting_warnings(
                effective_tax_rate=effective_tax_rate,
                cash_tax_to_tax_expense=_safe_div(cash_paid_for_taxes, tax_expense),
                investment_income_to_pretax=_safe_div(investment_income, pretax_income),
                impairment_to_revenue=_safe_div(impairment, revenue),
            ),
            "missing_optional": [
                metric
                for metric in [
                    "cash_paid_for_taxes",
                    "investment_income",
                    "equity_method_income",
                    "impairment",
                    "revenue",
                ]
                if metric not in facts
            ],
            "source_fact_ids": _source_fact_ids_for(
                facts,
                [
                    pretax_metric,
                    "tax_expense",
                    "cash_paid_for_taxes",
                    "investment_income",
                    "equity_method_income",
                    "impairment",
                    "revenue",
                ],
            ),
        }
        results.append(result)

    latest_non_gaap = _latest_non_gaap_bridge(quarterly)
    status = "calculated" if any(row.get("status") == "calculated" for row in results) or latest_non_gaap else "missing_required_facts"
    return {
        "formula_id": "tax_non_gaap_accounting_quality_v1",
        "status": status,
        "annual_results": results,
        "latest_interim_non_gaap": latest_non_gaap,
        "note": "Combines annual tax/accounting checks with the latest official non-GAAP bridge when an earnings-release table is available.",
    }


def _source_of_growth_attribution(
    annual: dict[int, dict[str, dict[str, Any]]],
    quarterly: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    annual_results = []
    for year, facts in sorted(annual.items()):
        annual_results.append(_source_of_growth_result(period=year, facts=facts, prior_facts=annual.get(year - 1, {})))

    latest_quarter_result = None
    if quarterly:
        latest_period = sorted(quarterly)[-1]
        prior_period = f"{int(latest_period[:4]) - 1}{latest_period[4:]}"
        latest_quarter_result = _source_of_growth_result(
            period=latest_period,
            facts=quarterly[latest_period],
            prior_facts=quarterly.get(prior_period, {}),
        )

    calculated_annual = [row for row in annual_results if row.get("status") == "calculated"]
    status = "calculated" if calculated_annual or (latest_quarter_result and latest_quarter_result.get("status") == "calculated") else "missing_required_facts"
    return {
        "formula_id": "source_of_growth_attribution_v1",
        "status": status,
        "annual_results": annual_results,
        "latest_interim_result": latest_quarter_result,
        "note": "Uses official revenue component facts only. If segment/product/geography/take-rate facts are not extracted, the metric stays partial or missing instead of guessing.",
    }


def _operating_profit_bridge(
    annual: dict[int, dict[str, dict[str, Any]]],
    quarterly: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    annual_results = []
    for year, facts in sorted(annual.items()):
        annual_results.append(
            _operating_profit_bridge_result(
                period=year,
                facts=facts,
                prior_facts=annual.get(year - 1, {}),
            )
        )

    latest_interim_result = None
    if quarterly:
        latest_period = sorted(quarterly)[-1]
        prior_period = f"{int(latest_period[:4]) - 1}{latest_period[4:]}"
        latest_interim_result = _operating_profit_bridge_result(
            period=latest_period,
            facts=quarterly[latest_period],
            prior_facts=quarterly.get(prior_period, {}),
        )

    return {
        "formula_id": "operating_profit_bridge_v1",
        "status": "calculated"
        if any(row.get("status") == "calculated" for row in annual_results)
        or (latest_interim_result and latest_interim_result.get("status") == "calculated")
        else "missing_required_facts",
        "annual_results": annual_results,
        "latest_interim_result": latest_interim_result,
        "note": "Bridges revenue growth to operating income through cost of revenue and operating expense buckets.",
    }


def _operating_profit_bridge_result(
    *,
    period: int | str,
    facts: dict[str, dict[str, Any]],
    prior_facts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    required = ["revenue", "cost_of_revenue", "gross_profit", "operating_income"]
    missing = [metric for metric in required if metric not in facts]
    if missing:
        return {"period": period, "status": "missing_required_facts", "missing": missing}

    bridge_metrics = [
        ("revenue", "positive_driver"),
        ("cost_of_revenue", "profit_headwind_when_increases"),
        ("gross_profit", "subtotal"),
        ("sales_and_marketing_expense", "profit_headwind_when_increases"),
        ("general_and_administrative_expense", "profit_headwind_when_increases"),
        ("research_and_development_expense", "profit_headwind_when_increases"),
        ("operating_income", "result"),
    ]
    rows = [
        _bridge_component(metric, role, facts, prior_facts, denominator_metric="revenue")
        for metric, role in bridge_metrics
        if metric in facts
    ]
    operating_income_delta = _delta(facts, prior_facts, "operating_income")
    revenue_delta = _delta(facts, prior_facts, "revenue")
    return {
        "period": period,
        "status": "calculated",
        "value": _safe_div(operating_income_delta, revenue_delta),
        "unit": "ratio",
        "formula": "changes in revenue, cost of revenue and operating expenses explain change in operating income",
        "revenue_delta": revenue_delta,
        "gross_profit_delta": _delta(facts, prior_facts, "gross_profit"),
        "operating_income_delta": operating_income_delta,
        "incremental_operating_margin": _safe_div(operating_income_delta, revenue_delta),
        "bridge_rows": rows,
        "source_fact_ids": _source_fact_ids_for(facts, [metric for metric, _role in bridge_metrics])
        + _source_fact_ids_for(prior_facts, [metric for metric, _role in bridge_metrics]),
    }


def _below_operating_bridge(
    annual: dict[int, dict[str, dict[str, Any]]],
    quarterly: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    annual_results = []
    for year, facts in sorted(annual.items()):
        annual_results.append(_below_operating_bridge_result(period=year, facts=facts, prior_facts=annual.get(year - 1, {})))

    latest_interim_result = None
    if quarterly:
        latest_period = sorted(quarterly)[-1]
        prior_period = f"{int(latest_period[:4]) - 1}{latest_period[4:]}"
        latest_interim_result = _below_operating_bridge_result(
            period=latest_period,
            facts=quarterly[latest_period],
            prior_facts=quarterly.get(prior_period, {}),
        )

    return {
        "formula_id": "below_operating_bridge_v1",
        "status": "calculated"
        if any(row.get("status") == "calculated" for row in annual_results)
        or (latest_interim_result and latest_interim_result.get("status") == "calculated")
        else "missing_required_facts",
        "annual_results": annual_results,
        "latest_interim_result": latest_interim_result,
        "note": "Bridges operating income to net income through investment income, FX, other income/loss, tax, and equity-method results.",
    }


def _below_operating_bridge_result(
    *,
    period: int | str,
    facts: dict[str, dict[str, Any]],
    prior_facts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    required = ["operating_income", "net_income"]
    missing = [metric for metric in required if metric not in facts]
    if missing:
        return {"period": period, "status": "missing_required_facts", "missing": missing}

    bridge_metrics = [
        ("operating_income", "starting_point"),
        ("investment_income", "below_operating_driver"),
        ("interest_expense", "below_operating_headwind_when_increases"),
        ("foreign_exchange_gain_loss", "below_operating_driver"),
        ("other_income_net", "below_operating_driver"),
        ("tax_expense", "below_operating_headwind_when_increases"),
        ("equity_method_income", "below_operating_driver"),
        ("net_income", "result"),
    ]
    rows = [
        _bridge_component(metric, role, facts, prior_facts, denominator_metric="revenue")
        for metric, role in bridge_metrics
        if metric in facts
    ]
    operating_income_delta = _delta(facts, prior_facts, "operating_income")
    net_income_delta = _delta(facts, prior_facts, "net_income")
    return {
        "period": period,
        "status": "calculated",
        "value": net_income_delta,
        "unit": "CNY",
        "formula": "operating_income plus below-operating items minus tax reconciles directionally to net_income",
        "operating_income_delta": operating_income_delta,
        "net_income_delta": net_income_delta,
        "below_operating_delta": net_income_delta - operating_income_delta
        if net_income_delta is not None and operating_income_delta is not None
        else None,
        "bridge_rows": rows,
        "source_fact_ids": _source_fact_ids_for(facts, [metric for metric, _role in bridge_metrics])
        + _source_fact_ids_for(prior_facts, [metric for metric, _role in bridge_metrics]),
    }


def _bridge_component(
    metric: str,
    role: str,
    facts: dict[str, dict[str, Any]],
    prior_facts: dict[str, dict[str, Any]],
    *,
    denominator_metric: str,
) -> dict[str, Any]:
    current = _value(facts, metric)
    prior = _value(prior_facts, metric)
    denominator = _value(facts, denominator_metric)
    return _compact_values(
        {
            "metric": metric,
            "role": role,
            "current": current,
            "prior": prior,
            "delta": current - prior if current is not None and prior is not None else None,
            "current_to_revenue": _safe_div(current, denominator),
            "prior_to_revenue": _safe_div(prior, _value(prior_facts, denominator_metric)),
            "source_fact_id": facts[metric].get("fact_id") if metric in facts else None,
            "prior_source_fact_id": prior_facts[metric].get("fact_id") if metric in prior_facts else None,
        }
    )


def _delta(
    facts: dict[str, dict[str, Any]],
    prior_facts: dict[str, dict[str, Any]],
    metric: str,
) -> float | None:
    current = _value(facts, metric)
    prior = _value(prior_facts, metric)
    if current is None or prior is None:
        return None
    return current - prior


def _margin_profile(annual: dict[int, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    results = []
    for year, facts in sorted(annual.items()):
        required = ["revenue", "gross_profit", "operating_income", "net_income"]
        missing = [metric for metric in required if metric not in facts]
        if missing:
            results.append({"year": year, "status": "missing_required_facts", "missing": missing})
            continue
        revenue = facts["revenue"]["value"]
        if revenue == 0:
            results.append({"year": year, "status": "not_calculable_zero_revenue"})
            continue
        previous_revenue = _value(annual.get(year - 1, {}), "revenue")
        free_cash_flow = _value(facts, "free_cash_flow")
        result = {
            "year": year,
            "status": "calculated",
            "value": facts["operating_income"]["value"] / revenue,
            "unit": "ratio",
            "formula": "operating_income / revenue",
            "revenue": revenue,
            "gross_margin": facts["gross_profit"]["value"] / revenue,
            "operating_margin": facts["operating_income"]["value"] / revenue,
            "net_margin": facts["net_income"]["value"] / revenue,
            "free_cash_flow_margin": _safe_div(free_cash_flow, revenue),
            "revenue_growth_yoy": _safe_div(revenue - previous_revenue, previous_revenue)
            if previous_revenue is not None
            else None,
            "source_fact_ids": [facts[metric]["fact_id"] for metric in required]
            + ([facts["free_cash_flow"]["fact_id"]] if "free_cash_flow" in facts else []),
        }
        results.append(result)
    return {
        "formula_id": "margin_profile_v1",
        "status": "calculated" if any(row.get("status") == "calculated" for row in results) else "missing_required_facts",
        "annual_results": results,
        "note": "Primary display value is operating margin; gross, net, and FCF margins are included as supporting fields.",
    }


def _incremental_margin(annual: dict[int, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    results = []
    for year, facts in sorted(annual.items()):
        prior = annual.get(year - 1, {})
        required = ["revenue", "gross_profit", "operating_income"]
        missing = [metric for metric in required if metric not in facts or metric not in prior]
        if missing:
            results.append({"year": year, "status": "missing_required_facts", "missing": sorted(set(missing))})
            continue
        revenue_delta = facts["revenue"]["value"] - prior["revenue"]["value"]
        if revenue_delta == 0:
            results.append({"year": year, "status": "not_calculable_zero_revenue_delta"})
            continue
        free_cash_flow_delta = (
            facts["free_cash_flow"]["value"] - prior["free_cash_flow"]["value"]
            if "free_cash_flow" in facts and "free_cash_flow" in prior
            else None
        )
        results.append(
            {
                "year": year,
                "status": "calculated",
                "value": (facts["operating_income"]["value"] - prior["operating_income"]["value"]) / revenue_delta,
                "unit": "ratio",
                "formula": "change in operating_income / change in revenue",
                "revenue_delta": revenue_delta,
                "gross_profit_delta": facts["gross_profit"]["value"] - prior["gross_profit"]["value"],
                "operating_income_delta": facts["operating_income"]["value"] - prior["operating_income"]["value"],
                "free_cash_flow_delta": free_cash_flow_delta,
                "incremental_gross_margin": (facts["gross_profit"]["value"] - prior["gross_profit"]["value"]) / revenue_delta,
                "incremental_operating_margin": (facts["operating_income"]["value"] - prior["operating_income"]["value"]) / revenue_delta,
                "incremental_free_cash_flow_margin": _safe_div(free_cash_flow_delta, revenue_delta),
                "source_fact_ids": [facts[metric]["fact_id"] for metric in required]
                + [prior[metric]["fact_id"] for metric in required]
                + (
                    [facts["free_cash_flow"]["fact_id"], prior["free_cash_flow"]["fact_id"]]
                    if "free_cash_flow" in facts and "free_cash_flow" in prior
                    else []
                ),
            }
        )
    return {
        "formula_id": "incremental_margin_v1",
        "status": "calculated" if any(row.get("status") == "calculated" for row in results) else "missing_required_facts",
        "annual_results": results,
        "note": "Shows how much gross profit, operating income, and FCF changed for each additional RMB of revenue.",
    }


def _capital_intensity(annual: dict[int, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    results = []
    for year, facts in sorted(annual.items()):
        required = ["revenue", "operating_cash_flow", "capex", "free_cash_flow"]
        missing = [metric for metric in required if metric not in facts]
        if missing:
            results.append({"year": year, "status": "missing_required_facts", "missing": missing})
            continue
        revenue = facts["revenue"]["value"]
        operating_cash_flow = facts["operating_cash_flow"]["value"]
        capex = abs(facts["capex"]["value"])
        if revenue == 0:
            results.append({"year": year, "status": "not_calculable_zero_revenue"})
            continue
        results.append(
            {
                "year": year,
                "status": "calculated",
                "value": capex / revenue,
                "unit": "ratio",
                "formula": "capex / revenue",
                "capex_to_revenue": capex / revenue,
                "capex_to_operating_cash_flow": _safe_div(capex, operating_cash_flow),
                "free_cash_flow_margin": facts["free_cash_flow"]["value"] / revenue,
                "free_cash_flow_to_operating_cash_flow": _safe_div(facts["free_cash_flow"]["value"], operating_cash_flow),
                "source_fact_ids": [facts[metric]["fact_id"] for metric in required],
            }
        )
    return {
        "formula_id": "capital_intensity_v1",
        "status": "calculated" if any(row.get("status") == "calculated" for row in results) else "missing_required_facts",
        "annual_results": results,
        "note": "Uses capex as reported/extracted. Maintenance versus growth capex is not separated in V1.",
    }


def _balance_sheet_risk(annual: dict[int, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    results = []
    for year, facts in sorted(annual.items()):
        required = ["cash", "total_assets", "total_liabilities"]
        missing = [metric for metric in required if metric not in facts]
        if missing:
            results.append({"year": year, "status": "missing_required_facts", "missing": missing})
            continue
        cash = facts["cash"]["value"]
        liabilities = facts["total_liabilities"]["value"]
        assets = facts["total_assets"]["value"]
        debt_fact = facts.get("debt")
        debt = debt_fact["value"] if debt_fact else None
        restricted_cash_fact = facts.get("restricted_cash")
        short_term_investments_fact = facts.get("short_term_investments")
        current_assets_fact = facts.get("current_assets")
        current_liabilities_fact = facts.get("current_liabilities")
        debt_current_fact = facts.get("debt_current")
        debt_noncurrent_fact = facts.get("debt_noncurrent")
        debt_from_maturity = (
            (debt_current_fact["value"] if debt_current_fact else 0)
            + (debt_noncurrent_fact["value"] if debt_noncurrent_fact else 0)
            if debt_current_fact or debt_noncurrent_fact
            else None
        )
        debt_for_maturity = debt if debt is not None else debt_from_maturity
        liquid_assets = cash + (short_term_investments_fact["value"] if short_term_investments_fact else 0)
        convertible_facts = [
            fact
            for fact in (debt_fact, debt_current_fact, debt_noncurrent_fact)
            if fact and "convertible" in str(fact.get("xbrl_tag") or fact.get("label") or "").lower()
        ]
        result = {
            "year": year,
            "status": "calculated",
            "value": _safe_div(liabilities, assets),
            "unit": "ratio",
            "formula": "total_liabilities / total_assets",
            "cash_to_total_liabilities": _safe_div(cash, liabilities),
            "liquid_assets_to_total_liabilities": _safe_div(liquid_assets, liabilities),
            "liabilities_to_assets": _safe_div(liabilities, assets),
            "debt_to_cash": _safe_div(debt, cash) if debt is not None else None,
            "net_cash": cash - debt if debt is not None else None,
            "restricted_cash_to_cash": _safe_div(
                restricted_cash_fact["value"] if restricted_cash_fact else None,
                cash,
            ),
            "current_ratio": _safe_div(
                current_assets_fact["value"] if current_assets_fact else None,
                current_liabilities_fact["value"] if current_liabilities_fact else None,
            ),
            "current_debt_to_total_debt": _safe_div(
                debt_current_fact["value"] if debt_current_fact else None,
                debt_for_maturity,
            ),
            "noncurrent_debt_to_total_debt": _safe_div(
                debt_noncurrent_fact["value"] if debt_noncurrent_fact else None,
                debt_for_maturity,
            ),
            "debt_maturity_profile": _compact_values(
                {
                    "current_debt": debt_current_fact["value"] if debt_current_fact else None,
                    "noncurrent_debt": debt_noncurrent_fact["value"] if debt_noncurrent_fact else None,
                    "total_debt_for_maturity": debt_for_maturity,
                }
            ),
            "convertible_terms_status": "structured_convertible_debt_detected_terms_not_parsed"
            if convertible_facts
            else "not_detected_in_structured_facts",
            "missing_optional": [
                metric
                for metric, fact in {
                    "debt": debt_fact,
                    "restricted_cash": restricted_cash_fact,
                    "short_term_investments": short_term_investments_fact,
                    "current_assets": current_assets_fact,
                    "current_liabilities": current_liabilities_fact,
                    "debt_current": debt_current_fact,
                    "debt_noncurrent": debt_noncurrent_fact,
                }.items()
                if fact is None
            ],
            "source_fact_ids": [facts[metric]["fact_id"] for metric in required]
            + _source_fact_ids_for(
                facts,
                [
                    "debt",
                    "restricted_cash",
                    "short_term_investments",
                    "current_assets",
                    "current_liabilities",
                    "debt_current",
                    "debt_noncurrent",
                ],
            ),
        }
        results.append(result)
    return {
        "formula_id": "balance_sheet_risk_v1",
        "status": "calculated" if any(row.get("status") == "calculated" for row in results) else "missing_required_facts",
        "annual_results": results,
        "note": "Debt is treated as optional here; missing debt is reported as a limitation rather than assumed away.",
    }


def _share_based_compensation_burden(annual: dict[int, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    results = []
    for year, facts in sorted(annual.items()):
        required = ["stock_based_compensation", "revenue", "operating_cash_flow"]
        missing = [metric for metric in required if metric not in facts]
        if missing:
            results.append({"year": year, "status": "missing_required_facts", "missing": missing})
            continue
        previous_shares = _value(annual.get(year - 1, {}), "diluted_shares")
        current_shares = _value(facts, "diluted_shares")
        results.append(
            {
                "year": year,
                "status": "calculated",
                "value": facts["stock_based_compensation"]["value"] / facts["revenue"]["value"]
                if facts["revenue"]["value"] != 0
                else None,
                "unit": "ratio",
                "formula": "stock_based_compensation / revenue",
                "sbc_to_revenue": _safe_div(facts["stock_based_compensation"]["value"], facts["revenue"]["value"]),
                "sbc_to_operating_cash_flow": _safe_div(
                    facts["stock_based_compensation"]["value"], facts["operating_cash_flow"]["value"]
                ),
                "diluted_shares_yoy": _safe_div(current_shares - previous_shares, previous_shares)
                if current_shares is not None and previous_shares is not None
                else None,
                "source_fact_ids": [facts[metric]["fact_id"] for metric in required]
                + ([facts["diluted_shares"]["fact_id"]] if "diluted_shares" in facts else [])
                + ([annual[year - 1]["diluted_shares"]["fact_id"]] if "diluted_shares" in annual.get(year - 1, {}) else []),
            }
        )
    return {
        "formula_id": "share_based_compensation_burden_v1",
        "status": "calculated" if any(row.get("status") == "calculated" for row in results) else "missing_required_facts",
        "annual_results": results,
        "note": "SBC is measured against revenue and operating cash flow; dilution needs share-count history.",
    }


def _one_dollar_test() -> dict[str, Any]:
    return {
        "formula_id": "one_dollar_test_5y_v1",
        "status": "pending_market_cap_and_retained_earnings",
        "note": "Requires market capitalization history and retained earnings history.",
    }


def _unlevered_roic(annual: dict[int, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    invested_capital_by_year = _invested_capital_by_year(annual)

    results = []
    years = sorted(annual)
    for year in years:
        facts = annual[year]
        nopat_result = _nopat_for_year(facts)
        missing = list(nopat_result.get("missing", []))
        if year not in invested_capital_by_year:
            missing.append("invested_capital")
        previous_year = year - 1
        if previous_year not in invested_capital_by_year:
            missing.append("prior_year_invested_capital")
        if missing:
            results.append({"year": year, "status": "missing_required_facts", "missing": sorted(set(missing))})
            continue
        if nopat_result.get("status") == "not_calculable_nonpositive_pretax_income":
            results.append({"year": year, "status": "not_calculable_nonpositive_pretax_income"})
            continue
        nopat = nopat_result["nopat"]
        average_invested_capital = (
            invested_capital_by_year[year]["value"] + invested_capital_by_year[previous_year]["value"]
        ) / 2
        if average_invested_capital == 0:
            results.append({"year": year, "status": "not_calculable_zero_invested_capital"})
            continue
        results.append(
            {
                "year": year,
                "status": "calculated",
                "value": nopat / average_invested_capital,
                "unit": "ratio",
                "display_name": "unlevered ROIC proxy",
                "formula": "NOPAT / average invested capital",
                "tax_rate": nopat_result["tax_rate"],
                "nopat": nopat,
                "average_invested_capital": average_invested_capital,
                "invested_capital_formula": "total_assets - total_liabilities + interest_bearing_debt - cash",
                "used_zero_debt_assumption": invested_capital_by_year[year]["used_zero_debt_assumption"],
                "review_required": invested_capital_by_year[year]["used_zero_debt_assumption"],
                "limitations": [
                    "Invested capital is a financing-side proxy: equity plus interest-bearing debt less cash.",
                    "V1 subtracts all cash and does not separate excess cash, trapped cash, investments, leases, goodwill, or VIE-specific adjustments.",
                ],
                "source_fact_ids": [
                    *nopat_result["source_fact_ids"],
                    *invested_capital_by_year[year]["source_fact_ids"],
                    *invested_capital_by_year[previous_year]["source_fact_ids"],
                ],
            }
        )
    return {
        "formula_id": "unlevered_roic_v1",
        "status": "calculated" if any(row.get("status") == "calculated" for row in results) else "missing_required_facts",
        "annual_results": results,
        "note": "No threshold is applied. Years without explicit debt facts use a zero-debt assumption and are flagged.",
    }


def _incremental_roic_proxy(annual: dict[int, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    invested_capital_by_year = _invested_capital_by_year(annual)
    nopat_by_year: dict[int, dict[str, Any]] = {}
    for year, facts in sorted(annual.items()):
        nopat_result = _nopat_for_year(facts)
        if nopat_result.get("status") == "calculated":
            nopat_by_year[year] = nopat_result

    results = []
    for year in sorted(annual):
        previous_year = year - 1
        missing = []
        if year not in nopat_by_year:
            missing.append("nopat")
        if previous_year not in nopat_by_year:
            missing.append("prior_year_nopat")
        if year not in invested_capital_by_year:
            missing.append("invested_capital")
        if previous_year not in invested_capital_by_year:
            missing.append("prior_year_invested_capital")
        if missing:
            results.append({"year": year, "status": "missing_required_facts", "missing": sorted(set(missing))})
            continue
        delta_invested_capital = (
            invested_capital_by_year[year]["value"] - invested_capital_by_year[previous_year]["value"]
        )
        if delta_invested_capital == 0:
            results.append({"year": year, "status": "not_calculable_zero_incremental_invested_capital"})
            continue
        delta_nopat = nopat_by_year[year]["nopat"] - nopat_by_year[previous_year]["nopat"]
        results.append(
            {
                "year": year,
                "status": "calculated",
                "value": delta_nopat / delta_invested_capital,
                "unit": "ratio",
                "display_name": "incremental ROIC proxy",
                "formula": "change in NOPAT / change in invested capital",
                "delta_nopat": delta_nopat,
                "delta_invested_capital": delta_invested_capital,
                "used_zero_debt_assumption": invested_capital_by_year[year]["used_zero_debt_assumption"],
                "review_required": True,
                "interpretation_limit": "Proxy only. It can be noisy when invested capital is small, negative, or cash-heavy.",
                "source_fact_ids": [
                    *nopat_by_year[year]["source_fact_ids"],
                    *nopat_by_year[previous_year]["source_fact_ids"],
                    *invested_capital_by_year[year]["source_fact_ids"],
                    *invested_capital_by_year[previous_year]["source_fact_ids"],
                ],
            }
        )
    return {
        "formula_id": "incremental_roic_proxy_v1",
        "status": "calculated" if any(row.get("status") == "calculated" for row in results) else "missing_required_facts",
        "annual_results": results,
        "note": "Proxy for whether incremental capital is earning attractive returns; no threshold is applied.",
    }


def _latest_interim_trend(
    annual: dict[int, dict[str, dict[str, Any]]],
    quarterly: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    if not annual or not quarterly:
        return {
            "formula_id": "latest_interim_trend_v1",
            "status": "missing_required_facts",
            "overall_status": "trend_unclear",
            "missing": ["annual facts", "quarterly facts"],
            "note": "Requires both an annual baseline and at least one official quarterly/interim period.",
        }

    annual_year = max(annual)
    annual_facts = annual[annual_year]
    prior_annual_facts = annual.get(annual_year - 1, {})
    latest_period = sorted(quarterly)[-1]
    latest_facts = quarterly[latest_period]
    prior_period = f"{int(latest_period[:4]) - 1}{latest_period[4:]}"
    prior_quarter_facts = quarterly.get(prior_period, {})

    topic_results = [
        _trend_revenue_growth(annual_facts, prior_annual_facts, latest_facts, prior_quarter_facts),
        _trend_margin_quality(annual_facts, latest_facts, prior_quarter_facts),
        _trend_cash_conversion(annual_facts, latest_facts),
        _trend_balance_sheet(annual_facts, latest_facts),
        _trend_dilution(latest_facts, prior_quarter_facts),
    ]
    changed = [topic for topic in topic_results if topic["status"] == "trend_changed"]
    high_priority_changed = [
        topic for topic in changed if topic["topic"] in {"revenue_growth", "margin_quality", "cash_conversion"}
    ]
    unclear_high_priority = [
        topic
        for topic in topic_results
        if topic["topic"] in {"revenue_growth", "margin_quality", "cash_conversion"}
        and topic["status"] == "trend_unclear"
    ]
    if high_priority_changed:
        overall_status = "trend_changed"
    elif len(unclear_high_priority) >= 2:
        overall_status = "trend_unclear"
    elif all(
        topic["status"] == "trend_confirmed"
        for topic in topic_results
        if topic["topic"] in {"revenue_growth", "margin_quality", "cash_conversion"}
    ):
        overall_status = "trend_confirmed"
    elif changed:
        overall_status = "trend_changed"
    else:
        overall_status = "trend_unclear"

    directions = {topic.get("direction") for topic in changed if topic.get("direction")}
    if "negative" in directions and "positive" in directions:
        direction = "mixed"
    elif "negative" in directions:
        direction = "negative"
    elif "positive" in directions:
        direction = "positive"
    else:
        direction = "neutral_or_unclear"

    return {
        "formula_id": "latest_interim_trend_v1",
        "status": "calculated",
        "overall_status": overall_status,
        "direction": direction,
        "annual_anchor_year": annual_year,
        "latest_period_end": latest_period,
        "same_quarter_prior_period_end": prior_period if prior_quarter_facts else None,
        "topic_results": topic_results,
        "note": "Compares latest official quarter against the annual baseline and same-quarter prior year. Trend changed can be positive or negative; it means the quarterly update changes the annual-report baseline.",
    }


def _invested_capital_by_year(annual: dict[int, dict[str, dict[str, Any]]]) -> dict[int, dict[str, Any]]:
    invested_capital_by_year: dict[int, dict[str, Any]] = {}
    for year, facts in sorted(annual.items()):
        required = ["total_assets", "total_liabilities", "cash"]
        if any(metric not in facts for metric in required):
            continue
        debt = facts.get("debt", {"value": 0, "fact_id": "assumption:no_interest_bearing_debt_fact_found"})
        invested_capital_by_year[year] = {
            "value": facts["total_assets"]["value"] - facts["total_liabilities"]["value"] + debt["value"] - facts["cash"]["value"],
            "source_fact_ids": [facts[metric]["fact_id"] for metric in required] + [debt["fact_id"]],
            "used_zero_debt_assumption": "debt" not in facts,
        }
    return invested_capital_by_year


def _nopat_for_year(facts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    required = ["operating_income", "pretax_income", "tax_expense"]
    missing = [metric for metric in required if metric not in facts]
    if missing:
        return {"status": "missing_required_facts", "missing": missing}
    pretax_income = facts["pretax_income"]["value"]
    if pretax_income <= 0:
        return {"status": "not_calculable_nonpositive_pretax_income", "missing": []}
    tax_rate = facts["tax_expense"]["value"] / pretax_income
    return {
        "status": "calculated",
        "tax_rate": tax_rate,
        "nopat": facts["operating_income"]["value"] * (1 - tax_rate),
        "source_fact_ids": [facts[metric]["fact_id"] for metric in required],
    }


def _source_of_growth_result(
    *,
    period: int | str,
    facts: dict[str, dict[str, Any]],
    prior_facts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    period_fields = {"year": period} if isinstance(period, int) else {"period_end": period}
    if "revenue" not in facts:
        return {**period_fields, "status": "missing_required_facts", "missing": ["revenue"]}
    component_metrics = _revenue_component_metrics(facts)
    if not component_metrics:
        return {
            **period_fields,
            "status": "missing_required_facts",
            "missing": ["official segment/product/geography/take-rate revenue component facts"],
        }
    revenue = facts["revenue"]["value"]
    prior_revenue = _value(prior_facts, "revenue")
    revenue_delta = revenue - prior_revenue if prior_revenue is not None else None
    component_details = []
    attributed_revenue = 0.0
    for metric in component_metrics:
        value = facts[metric]["value"]
        prior_value = _value(prior_facts, metric)
        component_delta = value - prior_value if prior_value is not None else None
        attributed_revenue += value
        component_details.append(
            _compact_values(
                {
                    "metric": metric,
                    "value": value,
                    "share_of_revenue": _safe_div(value, revenue),
                    "yoy_growth": _growth_rate(value, prior_value),
                    "revenue_growth_contribution": _safe_div(component_delta, revenue_delta)
                    if revenue_delta not in {None, 0}
                    else None,
                    "delta": component_delta,
                }
            )
        )
    top_component = max(component_details, key=lambda row: abs(float(row.get("value") or 0)))
    return {
        **period_fields,
        "status": "calculated",
        "value": _safe_div(attributed_revenue, revenue),
        "unit": "ratio",
        "formula": "sum(official revenue components) / total revenue",
        "attributed_revenue": attributed_revenue,
        "unattributed_revenue": revenue - attributed_revenue,
        "revenue_growth_yoy": _growth_rate(revenue, prior_revenue),
        "top_component": top_component,
        "component_details": component_details,
        "warning_flags": _source_of_growth_warnings(attributed_revenue, revenue, component_details),
        "source_fact_ids": [facts["revenue"]["fact_id"]]
        + _source_fact_ids_for(facts, component_metrics)
        + _source_fact_ids_for(prior_facts, ["revenue"] + component_metrics),
    }


def _revenue_component_metrics(facts: dict[str, dict[str, Any]]) -> list[str]:
    configured = [metric for metric in REVENUE_COMPONENT_METRICS if metric in facts]
    dynamic = [
        metric
        for metric in facts
        if metric.endswith("_revenue")
        and metric != "revenue"
        and not metric.startswith("non_gaap_")
        and metric not in REVENUE_COMPONENT_EXCLUDE
        and metric not in configured
    ]
    return sorted(configured + dynamic)


def _working_capital_component_specs(
    facts: dict[str, dict[str, Any]],
    prior_facts: dict[str, dict[str, Any]],
) -> list[tuple[str, str]]:
    has_combined_payables = (
        "accounts_payable_and_accrued_expenses" in facts
        or "accounts_payable_and_accrued_expenses" in prior_facts
    )
    if not has_combined_payables:
        return WORKING_CAPITAL_COMPONENTS
    return [
        (metric, role)
        for metric, role in WORKING_CAPITAL_COMPONENTS
        if metric not in {"accounts_payable", "accrued_expenses"}
    ]


def _latest_non_gaap_bridge(
    quarterly: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any] | None:
    periods = [
        period
        for period, facts in quarterly.items()
        if any(str(metric).startswith("non_gaap_") for metric in facts)
    ]
    if not periods:
        return None
    period = sorted(periods)[-1]
    facts = quarterly[period]
    revenue = _value(facts, "revenue")
    gaap_operating_income = _value(facts, "operating_income")
    gaap_net_income = _value(facts, "net_income")
    non_gaap_operating_income = _value(facts, "non_gaap_operating_income")
    non_gaap_net_income = _value(facts, "non_gaap_net_income")
    adjustments = {
        metric: facts[metric]["value"]
        for metric in NON_GAAP_ADJUSTMENT_METRICS
        if metric in facts
    }
    adjustment_total = sum(abs(value) for value in adjustments.values())
    result = {
        "period_end": period,
        "status": "calculated",
        "value": _safe_div(
            non_gaap_net_income - gaap_net_income
            if non_gaap_net_income is not None and gaap_net_income is not None
            else None,
            abs(gaap_net_income) if gaap_net_income not in {None, 0} else None,
        ),
        "unit": "ratio",
        "formula": "(non_gaap_net_income - gaap_net_income) / abs(gaap_net_income)",
        "non_gaap_operating_income_uplift": _safe_div(
            non_gaap_operating_income - gaap_operating_income
            if non_gaap_operating_income is not None and gaap_operating_income is not None
            else None,
            abs(gaap_operating_income) if gaap_operating_income not in {None, 0} else None,
        ),
        "non_gaap_net_income_uplift": _safe_div(
            non_gaap_net_income - gaap_net_income
            if non_gaap_net_income is not None and gaap_net_income is not None
            else None,
            abs(gaap_net_income) if gaap_net_income not in {None, 0} else None,
        ),
        "non_gaap_adjustment_burden_to_revenue": _safe_div(adjustment_total, revenue),
        "adjustments": adjustments,
        "warning_flags": _non_gaap_warnings(
            non_gaap_net_income_uplift=_safe_div(
                non_gaap_net_income - gaap_net_income
                if non_gaap_net_income is not None and gaap_net_income is not None
                else None,
                abs(gaap_net_income) if gaap_net_income not in {None, 0} else None,
            ),
            adjustment_burden_to_revenue=_safe_div(adjustment_total, revenue),
        ),
        "source_fact_ids": _source_fact_ids_for(
            facts,
            [
                "revenue",
                "operating_income",
                "net_income",
                "non_gaap_operating_income",
                "non_gaap_net_income",
                *NON_GAAP_ADJUSTMENT_METRICS,
            ],
        ),
    }
    return result


def _trend_revenue_growth(
    annual_facts: dict[str, dict[str, Any]],
    prior_annual_facts: dict[str, dict[str, Any]],
    latest_facts: dict[str, dict[str, Any]],
    prior_quarter_facts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    annual_growth = _growth_rate(_value(annual_facts, "revenue"), _value(prior_annual_facts, "revenue"))
    quarter_growth = _growth_rate(_value(latest_facts, "revenue"), _value(prior_quarter_facts, "revenue"))
    values = {"annual_revenue_growth": annual_growth, "latest_quarter_revenue_yoy": quarter_growth}
    if annual_growth is None or quarter_growth is None:
        return _trend_topic("revenue_growth", "trend_unclear", "missing annual or same-quarter revenue growth", values)
    if quarter_growth < annual_growth - 0.10 or (quarter_growth < 0 and annual_growth > 0):
        return _trend_topic("revenue_growth", "trend_changed", "latest quarter revenue growth is materially weaker than the annual baseline", values, direction="negative")
    if quarter_growth > annual_growth + 0.15:
        return _trend_topic("revenue_growth", "trend_changed", "latest quarter revenue growth is materially stronger than the annual baseline", values, direction="positive")
    if abs(quarter_growth - annual_growth) <= 0.05:
        return _trend_topic("revenue_growth", "trend_confirmed", "latest quarter revenue growth is close to the annual baseline", values)
    return _trend_topic("revenue_growth", "trend_unclear", "latest quarter revenue growth differs from the annual baseline but not enough for a hard trend change", values)


def _trend_margin_quality(
    annual_facts: dict[str, dict[str, Any]],
    latest_facts: dict[str, dict[str, Any]],
    prior_quarter_facts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    annual_margin = _margin(annual_facts, "operating_income")
    latest_margin = _margin(latest_facts, "operating_income")
    prior_quarter_margin = _margin(prior_quarter_facts, "operating_income")
    margin_delta_yoy = latest_margin - prior_quarter_margin if latest_margin is not None and prior_quarter_margin is not None else None
    values = {
        "annual_operating_margin": annual_margin,
        "latest_quarter_operating_margin": latest_margin,
        "same_quarter_prior_operating_margin": prior_quarter_margin,
        "quarter_margin_delta_yoy": margin_delta_yoy,
    }
    if annual_margin is None or latest_margin is None or prior_quarter_margin is None:
        return _trend_topic("margin_quality", "trend_unclear", "missing annual or same-quarter operating margin", values)
    if margin_delta_yoy < -0.03 or latest_margin < annual_margin - 0.05:
        return _trend_topic("margin_quality", "trend_changed", "latest quarter margin is materially weaker than the annual baseline", values, direction="negative")
    if margin_delta_yoy > 0.05 and latest_margin > annual_margin + 0.03:
        return _trend_topic("margin_quality", "trend_changed", "latest quarter margin is materially stronger than the annual baseline", values, direction="positive")
    if margin_delta_yoy >= -0.02 and latest_margin >= annual_margin - 0.03:
        return _trend_topic("margin_quality", "trend_confirmed", "latest quarter margin is broadly consistent with the annual baseline", values)
    return _trend_topic("margin_quality", "trend_unclear", "latest quarter margin moved, but the signal is not decisive", values)


def _trend_cash_conversion(
    annual_facts: dict[str, dict[str, Any]],
    latest_facts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    annual_ratio = _safe_div(_value(annual_facts, "operating_cash_flow"), _value(annual_facts, "net_income"))
    latest_ratio = _safe_div(_value(latest_facts, "operating_cash_flow"), _value(latest_facts, "net_income"))
    values = {"annual_cfo_to_net_income": annual_ratio, "latest_quarter_cfo_to_net_income": latest_ratio}
    if annual_ratio is None or latest_ratio is None:
        return _trend_topic("cash_conversion", "trend_unclear", "missing annual or latest-quarter cash conversion", values)
    if latest_ratio < 0.8 and annual_ratio >= 1.0:
        return _trend_topic("cash_conversion", "trend_changed", "latest quarter cash conversion fell below the quality threshold", values, direction="negative")
    if latest_ratio < annual_ratio - 0.5:
        return _trend_topic("cash_conversion", "trend_changed", "latest quarter cash conversion is materially weaker than the annual baseline", values, direction="negative")
    if latest_ratio >= 1.2 and annual_ratio < 0.9:
        return _trend_topic("cash_conversion", "trend_changed", "latest quarter cash conversion is materially stronger than a weak annual baseline", values, direction="positive")
    if latest_ratio >= 0.8 and abs(latest_ratio - annual_ratio) <= 0.3:
        return _trend_topic("cash_conversion", "trend_confirmed", "latest quarter cash conversion is close to the annual baseline", values)
    return _trend_topic("cash_conversion", "trend_unclear", "latest quarter cash conversion is too noisy for a hard trend decision", values)


def _trend_balance_sheet(
    annual_facts: dict[str, dict[str, Any]],
    latest_facts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    annual_liabilities_assets = _safe_div(_value(annual_facts, "total_liabilities"), _value(annual_facts, "total_assets"))
    latest_liabilities_assets = _safe_div(_value(latest_facts, "total_liabilities"), _value(latest_facts, "total_assets"))
    annual_cash_liabilities = _safe_div(_value(annual_facts, "cash"), _value(annual_facts, "total_liabilities"))
    latest_cash_liabilities = _safe_div(_value(latest_facts, "cash"), _value(latest_facts, "total_liabilities"))
    values = {
        "annual_liabilities_to_assets": annual_liabilities_assets,
        "latest_quarter_liabilities_to_assets": latest_liabilities_assets,
        "annual_cash_to_liabilities": annual_cash_liabilities,
        "latest_quarter_cash_to_liabilities": latest_cash_liabilities,
    }
    if None in {annual_liabilities_assets, latest_liabilities_assets, annual_cash_liabilities, latest_cash_liabilities}:
        return _trend_topic("balance_sheet", "trend_unclear", "missing annual or latest-quarter balance-sheet ratios", values)
    if latest_liabilities_assets > annual_liabilities_assets + 0.05 or latest_cash_liabilities < annual_cash_liabilities * 0.8:
        return _trend_topic("balance_sheet", "trend_changed", "latest quarter balance sheet is materially weaker than the annual baseline", values, direction="negative")
    if latest_liabilities_assets < annual_liabilities_assets - 0.05 and latest_cash_liabilities > annual_cash_liabilities * 1.2:
        return _trend_topic("balance_sheet", "trend_changed", "latest quarter balance sheet is materially stronger than the annual baseline", values, direction="positive")
    return _trend_topic("balance_sheet", "trend_confirmed", "latest quarter balance sheet is broadly consistent with the annual baseline", values)


def _trend_dilution(
    latest_facts: dict[str, dict[str, Any]],
    prior_quarter_facts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    share_growth = _growth_rate(_value(latest_facts, "diluted_shares"), _value(prior_quarter_facts, "diluted_shares"))
    values = {"latest_quarter_diluted_shares_yoy": share_growth}
    if share_growth is None:
        return _trend_topic("dilution", "trend_unclear", "missing same-quarter diluted shares", values)
    if share_growth > 0.05:
        return _trend_topic("dilution", "trend_changed", "diluted share count increased by more than 5% YoY", values, direction="negative")
    if share_growth < -0.02:
        return _trend_topic("dilution", "trend_changed", "diluted share count declined by more than 2% YoY", values, direction="positive")
    if abs(share_growth) <= 0.02:
        return _trend_topic("dilution", "trend_confirmed", "dilution is within the 2% confirmation band", values)
    return _trend_topic("dilution", "trend_unclear", "dilution is above the confirmation band but below the hard change threshold", values)


def _trend_topic(
    topic: str,
    status: str,
    reason: str,
    values: dict[str, Any],
    *,
    direction: str = "neutral_or_unclear",
) -> dict[str, Any]:
    return {
        "topic": topic,
        "status": status,
        "direction": direction,
        "reason": reason,
        "values": _compact_values(values),
    }


def _margin(facts: dict[str, dict[str, Any]], numerator_metric: str) -> float | None:
    return _safe_div(_value(facts, numerator_metric), _value(facts, "revenue"))


def _source_fact_ids_for(
    facts: dict[str, dict[str, Any]],
    metrics: list[str],
) -> list[str]:
    return [facts[metric]["fact_id"] for metric in metrics if metric in facts]


def _growth_rate(current: float | int | None, previous: float | int | None) -> float | None:
    if current is None or previous in {None, 0}:
        return None
    return (current - previous) / previous


def _safe_div(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in {None, 0}:
        return None
    return numerator / denominator


def _compact_values(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _working_capital_warnings(
    component_details: list[dict[str, Any]],
    working_capital_cash_tailwind: float | None,
) -> list[str]:
    warnings = []
    for component in component_details:
        growth_gap = component.get("growth_minus_revenue_growth")
        if growth_gap is None:
            continue
        metric = component.get("metric")
        role = component.get("role")
        if role == "cash_use_asset" and growth_gap > 0.10:
            warnings.append(f"{metric} grew more than 10 percentage points faster than revenue.")
        if role == "cash_source_liability" and growth_gap > 0.20:
            warnings.append(f"{metric} grew more than 20 percentage points faster than revenue; cash flow may have a working-capital tailwind.")
    if working_capital_cash_tailwind is not None and working_capital_cash_tailwind > 0.05:
        warnings.append("Working-capital source liabilities added more than 5% of revenue to cash-flow tailwind.")
    if working_capital_cash_tailwind is not None and working_capital_cash_tailwind < -0.05:
        warnings.append("Working-capital changes consumed more than 5% of revenue.")
    return warnings


def _tax_accounting_warnings(
    *,
    effective_tax_rate: float | None,
    cash_tax_to_tax_expense: float | None,
    investment_income_to_pretax: float | None,
    impairment_to_revenue: float | None,
) -> list[str]:
    warnings = []
    if effective_tax_rate is not None and (effective_tax_rate < 0.05 or effective_tax_rate > 0.35):
        warnings.append("Effective tax rate is outside the 5%-35% default review band.")
    if cash_tax_to_tax_expense is not None and cash_tax_to_tax_expense < 0.5:
        warnings.append("Cash taxes are less than half of reported tax expense.")
    if investment_income_to_pretax is not None and abs(investment_income_to_pretax) > 0.2:
        warnings.append("Investment income/loss is more than 20% of pretax income.")
    if impairment_to_revenue is not None and abs(impairment_to_revenue) > 0.05:
        warnings.append("Impairment charges exceed 5% of revenue.")
    return warnings


def _non_gaap_warnings(
    *,
    non_gaap_net_income_uplift: float | None,
    adjustment_burden_to_revenue: float | None,
) -> list[str]:
    warnings = []
    if non_gaap_net_income_uplift is not None and non_gaap_net_income_uplift > 0.2:
        warnings.append("Non-GAAP net income is more than 20% above GAAP net income.")
    if adjustment_burden_to_revenue is not None and adjustment_burden_to_revenue > 0.1:
        warnings.append("Non-GAAP adjustments exceed 10% of revenue.")
    return warnings


def _source_of_growth_warnings(
    attributed_revenue: float,
    revenue: float | int,
    component_details: list[dict[str, Any]],
) -> list[str]:
    warnings = []
    coverage = _safe_div(attributed_revenue, revenue)
    if coverage is not None and coverage < 0.75:
        warnings.append("Official revenue components explain less than 75% of revenue.")
    for component in component_details:
        contribution = component.get("revenue_growth_contribution")
        if contribution is not None and abs(contribution) > 1.2:
            warnings.append(f"{component.get('metric')} contribution to revenue growth is unusually large or offset by other components.")
    return warnings


def _value(facts: dict[str, dict[str, Any]], metric: str) -> float | int | None:
    fact = facts.get(metric)
    return fact.get("value") if fact else None


def _latest_fact(
    annual: dict[int, dict[str, dict[str, Any]]],
    metric: str,
) -> tuple[int, dict[str, Any]] | None:
    for year in sorted(annual, reverse=True):
        fact = annual[year].get(metric)
        if fact is not None:
            return year, fact
    return None


def _latest_calculated_result(metric: dict[str, Any]) -> dict[str, Any] | None:
    calculated = [
        result for result in metric.get("annual_results", []) if result.get("status") == "calculated"
    ]
    if not calculated:
        return None
    return sorted(calculated, key=lambda result: result.get("year", 0))[-1]


def _fact_preference_key(fact: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(fact.get("filing_date") or ""),
        str(fact.get("accession_number") or ""),
        str(fact.get("downloaded_file") or ""),
    )


def _quarter_label(period_end: str) -> str:
    year = period_end[:4]
    month = period_end[5:7]
    quarter = {"03": "Q1", "06": "Q2", "09": "Q3", "12": "Q4"}.get(month, "Q?")
    return f"{year} {quarter}"
