from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_MARKET_INPUTS = Path("config/market_data/manual_inputs.json")
REVIEWED_STATUSES = {"approved", "reviewed"}
BLOCKING_STATUSES = {
    "config_missing",
    "company_inputs_missing",
    "input_incomplete",
    "source_conflict",
    "review_required",
}


def load_manual_market_inputs(
    company_id: str | None,
    *,
    path: str | Path = DEFAULT_MARKET_INPUTS,
) -> dict[str, Any]:
    """Load user-reviewed market inputs without fetching live prices."""
    input_path = Path(path)
    if not input_path.exists():
        return {
            "status": "config_missing",
            "company_id": company_id,
            "path": str(input_path),
            "input_required": True,
            "review_required": False,
            "missing": ["manual valuation input config"],
        }

    registry = json.loads(input_path.read_text(encoding="utf-8"))
    normalized_company_id = (company_id or "").lower()
    company_inputs = registry.get("companies", {}).get(normalized_company_id)
    if company_inputs is None:
        return {
            "status": "company_inputs_missing",
            "company_id": normalized_company_id or company_id,
            "path": str(input_path),
            "input_required": True,
            "review_required": False,
            "missing": ["company market inputs"],
        }

    missing = _missing_required_fields(company_inputs)
    review_status = str(company_inputs.get("review_status") or "missing").lower()
    status = "input_available" if not missing else "input_incomplete"
    if review_status not in REVIEWED_STATUSES:
        status = "review_required" if not missing else status

    return {
        "status": status,
        "company_id": normalized_company_id,
        "path": str(input_path),
        "inputs": company_inputs,
        "missing": missing,
        "review_status": review_status,
        "input_required": bool(missing),
        "review_required": bool(not missing and review_status not in REVIEWED_STATUSES),
        "notes": registry.get("notes"),
    }


def market_cap_in_cny(market_inputs: dict[str, Any]) -> dict[str, Any]:
    inputs = market_inputs.get("inputs") or {}
    status = market_inputs.get("status")
    if status in BLOCKING_STATUSES:
        return {
            "status": status,
            "missing": market_inputs.get("missing", []),
            "conflicts": (market_inputs.get("validation") or {}).get("conflicts", []),
        }
    if market_inputs.get("missing"):
        return {
            "status": "missing_required_inputs",
            "missing": market_inputs.get("missing", []),
        }

    market_cap = _to_float(inputs.get("market_cap"))
    currency = str(inputs.get("currency") or "").upper()
    if market_cap is None:
        return {"status": "missing_required_inputs", "missing": ["market_cap"]}
    if currency == "CNY":
        fx_rate = 1.0
        fx_field = "identity"
    elif currency == "USD":
        fx_rate = _to_float(inputs.get("usd_cny_fx"))
        fx_field = "usd_cny_fx"
    elif currency == "HKD":
        fx_rate = _to_float(inputs.get("hkd_cny_fx"))
        fx_field = "hkd_cny_fx"
    else:
        return {"status": "unsupported_currency", "currency": currency or "missing"}

    if fx_rate is None:
        return {"status": "missing_required_inputs", "missing": [fx_field]}

    return {
        "status": "calculated",
        "value": market_cap * fx_rate,
        "unit": "CNY",
        "market_cap": market_cap,
        "currency": currency,
        "fx_rate": fx_rate,
        "fx_field": fx_field,
        "as_of_date": inputs.get("as_of_date"),
        "source": inputs.get("source"),
        "review_status": market_inputs.get("review_status"),
        "review_required": market_inputs.get("review_required", True),
    }


def _missing_required_fields(inputs: dict[str, Any]) -> list[str]:
    currency = str(inputs.get("currency") or "").upper()
    required = ["as_of_date", "source", "market_cap", "currency"]
    if currency == "USD":
        required.append("usd_cny_fx")
    elif currency == "HKD":
        required.append("hkd_cny_fx")
    return [field for field in required if inputs.get(field) in {None, ""}]


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
