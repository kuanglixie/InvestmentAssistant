from __future__ import annotations

import html
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

QUARTER_END_RE = re.compile(
    r"(?:quarter ended|three months ended)(?:\s+and\s+the\s+fiscal\s+year\s+ended)?\s+"
    r"([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})",
    flags=re.IGNORECASE,
)


def extract_earnings_release_facts(path: Path, document: dict[str, Any]) -> list[dict[str, Any]]:
    raw_html = path.read_text(encoding="utf-8", errors="ignore")
    text = _plain_text(raw_html)
    if not _is_earnings_release(text):
        return []

    end_date = _quarter_end_date(text)
    if end_date is None:
        return []
    start_date = _quarter_start_date(end_date)
    tables = _HtmlTableParser.parse(raw_html)

    facts: list[dict[str, Any]] = []
    values = _extract_current_quarter_values(tables, text)
    value_methods = {
        metric: "official_earnings_release_table"
        for metric, value in values.items()
        if value is not None
    }
    for metric, value in _extract_text_revenue_breakdown(text).items():
        if values.get(metric) is None:
            values[metric] = value
            value_methods[metric] = "official_earnings_release_text"
    for metric, value in values.items():
        if value is None:
            continue
        facts.append(
            _fact(
                document=document,
                metric=metric,
                label=_label(metric),
                value=value,
                unit="CNY",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                fact_index=len(facts),
                extraction_method=value_methods.get(metric, "official_earnings_release_table"),
            )
        )

    balance_sheet_values = _extract_balance_sheet_values(tables, text)
    for metric, value in balance_sheet_values.items():
        if value is None:
            continue
        facts.append(
            _fact(
                document=document,
                metric=metric,
                label=_label(metric),
                value=value,
                unit="CNY",
                start_date=None,
                end_date=end_date.isoformat(),
                fact_index=len(facts),
                period_type="instant",
            )
        )

    diluted_shares = _extract_diluted_shares(tables)
    if diluted_shares is not None:
        facts.append(
            _fact(
                document=document,
                metric="diluted_shares",
                label="Diluted shares",
                value=diluted_shares,
                unit="shares",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                fact_index=len(facts),
            )
        )

    for metric, value in _extract_non_gaap_bridge_values(tables, text).items():
        if value is None:
            continue
        facts.append(
            _fact(
                document=document,
                metric=metric,
                label=_label(metric),
                value=value,
                unit="CNY",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                fact_index=len(facts),
                extraction_method="official_earnings_release_non_gaap_bridge",
            )
        )

    return facts


def _extract_current_quarter_values(tables: list[list[list[str]]], text: str) -> dict[str, int | None]:
    income_table = _first_table_with_rows(tables, ("revenues", "operating profit", "net income"))
    cash_flow_table = _first_table_with_rows(tables, ("net cash", "operating activities"))

    revenue = _current_quarter_rmb(_find_row(income_table, "revenues"), income_table, text)
    online_marketing_services_revenue = _current_quarter_rmb(
        _find_row(income_table, "online", "marketing", "services"),
        income_table,
        text,
    )
    transaction_services_revenue = _current_quarter_rmb(
        _find_row(income_table, "transaction services"),
        income_table,
        text,
    )
    cost_of_revenue = _current_expense_rmb(_find_row(income_table, "costs of revenues"), income_table, text)
    sales_and_marketing = _current_expense_rmb(_find_row(income_table, "sales", "marketing"), income_table, text)
    research_and_development = _current_expense_rmb(
        _find_row(income_table, "research", "development"), income_table, text
    )
    general_and_administrative = _current_expense_rmb(
        _find_row(income_table, "general", "administrative"), income_table, text
    )
    operating_income = _current_quarter_rmb(_find_row(income_table, "operating profit"), income_table, text)
    net_income = _current_quarter_rmb(_find_row(income_table, "net income"), income_table, text)
    operating_cash_flow = _current_quarter_rmb(
        _find_row(cash_flow_table, "net cash", "operating activities"),
        cash_flow_table,
        text,
    )

    gross_profit = None
    if revenue is not None and cost_of_revenue is not None:
        gross_profit = revenue + cost_of_revenue if cost_of_revenue < 0 else revenue - cost_of_revenue

    return {
        "revenue": revenue,
        "online_marketing_services_revenue": online_marketing_services_revenue,
        "transaction_services_revenue": transaction_services_revenue,
        "cost_of_revenue": cost_of_revenue,
        "gross_profit": gross_profit,
        "sales_and_marketing_expense": sales_and_marketing,
        "research_and_development_expense": research_and_development,
        "general_and_administrative_expense": general_and_administrative,
        "operating_income": operating_income,
        "net_income": net_income,
        "operating_cash_flow": operating_cash_flow,
    }


def _extract_text_revenue_breakdown(text: str) -> dict[str, int]:
    patterns = {
        "online_marketing_services_revenue": (
            r"revenues\s+from\s+online\s+marketing\s+services\s+and\s+others\s+were\s+RMB\s*"
            r"([\d.]+)\s+billion"
        ),
        "transaction_services_revenue": (
            r"revenues\s+from\s+transaction\s+services\s+were\s+RMB\s*"
            r"([\d.]+)\s+billion"
        ),
    }
    values: dict[str, int] = {}
    for metric, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        values[metric] = int(float(match.group(1)) * 1_000_000_000)
    return values


def _extract_balance_sheet_values(tables: list[list[list[str]]], text: str) -> dict[str, int | None]:
    balance_sheet_table = _first_table_with_rows(tables, ("cash and cash equivalents",))
    liabilities_table = _first_table_with_rows(tables, ("total liabilities",))
    cash = _current_balance_sheet_rmb(
        _find_row(balance_sheet_table, "cash and cash equivalents"),
        balance_sheet_table,
        text,
    )
    short_term_investments = _current_balance_sheet_rmb(
        _find_row(balance_sheet_table, "short-term investments"),
        balance_sheet_table,
        text,
    )
    total_assets = _current_balance_sheet_rmb(
        _find_row(balance_sheet_table, "total assets"),
        balance_sheet_table,
        text,
    )
    current_assets = _current_balance_sheet_rmb(
        _find_row(balance_sheet_table, "total current assets"),
        balance_sheet_table,
        text,
    )
    current_liabilities = _current_balance_sheet_rmb(
        _find_row(liabilities_table, "total current liabilities"),
        liabilities_table,
        text,
    )
    total_liabilities = _current_balance_sheet_rmb(
        _find_row(liabilities_table, "total liabilities"),
        liabilities_table,
        text,
    )
    cash_and_short_term_investments = None
    if cash is not None and short_term_investments is not None:
        cash_and_short_term_investments = cash + short_term_investments
    return {
        "cash": cash,
        "short_term_investments": short_term_investments,
        "cash_and_short_term_investments": cash_and_short_term_investments,
        "current_assets": current_assets,
        "total_assets": total_assets,
        "current_liabilities": current_liabilities,
        "total_liabilities": total_liabilities,
    }


def _extract_non_gaap_bridge_values(tables: list[list[list[str]]], text: str) -> dict[str, int | None]:
    patterns = {
        "non_gaap_operating_income": [
            ("non-gaap", "operating", "profit"),
            ("non-gaap", "operating", "income"),
        ],
        "non_gaap_net_income": [
            ("non-gaap", "net income"),
        ],
        "non_gaap_adjustment_share_based_compensation": [
            ("share-based compensation",),
            ("share based compensation",),
        ],
        "non_gaap_adjustment_fair_value_changes": [
            ("fair value",),
        ],
        "non_gaap_adjustment_amortization": [
            ("amortization",),
        ],
        "non_gaap_adjustment_tax_effect": [
            ("tax effect",),
            ("income tax effect",),
        ],
    }
    values: dict[str, int | None] = {}
    for table in tables:
        table_text = " ".join(" ".join(row).lower() for row in table)
        if "non-gaap" not in table_text:
            continue
        for metric, candidates in patterns.items():
            if metric in values:
                continue
            row = _find_row_matching_any(table, candidates)
            value = _current_quarter_rmb(row, table, text) if row else None
            if value is None:
                continue
            if metric.startswith("non_gaap_adjustment_"):
                value = abs(value)
            values[metric] = value
    return values


def _extract_diluted_shares(tables: list[list[list[str]]]) -> int | None:
    for table in tables:
        in_weighted_average_section = False
        section_multiplier = 1000
        for row in table:
            label = _row_label(row)
            label_lower = label.lower()
            if "weighted" in label_lower and "average" in label_lower and "share" in label_lower:
                numbers = _numbers_from_row(row)
                section_multiplier = _share_multiplier(row, default=section_multiplier)
                if "diluted" in label_lower and len(numbers) >= 2:
                    return int(numbers[1] * section_multiplier)
                in_weighted_average_section = True
                continue
            if in_weighted_average_section and _is_diluted_share_count_row(label):
                numbers = _numbers_from_row(row)
                if len(numbers) >= 2:
                    return int(numbers[1] * section_multiplier)
    return None


def _current_quarter_rmb(row: list[str] | None, table: list[list[str]], text: str) -> int | None:
    if row is None:
        return None
    numbers = _numbers_from_row(row)
    if len(numbers) < 2:
        return None
    return int(numbers[1] * _rmb_multiplier(table, text))


def _current_expense_rmb(row: list[str] | None, table: list[list[str]], text: str) -> int | None:
    value = _current_quarter_rmb(row, table, text)
    return abs(value) if value is not None else None


def _current_balance_sheet_rmb(row: list[str] | None, table: list[list[str]], text: str) -> int | None:
    if row is None:
        return None
    numbers = _numbers_from_row(row)
    if len(numbers) < 2:
        return None
    return int(numbers[1] * _rmb_multiplier(table, text))


def _rmb_multiplier(table: list[list[str]], text: str) -> int:
    table_text = " ".join(" ".join(row).lower() for row in table)
    if "amounts in millions" in table_text:
        return 1_000_000
    if "amounts in thousands" in table_text:
        return 1_000
    text_lower = text.lower()
    if re.search(r"amounts\s+in\s+millions\s+of\s+(?:rmb|renminbi)", text_lower):
        return 1_000_000
    if re.search(r"amounts\s+in\s+thousands\s+of\s+(?:rmb|renminbi)", text_lower):
        return 1_000
    return 1_000


def _share_multiplier(row: list[str], *, default: int) -> int:
    label = _row_label(row).lower()
    if "in millions" in label:
        return 1_000_000
    if "in thousands" in label:
        return 1_000
    return default


def _first_table_with_rows(tables: list[list[list[str]]], labels: tuple[str, ...]) -> list[list[str]]:
    for table in tables:
        table_text = " ".join(" ".join(row).lower() for row in table)
        if all(label in table_text for label in labels):
            return table
    return []


def _find_row(table: list[list[str]], *labels: str) -> list[str] | None:
    for row in table:
        row_label = _row_label(row).lower()
        if all(label in row_label for label in labels):
            return row
    return None


def _find_row_matching_any(
    table: list[list[str]],
    candidates: list[tuple[str, ...]],
) -> list[str] | None:
    for row in table:
        row_label = _row_label(row).lower()
        if any(all(label in row_label for label in labels) for labels in candidates):
            return row
    return None


def _numbers_from_row(row: list[str]) -> list[float]:
    text = " ".join(row[1:])
    numbers = []
    for match in re.finditer(r"\(?\s*-?\d[\d,]*(?:\.\d+)?\s*\)?", text):
        raw = match.group(0)
        negative = raw.strip().startswith("(")
        cleaned = raw.replace(",", "").replace("(", "").replace(")", "").strip()
        try:
            value = float(cleaned)
        except ValueError:
            continue
        numbers.append(-value if negative else value)
    return numbers


def _quarter_end_date(text: str) -> date | None:
    match = QUARTER_END_RE.search(text)
    if not match:
        return None
    month_name, day, year = match.groups()
    month = MONTHS.get(month_name.lower())
    if month is None:
        return None
    return date(int(year), month, int(day))


def _quarter_start_date(end_date: date) -> date:
    quarter_start_month = {3: 1, 6: 4, 9: 7, 12: 10}.get(end_date.month)
    if quarter_start_month is None:
        return date(end_date.year, end_date.month, 1)
    return date(end_date.year, quarter_start_month, 1)


def _is_earnings_release(text: str) -> bool:
    lowered = text.lower()
    return "financial results" in lowered and "quarter" in lowered


def _fact(
    *,
    document: dict[str, Any],
    metric: str,
    label: str,
    value: int,
    unit: str,
    start_date: str | None,
    end_date: str,
    fact_index: int,
    period_type: str = "quarter",
    extraction_method: str = "official_earnings_release_table",
) -> dict[str, Any]:
    fact_id = (
        f"{document.get('document_id')}:{metric}:"
        f"{start_date or ''}:{end_date}:earnings_release_table:{fact_index}"
    )
    return {
        "fact_id": fact_id,
        "metric": metric,
        "label": label,
        "xbrl_tag": None,
        "context_ref": None,
        "context_rank": 0,
        "value": value,
        "unit": unit,
        "period_type": period_type,
        "start_date": start_date,
        "end_date": end_date,
        "instant": end_date if period_type == "instant" else None,
        "source_id": document.get("source_id"),
        "source_url": document.get("source_url"),
        "local_path": document.get("local_path"),
        "document_id": document.get("document_id"),
        "document_type": document.get("document_type"),
        "accession_number": _accession_from_document(document),
        "downloaded_file": document.get("downloaded_file"),
        "filing_date": document.get("filing_date"),
        "report_date": document.get("report_date"),
        "confidence": "medium",
        "extraction_method": extraction_method,
        "selection_policy": "current_quarter_rmb_column_from_official_6k_exhibit",
    }


def _label(metric: str) -> str:
    return {
        "revenue": "Revenue",
        "online_marketing_services_revenue": "Online marketing services and others revenue",
        "transaction_services_revenue": "Transaction services revenue",
        "cost_of_revenue": "Cost of revenue",
        "gross_profit": "Gross profit",
        "sales_and_marketing_expense": "Sales and marketing expense",
        "research_and_development_expense": "Research and development expense",
        "general_and_administrative_expense": "General and administrative expense",
        "operating_income": "Operating income",
        "net_income": "Net income",
        "operating_cash_flow": "Operating cash flow",
        "cash": "Cash and cash equivalents",
        "short_term_investments": "Short-term investments",
        "cash_and_short_term_investments": "Cash and short-term investments",
        "current_assets": "Current assets",
        "total_assets": "Total assets",
        "current_liabilities": "Current liabilities",
        "total_liabilities": "Total liabilities",
        "non_gaap_operating_income": "Non-GAAP operating income",
        "non_gaap_net_income": "Non-GAAP net income",
        "non_gaap_adjustment_share_based_compensation": "Non-GAAP adjustment: share-based compensation",
        "non_gaap_adjustment_fair_value_changes": "Non-GAAP adjustment: fair-value changes",
        "non_gaap_adjustment_amortization": "Non-GAAP adjustment: amortization",
        "non_gaap_adjustment_tax_effect": "Non-GAAP adjustment: tax effect",
    }.get(metric, metric)


def _row_label(row: list[str]) -> str:
    return row[0] if row else ""


def _is_diluted_share_count_row(label: str) -> bool:
    normalized = label.lower().replace("-", " ").strip()
    if normalized == "diluted":
        return True
    return "diluted" in normalized and "weighted" in normalized and "average" in normalized


def _plain_text(raw_html: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", raw_html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _accession_from_document(document: dict[str, Any]) -> str | None:
    document_id = document.get("document_id")
    if isinstance(document_id, str) and ":" in document_id:
        return document_id.split(":", 1)[0]
    return None


class _HtmlTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._table_depth = 0
        self._in_row = False
        self._in_cell = False
        self._cell_parts: list[str] = []
        self._row: list[str] = []
        self._current_table: list[list[str]] = []
        self.tables: list[list[list[str]]] = []

    @classmethod
    def parse(cls, raw_html: str) -> list[list[list[str]]]:
        parser = cls()
        parser.feed(raw_html)
        return parser.tables

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._current_table = []
        elif self._table_depth and tag == "tr":
            self._in_row = True
            self._row = []
        elif self._table_depth and tag in {"td", "th"}:
            self._in_cell = True
            self._cell_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._table_depth and tag in {"td", "th"} and self._in_cell:
            cell = html.unescape("".join(self._cell_parts))
            self._row.append(re.sub(r"\s+", " ", cell).strip())
            self._in_cell = False
        elif self._table_depth and tag == "tr" and self._in_row:
            if any(self._row):
                self._current_table.append(self._row)
            self._in_row = False
        elif tag == "table" and self._table_depth:
            self._table_depth -= 1
            if self._table_depth == 0:
                self.tables.append(self._current_table)
                self._current_table = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_parts.append(data)
