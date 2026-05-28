from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from stock_research.extraction.xbrl import derive_official_facts
from stock_research.qualitative.annual_report import _document_text
from stock_research.sources.http import FetchError, fetch_bytes, write_bytes


DEFAULT_IR_REPORTS_CONFIG = Path("config/ir_annual_reports.json")
DEFAULT_IR_PDF_CACHE = Path("data/raw/ir_pdfs")


SECTION_PATTERNS = {
    "balance_sheet": (
        "PDD HOLDINGS INC. CONSOLIDATED BALANCE SHEETS",
        "PDD HOLDINGS INC. CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME",
    ),
    "income_statement": (
        "PDD HOLDINGS INC. CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME",
        "PDD HOLDINGS INC. CONSOLIDATED STATEMENTS OF SHAREHOLDERS",
    ),
    "cash_flow": (
        "PDD HOLDINGS INC. CONSOLIDATED STATEMENTS OF CASH FLOWS",
        "PDD HOLDINGS INC. NOTES TO THE CONSOLIDATED FINANCIAL STATEMENTS",
    ),
}


FACT_ROWS = {
    "cash": {
        "section": "balance_sheet",
        "label": "Cash and cash equivalents",
        "stop": "Restricted cash",
        "columns": "balance",
    },
    "total_assets": {
        "section": "balance_sheet",
        "label": "Total Assets",
        "stop": "LIABILITIES AND SHAREHOLDERS",
        "columns": "balance",
    },
    "total_liabilities": {
        "section": "balance_sheet",
        "label": "Total liabilities",
        "stop": "Commitments and contingencies",
        "columns": "balance",
    },
    "revenue": {
        "section": "income_statement",
        "label": "Revenues (including services",
        "stop": "Costs of revenues",
        "columns": "three_year_income",
    },
    "operating_income": {
        "section": "income_statement",
        "label": "Operating profit",
        "stop": "Interest and investment income",
        "columns": "three_year_income",
    },
    "net_income": {
        "section": "income_statement",
        "label": "Net income attributable to ordinary shareholders",
        "stop": "Earnings per share",
        "columns": "three_year_income",
    },
    "operating_cash_flow": {
        "section": "cash_flow",
        "label": "Net cash generated from operating activities",
        "stop": "CASH FLOW FROM INVESTING ACTIVITIES",
        "columns": "three_year_income",
    },
    "stock_based_compensation": {
        "section": "cash_flow",
        "label": "Share-based compensation",
        "stop": "Foreign exchange",
        "columns": "three_year_income",
    },
    "depreciation_and_amortization": {
        "section": "cash_flow",
        "label": "Depreciation and amortization",
        "stop": "Deferred income tax",
        "columns": "three_year_income",
    },
    "capex": {
        "section": "cash_flow",
        "label": "Purchase of property, equipment and software and intangible assets",
        "stop": "Loans to a related party",
        "columns": "three_year_income",
        "absolute_value": True,
        "interpretation_note": "This official annual-report line includes property, equipment, software and intangible assets, so it is a broader CapEx proxy than a pure PP&E-only tag.",
    },
}

NUMBER_PATTERN = re.compile(r"\(\s*\d[\d,]*\s*\)|\d[\d,]*")


def cross_validate_and_fill_from_ir_reports(
    *,
    company: dict[str, Any],
    documents: list[dict[str, Any]],
    extracted_facts: list[dict[str, Any]],
    config_path: str | Path = DEFAULT_IR_REPORTS_CONFIG,
    cache_dir: str | Path = DEFAULT_IR_PDF_CACHE,
) -> dict[str, Any]:
    company_id = company.get("company_id")
    config = _load_config(config_path)
    company_config = config.get("companies", {}).get(company_id or "", {})
    report_configs = company_config.get("reports", [])
    if not report_configs:
        return {
            "status": "no_ir_report_config",
            "comparisons": [],
            "filled_facts": [],
            "source_attempts": [],
            "updated_facts": extracted_facts,
            "notes": ["No configured IR annual-report PDFs for this company."],
        }

    comparisons: list[dict[str, Any]] = []
    filled_facts: list[dict[str, Any]] = []
    source_attempts: list[dict[str, Any]] = []
    supplemental_facts: list[dict[str, Any]] = []
    for report_config in report_configs:
        text_result = _text_for_report(
            report_config=report_config,
            documents=documents,
            company_id=str(company_id),
            cache_dir=Path(cache_dir),
        )
        source_attempts.append(text_result["source_attempt"])
        if not text_result.get("text"):
            continue
        supplemental_facts.extend(
            _extract_pdd_annual_report_facts(
                text_result["text"],
                report_config=report_config,
                source_attempt=text_result["source_attempt"],
            )
        )

    existing_index = _fact_index(extracted_facts)
    updated = list(extracted_facts)
    for fact in supplemental_facts:
        key = _fact_key(fact)
        existing = existing_index.get(key)
        if existing:
            comparisons.append(_compare_fact(existing, fact))
            continue
        updated.append(fact)
        existing_index[key] = fact
        filled_facts.append(
            {
                "metric": fact.get("metric"),
                "year": str(fact.get("end_date", ""))[:4],
                "value": fact.get("value"),
                "unit": fact.get("unit"),
                "source_url": fact.get("source_url"),
                "extraction_method": fact.get("extraction_method"),
                "interpretation_note": fact.get("interpretation_note"),
            }
        )

    updated = derive_official_facts(updated)
    material_conflicts = [
        comparison for comparison in comparisons if comparison.get("status") == "material_conflict"
    ]
    return {
        "status": "completed" if supplemental_facts else "no_supplemental_facts_extracted",
        "comparisons": comparisons,
        "filled_facts": filled_facts,
        "source_attempts": source_attempts,
        "updated_facts": updated,
        "notes": [
            "IR annual report PDFs are attempted first when configured and reachable.",
            "When local DNS/PDF access is unavailable, the agent falls back to the cached SEC HTML copy of the same official 20-F filing.",
            "Filled facts are labeled separately from SEC inline-XBRL facts.",
        ],
        "material_conflicts": material_conflicts,
    }


def _load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {"companies": {}}
    return json.loads(config_path.read_text(encoding="utf-8"))


def _text_for_report(
    *,
    report_config: dict[str, Any],
    documents: list[dict[str, Any]],
    company_id: str,
    cache_dir: Path,
) -> dict[str, Any]:
    source_url = report_config.get("source_url")
    fiscal_year = report_config.get("fiscal_year")
    pdf_path = cache_dir / company_id / f"{fiscal_year}.pdf"
    source_attempt: dict[str, Any] = {
        "fiscal_year": fiscal_year,
        "source_url": source_url,
        "preferred_source": "official_ir_pdf",
        "cache_path": str(pdf_path),
    }

    if source_url:
        try:
            if not pdf_path.exists():
                data = fetch_bytes(
                    source_url,
                    headers={
                        "User-Agent": "stock-research-system/0.1",
                        "Accept": "application/pdf,text/html,*/*",
                    },
                    timeout=30,
                )
                write_bytes(pdf_path, data)
            pdf_text = _pdf_text(pdf_path)
            if pdf_text:
                source_attempt["status"] = "ir_pdf_text_extracted"
                source_attempt["text_source"] = "ir_pdf"
                return {"text": pdf_text, "source_attempt": source_attempt}
            source_attempt["pdf_error"] = "PDF downloaded but no parser/text was available."
        except (FetchError, OSError, RuntimeError) as exc:
            source_attempt["pdf_error"] = str(exc)

    fallback = _matching_sec_html_document(report_config, documents)
    if fallback and fallback.get("local_path"):
        source_attempt["status"] = "fallback_sec_html_same_filing"
        source_attempt["text_source"] = "sec_html_same_20f"
        source_attempt["fallback_local_path"] = fallback.get("local_path")
        source_attempt["fallback_source_url"] = fallback.get("source_url")
        return {
            "text": _document_text(Path(str(fallback["local_path"]))),
            "source_attempt": source_attempt,
        }

    source_attempt["status"] = "failed_no_text_source"
    return {"text": "", "source_attempt": source_attempt}


def _pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError:
        return ""
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _matching_sec_html_document(
    report_config: dict[str, Any],
    documents: list[dict[str, Any]],
) -> dict[str, Any] | None:
    accession = report_config.get("sec_accession_number")
    fiscal_year = report_config.get("fiscal_year")
    candidates = []
    for document in documents:
        if not str(document.get("document_type", "")).startswith("20-F"):
            continue
        if accession and str(document.get("document_id", "")).startswith(str(accession)):
            return document
        if fiscal_year and str(document.get("report_date", "")).startswith(str(fiscal_year)):
            candidates.append(document)
    return sorted(candidates, key=lambda doc: doc.get("filing_date") or "")[-1] if candidates else None


def _extract_pdd_annual_report_facts(
    text: str,
    *,
    report_config: dict[str, Any],
    source_attempt: dict[str, Any],
) -> list[dict[str, Any]]:
    fiscal_year = int(report_config["fiscal_year"])
    sections = {
        section_id: _section(text, start, end)
        for section_id, (start, end) in SECTION_PATTERNS.items()
    }
    facts: list[dict[str, Any]] = []
    for metric, row_config in FACT_ROWS.items():
        section = sections.get(str(row_config["section"]), "")
        segment = _row_segment(section, str(row_config["label"]), str(row_config["stop"]))
        if not segment:
            continue
        values = _row_values(segment)
        if row_config["columns"] == "balance":
            year_values = _balance_year_values(values, fiscal_year)
        else:
            year_values = _three_year_values(values, fiscal_year)
        for year, value in year_values.items():
            if row_config.get("absolute_value"):
                value = abs(value)
            facts.append(
                _supplemental_fact(
                    metric=metric,
                    value=value * 1000,
                    year=year,
                    report_config=report_config,
                    source_attempt=source_attempt,
                    interpretation_note=row_config.get("interpretation_note"),
                )
            )
    return facts


def _section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    if start == -1:
        return ""
    end = text.find(end_marker, start + len(start_marker))
    return text[start:] if end == -1 else text[start:end]


def _row_segment(section: str, label: str, stop: str) -> str:
    start = section.find(label)
    if start == -1:
        return ""
    end = section.find(stop, start + len(label))
    return section[start:] if end == -1 else section[start:end]


def _row_values(segment: str) -> list[float]:
    values = []
    for token in NUMBER_PATTERN.findall(segment):
        cleaned = token.replace(" ", "").replace(",", "")
        is_negative = cleaned.startswith("(") and cleaned.endswith(")")
        cleaned = cleaned.replace("(", "").replace(")", "")
        try:
            value = float(cleaned)
        except ValueError:
            continue
        values.append(-value if is_negative else value)
    return values


def _three_year_values(values: list[float], fiscal_year: int) -> dict[int, float]:
    if len(values) < 4:
        return {}
    selected = values[-4:-1]
    return {
        fiscal_year - 2: selected[0],
        fiscal_year - 1: selected[1],
        fiscal_year: selected[2],
    }


def _balance_year_values(values: list[float], fiscal_year: int) -> dict[int, float]:
    if len(values) < 3:
        return {}
    selected = values[-3:-1]
    return {
        fiscal_year - 1: selected[0],
        fiscal_year: selected[1],
    }


def _supplemental_fact(
    *,
    metric: str,
    value: float,
    year: int,
    report_config: dict[str, Any],
    source_attempt: dict[str, Any],
    interpretation_note: str | None,
) -> dict[str, Any]:
    method = (
        "official_ir_pdf_text_label"
        if source_attempt.get("text_source") == "ir_pdf"
        else "official_annual_report_text_label_fallback"
    )
    return {
        "fact_id": f"ir_pdf_cross_check:{report_config.get('fiscal_year')}:{metric}:{year}",
        "metric": metric,
        "label": metric.replace("_", " ").title(),
        "xbrl_tag": None,
        "value": int(value) if float(value).is_integer() else value,
        "unit": "CNY",
        "period_type": "annual" if metric not in {"cash", "total_assets", "total_liabilities"} else "instant",
        "start_date": f"{year}-01-01" if metric not in {"cash", "total_assets", "total_liabilities"} else None,
        "end_date": f"{year}-12-31",
        "instant": f"{year}-12-31" if metric in {"cash", "total_assets", "total_liabilities"} else None,
        "source_id": "pdd_investor_relations",
        "source_url": report_config.get("source_url"),
        "local_path": source_attempt.get("cache_path")
        if source_attempt.get("text_source") == "ir_pdf"
        else source_attempt.get("fallback_local_path"),
        "document_id": f"ir_annual_report:{report_config.get('fiscal_year')}",
        "document_type": "annual_report_pdf",
        "accession_number": report_config.get("sec_accession_number"),
        "downloaded_file": Path(str(source_attempt.get("cache_path", ""))).name,
        "filing_date": report_config.get("filing_date"),
        "report_date": f"{report_config.get('fiscal_year')}-12-31",
        "confidence": "medium",
        "extraction_method": method,
        "selection_policy": "supplement_missing_xbrl_fact_from_official_ir_annual_report",
        "interpretation_note": interpretation_note,
    }


def _fact_index(facts: list[dict[str, Any]]) -> dict[tuple[Any, ...], dict[str, Any]]:
    return {_fact_key(fact): fact for fact in facts}


def _fact_key(fact: dict[str, Any]) -> tuple[Any, ...]:
    return (
        fact.get("metric"),
        fact.get("unit"),
        fact.get("period_type"),
        fact.get("start_date"),
        fact.get("end_date"),
        fact.get("instant"),
    )


def _compare_fact(existing: dict[str, Any], supplemental: dict[str, Any]) -> dict[str, Any]:
    existing_value = float(existing.get("value", 0))
    supplemental_value = float(supplemental.get("value", 0))
    denominator = max(abs(existing_value), abs(supplemental_value), 1.0)
    mismatch_pct = abs(existing_value - supplemental_value) / denominator
    status = "material_conflict" if mismatch_pct > 0.02 else "matched"
    return {
        "status": status,
        "metric": existing.get("metric"),
        "unit": existing.get("unit"),
        "period_type": existing.get("period_type"),
        "start_date": existing.get("start_date"),
        "end_date": existing.get("end_date"),
        "instant": existing.get("instant"),
        "existing_value": existing_value,
        "supplemental_value": supplemental_value,
        "mismatch_pct": mismatch_pct,
        "existing_fact_id": existing.get("fact_id"),
        "supplemental_fact_id": supplemental.get("fact_id"),
        "source_url": supplemental.get("source_url"),
    }
