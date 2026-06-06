from __future__ import annotations

from typing import Any


def run_v1_financial_diagnostics(
    *,
    extracted_facts: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    metric_map = {metric.get("formula_id"): metric for metric in metrics}
    latest = {
        formula_id: _latest_calculated_result(metric)
        for formula_id, metric in metric_map.items()
    }
    latest_source_of_growth = latest.get("source_of_growth_attribution_v1")
    source_growth_metric = metric_map.get("source_of_growth_attribution_v1") or {}
    if latest_source_of_growth is None and (source_growth_metric.get("latest_interim_result") or {}).get("status") == "calculated":
        latest_source_of_growth = source_growth_metric["latest_interim_result"]

    latest_tax_accounting = latest.get("tax_non_gaap_accounting_quality_v1")
    tax_metric = metric_map.get("tax_non_gaap_accounting_quality_v1") or {}
    latest_non_gaap = tax_metric.get("latest_interim_non_gaap")

    questions = [
        _growth_quality_question(
            latest.get("margin_profile_v1"),
            latest.get("incremental_margin_v1"),
            latest_source_of_growth,
        ),
        _profitability_with_scale_question(
            latest.get("margin_profile_v1"),
            latest.get("incremental_margin_v1"),
        ),
        _cash_profit_quality_question(
            latest.get("cash_conversion_ratio_v1"),
            latest.get("owner_earnings_v1"),
            latest.get("share_based_compensation_burden_v1"),
            latest.get("working_capital_quality_v1"),
        ),
        _capital_needed_question(
            latest.get("capital_intensity_v1"),
            latest.get("unlevered_roic_v1"),
            latest.get("incremental_roic_proxy_v1"),
        ),
        _balance_sheet_question(latest.get("balance_sheet_risk_v1")),
        _sbc_question(latest.get("share_based_compensation_burden_v1")),
        _tax_non_gaap_question(latest_tax_accounting, latest_non_gaap),
    ]
    answered = [question for question in questions if question["status"] == "answered"]
    partial = [question for question in questions if question["status"] == "partial"]
    missing = [question for question in questions if question["status"] == "missing"]
    warning_flags = [
        {"question_id": question["question_id"], "warning": warning}
        for question in questions
        for warning in question.get("warning_flags", [])
    ]
    return {
        "diagnostic_id": "financial_diagnostic_rules_v1",
        "status": "calculated" if answered or partial else "missing_required_inputs",
        "source": "deterministic_financial_metric_rules",
        "questions": questions,
        "summary": {
            "questions_total": len(questions),
            "answered": len(answered),
            "partial": len(partial),
            "missing": len(missing),
            "warning_flags": len(warning_flags),
            "metric_families_used": sorted(metric_map),
            "extracted_fact_count": len(extracted_facts),
        },
        "warning_flags": warning_flags,
        "note": "Diagnostics turn calculated financial metrics into reading questions, warnings, and follow-up checks. They do not calculate metrics or valuation.",
    }


def _growth_quality_question(
    margin: dict[str, Any] | None,
    incremental_margin: dict[str, Any] | None,
    source_of_growth: dict[str, Any] | None,
) -> dict[str, Any]:
    status = "answered" if margin and source_of_growth else ("partial" if margin else "missing")
    missing = ["merchant cohort economics"] if source_of_growth else [
        "segment/product/geography/take-rate revenue facts",
        "merchant cohort economics",
    ]
    return {
        "rank": 1,
        "question_id": "growth_quality",
        "question": "收入增长来自哪里？增长质量好吗？",
        "priority": "highest",
        "status": status,
        "current_answer": _growth_quality_answer(margin, incremental_margin, source_of_growth),
        "metrics_used": [
            "revenue_growth_yoy",
            "revenue component share",
            "revenue component growth contribution",
            "gross_margin",
            "operating_margin",
            "incremental_operating_margin",
            "incremental_free_cash_flow_margin",
        ],
        "latest_values": _compact_values(
            {
                "year": margin.get("year") if margin else None,
                "revenue_growth_yoy": margin.get("revenue_growth_yoy") if margin else None,
                "gross_margin": margin.get("gross_margin") if margin else None,
                "operating_margin": margin.get("operating_margin") if margin else None,
                "incremental_operating_margin": incremental_margin.get("incremental_operating_margin")
                if incremental_margin
                else None,
                "incremental_free_cash_flow_margin": incremental_margin.get("incremental_free_cash_flow_margin")
                if incremental_margin
                else None,
                "revenue_attribution_coverage": source_of_growth.get("value") if source_of_growth else None,
                "top_revenue_component": source_of_growth.get("top_component", {}).get("metric")
                if source_of_growth
                else None,
            }
        ),
        "warning_flags": _growth_quality_warnings(margin, incremental_margin),
        "missing": missing,
        "interpretation_limit": "Source-of-growth attribution uses only official extracted revenue component facts. Missing segment/product/geography/take-rate fields remain evidence gaps.",
    }


def _profitability_with_scale_question(
    margin: dict[str, Any] | None,
    incremental_margin: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "rank": 2,
        "question_id": "profitability_with_scale",
        "question": "规模变大以后利润率是上升还是下降？",
        "priority": "highest",
        "status": "answered" if margin and incremental_margin else ("partial" if margin else "missing"),
        "current_answer": _profitability_with_scale_answer(margin, incremental_margin),
        "metrics_used": ["gross_margin", "operating_margin", "net_margin", "incremental_margin"],
        "latest_values": _compact_values(
            {
                "year": margin.get("year") if margin else None,
                "gross_margin": margin.get("gross_margin") if margin else None,
                "operating_margin": margin.get("operating_margin") if margin else None,
                "net_margin": margin.get("net_margin") if margin else None,
                "incremental_gross_margin": incremental_margin.get("incremental_gross_margin")
                if incremental_margin
                else None,
                "incremental_operating_margin": incremental_margin.get("incremental_operating_margin")
                if incremental_margin
                else None,
            }
        ),
        "warning_flags": _margin_warnings(margin, incremental_margin),
        "missing": [],
        "interpretation_limit": "Margin trend does not prove moat; it only shows whether scale is currently flowing through to profits.",
    }


def _cash_profit_quality_question(
    cash_conversion: dict[str, Any] | None,
    owner_earnings: dict[str, Any] | None,
    sbc_burden: dict[str, Any] | None,
    working_capital: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "rank": 3,
        "question_id": "cash_profit_quality",
        "question": "这个公司赚的钱是真钱吗？现金流质量好不好？",
        "priority": "highest",
        "status": "answered" if cash_conversion and working_capital else ("partial" if cash_conversion else "missing"),
        "current_answer": _cash_profit_quality_answer(cash_conversion, owner_earnings, sbc_burden),
        "metrics_used": [
            "operating_cash_flow / net_income",
            "free_cash_flow_margin",
            "owner_earnings_v1",
            "SBC / operating_cash_flow",
            "working-capital component deltas / revenue",
        ],
        "latest_values": _compact_values(
            {
                "year": cash_conversion.get("year") if cash_conversion else None,
                "cash_conversion": cash_conversion.get("value") if cash_conversion else None,
                "owner_earnings": owner_earnings.get("value") if owner_earnings else None,
                "sbc_to_operating_cash_flow": sbc_burden.get("sbc_to_operating_cash_flow")
                if sbc_burden
                else None,
                "working_capital_cash_tailwind_to_revenue": working_capital.get(
                    "working_capital_cash_tailwind_to_revenue"
                )
                if working_capital
                else None,
            }
        ),
        "warning_flags": _cash_profit_warnings(cash_conversion, sbc_burden)
        + (working_capital.get("warning_flags", []) if working_capital else []),
        "missing": working_capital.get("missing_optional", []) if working_capital else [
            "receivables/payables/inventory/deferred-revenue working-capital bridge"
        ],
        "interpretation_limit": "Working-capital quality is calculated only from extracted official line items. If a company embeds merchant balances inside broader line items, the report must flag that limitation.",
    }


def _capital_needed_question(
    capital_intensity: dict[str, Any] | None,
    roic: dict[str, Any] | None,
    incremental_roic: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "rank": 4,
        "question_id": "capital_needed_for_growth",
        "question": "增长需要消耗多少资本？资本效率有没有变差？",
        "priority": "high",
        "status": "answered" if capital_intensity else "missing",
        "current_answer": _capital_need_answer(capital_intensity, roic, incremental_roic),
        "metrics_used": ["capex / revenue", "capex / operating_cash_flow", "free_cash_flow_margin", "ROIC", "incremental ROIC proxy"],
        "latest_values": _compact_values(
            {
                "year": capital_intensity.get("year") if capital_intensity else None,
                "capex_to_revenue": capital_intensity.get("capex_to_revenue") if capital_intensity else None,
                "capex_to_operating_cash_flow": capital_intensity.get("capex_to_operating_cash_flow")
                if capital_intensity
                else None,
                "free_cash_flow_margin": capital_intensity.get("free_cash_flow_margin")
                if capital_intensity
                else None,
                "roic": roic.get("value") if roic else None,
                "incremental_roic_proxy": incremental_roic.get("value") if incremental_roic else None,
            }
        ),
        "warning_flags": _capital_need_warnings(capital_intensity, incremental_roic),
        "missing": ["maintenance capex versus growth capex"],
        "interpretation_limit": "V1 cannot yet separate maintenance and growth capex, so owner-earnings quality remains approximate.",
    }


def _balance_sheet_question(balance_sheet: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "rank": 5,
        "question_id": "balance_sheet_resilience",
        "question": "资产负债表风险大不大？公司能不能扛住坏年份？",
        "priority": "high",
        "status": "answered" if balance_sheet else "missing",
        "current_answer": _balance_sheet_answer(balance_sheet),
        "metrics_used": [
            "cash / total liabilities",
            "liquid assets / total liabilities",
            "liabilities / assets",
            "current ratio",
            "restricted cash / cash",
            "debt maturity profile",
            "convertible debt structured flag",
        ],
        "latest_values": _compact_values(
            {
                "year": balance_sheet.get("year") if balance_sheet else None,
                "cash_to_total_liabilities": balance_sheet.get("cash_to_total_liabilities")
                if balance_sheet
                else None,
                "liabilities_to_assets": balance_sheet.get("liabilities_to_assets") if balance_sheet else None,
                "debt_to_cash": balance_sheet.get("debt_to_cash") if balance_sheet else None,
                "net_cash": balance_sheet.get("net_cash") if balance_sheet else None,
                "current_ratio": balance_sheet.get("current_ratio") if balance_sheet else None,
                "restricted_cash_to_cash": balance_sheet.get("restricted_cash_to_cash") if balance_sheet else None,
                "current_debt_to_total_debt": balance_sheet.get("current_debt_to_total_debt")
                if balance_sheet
                else None,
            }
        ),
        "warning_flags": _balance_sheet_warnings(balance_sheet),
        "missing": balance_sheet.get("missing_optional", []) if balance_sheet else ["cash", "assets", "liabilities"],
        "interpretation_limit": "Balance-sheet ratios do not address trapped cash, VIE structure, or capital-control risk.",
    }


def _sbc_question(sbc_burden: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "rank": 6,
        "question_id": "sbc_and_per_share_quality",
        "question": "增长有没有被股权激励和稀释吃掉？",
        "priority": "medium",
        "status": "partial" if sbc_burden else "missing",
        "current_answer": _sbc_answer(sbc_burden),
        "metrics_used": ["SBC / revenue", "SBC / operating cash flow", "diluted shares YoY"],
        "latest_values": _compact_values(
            {
                "year": sbc_burden.get("year") if sbc_burden else None,
                "sbc_to_revenue": sbc_burden.get("sbc_to_revenue") if sbc_burden else None,
                "sbc_to_operating_cash_flow": sbc_burden.get("sbc_to_operating_cash_flow")
                if sbc_burden
                else None,
                "diluted_shares_yoy": sbc_burden.get("diluted_shares_yoy") if sbc_burden else None,
            }
        ),
        "warning_flags": _sbc_warnings(sbc_burden),
        "missing": ["buyback offset analysis", "full per-ADS dilution bridge"],
        "interpretation_limit": "SBC is not automatically bad, but it must be measured against cash generation and per-share value.",
    }


def _tax_non_gaap_question(
    tax_accounting: dict[str, Any] | None,
    latest_non_gaap: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "rank": 7,
        "question_id": "tax_non_gaap_accounting_quality",
        "question": "税率、非 GAAP 调整和会计项目有没有让利润看起来更好？",
        "priority": "medium",
        "status": "answered" if tax_accounting else ("partial" if latest_non_gaap else "missing"),
        "current_answer": _tax_accounting_answer(tax_accounting, latest_non_gaap),
        "metrics_used": [
            "effective tax rate",
            "cash taxes / tax expense",
            "non-GAAP uplift",
            "non-GAAP adjustment burden",
            "investment income / pretax income",
            "impairment / revenue",
        ],
        "latest_values": _compact_values(
            {
                "year": tax_accounting.get("year") if tax_accounting else None,
                "effective_tax_rate": tax_accounting.get("effective_tax_rate") if tax_accounting else None,
                "cash_tax_to_tax_expense": tax_accounting.get("cash_tax_to_tax_expense")
                if tax_accounting
                else None,
                "latest_non_gaap_net_income_uplift": latest_non_gaap.get("non_gaap_net_income_uplift")
                if latest_non_gaap
                else None,
            }
        ),
        "warning_flags": (tax_accounting.get("warning_flags", []) if tax_accounting else [])
        + (latest_non_gaap.get("warning_flags", []) if latest_non_gaap else []),
        "missing": tax_accounting.get("missing_optional", []) if tax_accounting else ["pretax_income", "tax_expense"],
        "interpretation_limit": "The rule flags unusual accounting/tax/non-GAAP patterns. It does not prove manipulation without reading the footnotes.",
    }


def _latest_calculated_result(metric: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metric:
        return None
    calculated = [
        result for result in metric.get("annual_results", []) if result.get("status") == "calculated"
    ]
    if not calculated:
        return None
    return sorted(calculated, key=lambda result: result.get("year", 0))[-1]


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
    source_of_growth: dict[str, Any] | None,
) -> str:
    if not margin:
        return "Missing. Revenue and margin facts are required before growth quality can be judged."
    revenue_growth = margin.get("revenue_growth_yoy")
    incremental_operating_margin = incremental_margin.get("incremental_operating_margin") if incremental_margin else None
    source_text = (
        f" Official revenue components cover {_pct_text(source_of_growth.get('value'))} of revenue, with "
        f"{source_of_growth.get('top_component', {}).get('metric')} as the largest extracted component."
        if source_of_growth
        else " Source-of-growth attribution is still missing from extracted official component facts."
    )
    return (
        f"Partial. Latest revenue growth is {_pct_text(revenue_growth)} and operating margin is "
        f"{_pct_text(margin.get('operating_margin'))}; incremental operating margin is "
        f"{_pct_text(incremental_operating_margin)}.{source_text}"
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
        f"current ratio is {_ratio_text(balance_sheet.get('current_ratio'))}; "
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


def _tax_accounting_answer(
    tax_accounting: dict[str, Any] | None,
    latest_non_gaap: dict[str, Any] | None,
) -> str:
    if not tax_accounting and not latest_non_gaap:
        return "Missing. Pretax income, tax expense, or an official non-GAAP bridge is required."
    tax_text = _pct_text(tax_accounting.get("effective_tax_rate")) if tax_accounting else "not available"
    non_gaap_text = _pct_text(latest_non_gaap.get("non_gaap_net_income_uplift")) if latest_non_gaap else "not available"
    return f"Latest effective tax rate is {tax_text}; latest official non-GAAP net income uplift is {non_gaap_text}."


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
    if balance_sheet.get("current_ratio") is not None and balance_sheet["current_ratio"] < 1:
        warnings.append("Current assets are below current liabilities.")
    if balance_sheet.get("restricted_cash_to_cash") is not None and balance_sheet["restricted_cash_to_cash"] > 0.25:
        warnings.append("Restricted cash exceeds 25% of cash.")
    if balance_sheet.get("liabilities_to_assets") is not None and balance_sheet["liabilities_to_assets"] > 0.7:
        warnings.append("Liabilities exceed 70% of assets.")
    if balance_sheet.get("current_debt_to_total_debt") is not None and balance_sheet["current_debt_to_total_debt"] > 0.5:
        warnings.append("More than half of interest-bearing debt is current.")
    if balance_sheet.get("convertible_terms_status") == "structured_convertible_debt_detected_terms_not_parsed":
        warnings.append("Convertible debt was detected in structured facts, but conversion terms are not parsed in V1.")
    if balance_sheet.get("missing_optional"):
        warnings.append(f"Optional balance-sheet details are missing: {', '.join(balance_sheet['missing_optional'])}.")
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
