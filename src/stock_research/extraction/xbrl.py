from __future__ import annotations

import html
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from stock_research.extraction.earnings_release import extract_earnings_release_facts
from stock_research.extraction.tencent_reports import extract_tencent_report_facts
from stock_research.sources.document_policy import is_financial_extraction_document


TARGET_TAGS: dict[str, dict[str, Any]] = {
    "revenue": {
        "label": "Revenue",
        "tags": [
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap:Revenues",
        ],
    },
    "cost_of_revenue": {
        "label": "Cost of revenue",
        "tags": ["us-gaap:CostOfRevenue"],
    },
    "sales_and_marketing_expense": {
        "label": "Sales and marketing expense",
        "tags": ["us-gaap:SellingAndMarketingExpense"],
    },
    "research_and_development_expense": {
        "label": "Research and development expense",
        "tags": ["us-gaap:ResearchAndDevelopmentExpense"],
    },
    "general_and_administrative_expense": {
        "label": "General and administrative expense",
        "tags": ["us-gaap:GeneralAndAdministrativeExpense"],
    },
    "advertising_expense": {
        "label": "Advertising expense",
        "tags": ["us-gaap:AdvertisingExpense"],
    },
    "gross_profit": {
        "label": "Gross profit",
        "tags": ["us-gaap:GrossProfit"],
    },
    "operating_income": {
        "label": "Operating income",
        "tags": ["us-gaap:OperatingIncomeLoss"],
    },
    "pretax_income": {
        "label": "Pretax income before equity-method results",
        "tags": [
            "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        ],
    },
    "pretax_income_after_equity_method": {
        "label": "Pretax income after equity-method results",
        "tags": [
            "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        ],
    },
    "tax_expense": {
        "label": "Income tax expense",
        "tags": ["us-gaap:IncomeTaxExpenseBenefit"],
    },
    "net_income": {
        "label": "Net income",
        "tags": ["us-gaap:NetIncomeLoss"],
    },
    "operating_cash_flow": {
        "label": "Operating cash flow",
        "tags": ["us-gaap:NetCashProvidedByUsedInOperatingActivities"],
    },
    "capex": {
        "label": "Capital expenditure",
        "tags": [
            "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
            "pdd:PaymentsToAcquirePropertyEquipmentAndSoftwareAndIntangibleAssets",
        ],
    },
    "cash": {
        "label": "Cash and cash equivalents",
        "tags": ["us-gaap:CashAndCashEquivalentsAtCarryingValue"],
    },
    "short_term_investments": {
        "label": "Short-term investments",
        "tags": [
            "us-gaap:ShortTermInvestments",
            "us-gaap:ShortTermInvestmentsAvailableForSale",
            "us-gaap:MarketableSecuritiesCurrent",
        ],
    },
    "restricted_cash": {
        "label": "Restricted cash",
        "tags": [
            "us-gaap:RestrictedCashAndCashEquivalentsAtCarryingValue",
            "us-gaap:RestrictedCashCurrent",
            "us-gaap:RestrictedCashNoncurrent",
        ],
    },
    "debt": {
        "label": "Interest-bearing debt",
        "tags": [
            "us-gaap:ConvertibleDebt",
            "us-gaap:ShortTermBorrowings",
        ],
    },
    "debt_current": {
        "label": "Current interest-bearing debt",
        "tags": [
            "us-gaap:ConvertibleDebtCurrent",
            "us-gaap:LongTermDebtAndFinanceLeaseObligationsCurrent",
        ],
    },
    "debt_noncurrent": {
        "label": "Noncurrent interest-bearing debt",
        "tags": [
            "us-gaap:ConvertibleDebtNoncurrent",
            "us-gaap:LongTermDebtAndFinanceLeaseObligationsNoncurrent",
        ],
    },
    "stock_based_compensation": {
        "label": "Stock-based compensation cash-flow addback",
        "tags": [
            "us-gaap:ShareBasedCompensation",
        ],
    },
    "depreciation_and_amortization": {
        "label": "Depreciation and amortization",
        "tags": ["us-gaap:DepreciationAndAmortization"],
    },
    "basic_shares": {
        "label": "Basic shares",
        "tags": ["us-gaap:WeightedAverageNumberOfSharesOutstandingBasic"],
    },
    "diluted_shares": {
        "label": "Diluted shares",
        "tags": ["us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding"],
    },
    "basic_eps": {
        "label": "Basic EPS",
        "tags": ["us-gaap:EarningsPerShareBasic"],
    },
    "diluted_eps": {
        "label": "Diluted EPS",
        "tags": ["us-gaap:EarningsPerShareDiluted"],
    },
    "current_assets": {
        "label": "Current assets",
        "tags": ["us-gaap:AssetsCurrent"],
    },
    "total_assets": {
        "label": "Total assets",
        "tags": ["us-gaap:Assets"],
    },
    "current_liabilities": {
        "label": "Current liabilities",
        "tags": ["us-gaap:LiabilitiesCurrent"],
    },
    "total_liabilities": {
        "label": "Total liabilities",
        "tags": ["us-gaap:Liabilities"],
    },
    "accounts_receivable": {
        "label": "Accounts receivable",
        "tags": ["us-gaap:AccountsReceivableNetCurrent"],
    },
    "inventory": {
        "label": "Inventory",
        "tags": ["us-gaap:InventoryNet"],
    },
    "accounts_payable": {
        "label": "Accounts payable",
        "tags": ["us-gaap:AccountsPayableCurrent"],
    },
    "accounts_payable_and_accrued_expenses": {
        "label": "Accounts payable and accrued liabilities",
        "tags": ["us-gaap:AccountsPayableAndAccruedLiabilitiesCurrent"],
    },
    "payable_to_merchants": {
        "label": "Payable to merchants",
        "tags": ["pdd:PayableToMerchantsCurrent"],
    },
    "accrued_expenses": {
        "label": "Accrued expenses and other current liabilities",
        "tags": [
            "us-gaap:AccruedLiabilitiesCurrent",
            "us-gaap:AccruedIncomeTaxesCurrent",
        ],
    },
    "deferred_revenue": {
        "label": "Deferred revenue / contract liabilities",
        "tags": [
            "us-gaap:ContractWithCustomerLiabilityCurrent",
            "us-gaap:DeferredRevenueCurrent",
            "us-gaap:DeferredRevenueAndCreditsCurrent",
            "pdd:AdvancesToCustomerAndDeferredRevenueCurrent",
        ],
    },
    "merchant_deposits": {
        "label": "Merchant / customer deposits",
        "tags": [
            "us-gaap:DepositLiabilityCurrent",
            "pdd:MerchantDepositsCurrent",
        ],
    },
    "change_in_payable_to_merchants": {
        "label": "Change in payables to merchants",
        "tags": ["pdd:IncreaseDecreaseInPayablesToMerchants"],
    },
    "change_in_merchant_deposits": {
        "label": "Change in merchant deposits",
        "tags": ["pdd:IncreaseDecreaseInMerchantDeposits"],
    },
    "change_in_deferred_revenue": {
        "label": "Change in advances to customers and deferred revenue",
        "tags": ["pdd:IncreaseDecreaseInAdvancesToCustomersAndDeferredRevenue"],
    },
    "cash_paid_for_taxes": {
        "label": "Cash paid for income taxes",
        "tags": ["us-gaap:IncomeTaxesPaidNet"],
    },
    "cash_paid_for_interest": {
        "label": "Cash paid for interest",
        "tags": ["us-gaap:InterestPaidNet"],
    },
    "equity_method_income": {
        "label": "Equity-method income / loss",
        "tags": ["us-gaap:IncomeLossFromEquityMethodInvestments"],
    },
    "investment_income": {
        "label": "Investment income",
        "tags": [
            "us-gaap:InvestmentIncomeNet",
            "us-gaap:InvestmentIncomeInterest",
        ],
    },
    "impairment": {
        "label": "Impairment charges",
        "tags": [
            "us-gaap:ImpairmentOfGoodwillAndIndefiniteLivedIntangibleAssets",
            "us-gaap:ImpairmentOfIntangibleAssetsExcludingGoodwill",
        ],
    },
}

TAG_TO_METRIC = {
    tag.lower(): metric
    for metric, config in TARGET_TAGS.items()
    for tag in config["tags"]
}

CORE_PRIORITY_A_METRICS = [
    "revenue",
    "cost_of_revenue",
    "gross_profit",
    "operating_income",
    "pretax_income",
    "tax_expense",
    "net_income",
    "operating_cash_flow",
    "capex",
    "free_cash_flow",
    "cash",
    "total_assets",
    "total_liabilities",
    "diluted_shares",
]

CORE_PRIORITY_B_METRICS = [
    "online_marketing_services_revenue",
    "transaction_services_revenue",
    "sales_and_marketing_expense",
    "research_and_development_expense",
    "general_and_administrative_expense",
    "stock_based_compensation",
    "depreciation_and_amortization",
    "short_term_investments",
    "restricted_cash",
    "current_assets",
    "current_liabilities",
    "basic_shares",
    "basic_eps",
    "diluted_eps",
    "debt",
    "debt_current",
    "debt_noncurrent",
    "accounts_receivable",
    "inventory",
    "accounts_payable",
    "accounts_payable_and_accrued_expenses",
    "payable_to_merchants",
    "accrued_expenses",
    "deferred_revenue",
    "merchant_deposits",
    "change_in_payable_to_merchants",
    "change_in_merchant_deposits",
    "change_in_deferred_revenue",
    "cash_paid_for_taxes",
    "cash_paid_for_interest",
    "investment_income",
    "equity_method_income",
    "impairment",
]

FINANCIAL_QUESTION_COVERAGE = [
    {
        "question_id": "growth_source",
        "question": "收入增长来自哪里？ / Where does revenue growth come from?",
        "core_metrics": ["revenue"],
        "supporting_metrics": [
            "online_marketing_services_revenue",
            "transaction_services_revenue",
        ],
    },
    {
        "question_id": "margin_change",
        "question": "毛利率、经营利润率有没有变化？ / Are gross and operating margins changing?",
        "core_metrics": ["revenue", "gross_profit", "operating_income"],
        "supporting_metrics": ["cost_of_revenue", "sales_and_marketing_expense"],
    },
    {
        "question_id": "cash_quality",
        "question": "现金流质量好不好？这个公司赚的钱是真钱吗？ / Is cash-flow quality good?",
        "core_metrics": ["net_income", "operating_cash_flow", "free_cash_flow"],
        "supporting_metrics": [
            "stock_based_compensation",
            "depreciation_and_amortization",
            "accounts_receivable",
            "inventory",
            "accounts_payable",
            "deferred_revenue",
        ],
    },
    {
        "question_id": "capital_consumption",
        "question": "增长需要消耗多少资本？ / How much capital does growth consume?",
        "core_metrics": ["capex", "operating_cash_flow", "free_cash_flow"],
        "supporting_metrics": ["current_assets", "current_liabilities", "cash_paid_for_taxes"],
    },
    {
        "question_id": "balance_sheet_risk",
        "question": "资产负债表风险有多大？ / What balance-sheet risks are visible?",
        "core_metrics": ["cash", "total_assets", "total_liabilities"],
        "supporting_metrics": ["short_term_investments", "restricted_cash", "debt", "debt_current", "debt_noncurrent"],
    },
]

CONTEXT_PATTERN = re.compile(
    r"<xbrli:context\b(?P<attrs>[^>]*)>(?P<body>.*?)</xbrli:context>",
    flags=re.IGNORECASE | re.DOTALL,
)
NON_FRACTION_PATTERN = re.compile(
    r"<ix:nonFraction\b(?P<attrs>[^>]*)>(?P<body>.*?)</ix:nonFraction>",
    flags=re.IGNORECASE | re.DOTALL,
)
ATTRIBUTE_PATTERN = re.compile(r"([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*\"([^\"]*)\"")
TAG_PATTERN = re.compile(r"<[^>]+>")

SKIPPED_CONTEXT_MARKERS = (
    "RelatedParty",
    "CounterpartyNameAxis",
    "StatementEquityComponentsAxis",
    "AwardTypeAxis",
    "PlanNameAxis",
    "FairValueByMeasurementFrequencyAxis",
    "PropertyPlantAndEquipmentByTypeAxis",
    "CumulativeEffectPeriodOfAdoptionAxis",
    "ParentCompanyMember",
    "StatementClassOfStockAxis",
    "VariableInterestEntityPrimaryBeneficiaryMember",
)


def extract_financial_facts_from_documents(documents: list[dict[str, Any]]) -> dict[str, Any]:
    raw_facts: list[dict[str, Any]] = []
    extraction_errors: list[dict[str, str]] = []
    latest_tencent_annual_year = _latest_tencent_annual_year(documents)
    latest_tencent_interim_year = _latest_tencent_interim_year(documents)

    for document in documents:
        if not is_financial_extraction_document(document):
            continue
        path_value = document.get("local_path")
        if not path_value:
            continue
        path = Path(path_value)
        if path.suffix.lower() == ".pdf":
            if (
                document.get("source_id") == "tencent_investor_relations"
                and document.get("report_kind") == "annual"
                and latest_tencent_annual_year is not None
                and int(document.get("fiscal_year") or 0) != latest_tencent_annual_year
            ):
                continue
            if (
                document.get("source_id") == "tencent_investor_relations"
                and document.get("report_kind") == "interim"
                and latest_tencent_interim_year is not None
                and int(document.get("fiscal_year") or 0) != latest_tencent_interim_year
            ):
                continue
            try:
                raw_facts.extend(extract_tencent_report_facts(path, document))
            except Exception as exc:  # noqa: BLE001 - recorded for audit instead of failing the run.
                extraction_errors.append({"path": str(path), "error": str(exc)})
            continue
        if path.suffix.lower() not in {".htm", ".html"}:
            continue
        try:
            raw_facts.extend(_extract_document_facts(path, document))
            raw_facts.extend(extract_earnings_release_facts(path, document))
        except Exception as exc:  # noqa: BLE001 - recorded for audit instead of failing the run.
            extraction_errors.append({"path": str(path), "error": str(exc)})

    selected_facts = _select_best_facts(raw_facts)
    selected_facts = _derive_facts(selected_facts)

    counts_by_metric = Counter(fact["metric"] for fact in selected_facts)
    counts_by_period = Counter(fact["period_type"] for fact in selected_facts)
    methods = sorted({fact.get("extraction_method") for fact in selected_facts if fact.get("extraction_method")})
    coverage = _build_extraction_coverage(selected_facts)
    review_flags = _build_extraction_review_flags(selected_facts, coverage)
    summary = {
        "raw_fact_count": len(raw_facts),
        "selected_fact_count": len(selected_facts),
        "counts_by_metric": dict(sorted(counts_by_metric.items())),
        "counts_by_period": dict(sorted(counts_by_period.items())),
        "coverage": coverage,
        "review_flags": review_flags,
        "extraction_errors": extraction_errors,
        "method": "official_document_table_extraction",
        "methods_used": methods,
        "notes": [
            "Only mapped SEC XBRL tags and controlled official earnings-release table labels are extracted.",
            "Comparative values are deduplicated by metric, unit, and period, preferring the latest official filing.",
            "Gross profit and free cash flow may be derived only from official component tags.",
            "SEC helper pages and wrapper-only 6-K documents are skipped by the document corpus policy.",
            "Pretax income and stock-based compensation tags are kept to one accounting concept per metric.",
            "Tencent PDF extraction prefers audited statement tables over five-year summary tables for overlapping periods.",
            "Tencent interim PDF extraction is limited to the latest interim report until older PDF scale formats are mapped safely.",
            "Financial extraction is source-gated to SEC/regulator filings and company investor-relations documents; third-party mirrors are rejected.",
            "No number is filled from memory or from non-official sources.",
        ],
    }

    return {
        "raw_facts": raw_facts,
        "selected_facts": selected_facts,
        "summary": summary,
    }


def _latest_tencent_annual_year(documents: list[dict[str, Any]]) -> int | None:
    years = [
        int(document.get("fiscal_year"))
        for document in documents
        if document.get("source_id") == "tencent_investor_relations"
        and document.get("report_kind") == "annual"
        and str(document.get("fiscal_year") or "").isdigit()
    ]
    return max(years) if years else None


def _latest_tencent_interim_year(documents: list[dict[str, Any]]) -> int | None:
    years = [
        int(document.get("fiscal_year"))
        for document in documents
        if document.get("source_id") == "tencent_investor_relations"
        and document.get("report_kind") == "interim"
        and str(document.get("fiscal_year") or "").isdigit()
    ]
    return max(years) if years else None


def derive_official_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _derive_facts(facts)


def verify_financial_facts(raw_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for fact in raw_facts:
        key = (
            fact.get("metric"),
            fact.get("unit"),
            fact.get("period_type"),
            fact.get("start_date"),
            fact.get("end_date"),
            fact.get("instant"),
        )
        grouped[key].append(fact)

    results: list[dict[str, Any]] = []
    for key, facts in sorted(grouped.items(), key=lambda item: str(item[0])):
        best_rank = min(_context_rank(fact.get("context_ref") or "") for fact in facts)
        facts = [fact for fact in facts if _context_rank(fact.get("context_ref") or "") == best_rank]
        values = [fact["value"] for fact in facts if fact.get("value") is not None]
        if len(values) <= 1:
            continue
        low = min(values)
        high = max(values)
        denominator = max(abs(high), abs(low), 1.0)
        mismatch_pct = abs(high - low) / denominator
        if mismatch_pct == 0:
            continue
        status = "material_conflict" if mismatch_pct > 0.02 else "accepted_rounding_difference"
        results.append(
            {
                "status": status,
                "severity": "high" if status == "material_conflict" else "info",
                "metric": key[0],
                "unit": key[1],
                "period_type": key[2],
                "start_date": key[3],
                "end_date": key[4],
                "instant": key[5],
                "mismatch_pct": mismatch_pct,
                "min_value": low,
                "max_value": high,
                "sources": sorted(
                    {
                        f"{fact.get('accession_number')}:{fact.get('downloaded_file')}"
                        for fact in facts
                    }
                ),
                "explanation": "Official filing values differ by more than 2%."
                if status == "material_conflict"
                else "Difference is within the 2% rounding tolerance.",
                "context_rank": best_rank,
            }
        )

    if not results:
        results.append(
            {
                "status": "passed_no_material_conflicts",
                "severity": "info",
                "explanation": "No official-to-official extracted fact conflicts exceeded the 2% materiality rule.",
            }
        )
    return results


def _build_extraction_coverage(facts: list[dict[str, Any]]) -> dict[str, Any]:
    present_metrics = sorted({str(fact.get("metric")) for fact in facts if fact.get("metric")})
    return {
        "present_metrics": present_metrics,
        "priority_a": _coverage_group(CORE_PRIORITY_A_METRICS, present_metrics),
        "priority_b": _coverage_group(CORE_PRIORITY_B_METRICS, present_metrics),
        "question_coverage": [
            _question_coverage(question, present_metrics) for question in FINANCIAL_QUESTION_COVERAGE
        ],
    }


def _coverage_group(required_metrics: list[str], present_metrics: list[str]) -> dict[str, Any]:
    present = set(present_metrics)
    return {
        "present": [metric for metric in required_metrics if metric in present],
        "missing": [metric for metric in required_metrics if metric not in present],
    }


def _question_coverage(question: dict[str, Any], present_metrics: list[str]) -> dict[str, Any]:
    present = set(present_metrics)
    core_metrics = list(question["core_metrics"])
    supporting_metrics = list(question["supporting_metrics"])
    available_core = [metric for metric in core_metrics if metric in present]
    missing_core = [metric for metric in core_metrics if metric not in present]
    available_supporting = [metric for metric in supporting_metrics if metric in present]
    missing_supporting = [metric for metric in supporting_metrics if metric not in present]
    if not missing_core and available_supporting:
        status = "supported"
    elif not missing_core:
        status = "basic_supported"
    elif available_core:
        status = "partial"
    else:
        status = "missing"
    return {
        "question_id": question["question_id"],
        "question": question["question"],
        "status": status,
        "available_core_metrics": available_core,
        "missing_core_metrics": missing_core,
        "available_supporting_metrics": available_supporting,
        "missing_supporting_metrics": missing_supporting,
    }


def _build_extraction_review_flags(
    facts: list[dict[str, Any]],
    coverage: dict[str, Any],
) -> list[dict[str, Any]]:
    present = {str(fact.get("metric")) for fact in facts if fact.get("metric")}
    flags: list[dict[str, Any]] = []
    if not facts:
        return [
            {
                "flag_id": "no_official_financial_facts_extracted",
                "severity": "high",
                "message": "No mapped official financial facts were extracted from the eligible document set.",
            }
        ]

    priority_a_missing = coverage.get("priority_a", {}).get("missing", [])
    if priority_a_missing:
        flags.append(
            {
                "flag_id": "priority_a_metric_gap",
                "severity": "medium",
                "missing_metrics": priority_a_missing,
                "message": "Some core financial-statement facts are still missing from mapped extraction.",
            }
        )

    if {"cash", "total_assets", "total_liabilities"} & present and not ({"debt", "debt_current", "debt_noncurrent"} & present):
        flags.append(
            {
                "flag_id": "interest_bearing_debt_not_explicitly_extracted",
                "severity": "info",
                "message": "No explicit interest-bearing debt fact was extracted. The extractor does not assume debt is zero.",
            }
        )

    working_capital_metrics = {
        "accounts_receivable",
        "inventory",
        "accounts_payable",
        "accounts_payable_and_accrued_expenses",
        "accrued_expenses",
        "deferred_revenue",
    }
    if "operating_cash_flow" in present and not (working_capital_metrics & present):
        flags.append(
            {
                "flag_id": "working_capital_detail_gap",
                "severity": "medium",
                "message": "Operating cash flow was extracted, but working-capital detail was not. Cash-conversion analysis should remain cautious.",
            }
        )

    revenue_breakdown_metrics = {
        "online_marketing_services_revenue",
        "transaction_services_revenue",
    }
    if "revenue" in present and not (revenue_breakdown_metrics & present):
        flags.append(
            {
                "flag_id": "revenue_breakdown_gap",
                "severity": "info",
                "message": "Revenue was extracted, but no controlled revenue breakdown fact was found in the mapped tags/tables.",
            }
        )

    has_earnings_release_table = any(
        str(fact.get("extraction_method") or "").startswith("official_earnings_release")
        for fact in facts
    )
    has_non_gaap_bridge = any(str(fact.get("metric") or "").startswith("non_gaap_") for fact in facts)
    if has_earnings_release_table and not has_non_gaap_bridge:
        flags.append(
            {
                "flag_id": "non_gaap_bridge_not_extracted",
                "severity": "info",
                "message": "Official earnings-release facts were extracted, but no non-GAAP bridge rows were found by the controlled parser.",
            }
        )

    return flags


def _extract_document_facts(path: Path, document: dict[str, Any]) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    contexts = _parse_contexts(text)
    facts = []
    for match in NON_FRACTION_PATTERN.finditer(text):
        attrs = _parse_attrs(match.group("attrs"))
        name = attrs.get("name")
        if not name:
            continue
        metric = TAG_TO_METRIC.get(name.lower())
        if not metric:
            continue
        context_ref = attrs.get("contextRef") or attrs.get("contextref")
        if not context_ref:
            continue
        context = contexts.get(context_ref, {"context_id": context_ref})
        if _skip_context(context_ref):
            continue
        unit = attrs.get("unitRef") or attrs.get("unitref")
        value = _parse_number(match.group("body"), attrs)
        if value is None:
            continue
        adjustment_note = None
        if metric in {"basic_shares", "diluted_shares"} and value and value < 100_000_000:
            value *= 1000
            adjustment_note = "Applied share-count scale normalization: values below 100 million are treated as thousands."
        period = _period_fields(context)
        fact_id = (
            f"{document.get('document_id')}:{metric}:"
            f"{period.get('start_date') or ''}:{period.get('end_date') or period.get('instant') or ''}:"
            f"{unit or ''}:{len(facts)}"
        )
        facts.append(
            {
                "fact_id": fact_id,
                "metric": metric,
                "label": TARGET_TAGS[metric]["label"],
                "xbrl_tag": name,
                "context_ref": context_ref,
                "context_rank": _context_rank(context_ref),
                "value": value,
                "unit": _normalize_unit(unit),
                "period_type": period["period_type"],
                "start_date": period.get("start_date"),
                "end_date": period.get("end_date"),
                "instant": period.get("instant"),
                "source_id": document.get("source_id"),
                "source_url": document.get("source_url"),
                "local_path": document.get("local_path"),
                "document_id": document.get("document_id"),
                "document_type": document.get("document_type"),
                "accession_number": _accession_from_document(document),
                "downloaded_file": document.get("downloaded_file"),
                "filing_date": document.get("filing_date"),
                "report_date": document.get("report_date"),
                "confidence": "high",
                "extraction_method": "inline_xbrl_tag",
                "adjustment_note": adjustment_note,
            }
        )
    return facts


def _parse_contexts(text: str) -> dict[str, dict[str, str]]:
    contexts = {}
    for match in CONTEXT_PATTERN.finditer(text):
        attrs = _parse_attrs(match.group("attrs"))
        context_id = attrs.get("id")
        if not context_id:
            continue
        body = match.group("body")
        start_date = _first_match(r"<xbrli:startDate>([^<]+)</xbrli:startDate>", body)
        end_date = _first_match(r"<xbrli:endDate>([^<]+)</xbrli:endDate>", body)
        instant = _first_match(r"<xbrli:instant>([^<]+)</xbrli:instant>", body)
        contexts[context_id] = {
            "context_id": context_id,
            "start_date": start_date,
            "end_date": end_date,
            "instant": instant,
        }
    return contexts


def _period_fields(context: dict[str, str]) -> dict[str, str | None]:
    start = context.get("start_date")
    end = context.get("end_date")
    instant = context.get("instant")
    if start and end:
        return {
            "period_type": _duration_type(start, end),
            "start_date": start,
            "end_date": end,
            "instant": None,
        }
    return {
        "period_type": "instant",
        "start_date": None,
        "end_date": instant,
        "instant": instant,
    }


def _duration_type(start: str, end: str) -> str:
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError:
        return "duration"
    days = (end_date - start_date).days + 1
    if start.endswith("-01-01") and end.endswith("-12-31"):
        return "annual"
    if 80 <= days <= 100:
        return "quarter"
    if 170 <= days <= 190:
        return "half_year"
    if 260 <= days <= 285:
        return "nine_month"
    return "duration"


def _select_best_facts(raw_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for fact in raw_facts:
        key = (
            fact.get("metric"),
            fact.get("unit"),
            fact.get("period_type"),
            fact.get("start_date"),
            fact.get("end_date"),
            fact.get("instant"),
        )
        grouped[key].append(fact)

    selected = []
    for facts in grouped.values():
        facts = sorted(
            facts,
            key=lambda fact: (
                -int(fact.get("context_rank", 99)),
                _extraction_method_rank(fact),
                fact.get("filing_date") or "",
                fact.get("accession_number") or "",
                fact.get("downloaded_file") or "",
            ),
            reverse=True,
        )
        selected.append({**facts[0], "selection_policy": "latest_official_filing_for_same_period"})
    return sorted(
        selected,
        key=lambda fact: (
            str(fact.get("end_date") or fact.get("instant") or ""),
            str(fact.get("metric") or ""),
            str(fact.get("unit") or ""),
        ),
    )


def _extraction_method_rank(fact: dict[str, Any]) -> int:
    method = str(fact.get("extraction_method") or "")
    if method == "inline_xbrl_tag":
        return 100
    if "income_statement" in method or "cash_flow" in method or "financial_position" in method:
        return 90
    if "adjusted_ebitda" in method:
        return 80
    if "financial_summary" in method:
        return 60
    return 50


def _derive_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = list(facts)
    grouped: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for fact in facts:
        key = (
            fact.get("unit"),
            fact.get("period_type"),
            fact.get("start_date"),
            fact.get("end_date"),
            fact.get("instant"),
        )
        grouped[key][fact["metric"]] = fact

    for key, by_metric in grouped.items():
        if "gross_profit" not in by_metric and {"revenue", "cost_of_revenue"} <= by_metric.keys():
            revenue = by_metric["revenue"]
            cost = by_metric["cost_of_revenue"]
            output.append(
                _derived_fact(
                    metric="gross_profit",
                    label="Gross profit",
                    value=revenue["value"] - cost["value"],
                    source_facts=[revenue, cost],
                    formula="revenue - cost_of_revenue",
                )
            )
        if "free_cash_flow" not in by_metric and {"operating_cash_flow", "capex"} <= by_metric.keys():
            ocf = by_metric["operating_cash_flow"]
            capex = by_metric["capex"]
            output.append(
                _derived_fact(
                    metric="free_cash_flow",
                    label="Free cash flow",
                    value=ocf["value"] - capex["value"],
                    source_facts=[ocf, capex],
                    formula="operating_cash_flow - capex",
                )
            )
        if "debt" not in by_metric and ("debt_current" in by_metric or "debt_noncurrent" in by_metric):
            components = [
                fact for metric, fact in by_metric.items() if metric in {"debt_current", "debt_noncurrent"}
            ]
            output.append(
                _derived_fact(
                    metric="debt",
                    label="Interest-bearing debt",
                    value=sum(fact["value"] for fact in components),
                    source_facts=components,
                    formula="debt_current + debt_noncurrent",
                )
            )

    return sorted(
        output,
        key=lambda fact: (
            str(fact.get("end_date") or fact.get("instant") or ""),
            str(fact.get("metric") or ""),
            str(fact.get("unit") or ""),
        ),
    )


def _derived_fact(
    *,
    metric: str,
    label: str,
    value: float,
    source_facts: list[dict[str, Any]],
    formula: str,
) -> dict[str, Any]:
    first = source_facts[0]
    all_xbrl = all("xbrl" in str(fact.get("extraction_method", "")) for fact in source_facts)
    source_ids = sorted({str(fact.get("source_id")) for fact in source_facts if fact.get("source_id")})
    return {
        **{key: first.get(key) for key in (
            "unit",
            "period_type",
            "start_date",
            "end_date",
            "instant",
            "source_id",
            "source_url",
            "local_path",
            "document_id",
            "document_type",
            "accession_number",
            "downloaded_file",
            "filing_date",
            "report_date",
        )},
        "source_id": source_ids[0] if len(source_ids) == 1 else "mixed_official_sources",
        "fact_id": f"derived:{metric}:{first.get('unit')}:{first.get('start_date')}:{first.get('end_date') or first.get('instant')}",
        "metric": metric,
        "label": label,
        "xbrl_tag": None,
        "value": value,
        "confidence": "medium",
        "extraction_method": "derived_from_official_xbrl_components" if all_xbrl else "derived_from_mixed_official_components",
        "formula": formula,
        "source_fact_ids": [fact["fact_id"] for fact in source_facts],
        "selection_policy": "derived_after_latest_official_filing_selection",
    }


def _parse_number(body: str, attrs: dict[str, str]) -> float | None:
    if attrs.get("xs:nil") == "true":
        return None
    text = html.unescape(TAG_PATTERN.sub("", body)).strip()
    if not text:
        return None
    negative_from_parentheses = text.startswith("(") and text.endswith(")")
    cleaned = (
        text.replace(",", "")
        .replace("\u00a0", "")
        .replace("$", "")
        .replace("RMB", "")
        .replace("US", "")
        .replace("(", "")
        .replace(")", "")
        .strip()
    )
    if cleaned in {"", "-", "—", "--"}:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    scale = int(attrs.get("scale", "0") or "0")
    value *= 10**scale
    if attrs.get("sign") == "-" or negative_from_parentheses:
        value *= -1
    if value.is_integer():
        return int(value)
    return value


def _parse_attrs(raw_attrs: str) -> dict[str, str]:
    return {name: html.unescape(value) for name, value in ATTRIBUTE_PATTERN.findall(raw_attrs)}


def _first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    return html.unescape(match.group(1).strip()) if match else None


def _normalize_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    if "_CNY_" in unit or unit.endswith("_CNY") or "CNY" in unit:
        return "CNY"
    if "_USD_" in unit or unit.endswith("_USD") or "USD" in unit:
        return "USD"
    if "shares" in unit.lower():
        return "shares"
    if "pure" in unit.lower():
        return "pure"
    return unit


def _skip_context(context_id: str) -> bool:
    return any(marker in context_id for marker in SKIPPED_CONTEXT_MARKERS)


def _context_rank(context_id: str) -> int:
    if "Axis" not in context_id and "Member" not in context_id:
        return 0
    if "ProductOrServiceAxis" in context_id:
        return 1
    return 3


def _accession_from_document(document: dict[str, Any]) -> str | None:
    document_id = document.get("document_id")
    if isinstance(document_id, str) and ":" in document_id:
        return document_id.split(":", 1)[0]
    return None
