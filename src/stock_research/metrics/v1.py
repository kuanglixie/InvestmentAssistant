from __future__ import annotations

from collections import defaultdict
from typing import Any

from stock_research.valuation.market_inputs import market_cap_in_cny


def calculate_v1_metrics(
    extracted_facts: list[dict[str, Any]],
    *,
    market_inputs: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    annual = _annual_cny_fact_map(extracted_facts)
    owner_earnings = _owner_earnings(annual)
    enterprise_value = _enterprise_value(annual, market_inputs or {})
    margin_profile = _margin_profile(annual)
    incremental_margin = _incremental_margin(annual)
    capital_intensity = _capital_intensity(annual)
    balance_sheet_risk = _balance_sheet_risk(annual)
    sbc_burden = _share_based_compensation_burden(annual)
    cash_conversion = _cash_conversion(annual)
    roic = _unlevered_roic(annual)
    incremental_roic = _incremental_roic_proxy(annual)
    financial_quality = _financial_quality_questions(
        annual,
        margin_profile=margin_profile,
        incremental_margin=incremental_margin,
        capital_intensity=capital_intensity,
        balance_sheet_risk=balance_sheet_risk,
        sbc_burden=sbc_burden,
        cash_conversion=cash_conversion,
        owner_earnings=owner_earnings,
        roic=roic,
        incremental_roic=incremental_roic,
    )
    metrics = [
        financial_quality,
        margin_profile,
        incremental_margin,
        capital_intensity,
        balance_sheet_risk,
        sbc_burden,
        owner_earnings,
        enterprise_value,
        _true_yield(owner_earnings, enterprise_value),
        _free_cash_flow_yield(annual, enterprise_value),
        cash_conversion,
        _one_dollar_test(),
        roic,
        incremental_roic,
    ]
    return metrics


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
                "debt": _value(by_metric, "debt"),
                "stock_based_compensation": _value(by_metric, "stock_based_compensation"),
                "diluted_shares": _value(by_metric, "diluted_shares"),
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
                "cash": _value(by_metric, "cash"),
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
        if unit not in {"CNY", "shares"} or metric not in {"cash", "total_assets", "total_liabilities"}:
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
                "formula": "operating_cash_flow - stock_based_compensation - depreciation_and_amortization",
                "assumption": "V1 uses D&A as the maintenance CapEx approximation.",
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
                "formula": "owner_earnings / enterprise_value",
                "owner_earnings": owner_result["value"],
                "enterprise_value": ev_result["value"],
                "enterprise_value_year": ev_result.get("year"),
                "as_of_date": ev_result.get("as_of_date"),
                "review_required": ev_result.get("review_required", True),
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
                "formula": "free_cash_flow / enterprise_value",
                "free_cash_flow": fcf_fact["value"],
                "enterprise_value": ev_result["value"],
                "enterprise_value_year": ev_result.get("year"),
                "as_of_date": ev_result.get("as_of_date"),
                "review_required": ev_result.get("review_required", True),
                "source_fact_ids": [fcf_fact["fact_id"]] + ev_result.get("source_fact_ids", []),
            }
        ],
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
                "formula": "operating_cash_flow / net_income",
                "source_fact_ids": [facts[metric]["fact_id"] for metric in required],
            }
        )
    return {
        "formula_id": "cash_conversion_ratio_v1",
        "status": "calculated" if any(row.get("status") == "calculated" for row in results) else "missing_required_facts",
        "annual_results": results,
    }


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
        result = {
            "year": year,
            "status": "calculated",
            "value": _safe_div(liabilities, assets),
            "unit": "ratio",
            "formula": "total_liabilities / total_assets",
            "cash_to_total_liabilities": _safe_div(cash, liabilities),
            "liabilities_to_assets": _safe_div(liabilities, assets),
            "debt_to_cash": _safe_div(debt, cash) if debt is not None else None,
            "net_cash": cash - debt if debt is not None else None,
            "missing_optional": [] if debt_fact else ["debt"],
            "source_fact_ids": [facts[metric]["fact_id"] for metric in required]
            + ([debt_fact["fact_id"]] if debt_fact else []),
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
                "formula": "NOPAT / average invested capital",
                "tax_rate": nopat_result["tax_rate"],
                "nopat": nopat,
                "average_invested_capital": average_invested_capital,
                "invested_capital_formula": "total_assets - total_liabilities + interest_bearing_debt - cash",
                "used_zero_debt_assumption": invested_capital_by_year[year]["used_zero_debt_assumption"],
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
                "formula": "change in NOPAT / change in invested capital",
                "delta_nopat": delta_nopat,
                "delta_invested_capital": delta_invested_capital,
                "used_zero_debt_assumption": invested_capital_by_year[year]["used_zero_debt_assumption"],
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


def _financial_quality_questions(
    annual: dict[int, dict[str, dict[str, Any]]],
    *,
    margin_profile: dict[str, Any],
    incremental_margin: dict[str, Any],
    capital_intensity: dict[str, Any],
    balance_sheet_risk: dict[str, Any],
    sbc_burden: dict[str, Any],
    cash_conversion: dict[str, Any],
    owner_earnings: dict[str, Any],
    roic: dict[str, Any],
    incremental_roic: dict[str, Any],
) -> dict[str, Any]:
    latest_margin = _latest_calculated_result(margin_profile)
    latest_incremental_margin = _latest_calculated_result(incremental_margin)
    latest_capital_intensity = _latest_calculated_result(capital_intensity)
    latest_balance_sheet_risk = _latest_calculated_result(balance_sheet_risk)
    latest_sbc_burden = _latest_calculated_result(sbc_burden)
    latest_cash_conversion = _latest_calculated_result(cash_conversion)
    latest_owner_earnings = _latest_calculated_result(owner_earnings)
    latest_roic = _latest_calculated_result(roic)
    latest_incremental_roic = _latest_calculated_result(incremental_roic)

    questions = [
        {
            "rank": 1,
            "question_id": "growth_quality",
            "question": "收入增长来自哪里？增长质量好吗？",
            "priority": "highest",
            "status": "partial" if latest_margin else "missing",
            "current_answer": _growth_quality_answer(latest_margin, latest_incremental_margin),
            "metrics_used": [
                "revenue_growth_yoy",
                "gross_margin",
                "operating_margin",
                "incremental_operating_margin",
                "incremental_free_cash_flow_margin",
            ],
            "latest_values": _compact_values(
                {
                    "year": latest_margin.get("year") if latest_margin else None,
                    "revenue_growth_yoy": latest_margin.get("revenue_growth_yoy") if latest_margin else None,
                    "gross_margin": latest_margin.get("gross_margin") if latest_margin else None,
                    "operating_margin": latest_margin.get("operating_margin") if latest_margin else None,
                    "incremental_operating_margin": latest_incremental_margin.get("incremental_operating_margin")
                    if latest_incremental_margin
                    else None,
                    "incremental_free_cash_flow_margin": latest_incremental_margin.get("incremental_free_cash_flow_margin")
                    if latest_incremental_margin
                    else None,
                }
            ),
            "warning_flags": _growth_quality_warnings(latest_margin, latest_incremental_margin),
            "missing": ["revenue attribution by platform/product/geography", "merchant cohort economics"],
            "interpretation_limit": "The metrics agent can judge growth quality, but source-of-growth attribution belongs to financial extraction and business-model agents.",
        },
        {
            "rank": 2,
            "question_id": "profitability_with_scale",
            "question": "规模变大以后利润率是上升还是下降？",
            "priority": "highest",
            "status": "answered" if latest_margin and latest_incremental_margin else "partial",
            "current_answer": _profitability_with_scale_answer(latest_margin, latest_incremental_margin),
            "metrics_used": ["gross_margin", "operating_margin", "net_margin", "incremental_margin"],
            "latest_values": _compact_values(
                {
                    "year": latest_margin.get("year") if latest_margin else None,
                    "gross_margin": latest_margin.get("gross_margin") if latest_margin else None,
                    "operating_margin": latest_margin.get("operating_margin") if latest_margin else None,
                    "net_margin": latest_margin.get("net_margin") if latest_margin else None,
                    "incremental_gross_margin": latest_incremental_margin.get("incremental_gross_margin")
                    if latest_incremental_margin
                    else None,
                    "incremental_operating_margin": latest_incremental_margin.get("incremental_operating_margin")
                    if latest_incremental_margin
                    else None,
                }
            ),
            "warning_flags": _margin_warnings(latest_margin, latest_incremental_margin),
            "missing": [],
            "interpretation_limit": "Margin trend does not prove moat; it only shows whether scale is currently flowing through to profits.",
        },
        {
            "rank": 3,
            "question_id": "cash_profit_quality",
            "question": "这个公司赚的钱是真钱吗？现金流质量好不好？",
            "priority": "highest",
            "status": "answered" if latest_cash_conversion else "partial",
            "current_answer": _cash_profit_quality_answer(latest_cash_conversion, latest_owner_earnings, latest_sbc_burden),
            "metrics_used": [
                "operating_cash_flow / net_income",
                "free_cash_flow_margin",
                "owner_earnings_v1",
                "SBC / operating_cash_flow",
            ],
            "latest_values": _compact_values(
                {
                    "year": latest_cash_conversion.get("year") if latest_cash_conversion else None,
                    "cash_conversion": latest_cash_conversion.get("value") if latest_cash_conversion else None,
                    "owner_earnings": latest_owner_earnings.get("value") if latest_owner_earnings else None,
                    "sbc_to_operating_cash_flow": latest_sbc_burden.get("sbc_to_operating_cash_flow")
                    if latest_sbc_burden
                    else None,
                }
            ),
            "warning_flags": _cash_profit_warnings(latest_cash_conversion, latest_sbc_burden),
            "missing": ["receivables/payables/inventory/deferred-revenue working-capital bridge"],
            "interpretation_limit": "V1 cash quality uses OCF, FCF, owner earnings, and SBC; a full working-capital bridge is a later extraction upgrade.",
        },
        {
            "rank": 4,
            "question_id": "capital_needed_for_growth",
            "question": "增长需要消耗多少资本？资本效率有没有变差？",
            "priority": "high",
            "status": "answered" if latest_capital_intensity else "partial",
            "current_answer": _capital_need_answer(latest_capital_intensity, latest_roic, latest_incremental_roic),
            "metrics_used": ["capex / revenue", "capex / operating_cash_flow", "free_cash_flow_margin", "ROIC", "incremental ROIC proxy"],
            "latest_values": _compact_values(
                {
                    "year": latest_capital_intensity.get("year") if latest_capital_intensity else None,
                    "capex_to_revenue": latest_capital_intensity.get("capex_to_revenue") if latest_capital_intensity else None,
                    "capex_to_operating_cash_flow": latest_capital_intensity.get("capex_to_operating_cash_flow")
                    if latest_capital_intensity
                    else None,
                    "free_cash_flow_margin": latest_capital_intensity.get("free_cash_flow_margin")
                    if latest_capital_intensity
                    else None,
                    "roic": latest_roic.get("value") if latest_roic else None,
                    "incremental_roic_proxy": latest_incremental_roic.get("value") if latest_incremental_roic else None,
                }
            ),
            "warning_flags": _capital_need_warnings(latest_capital_intensity, latest_incremental_roic),
            "missing": ["maintenance capex versus growth capex"],
            "interpretation_limit": "V1 cannot yet separate maintenance and growth capex, so owner-earnings quality remains approximate.",
        },
        {
            "rank": 5,
            "question_id": "balance_sheet_resilience",
            "question": "资产负债表风险大不大？公司能不能扛住坏年份？",
            "priority": "high",
            "status": "answered" if latest_balance_sheet_risk else "missing",
            "current_answer": _balance_sheet_answer(latest_balance_sheet_risk),
            "metrics_used": ["cash / total liabilities", "liabilities / assets", "debt / cash", "net cash"],
            "latest_values": _compact_values(
                {
                    "year": latest_balance_sheet_risk.get("year") if latest_balance_sheet_risk else None,
                    "cash_to_total_liabilities": latest_balance_sheet_risk.get("cash_to_total_liabilities")
                    if latest_balance_sheet_risk
                    else None,
                    "liabilities_to_assets": latest_balance_sheet_risk.get("liabilities_to_assets")
                    if latest_balance_sheet_risk
                    else None,
                    "debt_to_cash": latest_balance_sheet_risk.get("debt_to_cash") if latest_balance_sheet_risk else None,
                    "net_cash": latest_balance_sheet_risk.get("net_cash") if latest_balance_sheet_risk else None,
                }
            ),
            "warning_flags": _balance_sheet_warnings(latest_balance_sheet_risk),
            "missing": latest_balance_sheet_risk.get("missing_optional", []) if latest_balance_sheet_risk else ["cash", "assets", "liabilities"],
            "interpretation_limit": "Balance-sheet ratios do not address trapped cash, VIE structure, or capital-control risk.",
        },
        {
            "rank": 6,
            "question_id": "sbc_and_per_share_quality",
            "question": "增长有没有被股权激励和稀释吃掉？",
            "priority": "medium",
            "status": "partial" if latest_sbc_burden else "missing",
            "current_answer": _sbc_answer(latest_sbc_burden),
            "metrics_used": ["SBC / revenue", "SBC / operating cash flow", "diluted shares YoY"],
            "latest_values": _compact_values(
                {
                    "year": latest_sbc_burden.get("year") if latest_sbc_burden else None,
                    "sbc_to_revenue": latest_sbc_burden.get("sbc_to_revenue") if latest_sbc_burden else None,
                    "sbc_to_operating_cash_flow": latest_sbc_burden.get("sbc_to_operating_cash_flow")
                    if latest_sbc_burden
                    else None,
                    "diluted_shares_yoy": latest_sbc_burden.get("diluted_shares_yoy") if latest_sbc_burden else None,
                }
            ),
            "warning_flags": _sbc_warnings(latest_sbc_burden),
            "missing": ["buyback offset analysis", "full per-ADS dilution bridge"],
            "interpretation_limit": "SBC is not automatically bad, but it must be measured against cash generation and per-share value.",
        },
    ]
    return {
        "formula_id": "financial_quality_questions_v1",
        "status": "calculated" if any(question["status"] != "missing" for question in questions) else "missing_required_facts",
        "questions": questions,
        "note": "Ranked question layer for the Financial Metrics Agent. Metrics are ordered by value-investor decision usefulness.",
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


def _safe_div(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in {None, 0}:
        return None
    return numerator / denominator


def _compact_values(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _pct_text(value: Any) -> str:
    if value is None:
        return "not available"
    return f"{float(value) * 100:.1f}%"


def _ratio_text(value: Any) -> str:
    if value is None:
        return "not available"
    return f"{float(value):.2f}x"


def _growth_quality_answer(
    margin: dict[str, Any] | None,
    incremental_margin: dict[str, Any] | None,
) -> str:
    if not margin:
        return "Missing. Revenue and margin facts are required before growth quality can be judged."
    revenue_growth = margin.get("revenue_growth_yoy")
    incremental_operating_margin = incremental_margin.get("incremental_operating_margin") if incremental_margin else None
    return (
        f"Partial. Latest revenue growth is {_pct_text(revenue_growth)} and operating margin is "
        f"{_pct_text(margin.get('operating_margin'))}; incremental operating margin is "
        f"{_pct_text(incremental_operating_margin)}. This answers whether growth is profitable, but not yet exactly where growth came from."
    )


def _profitability_with_scale_answer(
    margin: dict[str, Any] | None,
    incremental_margin: dict[str, Any] | None,
) -> str:
    if not margin:
        return "Missing. Revenue, gross profit, operating income, and net income are required."
    return (
        f"Latest gross margin is {_pct_text(margin.get('gross_margin'))}, operating margin is "
        f"{_pct_text(margin.get('operating_margin'))}, and net margin is {_pct_text(margin.get('net_margin'))}. "
        f"Incremental operating margin is {_pct_text(incremental_margin.get('incremental_operating_margin') if incremental_margin else None)}."
    )


def _cash_profit_quality_answer(
    cash_conversion: dict[str, Any] | None,
    owner_earnings: dict[str, Any] | None,
    sbc_burden: dict[str, Any] | None,
) -> str:
    if not cash_conversion:
        return "Missing. Net income and operating cash flow are required."
    owner_text = "available" if owner_earnings else "not available"
    return (
        f"Latest cash conversion is {_ratio_text(cash_conversion.get('value'))}. "
        f"Owner earnings are {owner_text}; SBC consumed "
        f"{_pct_text(sbc_burden.get('sbc_to_operating_cash_flow') if sbc_burden else None)} of operating cash flow."
    )


def _capital_need_answer(
    capital_intensity: dict[str, Any] | None,
    roic: dict[str, Any] | None,
    incremental_roic: dict[str, Any] | None,
) -> str:
    if not capital_intensity:
        return "Missing. Revenue, operating cash flow, capex, and free cash flow are required."
    return (
        f"Latest capex/revenue is {_pct_text(capital_intensity.get('capex_to_revenue'))}; "
        f"FCF margin is {_pct_text(capital_intensity.get('free_cash_flow_margin'))}; "
        f"ROIC is {_pct_text(roic.get('value') if roic else None)}; incremental ROIC proxy is "
        f"{_pct_text(incremental_roic.get('value') if incremental_roic else None)}."
    )


def _balance_sheet_answer(balance_sheet: dict[str, Any] | None) -> str:
    if not balance_sheet:
        return "Missing. Cash, total assets, and total liabilities are required."
    return (
        f"Latest liabilities/assets is {_pct_text(balance_sheet.get('liabilities_to_assets'))}; "
        f"cash/total liabilities is {_ratio_text(balance_sheet.get('cash_to_total_liabilities'))}; "
        f"debt/cash is {_ratio_text(balance_sheet.get('debt_to_cash'))}."
    )


def _sbc_answer(sbc_burden: dict[str, Any] | None) -> str:
    if not sbc_burden:
        return "Missing. SBC, revenue, and operating cash flow are required."
    return (
        f"Latest SBC/revenue is {_pct_text(sbc_burden.get('sbc_to_revenue'))}; "
        f"SBC/operating cash flow is {_pct_text(sbc_burden.get('sbc_to_operating_cash_flow'))}; "
        f"diluted share growth is {_pct_text(sbc_burden.get('diluted_shares_yoy'))}."
    )


def _growth_quality_warnings(
    margin: dict[str, Any] | None,
    incremental_margin: dict[str, Any] | None,
) -> list[str]:
    warnings = []
    if margin and margin.get("revenue_growth_yoy") is not None and margin.get("revenue_growth_yoy") < 0:
        warnings.append("Revenue declined year over year.")
    if incremental_margin and (incremental_margin.get("incremental_operating_margin") or 0) < 0:
        warnings.append("Incremental operating margin is negative.")
    if incremental_margin and incremental_margin.get("incremental_free_cash_flow_margin") is not None and incremental_margin["incremental_free_cash_flow_margin"] < 0:
        warnings.append("Incremental FCF margin is negative.")
    return warnings


def _margin_warnings(
    margin: dict[str, Any] | None,
    incremental_margin: dict[str, Any] | None,
) -> list[str]:
    warnings = []
    if margin and (margin.get("operating_margin") or 0) < 0:
        warnings.append("Operating margin is negative.")
    if incremental_margin and (incremental_margin.get("incremental_operating_margin") or 0) < (margin.get("operating_margin") if margin else 0):
        warnings.append("Incremental operating margin is below latest operating margin.")
    return warnings


def _cash_profit_warnings(
    cash_conversion: dict[str, Any] | None,
    sbc_burden: dict[str, Any] | None,
) -> list[str]:
    warnings = []
    if cash_conversion and cash_conversion.get("value") is not None and cash_conversion["value"] < 1:
        warnings.append("Operating cash flow is below net income.")
    if sbc_burden and sbc_burden.get("sbc_to_operating_cash_flow") is not None and sbc_burden["sbc_to_operating_cash_flow"] > 0.2:
        warnings.append("SBC consumes more than 20% of operating cash flow.")
    return warnings


def _capital_need_warnings(
    capital_intensity: dict[str, Any] | None,
    incremental_roic: dict[str, Any] | None,
) -> list[str]:
    warnings = []
    if capital_intensity and capital_intensity.get("free_cash_flow_margin") is not None and capital_intensity["free_cash_flow_margin"] < 0:
        warnings.append("Free cash flow margin is negative.")
    if incremental_roic and incremental_roic.get("delta_invested_capital") is not None and incremental_roic["delta_invested_capital"] <= 0:
        warnings.append("Incremental ROIC proxy is hard to interpret because invested capital did not increase.")
    return warnings


def _balance_sheet_warnings(balance_sheet: dict[str, Any] | None) -> list[str]:
    warnings = []
    if not balance_sheet:
        return warnings
    if balance_sheet.get("cash_to_total_liabilities") is not None and balance_sheet["cash_to_total_liabilities"] < 0.5:
        warnings.append("Cash covers less than half of total liabilities.")
    if balance_sheet.get("liabilities_to_assets") is not None and balance_sheet["liabilities_to_assets"] > 0.7:
        warnings.append("Liabilities exceed 70% of assets.")
    if balance_sheet.get("missing_optional"):
        warnings.append("Explicit debt fact is missing for this year.")
    return warnings


def _sbc_warnings(sbc_burden: dict[str, Any] | None) -> list[str]:
    warnings = []
    if not sbc_burden:
        return warnings
    if sbc_burden.get("sbc_to_revenue") is not None and sbc_burden["sbc_to_revenue"] > 0.1:
        warnings.append("SBC exceeds 10% of revenue.")
    if sbc_burden.get("diluted_shares_yoy") is not None and sbc_burden["diluted_shares_yoy"] > 0.05:
        warnings.append("Diluted shares increased by more than 5% year over year.")
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
