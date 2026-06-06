from __future__ import annotations

import re
from pathlib import Path
from typing import Any


MILLION = 1_000_000

SUMMARY_METRICS = {
    "revenue": "Revenues",
    "gross_profit": "Gross profit",
    "operating_income": "Operating profit",
    "pretax_income": "Profit before income tax",
    "net_income": "Profit attributable to equity holders of the Company",
    "total_assets": "Total assets",
    "total_liabilities": "Total liabilities",
}


def extract_tencent_report_facts(path: Path, document: dict[str, Any]) -> list[dict[str, Any]]:
    if document.get("source_id") != "tencent_investor_relations":
        return []
    if document.get("report_kind") not in {"annual", "interim"}:
        return []
    text = pdf_text(path)
    if not text:
        return []
    text_path = path.with_suffix(".txt")
    text_path.write_text(text, encoding="utf-8")
    if document.get("report_kind") == "interim":
        return extract_tencent_interim_report_text_facts(text, document)
    return extract_tencent_annual_report_text_facts(text, document)


def extract_tencent_annual_report_text_facts(text: str, document: dict[str, Any]) -> list[dict[str, Any]]:
    if document.get("source_id") != "tencent_investor_relations":
        return []
    if document.get("report_kind") != "annual":
        return []

    fiscal_year = int(document.get("fiscal_year") or str(document.get("report_date", ""))[:4] or 0)
    if fiscal_year <= 0:
        return []

    facts = []
    facts.extend(_summary_facts(text, document=document, fiscal_year=fiscal_year))
    facts.extend(_annual_income_statement_facts(text, document=document, fiscal_year=fiscal_year))
    facts.extend(_latest_statement_facts(text, document=document, fiscal_year=fiscal_year))
    return facts


def extract_tencent_interim_report_text_facts(text: str, document: dict[str, Any]) -> list[dict[str, Any]]:
    if document.get("source_id") != "tencent_investor_relations":
        return []
    if document.get("report_kind") != "interim":
        return []

    fiscal_year = int(document.get("fiscal_year") or str(document.get("report_date", ""))[:4] or 0)
    if fiscal_year <= 0:
        return []

    facts = []
    facts.extend(_interim_income_statement_facts(text, document=document, fiscal_year=fiscal_year))
    facts.extend(_interim_financial_position_facts(text, document=document, fiscal_year=fiscal_year))
    facts.extend(_interim_cash_flow_facts(text, document=document, fiscal_year=fiscal_year))
    return facts


def pdf_text(path: Path) -> str:
    text_path = path.with_suffix(".txt")
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError:
        return text_path.read_text(encoding="utf-8") if text_path.exists() else ""
    reader = PdfReader(str(path))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    if extracted.strip():
        return extracted
    return text_path.read_text(encoding="utf-8") if text_path.exists() else ""


def _summary_facts(text: str, *, document: dict[str, Any], fiscal_year: int) -> list[dict[str, Any]]:
    summary = _section(text, "Financial Summary", "Chairman")
    facts = []
    for metric, label in SUMMARY_METRICS.items():
        values = _values_after_label(summary, label, count=5)
        if len(values) < 5:
            continue
        for offset, value in enumerate(values[-5:]):
            year = fiscal_year - 4 + offset
            period_type = "instant" if metric in {"total_assets", "total_liabilities"} else "annual"
            facts.append(
                _fact(
                    document=document,
                    metric=metric,
                    label=label,
                    value=value * MILLION,
                    year=year,
                    unit="CNY",
                    period_type=period_type,
                    extraction_method="official_tencent_annual_report_financial_summary",
                    fact_index=len(facts),
                )
            )
    return facts


def _latest_statement_facts(text: str, *, document: dict[str, Any], fiscal_year: int) -> list[dict[str, Any]]:
    facts = []
    financial_position = _financial_position_section(text)
    cash_flow = _cash_flow_section(text)
    labels = {
        "operating_cash_flow": (
            "Net cash flows generated from operating activities",
            "annual",
            "official_tencent_annual_report_cash_flow_statement",
            cash_flow,
        ),
        "cash": (
            "Cash and cash equivalents",
            "instant",
            "official_tencent_annual_report_financial_position_statement",
            financial_position,
        ),
        "total_assets": (
            "Total assets",
            "instant",
            "official_tencent_annual_report_financial_position_statement",
            financial_position,
        ),
        "total_liabilities": (
            "Total liabilities",
            "instant",
            "official_tencent_annual_report_financial_position_statement",
            financial_position,
        ),
        "tax_expense": (
            "Income tax expense",
            "annual",
            "official_tencent_annual_report_income_statement",
            text,
        ),
    }
    for metric, (label, period_type, method, source_text) in labels.items():
        values = _values_after_label(source_text, label, count=2)
        if len(values) < 2:
            continue
        for year, value in {fiscal_year: values[-2], fiscal_year - 1: values[-1]}.items():
            facts.append(
                _fact(
                    document=document,
                    metric=metric,
                    label=label,
                    value=abs(value) * MILLION if metric == "tax_expense" else value * MILLION,
                    year=year,
                    unit="CNY",
                    period_type=period_type,
                    extraction_method=method,
                    fact_index=len(facts),
                )
            )

    capex_values = _capex_values(text)
    for year, value in capex_values.items():
        facts.append(
            _fact(
                document=document,
                metric="capex",
                label="CapEx proxy",
                value=value * MILLION,
                year=year,
                unit="CNY",
                period_type="annual",
                extraction_method="official_tencent_annual_report_cash_flow_statement",
                fact_index=len(facts),
                interpretation_note=(
                    "Tencent V1 CapEx proxy includes purchase/prepayments for property, plant and equipment, "
                    "construction in progress, investment properties, and intangible assets."
                ),
            )
        )

    debt_values = _debt_values(text)
    for year, value in debt_values.items():
        facts.append(
            _fact(
                document=document,
                metric="debt",
                label="Borrowings plus notes payable",
                value=value * MILLION,
                year=year,
                unit="CNY",
                period_type="instant",
                extraction_method="official_tencent_annual_report_financial_position_statement",
                fact_index=len(facts),
                interpretation_note="Debt includes current and non-current borrowings plus notes payable.",
            )
        )

    investment_portfolio_values = _investment_portfolio_values(text)
    for year, value in investment_portfolio_values.items():
        facts.append(
            _fact(
                document=document,
                metric="investment_portfolio",
                label="Investment portfolio",
                value=value * MILLION,
                year=year,
                unit="CNY",
                period_type="instant",
                extraction_method="official_tencent_annual_report_investments_held",
                fact_index=len(facts),
                interpretation_note=(
                    "Tencent reports this investment portfolio under investments in associates and joint ventures, "
                    "FVPL, and FVOCI. V1 uses the official carrying amount as an operating EV adjustment."
                ),
            )
        )

    da_values = _depreciation_and_amortization_values(text)
    for year, value in da_values.items():
        facts.append(
            _fact(
                document=document,
                metric="depreciation_and_amortization",
                label="Depreciation and amortisation",
                value=value * MILLION,
                year=year,
                unit="CNY",
                period_type="annual",
                extraction_method="official_tencent_annual_report_adjusted_ebitda_reconciliation",
                fact_index=len(facts),
            )
        )

    sbc_values = _values_after_label(text, "Equity-settled share-based compensation", count=5)[-2:]
    if len(sbc_values) >= 2:
        for year, value in {fiscal_year: sbc_values[0], fiscal_year - 1: sbc_values[1]}.items():
            facts.append(
                _fact(
                    document=document,
                    metric="stock_based_compensation",
                    label="Equity-settled share-based compensation",
                    value=value * MILLION,
                    year=year,
                    unit="CNY",
                    period_type="annual",
                    extraction_method="official_tencent_annual_report_adjusted_ebitda_reconciliation",
                    fact_index=len(facts),
                )
            )
    return facts


def _annual_income_statement_facts(text: str, *, document: dict[str, Any], fiscal_year: int) -> list[dict[str, Any]]:
    section = _income_statement_section(text)
    if not section:
        return []
    facts = []
    labels = {
        "revenue": "total revenues",
        "cost_of_revenue": "Cost of revenues",
        "gross_profit": "Gross profit",
        "operating_income": "Operating profit",
        "pretax_income": "Profit before income tax",
        "tax_expense": "Income tax expense",
        "net_income": "Equity holders of the Company",
    }
    for metric, label in labels.items():
        values = (
            _annual_income_statement_revenue_values(section)
            if metric == "revenue"
            else _values_after_label(section, label, count=2)
        )
        if len(values) < 2:
            continue
        for year, value in ((fiscal_year, values[0]), (fiscal_year - 1, values[1])):
            facts.append(
                _fact(
                    document=document,
                    metric=metric,
                    label=label,
                    value=abs(value) * MILLION if metric in {"cost_of_revenue", "tax_expense"} else value * MILLION,
                    year=year,
                    unit="CNY",
                    period_type="annual",
                    extraction_method="official_tencent_annual_report_income_statement",
                    fact_index=len(facts),
                )
            )
    return facts


def _interim_income_statement_facts(text: str, *, document: dict[str, Any], fiscal_year: int) -> list[dict[str, Any]]:
    section = _interim_income_statement_section(text)
    if not section:
        return []
    facts = []
    labels = {
        "revenue": "total revenues",
        "cost_of_revenue": "Cost of revenues",
        "gross_profit": "Gross profit",
        "operating_income": "Operating profit",
        "pretax_income": "Profit before income tax",
        "tax_expense": "Income tax expense",
        "net_income": "Equity holders of the Company",
    }
    periods = [
        (fiscal_year, "quarter", f"{fiscal_year}-04-01", f"{fiscal_year}-06-30"),
        (fiscal_year - 1, "quarter", f"{fiscal_year - 1}-04-01", f"{fiscal_year - 1}-06-30"),
        (fiscal_year, "half_year", f"{fiscal_year}-01-01", f"{fiscal_year}-06-30"),
        (fiscal_year - 1, "half_year", f"{fiscal_year - 1}-01-01", f"{fiscal_year - 1}-06-30"),
    ]
    for metric, label in labels.items():
        values = (
            _interim_income_statement_revenue_values(section)
            if metric == "revenue"
            else _values_after_label(section, label, count=4)
        )
        if len(values) < 4:
            continue
        for index, (year, period_type, start_date, end_date) in enumerate(periods):
            value = values[index]
            facts.append(
                _fact(
                    document=document,
                    metric=metric,
                    label=label,
                    value=abs(value) * MILLION if metric in {"cost_of_revenue", "tax_expense"} else value * MILLION,
                    year=year,
                    unit="CNY",
                    period_type=period_type,
                    extraction_method="official_tencent_interim_report_income_statement",
                    fact_index=len(facts),
                    start_date=start_date,
                    end_date=end_date,
                )
            )
    return facts


def _interim_financial_position_facts(text: str, *, document: dict[str, Any], fiscal_year: int) -> list[dict[str, Any]]:
    section = _financial_position_section(text)
    if not section:
        return []
    facts = []
    labels = {
        "cash": "Cash and cash equivalents",
        "total_assets": "Total assets",
        "total_liabilities": "Total liabilities",
    }
    for metric, label in labels.items():
        values = _values_after_label(section, label, count=2)
        if len(values) < 2:
            continue
        for year, end_date, value in (
            (fiscal_year, f"{fiscal_year}-06-30", values[0]),
            (fiscal_year - 1, f"{fiscal_year - 1}-12-31", values[1]),
        ):
            facts.append(
                _fact(
                    document=document,
                    metric=metric,
                    label=label,
                    value=value * MILLION,
                    year=year,
                    unit="CNY",
                    period_type="instant",
                    extraction_method="official_tencent_interim_report_financial_position_statement",
                    fact_index=len(facts),
                    end_date=end_date,
                    instant=end_date,
                )
            )

    debt_values = {fiscal_year: 0.0, fiscal_year - 1: 0.0}
    for label in ("Borrowings", "Notes payable"):
        for values in _all_two_year_values(section, label):
            if len(values) >= 2:
                debt_values[fiscal_year] += values[0]
                debt_values[fiscal_year - 1] += values[1]
    for year, end_date, value in (
        (fiscal_year, f"{fiscal_year}-06-30", debt_values[fiscal_year]),
        (fiscal_year - 1, f"{fiscal_year - 1}-12-31", debt_values[fiscal_year - 1]),
    ):
        if value:
            facts.append(
                _fact(
                    document=document,
                    metric="debt",
                    label="Borrowings plus notes payable",
                    value=value * MILLION,
                    year=year,
                    unit="CNY",
                    period_type="instant",
                    extraction_method="official_tencent_interim_report_financial_position_statement",
                    fact_index=len(facts),
                    end_date=end_date,
                    instant=end_date,
                    interpretation_note="Debt includes current and non-current borrowings plus notes payable.",
                )
            )
    return facts


def _interim_cash_flow_facts(text: str, *, document: dict[str, Any], fiscal_year: int) -> list[dict[str, Any]]:
    section = _cash_flow_section(text)
    if not section:
        return []
    facts = []
    labels = {
        "operating_cash_flow": "Net cash flows generated from operating activities",
    }
    for metric, label in labels.items():
        values = _values_after_label(section, label, count=2)
        if len(values) < 2:
            continue
        for year, value in ((fiscal_year, values[0]), (fiscal_year - 1, values[1])):
            facts.append(
                _fact(
                    document=document,
                    metric=metric,
                    label=label,
                    value=value * MILLION,
                    year=year,
                    unit="CNY",
                    period_type="half_year",
                    extraction_method="official_tencent_interim_report_cash_flow_statement",
                    fact_index=len(facts),
                    start_date=f"{year}-01-01",
                    end_date=f"{year}-06-30",
                )
            )

    ppe = _two_year_values(
        section,
        "Purchase of/prepayments for property, plant and equipment, construction in progress and investment properties",
    )
    intangibles = _two_year_values(section, "Purchase of/prepayments for intangible assets")
    if len(ppe) >= 2 and len(intangibles) >= 2:
        for year, value in (
            (fiscal_year, abs(ppe[0]) + abs(intangibles[0])),
            (fiscal_year - 1, abs(ppe[1]) + abs(intangibles[1])),
        ):
            facts.append(
                _fact(
                    document=document,
                    metric="capex",
                    label="CapEx proxy",
                    value=value * MILLION,
                    year=year,
                    unit="CNY",
                    period_type="half_year",
                    extraction_method="official_tencent_interim_report_cash_flow_statement",
                    fact_index=len(facts),
                    start_date=f"{year}-01-01",
                    end_date=f"{year}-06-30",
                    interpretation_note=(
                        "Tencent V1 CapEx proxy includes purchase/prepayments for property, plant and equipment, "
                        "construction in progress, investment properties, and intangible assets."
                    ),
                )
            )
    return facts


def _capex_values(text: str) -> dict[int, float]:
    text = _cash_flow_section(text)
    ppe = _two_year_values(
        text,
        "Purchase of/prepayments for property, plant and equipment, construction in progress and investment properties",
    )
    intangibles = _two_year_values(text, "Purchase of/prepayments for intangible assets")
    fiscal_year = _fiscal_year_from_text(text)
    if len(ppe) < 2 or len(intangibles) < 2 or fiscal_year is None:
        return {}
    return {
        fiscal_year: abs(ppe[0]) + abs(intangibles[0]),
        fiscal_year - 1: abs(ppe[1]) + abs(intangibles[1]),
    }


def _debt_values(text: str) -> dict[int, float]:
    fiscal_year = _fiscal_year_from_text(text)
    if fiscal_year is None:
        return {}
    text = _financial_position_section(text)
    values_by_year = {fiscal_year: 0.0, fiscal_year - 1: 0.0}
    for label in ("Borrowings", "Notes payable"):
        matches = _all_two_year_values(text, label)
        for values in matches:
            if len(values) >= 2:
                values_by_year[fiscal_year] += values[0]
                values_by_year[fiscal_year - 1] += values[1]
    return {year: value for year, value in values_by_year.items() if value}


def _depreciation_and_amortization_values(text: str) -> dict[int, float]:
    fiscal_year = _fiscal_year_from_text(text)
    if fiscal_year is None:
        return {}
    components = [
        _values_after_label(text, "Depreciation of property, plant and equipment and investment properties", count=5)[-2:],
        _values_after_label(text, "Depreciation of right-of-use assets", count=5)[-2:],
        _values_after_label(text, "Amortisation of intangible assets and land use rights", count=5)[-2:],
    ]
    if any(len(component) < 2 for component in components):
        return {}
    return {
        fiscal_year: sum(component[0] for component in components),
        fiscal_year - 1: sum(component[1] for component in components),
    }


def _investment_portfolio_values(text: str) -> dict[int, float]:
    fiscal_year = _fiscal_year_from_text(text)
    if fiscal_year is None:
        return {}
    normalized = _normalize_text(text)
    match = re.search(
        r"investment portfolio amounted to approximately RMB\s*([\d,]+)\s*million"
        r"\s*\(31 December\s+(20\d{2}):\s*RMB\s*([\d,]+)\s*million\)",
        normalized,
        flags=re.IGNORECASE,
    )
    if not match:
        return {}
    current_value, prior_year, prior_value = match.groups()
    values = {
        fiscal_year: float(current_value.replace(",", "")),
    }
    if int(prior_year) == fiscal_year - 1:
        values[fiscal_year - 1] = float(prior_value.replace(",", ""))
    return values


def _financial_position_section(text: str) -> str:
    start = _heading_start(text, "Consolidated Statement of Financial Position", required_after="As at")
    if start == -1:
        return text
    end = text.find("Consolidated Statement of Changes in Equity", start)
    return text[start:] if end == -1 else text[start:end]


def _cash_flow_section(text: str) -> str:
    start = _heading_start(text, "Consolidated Statement of Cash Flows", required_after="For the")
    if start == -1:
        return text
    end = text.find("Notes to the Consolidated Financial Statements", start)
    if end == -1:
        end = text.find("Notes to the Interim Financial Information", start)
    return text[start:] if end == -1 else text[start:end]


def _income_statement_section(text: str) -> str:
    start = _heading_start(text, "Consolidated Income Statement", required_after="For the year ended")
    if start == -1:
        return ""
    end = text.find("Consolidated Statement of Comprehensive Income", start)
    return text[start:] if end == -1 else text[start:end]


def _interim_income_statement_section(text: str) -> str:
    start = _heading_start(
        text,
        "Condensed Consolidated Income Statement",
        required_after="For the three and six months ended",
    )
    if start == -1:
        return ""
    end = text.find("Condensed Consolidated Statement of Comprehensive Income", start)
    return text[start:] if end == -1 else text[start:end]


def _heading_start(text: str, heading: str, *, required_after: str | None = None) -> int:
    start = -1
    while True:
        start = text.find(heading, start + 1)
        if start == -1:
            return -1
        if required_after is None or required_after in text[start : start + 300]:
            return start


def _annual_income_statement_revenue_values(section: str) -> list[float]:
    normalized = _normalize_text(section)
    match = re.search(
        r"\b\d+\s+(\(?-?\d[\d,]*\)?)\s+(\(?-?\d[\d,]*\)?)\s+Cost of revenues",
        normalized,
        flags=re.IGNORECASE,
    )
    return _numbers(" ".join(match.groups())) if match else []


def _interim_income_statement_revenue_values(section: str) -> list[float]:
    normalized = _normalize_text(section)
    match = re.search(
        r"\b\d+\s+(\(?-?\d[\d,]*\)?)\s+(\(?-?\d[\d,]*\)?)\s+"
        r"(\(?-?\d[\d,]*\)?)\s+(\(?-?\d[\d,]*\)?)\s+Cost of revenues",
        normalized,
        flags=re.IGNORECASE,
    )
    return _numbers(" ".join(match.groups())) if match else []


def _fact(
    *,
    document: dict[str, Any],
    metric: str,
    label: str,
    value: float,
    year: int,
    unit: str,
    period_type: str,
    extraction_method: str,
    fact_index: int,
    interpretation_note: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    instant: str | None = None,
) -> dict[str, Any]:
    if period_type == "instant":
        start_date = None
        end_date = end_date or f"{year}-12-31"
        instant = instant or end_date
    else:
        start_date = start_date or f"{year}-01-01"
        end_date = end_date or f"{year}-12-31"
        instant = None
    return {
        "fact_id": f"{document.get('document_id')}:{metric}:{year}:{fact_index}",
        "metric": metric,
        "label": label,
        "xbrl_tag": None,
        "context_ref": None,
        "context_rank": 0,
        "value": int(value) if float(value).is_integer() else value,
        "unit": unit,
        "period_type": period_type,
        "start_date": start_date,
        "end_date": end_date,
        "instant": instant,
        "source_id": document.get("source_id"),
        "source_url": document.get("source_url"),
        "local_path": document.get("local_path"),
        "document_id": document.get("document_id"),
        "document_type": document.get("document_type"),
        "accession_number": None,
        "downloaded_file": document.get("downloaded_file"),
        "filing_date": document.get("filing_date"),
        "report_date": document.get("report_date"),
        "confidence": "medium",
        "extraction_method": extraction_method,
        "selection_policy": "official_tencent_pdf_text_table_extraction",
        "interpretation_note": interpretation_note,
    }


def _dedupe_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = {}
    for fact in facts:
        key = (
            fact.get("metric"),
            fact.get("unit"),
            fact.get("period_type"),
            fact.get("start_date"),
            fact.get("end_date"),
            fact.get("instant"),
        )
        current = selected.get(key)
        if current is None or _method_rank(fact) > _method_rank(current):
            selected[key] = fact
    return list(selected.values())


def _method_rank(fact: dict[str, Any]) -> int:
    method = str(fact.get("extraction_method") or "")
    if "cash_flow" in method or "financial_position" in method or "income_statement" in method:
        return 3
    if "adjusted_ebitda" in method:
        return 2
    return 1


def _section(text: str, start: str, end: str) -> str:
    start_index = text.find(start)
    if start_index == -1:
        return ""
    end_index = text.find(end, start_index + len(start))
    return text[start_index:] if end_index == -1 else text[start_index:end_index]


def _values_after_label(text: str, label: str, *, count: int) -> list[float]:
    values = _two_year_values(text, label) if count == 2 else []
    if values:
        return values
    pattern = re.compile(re.escape(label) + r"\s+((?:\(?-?\d[\d,]*\)?\s+){%d,})" % count, re.IGNORECASE)
    match = pattern.search(_normalize_text(text))
    if not match:
        return []
    return _numbers(match.group(1))[-count:]


def _two_year_values(text: str, label: str) -> list[float]:
    matches = _all_two_year_values(text, label)
    return matches[0] if matches else []


def _all_two_year_values(text: str, label: str) -> list[list[float]]:
    normalized = _normalize_text(text)
    pattern = re.compile(re.escape(label) + r"\s+(?:\d+[a-z]?\s+)?(\(?-?\d[\d,]*\)?)\s+(\(?-?\d[\d,]*\)?)", re.IGNORECASE)
    return [_numbers(" ".join(match.groups())) for match in pattern.finditer(normalized)]


def _numbers(text: str) -> list[float]:
    values = []
    for token in re.findall(r"\(?-?\d[\d,]*\)?", text):
        negative = token.startswith("(") and token.endswith(")")
        cleaned = token.replace("(", "").replace(")", "").replace(",", "")
        try:
            value = float(cleaned)
        except ValueError:
            continue
        values.append(-value if negative else value)
    return values


def _normalize_text(text: str) -> str:
    return " ".join(text.replace("\u2019", "'").replace("\xa0", " ").split())


def _fiscal_year_from_text(text: str) -> int | None:
    match = re.search(r"For the year ended 31 December\s+(20\d{2})", text)
    return int(match.group(1)) if match else None
