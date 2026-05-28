from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from stock_research.extraction.tencent_reports import pdf_text
from stock_research.sources.http import FetchError, fetch_bytes, fetch_json, write_bytes, write_json
from stock_research.valuation.market_inputs import load_manual_market_inputs


GOOGLE_PDD_QUOTE_URL = "https://www.google.com/finance/quote/PDD:NASDAQ?hl=en"
GOOGLE_USD_CNY_URL = "https://www.google.com/finance/quote/USD-CNY?hl=en"
YAHOO_PDD_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/PDD?range=1d&interval=1d"
GOOGLE_TENCENT_QUOTE_URL = "https://www.google.com/finance/quote/0700:HKG?hl=en"
GOOGLE_HKD_CNY_URL = "https://www.google.com/finance/quote/HKD-CNY?hl=en"
YAHOO_TENCENT_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/0700.HK?range=1d&interval=1d"
GOOGLE_HEADERS = {"User-Agent": "Mozilla/5.0 stock-research-system/0.1"}
PRICE_MISMATCH_REVIEW_THRESHOLD = 0.01
MARKET_CAP_MISMATCH_REVIEW_THRESHOLD = 0.03


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return normalize_text(" ".join(self.parts))


def collect_market_inputs(
    *,
    company: dict[str, Any],
    documents: list[dict[str, Any]],
    cache_root: str | Path = "data/raw/market_data",
) -> dict[str, Any]:
    company_id = company.get("company_id")
    if _offline_mode():
        result = load_manual_market_inputs(company_id)
        result["collection_method"] = "offline_manual_inputs_only"
        return result

    if company_id == "tencent":
        try:
            return collect_tencent_market_inputs(documents=documents, cache_root=cache_root)
        except Exception as exc:  # noqa: BLE001 - report market-data failures without blocking the run.
            result = load_manual_market_inputs(company_id)
            result["collection_method"] = "auto_collection_failed_manual_fallback"
            result["auto_collection_error"] = str(exc)
            return result

    if company_id != "pdd":
        result = load_manual_market_inputs(company_id)
        result["collection_method"] = "manual_inputs_only_for_unimplemented_company"
        return result

    try:
        return collect_pdd_market_inputs(documents=documents, cache_root=cache_root)
    except Exception as exc:  # noqa: BLE001 - report market-data failures without blocking the run.
        result = load_manual_market_inputs(company_id)
        result["collection_method"] = "auto_collection_failed_manual_fallback"
        result["auto_collection_error"] = str(exc)
        return result


def collect_pdd_market_inputs(
    *,
    documents: list[dict[str, Any]],
    cache_root: str | Path = "data/raw/market_data",
) -> dict[str, Any]:
    cache_dir = Path(cache_root) / "pdd"
    cache_dir.mkdir(parents=True, exist_ok=True)

    share_structure = extract_pdd_share_structure(documents)
    google_quote = fetch_google_pdd_quote(cache_dir=cache_dir)
    google_fx = fetch_google_usd_cny(cache_dir=cache_dir)
    yahoo_quote = fetch_yahoo_pdd_quote(cache_dir=cache_dir)
    validation = validate_market_inputs(
        share_structure=share_structure,
        google_quote=google_quote,
        google_fx=google_fx,
        yahoo_quote=yahoo_quote,
    )

    missing = validation["missing"]
    conflicts = validation["conflicts"]
    inputs: dict[str, Any] = {}
    if not missing:
        ads_outstanding = share_structure["ordinary_shares_outstanding"] / share_structure["ordinary_shares_per_ads"]
        market_cap_usd = google_quote["price"] * ads_outstanding
        inputs = {
            "as_of_date": google_quote.get("as_of_date") or utc_now_iso(),
            "currency": "USD",
            "source": "Google Finance PDD:NASDAQ price with official PDD 20-F share structure",
            "share_price": google_quote["price"],
            "share_price_source": "Google Finance PDD:NASDAQ",
            "share_price_source_url": GOOGLE_PDD_QUOTE_URL,
            "market_cap": market_cap_usd,
            "market_cap_method": "ADS price * (ordinary shares outstanding / ordinary shares per ADS)",
            "ads_outstanding": ads_outstanding,
            "ordinary_shares_outstanding": share_structure["ordinary_shares_outstanding"],
            "ordinary_shares_per_ads": share_structure["ordinary_shares_per_ads"],
            "share_structure_source": share_structure.get("source_document"),
            "share_structure_as_of_date": share_structure.get("as_of_date"),
            "usd_cny_fx": google_fx["rate"],
            "fx_source": "Google Finance USD/CNY",
            "fx_source_url": GOOGLE_USD_CNY_URL,
            "fx_as_of_date": google_fx.get("as_of_date"),
            "review_status": "auto_collected_verified" if not conflicts else "source_conflict",
        }

    status = "input_available"
    if missing:
        status = "input_incomplete"
    elif conflicts:
        status = "source_conflict"

    result = {
        "status": status,
        "company_id": "pdd",
        "path": "auto:market_data_agent",
        "collection_method": "auto_google_quote_google_fx_official_20f_share_structure",
        "inputs": inputs,
        "missing": missing,
        "input_required": bool(missing),
        "review_status": inputs.get("review_status", "missing" if missing else "source_conflict"),
        "review_required": bool(conflicts),
        "validation": validation,
        "source_records": {
            "share_structure": share_structure,
            "google_quote": google_quote,
            "google_fx": google_fx,
            "yahoo_quote": yahoo_quote,
        },
        "notes": "Market cap is calculated from quote price and official share structure; vendor market caps are cross-checks only.",
    }
    write_json(cache_dir / "market_inputs.latest.json", result)
    return result


def collect_tencent_market_inputs(
    *,
    documents: list[dict[str, Any]],
    cache_root: str | Path = "data/raw/market_data",
) -> dict[str, Any]:
    cache_dir = Path(cache_root) / "tencent"
    cache_dir.mkdir(parents=True, exist_ok=True)

    share_structure = extract_tencent_share_structure(documents)
    google_quote = fetch_google_tencent_quote(cache_dir=cache_dir)
    google_fx = fetch_google_hkd_cny(cache_dir=cache_dir)
    yahoo_quote = fetch_yahoo_tencent_quote(cache_dir=cache_dir)
    validation = validate_tencent_market_inputs(
        share_structure=share_structure,
        google_quote=google_quote,
        google_fx=google_fx,
        yahoo_quote=yahoo_quote,
    )

    missing = validation["missing"]
    conflicts = validation["conflicts"]
    inputs: dict[str, Any] = {}
    if not missing:
        shares_outstanding = share_structure["ordinary_shares_outstanding"]
        market_cap_hkd = google_quote["price"] * shares_outstanding
        inputs = {
            "as_of_date": google_quote.get("as_of_date") or utc_now_iso(),
            "currency": "HKD",
            "source": "Google Finance 0700:HKG price with official Tencent annual report issued share count",
            "share_price": google_quote["price"],
            "share_price_source": "Google Finance 0700:HKG",
            "share_price_source_url": GOOGLE_TENCENT_QUOTE_URL,
            "market_cap": market_cap_hkd,
            "market_cap_method": "ordinary share price * official issued shares outstanding",
            "ordinary_shares_outstanding": shares_outstanding,
            "share_structure_source": share_structure.get("source_document"),
            "share_structure_as_of_date": share_structure.get("as_of_date"),
            "hkd_cny_fx": google_fx["rate"],
            "fx_source": "Google Finance HKD/CNY",
            "fx_source_url": GOOGLE_HKD_CNY_URL,
            "fx_as_of_date": google_fx.get("as_of_date"),
            "review_status": "auto_collected_verified" if not conflicts else "source_conflict",
        }

    status = "input_available"
    if missing:
        status = "input_incomplete"
    elif conflicts:
        status = "source_conflict"

    result = {
        "status": status,
        "company_id": "tencent",
        "path": "auto:market_data_agent",
        "collection_method": "auto_google_quote_google_fx_official_annual_report_share_structure",
        "inputs": inputs,
        "missing": missing,
        "input_required": bool(missing),
        "review_status": inputs.get("review_status", "missing" if missing else "source_conflict"),
        "review_required": bool(conflicts),
        "validation": validation,
        "source_records": {
            "share_structure": share_structure,
            "google_quote": google_quote,
            "google_fx": google_fx,
            "yahoo_quote": yahoo_quote,
        },
        "notes": "Market cap is calculated from 0700.HK quote price and official Tencent issued shares; vendor market caps are cross-checks only.",
    }
    write_json(cache_dir / "market_inputs.latest.json", result)
    return result


def extract_pdd_share_structure(documents: list[dict[str, Any]]) -> dict[str, Any]:
    latest_20f = _latest_20f_document(documents)
    if not latest_20f:
        return {"status": "missing_latest_20f", "missing": ["latest 20-F document"]}
    path = Path(latest_20f.get("local_path") or "")
    if not path.exists():
        return {
            "status": "missing_latest_20f_file",
            "missing": ["latest 20-F local file"],
            "source_document": latest_20f.get("document_id"),
        }
    text = html_to_text(path.read_text(encoding="utf-8", errors="replace"))
    return parse_pdd_share_structure_text(
        text,
        source_document=latest_20f.get("document_id"),
        source_path=str(path),
    )


def parse_pdd_share_structure_text(
    text: str,
    *,
    source_document: str | None = None,
    source_path: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_text(text)
    ratio = _extract_ads_ratio(normalized)
    shares = _extract_ordinary_shares_outstanding(normalized)
    missing = []
    if ratio is None:
        missing.append("ordinary shares per ADS")
    if shares is None:
        missing.append("ordinary shares outstanding")
    if missing:
        return {
            "status": "missing_required_share_structure",
            "missing": missing,
            "source_document": source_document,
            "source_path": source_path,
        }
    return {
        "status": "extracted",
        "ordinary_shares_per_ads": ratio,
        "ordinary_shares_outstanding": shares["ordinary_shares_outstanding"],
        "as_of_date": shares.get("as_of_date"),
        "source_document": source_document,
        "source_path": source_path,
        "evidence": {
            "ads_ratio": "ADSs are defined as representing four Class A ordinary shares.",
            "ordinary_shares": shares.get("evidence"),
        },
    }


def extract_tencent_share_structure(documents: list[dict[str, Any]]) -> dict[str, Any]:
    latest_annual = _latest_tencent_annual_document(documents)
    if not latest_annual:
        return {"status": "missing_latest_annual_report", "missing": ["latest Tencent annual report"]}
    path = Path(latest_annual.get("local_path") or "")
    if not path.exists():
        return {
            "status": "missing_latest_annual_report_file",
            "missing": ["latest Tencent annual report local file"],
            "source_document": latest_annual.get("document_id"),
        }
    text_path = path.with_suffix(".txt")
    text = text_path.read_text(encoding="utf-8", errors="replace") if text_path.exists() else pdf_text(path)
    if not text:
        return {
            "status": "missing_pdf_text",
            "missing": ["Tencent annual report text"],
            "source_document": latest_annual.get("document_id"),
            "source_path": str(path),
        }
    return parse_tencent_share_structure_text(
        text,
        source_document=latest_annual.get("document_id"),
        source_path=str(path),
    )


def parse_tencent_share_structure_text(
    text: str,
    *,
    source_document: str | None = None,
    source_path: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_text(text)
    match = re.search(
        r"As at\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4}),\s+the total number of issued Shares was\s+([\d,]+)",
        normalized,
        flags=re.IGNORECASE,
    )
    if not match:
        return {
            "status": "missing_required_share_structure",
            "missing": ["ordinary shares outstanding"],
            "source_document": source_document,
            "source_path": source_path,
        }
    return {
        "status": "extracted",
        "ordinary_shares_outstanding": int(match.group(2).replace(",", "")),
        "as_of_date": match.group(1),
        "source_document": source_document,
        "source_path": source_path,
        "evidence": {
            "ordinary_shares": match.group(0),
        },
    }


def fetch_google_pdd_quote(*, cache_dir: Path) -> dict[str, Any]:
    data = fetch_bytes(GOOGLE_PDD_QUOTE_URL, headers=GOOGLE_HEADERS, timeout=20)
    path = write_bytes(cache_dir / "google_pdd_quote.html", data)
    text = html_to_text(data.decode("utf-8", errors="replace"))
    quote = parse_google_pdd_quote_text(text)
    quote.update(
        {
            "status": "fetched" if quote.get("price") is not None else "parse_failed",
            "source": "Google Finance PDD:NASDAQ",
            "url": GOOGLE_PDD_QUOTE_URL,
            "local_path": str(path),
            "fetched_at": utc_now_iso(),
        }
    )
    return quote


def parse_google_pdd_quote_text(text: str) -> dict[str, Any]:
    normalized = normalize_text(text)
    price = _first_float_match(
        normalized,
        [
            r"PDD Holdings Inc - ADR\s+\$([\d,.]+)",
            r"PDD:NASDAQ\s+PDD Holdings Inc - ADR\s+\$([\d,.]+)",
        ],
    )
    market_cap = _first_abbrev_match(normalized, [r"Mkt\.?\s*cap\s+([\d,.]+)\s*([TMB])"])
    shares_outstanding = _first_abbrev_match(
        normalized,
        [r"Shares outstanding\s+([\d,.]+)\s*([TMB])"],
    )
    timestamp = _first_text_match(
        normalized,
        [
            r"Closed:\s*([^·]+?)\s*·\s*USD",
            r"([A-Z][a-z]{2}\s+\d{1,2},\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M\s+GMT[-+]\d+)",
        ],
    )
    return {
        "price": price,
        "currency": "USD" if price is not None else None,
        "market_cap": market_cap,
        "shares_outstanding": shares_outstanding,
        "as_of_date": timestamp,
    }


def fetch_google_usd_cny(*, cache_dir: Path) -> dict[str, Any]:
    data = fetch_bytes(GOOGLE_USD_CNY_URL, headers=GOOGLE_HEADERS, timeout=20)
    path = write_bytes(cache_dir / "google_usd_cny.html", data)
    text = html_to_text(data.decode("utf-8", errors="replace"))
    quote = parse_google_usd_cny_text(text)
    quote.update(
        {
            "status": "fetched" if quote.get("rate") is not None else "parse_failed",
            "source": "Google Finance USD/CNY",
            "url": GOOGLE_USD_CNY_URL,
            "local_path": str(path),
            "fetched_at": utc_now_iso(),
        }
    )
    return quote


def parse_google_usd_cny_text(text: str) -> dict[str, Any]:
    normalized = normalize_text(text)
    rate = _first_float_match(
        normalized,
        [
            r"United States Dollar\s*/\s*Chinese Yuan\s+([\d,.]+)",
            r"USD\s*/\s*CNY\s+[\w\s/]*?([\d,.]+)",
        ],
    )
    timestamp = _first_text_match(
        normalized,
        [r"([A-Z][a-z]{2}\s+\d{1,2},\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M\s+UTC)"],
    )
    return {"rate": rate, "currency_pair": "USD/CNY", "as_of_date": timestamp}


def fetch_google_tencent_quote(*, cache_dir: Path) -> dict[str, Any]:
    data = fetch_bytes(GOOGLE_TENCENT_QUOTE_URL, headers=GOOGLE_HEADERS, timeout=20)
    path = write_bytes(cache_dir / "google_tencent_quote.html", data)
    text = html_to_text(data.decode("utf-8", errors="replace"))
    quote = parse_google_tencent_quote_text(text)
    quote.update(
        {
            "status": "fetched" if quote.get("price") is not None else "parse_failed",
            "source": "Google Finance 0700:HKG",
            "url": GOOGLE_TENCENT_QUOTE_URL,
            "local_path": str(path),
            "fetched_at": utc_now_iso(),
        }
    )
    return quote


def parse_google_tencent_quote_text(text: str) -> dict[str, Any]:
    normalized = normalize_text(text)
    price = _first_float_match(
        normalized,
        [
            r"0700:HKG\s+.*?Tencent Holdings Ltd\s+HK\$([\d,.]+)",
            r"Tencent Holdings Ltd\s+HK\$([\d,.]+)",
        ],
    )
    market_cap = _first_abbrev_match(normalized, [r"Mkt\.?\s*cap\s+([\d,.]+)\s*([TMB])"])
    shares_outstanding = _first_abbrev_match(
        normalized,
        [r"Shares outstanding\s+([\d,.]+)\s*([TMB])"],
    )
    timestamp = _first_text_match(
        normalized,
        [
            r"1D\s+([A-Z][a-z]{2}\s+\d{1,2},\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M\s+GMT[-+]\d+)\s*·\s*HKD",
            r"([A-Z][a-z]{2}\s+\d{1,2},\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M\s+GMT[-+]\d+)\s*·\s*HKD",
        ],
    )
    return {
        "price": price,
        "currency": "HKD" if price is not None else None,
        "market_cap": market_cap,
        "shares_outstanding": shares_outstanding,
        "as_of_date": timestamp,
    }


def fetch_google_hkd_cny(*, cache_dir: Path) -> dict[str, Any]:
    data = fetch_bytes(GOOGLE_HKD_CNY_URL, headers=GOOGLE_HEADERS, timeout=20)
    path = write_bytes(cache_dir / "google_hkd_cny.html", data)
    text = html_to_text(data.decode("utf-8", errors="replace"))
    quote = parse_google_hkd_cny_text(text)
    quote.update(
        {
            "status": "fetched" if quote.get("rate") is not None else "parse_failed",
            "source": "Google Finance HKD/CNY",
            "url": GOOGLE_HKD_CNY_URL,
            "local_path": str(path),
            "fetched_at": utc_now_iso(),
        }
    )
    return quote


def parse_google_hkd_cny_text(text: str) -> dict[str, Any]:
    normalized = normalize_text(text)
    rate = _first_float_match(
        normalized,
        [
            r"Hong Kong Dollar\s*/\s*Chinese Yuan\s+([\d,.]+)",
            r"HKD\s*/\s*CNY\s+.*?Hong Kong Dollar\s*/\s*Chinese Yuan\s+([\d,.]+)",
        ],
    )
    timestamp = _first_text_match(
        normalized,
        [r"1D\s+([A-Z][a-z]{2}\s+\d{1,2},\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M\s+UTC)"],
    )
    return {"rate": rate, "currency_pair": "HKD/CNY", "as_of_date": timestamp}


def fetch_yahoo_pdd_quote(*, cache_dir: Path) -> dict[str, Any]:
    try:
        data = fetch_json(YAHOO_PDD_CHART_URL, headers=GOOGLE_HEADERS, timeout=20)
    except FetchError as exc:
        return {
            "status": "fetch_failed",
            "source": "Yahoo Finance chart endpoint",
            "url": YAHOO_PDD_CHART_URL,
            "error": str(exc),
            "fetched_at": utc_now_iso(),
        }
    path = write_json(cache_dir / "yahoo_pdd_chart.json", data)
    quote = parse_yahoo_chart_quote(data)
    quote.update(
        {
            "status": "fetched" if quote.get("price") is not None else "parse_failed",
            "source": "Yahoo Finance chart endpoint",
            "url": YAHOO_PDD_CHART_URL,
            "local_path": str(path),
            "fetched_at": utc_now_iso(),
        }
    )
    return quote


def fetch_yahoo_tencent_quote(*, cache_dir: Path) -> dict[str, Any]:
    try:
        data = fetch_json(YAHOO_TENCENT_CHART_URL, headers=GOOGLE_HEADERS, timeout=20)
    except FetchError as exc:
        return {
            "status": "fetch_failed",
            "source": "Yahoo Finance chart endpoint",
            "url": YAHOO_TENCENT_CHART_URL,
            "error": str(exc),
            "fetched_at": utc_now_iso(),
        }
    path = write_json(cache_dir / "yahoo_tencent_chart.json", data)
    quote = parse_yahoo_chart_quote(data)
    quote.update(
        {
            "status": "fetched" if quote.get("price") is not None else "parse_failed",
            "source": "Yahoo Finance chart endpoint",
            "url": YAHOO_TENCENT_CHART_URL,
            "local_path": str(path),
            "fetched_at": utc_now_iso(),
        }
    )
    return quote


def parse_yahoo_chart_quote(data: dict[str, Any]) -> dict[str, Any]:
    result = ((data.get("chart") or {}).get("result") or [{}])[0]
    meta = result.get("meta") or {}
    return {
        "price": _to_float(meta.get("regularMarketPrice")),
        "currency": meta.get("currency"),
        "exchange": meta.get("exchangeName"),
        "regular_market_time": meta.get("regularMarketTime"),
    }


def validate_tencent_market_inputs(
    *,
    share_structure: dict[str, Any],
    google_quote: dict[str, Any],
    google_fx: dict[str, Any],
    yahoo_quote: dict[str, Any],
) -> dict[str, Any]:
    missing = []
    conflicts = []
    warnings = []
    if share_structure.get("status") != "extracted":
        missing.extend(share_structure.get("missing", ["official Tencent issued shares"]))
    if google_quote.get("price") is None:
        missing.append("Google Finance 0700:HKG price")
    if google_fx.get("rate") is None:
        missing.append("Google Finance HKD/CNY")

    if not missing:
        calculated_market_cap = google_quote["price"] * share_structure["ordinary_shares_outstanding"]
        google_market_cap = google_quote.get("market_cap")
        if google_market_cap:
            mismatch = _mismatch_pct(calculated_market_cap, google_market_cap)
            if mismatch > MARKET_CAP_MISMATCH_REVIEW_THRESHOLD:
                conflicts.append(
                    {
                        "type": "market_cap_cross_check",
                        "source": "Google Finance market cap",
                        "calculated_market_cap": calculated_market_cap,
                        "source_market_cap": google_market_cap,
                        "mismatch_pct": mismatch,
                        "threshold": MARKET_CAP_MISMATCH_REVIEW_THRESHOLD,
                    }
                )
        else:
            warnings.append("Google Finance market cap was unavailable for cross-check.")

        google_shares = google_quote.get("shares_outstanding")
        if google_shares:
            shares_mismatch = _mismatch_pct(share_structure["ordinary_shares_outstanding"], google_shares)
            if shares_mismatch > MARKET_CAP_MISMATCH_REVIEW_THRESHOLD:
                warnings.append(
                    "Google Finance shares outstanding differs from official Tencent issued shares; "
                    "official annual-report share count is used."
                )

        yahoo_price = yahoo_quote.get("price")
        if yahoo_price:
            price_mismatch = _mismatch_pct(google_quote["price"], yahoo_price)
            if price_mismatch > PRICE_MISMATCH_REVIEW_THRESHOLD:
                conflicts.append(
                    {
                        "type": "price_cross_check",
                        "source": "Yahoo Finance",
                        "google_price": google_quote["price"],
                        "yahoo_price": yahoo_price,
                        "mismatch_pct": price_mismatch,
                        "threshold": PRICE_MISMATCH_REVIEW_THRESHOLD,
                    }
                )
        else:
            warnings.append("Yahoo Finance price was unavailable; Google market cap cross-check was used instead.")

    return {
        "missing": sorted(set(missing)),
        "conflicts": conflicts,
        "warnings": warnings,
        "thresholds": {
            "price_mismatch_review_threshold": PRICE_MISMATCH_REVIEW_THRESHOLD,
            "market_cap_mismatch_review_threshold": MARKET_CAP_MISMATCH_REVIEW_THRESHOLD,
        },
    }


def validate_market_inputs(
    *,
    share_structure: dict[str, Any],
    google_quote: dict[str, Any],
    google_fx: dict[str, Any],
    yahoo_quote: dict[str, Any],
) -> dict[str, Any]:
    missing = []
    conflicts = []
    warnings = []
    if share_structure.get("status") != "extracted":
        missing.extend(share_structure.get("missing", ["official share structure"]))
    if google_quote.get("price") is None:
        missing.append("Google Finance PDD price")
    if google_fx.get("rate") is None:
        missing.append("Google Finance USD/CNY")

    if not missing:
        ads_outstanding = share_structure["ordinary_shares_outstanding"] / share_structure["ordinary_shares_per_ads"]
        calculated_market_cap = google_quote["price"] * ads_outstanding
        google_market_cap = google_quote.get("market_cap")
        if google_market_cap:
            mismatch = _mismatch_pct(calculated_market_cap, google_market_cap)
            if mismatch > MARKET_CAP_MISMATCH_REVIEW_THRESHOLD:
                conflicts.append(
                    {
                        "type": "market_cap_cross_check",
                        "source": "Google Finance market cap",
                        "calculated_market_cap": calculated_market_cap,
                        "source_market_cap": google_market_cap,
                        "mismatch_pct": mismatch,
                        "threshold": MARKET_CAP_MISMATCH_REVIEW_THRESHOLD,
                    }
                )
        else:
            warnings.append("Google Finance market cap was unavailable for cross-check.")

        yahoo_price = yahoo_quote.get("price")
        if yahoo_price:
            price_mismatch = _mismatch_pct(google_quote["price"], yahoo_price)
            if price_mismatch > PRICE_MISMATCH_REVIEW_THRESHOLD:
                conflicts.append(
                    {
                        "type": "price_cross_check",
                        "source": "Yahoo Finance",
                        "google_price": google_quote["price"],
                        "yahoo_price": yahoo_price,
                        "mismatch_pct": price_mismatch,
                        "threshold": PRICE_MISMATCH_REVIEW_THRESHOLD,
                    }
                )
        else:
            warnings.append("Yahoo Finance price was unavailable; Google market cap cross-check was used instead.")

    return {
        "missing": sorted(set(missing)),
        "conflicts": conflicts,
        "warnings": warnings,
        "thresholds": {
            "price_mismatch_review_threshold": PRICE_MISMATCH_REVIEW_THRESHOLD,
            "market_cap_mismatch_review_threshold": MARKET_CAP_MISMATCH_REVIEW_THRESHOLD,
        },
    }


def html_to_text(raw_html: str) -> str:
    parser = TextParser()
    parser.feed(html.unescape(raw_html))
    return parser.text()


def normalize_text(text: str) -> str:
    return " ".join(html.unescape(text).replace("\xa0", " ").split())


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _latest_20f_document(documents: list[dict[str, Any]]) -> dict[str, Any] | None:
    annuals = [
        document
        for document in documents
        if str(document.get("document_type", "")).startswith("20-F")
        and document.get("local_path")
    ]
    if not annuals:
        return None
    return sorted(annuals, key=lambda document: document.get("filing_date") or "")[-1]


def _latest_tencent_annual_document(documents: list[dict[str, Any]]) -> dict[str, Any] | None:
    annuals = [
        document
        for document in documents
        if document.get("source_id") == "tencent_investor_relations"
        and document.get("report_kind") == "annual"
        and document.get("local_path")
    ]
    if not annuals:
        return None
    return sorted(
        annuals,
        key=lambda document: (
            int(document.get("fiscal_year") or 0),
            document.get("filing_date") or "",
        ),
    )[-1]


def _extract_ads_ratio(text: str) -> int | None:
    match = re.search(
        r"ADSs?[^.]{0,120}?each[^.]{0,120}?represents?\s+(four|[\d,]+)\s+Class A ordinary shares",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return _number_word_to_int(match.group(1))


def _extract_ordinary_shares_outstanding(text: str) -> dict[str, Any] | None:
    match = re.search(
        r"based on\s+([\d,]+)\s+Class A ordinary shares\s+and\s+no\s+Class B ordinary Shares outstanding\s+as of\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return {
        "ordinary_shares_outstanding": int(match.group(1).replace(",", "")),
        "as_of_date": match.group(2),
        "evidence": match.group(0),
    }


def _number_word_to_int(value: str) -> int | None:
    words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }
    normalized = value.lower().replace(",", "")
    if normalized.isdigit():
        return int(normalized)
    return words.get(normalized)


def _first_float_match(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _to_float(match.group(1))
    return None


def _first_text_match(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _first_abbrev_match(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = _to_float(match.group(1))
            suffix = match.group(2).upper()
            if value is None:
                return None
            return value * {"T": 1_000_000_000_000, "B": 1_000_000_000, "M": 1_000_000}[suffix]
    return None


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _mismatch_pct(left: float, right: float) -> float:
    denominator = max(abs(left), abs(right))
    if denominator == 0:
        return 0.0
    return abs(left - right) / denominator


def _offline_mode() -> bool:
    import os

    return os.environ.get("STOCK_RESEARCH_OFFLINE") == "1"
