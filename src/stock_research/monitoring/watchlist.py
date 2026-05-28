from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from stock_research.companies import resolve_company_from_registry


def run_watchlist_monitor(
    *,
    watchlist_path: str | Path = "config/watchlist.json",
    cache_root: str | Path = "data/raw",
    output_dir: str | Path = "data/monitoring",
) -> dict[str, Any]:
    watchlist = _read_json(Path(watchlist_path), default={"companies": [], "triggers": []})
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    previous_snapshot_path = output / "watchlist_latest_snapshot.json"
    previous_snapshot = _read_json(previous_snapshot_path, default={"companies": {}})

    results = []
    next_snapshot: dict[str, Any] = {
        "created_at": _timestamp_iso(),
        "companies": {},
    }
    for item in watchlist.get("companies", []):
        company = _resolve_watchlist_company(item)
        company_id = company.get("company_id") or item.get("company_id") or item.get("ticker")
        latest_filing = _latest_cached_sec_filing(company, cache_root=Path(cache_root))
        previous_company = previous_snapshot.get("companies", {}).get(company_id, {})
        new_filing_check = _new_filing_status(
            latest_filing=latest_filing,
            previous_accession=previous_company.get("latest_filing_accession_number"),
            trigger_enabled="new_filing" in watchlist.get("triggers", []),
        )
        management_change_check = {
            "trigger": "management_change",
            "status": "not_implemented_yet",
            "note": "Skeleton recorded. Future version will scan official filings, IR leadership pages, and approved leadership sources.",
        }
        result = {
            "company_id": company_id,
            "company": company.get("legal_name") or item.get("company"),
            "ticker": item.get("ticker"),
            "market": item.get("market"),
            "role": item.get("role"),
            "source_pipeline_status": company.get("source_pipeline_status", "unconfigured"),
            "latest_cached_filing": latest_filing,
            "new_filing_check": new_filing_check,
            "management_change_check": management_change_check,
        }
        results.append(result)
        next_snapshot["companies"][company_id] = {
            "company": result["company"],
            "ticker": result["ticker"],
            "latest_filing_accession_number": latest_filing.get("accession_number")
            if latest_filing
            else None,
            "latest_filing_date": latest_filing.get("filing_date") if latest_filing else None,
            "latest_filing_form": latest_filing.get("form") if latest_filing else None,
        }

    report_path = output / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-watchlist.md"
    report_path.write_text(
        _build_monitor_report(watchlist=watchlist, results=results),
        encoding="utf-8",
    )
    previous_snapshot_path.write_text(
        json.dumps(next_snapshot, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "report_path": str(report_path),
        "snapshot_path": str(previous_snapshot_path),
        "companies_checked": len(results),
        "active_triggers": [
            result
            for result in results
            if result.get("new_filing_check", {}).get("status") == "triggered"
        ],
    }


def _resolve_watchlist_company(item: dict[str, Any]) -> dict[str, Any]:
    query = item.get("registry_company_id") or item.get("company") or item.get("ticker")
    company = resolve_company_from_registry(str(query), market=item.get("market"))
    if company:
        return company
    return {
        "company_id": item.get("company_id") or str(query).lower(),
        "legal_name": item.get("company") or item.get("ticker"),
        "source_pipeline_status": "unconfigured",
    }


def _latest_cached_sec_filing(company: dict[str, Any], *, cache_root: Path) -> dict[str, Any] | None:
    cik_padded = company.get("sec_cik_padded")
    if not cik_padded:
        return None
    filing_index_path = cache_root / "sec" / str(cik_padded) / "filing_index.json"
    if not filing_index_path.exists():
        return None
    filings = json.loads(filing_index_path.read_text(encoding="utf-8"))
    if not filings:
        return None
    latest = sorted(filings, key=lambda filing: filing.get("filing_date") or "", reverse=True)[0]
    return {
        "accession_number": latest.get("accession_number"),
        "form": latest.get("form"),
        "filing_date": latest.get("filing_date"),
        "report_date": latest.get("report_date"),
        "primary_document": latest.get("primary_document"),
        "archive_url": latest.get("archive_url"),
    }


def _new_filing_status(
    *,
    latest_filing: dict[str, Any] | None,
    previous_accession: str | None,
    trigger_enabled: bool,
) -> dict[str, Any]:
    if not trigger_enabled:
        return {"trigger": "new_filing", "status": "disabled"}
    if not latest_filing:
        return {
            "trigger": "new_filing",
            "status": "no_cached_filing_index",
            "note": "No network fetch was attempted by the monitor skeleton.",
        }
    accession = latest_filing.get("accession_number")
    if previous_accession and accession != previous_accession:
        return {
            "trigger": "new_filing",
            "status": "triggered",
            "previous_accession_number": previous_accession,
            "latest_accession_number": accession,
        }
    if not previous_accession:
        return {
            "trigger": "new_filing",
            "status": "baseline_created",
            "latest_accession_number": accession,
        }
    return {
        "trigger": "new_filing",
        "status": "no_change",
        "latest_accession_number": accession,
    }


def _build_monitor_report(*, watchlist: dict[str, Any], results: list[dict[str, Any]]) -> str:
    lines = [
        "# Watchlist Monitor",
        "",
        f"- Generated at: {_timestamp_iso()}",
        f"- Cadence: {watchlist.get('cadence', 'weekly')}",
        "- Triggers: " + ", ".join(watchlist.get("triggers", [])),
        "- Note: this skeleton uses cached source metadata only; it does not ask for network permissions.",
        "",
        "| Company | Ticker | Latest Cached Filing | New Filing | Management Change | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        latest = result.get("latest_cached_filing") or {}
        filing_text = "none"
        if latest:
            filing_text = (
                f"{latest.get('filing_date')} {latest.get('form')} "
                f"{latest.get('accession_number')}"
            )
        lines.append(
            "| {company} | {ticker} | {filing} | {new_filing} | {management} | {notes} |".format(
                company=result.get("company"),
                ticker=result.get("ticker"),
                filing=filing_text,
                new_filing=result.get("new_filing_check", {}).get("status"),
                management=result.get("management_change_check", {}).get("status"),
                notes=result.get("source_pipeline_status"),
            )
        )
    lines.extend(
        [
            "",
            "## Human Review Rules",
            "",
            "- New-filing triggers should route the company back through source discovery and extraction.",
            "- Management-change triggers should route to the Leadership / People Agent once the source collector is implemented.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _read_json(path: Path, *, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _timestamp_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
