from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_COMPANY_REGISTRY = Path("config/company_registry.json")


def load_company_registry(path: str | Path = DEFAULT_COMPANY_REGISTRY) -> dict[str, Any]:
    registry_path = Path(path)
    if not registry_path.exists():
        return {"schema_version": 1, "companies": []}
    return json.loads(registry_path.read_text(encoding="utf-8"))


def resolve_company_from_registry(
    query: str,
    *,
    market: str | None = None,
    registry_path: str | Path = DEFAULT_COMPANY_REGISTRY,
) -> dict[str, Any] | None:
    normalized_query = _normalize(query)
    normalized_market = _normalize(market or "")
    registry = load_company_registry(registry_path)
    for company in registry.get("companies", []):
        names = [
            company.get("company_id"),
            company.get("legal_name"),
            *company.get("common_names", []),
            *company.get("aliases", []),
            *(ticker.get("symbol") for ticker in company.get("tickers", [])),
        ]
        if normalized_query not in {_normalize(str(name)) for name in names if name}:
            continue
        if normalized_market and _normalize(str(company.get("market", ""))) != normalized_market:
            ticker_markets = {
                _normalize(str(ticker.get("market", ""))) for ticker in company.get("tickers", [])
            }
            if normalized_market not in ticker_markets:
                continue
        return dict(company)
    return None


def _normalize(value: str) -> str:
    return value.strip().casefold().replace(" ", "").replace("-", "").replace("_", "")
