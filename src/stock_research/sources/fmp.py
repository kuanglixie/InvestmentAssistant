from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


FMP_BASE_URL = "https://financialmodelingprep.com"
FMP_API_KEY_ENV = "FMP_API_KEY"
FMP_DASHBOARD_URL = "https://site.financialmodelingprep.com/developer/docs/quickstart"


class FmpApiError(RuntimeError):
    pass


def get_fmp_api_key() -> str | None:
    key = os.environ.get(FMP_API_KEY_ENV)
    return key.strip() if key and key.strip() else None


def run_fmp_smoke_test(
    *,
    symbol: str,
    api_key: str | None = None,
    output_dir: str | Path = "data/fmp_smoke",
    limit: int = 5,
    timeout: int = 30,
) -> dict[str, Any]:
    key = api_key or get_fmp_api_key()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if not key:
        return {
            "status": "missing_api_key",
            "symbol": symbol.upper(),
            "required_env": FMP_API_KEY_ENV,
            "api_key_link": FMP_DASHBOARD_URL,
            "message": "Set FMP_API_KEY in .env or environment before calling Financial Modeling Prep.",
            "endpoints": _endpoint_catalog(symbol=symbol, limit=limit),
        }

    endpoint_results: dict[str, Any] = {}
    for name, path, params in _endpoint_specs(symbol=symbol, limit=limit):
        endpoint_results[name] = _request_fmp_json(
            path=path,
            params={**params, "apikey": key},
            timeout=timeout,
        )

    result = {
        "status": _overall_status(endpoint_results),
        "symbol": symbol.upper(),
        "source": "financial_modeling_prep",
        "source_tier": "third_party_financial_data",
        "api_key_env": FMP_API_KEY_ENV,
        "endpoints": endpoint_results,
        "field_preview": _field_preview(endpoint_results),
        "recommended_use": (
            "Use FMP as a validation/fallback source. Do not silently replace official SEC/20-F facts "
            "when FMP and official extraction disagree."
        ),
    }
    output_path = output / f"{symbol.lower()}_fmp_smoke.json"
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    result["output_path"] = str(output_path)
    return result


def _endpoint_catalog(*, symbol: str, limit: int) -> list[dict[str, Any]]:
    return [
        {"name": name, "url": _url(path, {**params, "apikey": "YOUR_API_KEY"})}
        for name, path, params in _endpoint_specs(symbol=symbol, limit=limit)
    ]


def _endpoint_specs(symbol: str, limit: int) -> list[tuple[str, str, dict[str, str]]]:
    symbol = symbol.upper()
    limit_text = str(limit)
    return [
        (
            "search_symbol",
            "/stable/search-symbol",
            {"query": symbol, "limit": "10"},
        ),
        (
            "company_profile",
            "/stable/profile",
            {"symbol": symbol},
        ),
        (
            "quote",
            "/stable/quote",
            {"symbol": symbol},
        ),
        (
            "income_statement_annual",
            "/stable/income-statement",
            {"symbol": symbol, "period": "annual", "limit": limit_text},
        ),
        (
            "balance_sheet_annual",
            "/stable/balance-sheet-statement",
            {"symbol": symbol, "period": "annual", "limit": limit_text},
        ),
        (
            "cash_flow_annual",
            "/stable/cash-flow-statement",
            {"symbol": symbol, "period": "annual", "limit": limit_text},
        ),
        (
            "income_statement_quarter",
            "/stable/income-statement",
            {"symbol": symbol, "period": "quarter", "limit": limit_text},
        ),
        (
            "balance_sheet_quarter",
            "/stable/balance-sheet-statement",
            {"symbol": symbol, "period": "quarter", "limit": limit_text},
        ),
        (
            "cash_flow_quarter",
            "/stable/cash-flow-statement",
            {"symbol": symbol, "period": "quarter", "limit": limit_text},
        ),
        (
            "as_reported_full",
            "/stable/financial-statement-full-as-reported",
            {"symbol": symbol, "period": "annual"},
        ),
    ]


def _request_fmp_json(*, path: str, params: dict[str, str], timeout: int) -> dict[str, Any]:
    url = _url(path, params)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "stock-research-fmp/0.1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            payload = json.loads(raw) if raw.strip() else None
            return {
                "status": "ok",
                "http_status": response.status,
                "url": _redact_apikey(url),
                "row_count": len(payload) if isinstance(payload, list) else None,
                "payload_preview": _payload_preview(payload),
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(1000).decode("utf-8", errors="replace")
        return {
            "status": "http_error",
            "http_status": exc.code,
            "url": _redact_apikey(url),
            "error_body": body,
        }
    except urllib.error.URLError as exc:
        return {
            "status": "network_error",
            "url": _redact_apikey(url),
            "error": str(exc),
        }
    except json.JSONDecodeError as exc:
        return {
            "status": "json_decode_error",
            "url": _redact_apikey(url),
            "error": str(exc),
        }


def _url(path: str, params: dict[str, str]) -> str:
    return f"{FMP_BASE_URL}{path}?{urllib.parse.urlencode(params)}"


def _redact_apikey(url: str) -> str:
    return re_sub_apikey(url)


def re_sub_apikey(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    redacted = [(key, "REDACTED" if key.lower() == "apikey" else value) for key, value in query]
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(redacted), parsed.fragment)
    )


def _payload_preview(payload: Any) -> Any:
    if isinstance(payload, list):
        return payload[:2]
    if isinstance(payload, dict):
        return payload
    return payload


def _field_preview(endpoint_results: dict[str, Any]) -> dict[str, list[str]]:
    preview: dict[str, list[str]] = {}
    for name, result in endpoint_results.items():
        payload = result.get("payload_preview")
        first = payload[0] if isinstance(payload, list) and payload else payload
        if isinstance(first, dict):
            preview[name] = sorted(first.keys())[:80]
    return preview


def _overall_status(endpoint_results: dict[str, Any]) -> str:
    if any(result.get("status") == "ok" for result in endpoint_results.values()):
        if all(result.get("status") == "ok" for result in endpoint_results.values()):
            return "ok"
        return "partial"
    return "failed"
