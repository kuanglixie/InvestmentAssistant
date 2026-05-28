from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from stock_research.env import load_dotenv
from stock_research.qualitative.business_model_video_questions import (
    business_model_question_pack_summary,
    business_model_question_results_from_segments,
    question_results_without_transcript,
)
from stock_research.sources.http import FetchError, fetch_json, write_json
from stock_research.state import utc_now_iso


DEFAULT_PDD_OFFICIAL_EVENT_REGISTRY = Path("config/qualitative/pdd_official_event_sources.v1.json")
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
OFFICIAL_EVENT_USER_AGENT = "stock-research-system/0.1 earnings-call-transcript-research"

ALPHA_VANTAGE_KEY_NAMES = ("ALPHA_VANTAGE_API_KEY", "ALPHAVANTAGE_API_KEY")

OFFICIAL_EVENT_TERM_GROUPS = {
    "long_term_investment": [
        "long-term",
        "long term",
        "investment",
        "investing",
        "sustainable",
        "high-quality development",
        "intrinsic value",
    ],
    "customer_value": [
        "consumer",
        "customer",
        "buyer",
        "value-for-money",
        "value for money",
        "quality",
        "trust",
        "shopping experience",
    ],
    "merchant_support": [
        "merchant",
        "seller",
        "fee reduction",
        "support program",
        "supply chain",
        "ecosystem",
        "industrial belt",
        "logistics",
    ],
    "competition_and_pressure": [
        "competition",
        "competitive",
        "margin",
        "profitability",
        "pressure",
        "uncertainty",
        "slowdown",
    ],
    "temu_global": [
        "Temu",
        "global",
        "cross-border",
        "international",
        "overseas",
        "trade",
        "tariff",
        "regulatory",
    ],
    "organization_and_people": [
        "organization",
        "governance",
        "leadership",
        "culture",
        "talent",
        "co-chair",
        "co-chief executive",
    ],
}


def collect_official_event_transcripts(
    *,
    company: dict[str, Any],
    cache_root: str | Path = "data/raw/official_event_transcripts",
    offline: bool | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """Collect earnings-call transcript evidence using the productionized prototype.

    The previous V1 collector mixed official webcast probing, YouTube captions,
    and Gemini video-understanding. This production path intentionally adopts
    the separate prototype design: provider-chain transcript records first,
    source-candidate links second, and no invented transcript text.
    """

    company_id = str(company.get("company_id") or "").lower()
    if company_id != "pdd":
        return {
            "status": "not_configured_for_company_v1",
            "company_id": company_id or "unknown",
            "source_results": [],
            "evidence_items": [],
            "audit_notes": ["Official event transcript collection is currently configured for PDD only."],
        }

    if offline is None:
        offline = os.environ.get("STOCK_RESEARCH_OFFLINE") == "1"

    registry = _load_registry(registry_path or DEFAULT_PDD_OFFICIAL_EVENT_REGISTRY)
    cache_dir = Path(cache_root) / company_id
    source_results: list[dict[str, Any]] = []
    evidence_items: list[dict[str, Any]] = []

    for source in registry.get("sources", []):
        adapter = str(source.get("adapter") or "")
        if adapter == "alpha_vantage_backfill":
            collected = _collect_alpha_vantage_backfill_source(source, cache_dir=cache_dir, offline=offline)
        elif adapter == "local_transcript_file":
            collected = [_collect_local_transcript_file_source(source, cache_dir=cache_dir, offline=offline)]
        elif adapter == "source_candidates":
            collected = [_collect_source_candidate_source(source, cache_dir=cache_dir, offline=offline)]
        else:
            collected = [_manual_source_result(source, offline=offline)]
        source_results.extend(collected)
        for result in collected:
            evidence_items.extend(result.get("evidence_items", []))

    status_counts = Counter(str(result.get("status") or "unknown") for result in source_results)
    adapter_counts = Counter(str(source.get("adapter") or "unknown") for source in registry.get("sources", []))
    result_adapter_counts = Counter(str(result.get("adapter") or "unknown") for result in source_results)
    transcript_results = [
        result
        for result in source_results
        if int(result.get("transcript_record_count") or 0) > 0
        or int(result.get("transcript_segment_count") or 0) > 0
    ]
    source_candidate_count = sum(int(result.get("source_candidate_count") or 0) for result in source_results)
    errors = [error for result in source_results for error in result.get("errors", [])]

    if transcript_results:
        status = "earnings_call_transcripts_collected"
    elif source_candidate_count:
        status = "earnings_call_source_candidates_recorded"
    elif offline:
        status = "offline_provider_chain_ready"
    elif status_counts.get("alpha_vantage_key_missing"):
        status = "provider_chain_ready_alpha_vantage_key_missing"
    else:
        status = "provider_chain_ready_no_transcripts_collected"

    return {
        "status": status,
        "company_id": company_id,
        "registry_path": str(registry_path or DEFAULT_PDD_OFFICIAL_EVENT_REGISTRY),
        "generated_at": utc_now_iso(),
        "offline": offline,
        "source_count": len(registry.get("sources", [])),
        "source_result_count": len(source_results),
        "source_adapter_counts": dict(sorted(adapter_counts.items())),
        "source_result_adapter_counts": dict(sorted(result_adapter_counts.items())),
        "source_status_counts": dict(sorted(status_counts.items())),
        "provider_chain": registry.get("provider_chain", []),
        "alpha_vantage_source_count": adapter_counts.get("alpha_vantage_backfill", 0),
        "local_transcript_source_count": adapter_counts.get("local_transcript_file", 0),
        "source_candidate_registry_count": adapter_counts.get("source_candidates", 0),
        "source_candidate_count": source_candidate_count,
        "transcript_source_count": len(transcript_results),
        "transcript_record_count": sum(int(result.get("transcript_record_count") or 0) for result in source_results),
        "call_transcript_count": sum(int(result.get("transcript_record_count") or 0) for result in source_results),
        "transcript_segment_count": sum(int(result.get("transcript_segment_count") or 0) for result in source_results),
        "evidence_item_count": len(evidence_items),
        "business_model_question_pack": business_model_question_pack_summary(source_results),
        "source_results": source_results,
        "evidence_items": evidence_items,
        "video_manifest": _empty_video_manifest(company_id),
        "theme_summary": _theme_summary(evidence_items),
        "audit_policy": registry.get("audit_policy", {}),
        "prototype_adopted_from": registry.get("prototype_adopted_from"),
        "audit_notes": [
            "This agent now follows the productionized earnings-call-transcripts prototype provider chain.",
            "Alpha Vantage transcript records are third-party API evidence, not official filings; use them for management commentary and Q&A, not as source of record for financial numbers.",
            "Cached transcript records are reused before any live Alpha Vantage request to avoid wasting quota.",
            "Third-party transcript web pages are stored as link-only candidates unless storage rights are confirmed.",
            "Local transcript ingestion requires source/rights metadata and preserves provider, source type, confidence, and storage policy.",
        ],
        "errors": errors,
    }


def _collect_alpha_vantage_backfill_source(
    source: dict[str, Any],
    *,
    cache_dir: Path,
    offline: bool,
) -> list[dict[str, Any]]:
    source_dir = cache_dir / _slug(str(source.get("source_id") or "alpha_vantage_backfill"))
    symbol = str(source.get("symbol") or "PDD").upper()
    requested_quarters = _quarter_range(
        str(source.get("start_quarter") or "2020Q1"),
        str(source.get("end_quarter") or source.get("start_quarter") or "2020Q1"),
    )
    if source.get("newest_first", True):
        requested_quarters = list(reversed(requested_quarters))

    cached_records = _load_cached_transcript_records(source=source, cache_dir=cache_dir, symbol=symbol)
    cached_by_quarter = {
        str(item["record"].get("quarter") or "").upper(): item
        for item in cached_records
        if str(item["record"].get("quarter") or "").upper()
    }
    missing_quarters = [quarter for quarter in requested_quarters if quarter not in cached_by_quarter]
    fetched_records: list[dict[str, Any]] = []
    fetch_errors: list[dict[str, Any]] = []

    api_key = _alpha_vantage_api_key()
    if missing_quarters and not offline and api_key:
        max_requests = int(source.get("max_requests_per_run") or 0)
        quarters_to_fetch = missing_quarters[:max_requests] if max_requests > 0 else missing_quarters
        for position, quarter in enumerate(quarters_to_fetch, start=1):
            try:
                payload = _fetch_alpha_vantage(symbol, quarter, api_key, timeout=int(source.get("timeout", 30)))
                miss_reason = _alpha_vantage_miss(payload)
                if miss_reason:
                    fetch_errors.append({"quarter": quarter, "status": "missing", "reason": miss_reason})
                    if source.get("stop_on_rate_limit", True) and _looks_like_rate_limit(miss_reason):
                        break
                    continue
                record = _normalize_alpha_vantage_record(symbol=symbol, quarter=quarter, payload=payload)
                record_dir = _record_dir(cache_dir / "alpha_vantage", record)
                _write_transcript_record(record_dir, record)
                fetched_records.append({"record": record, "record_path": record_dir / "record.json"})
            except Exception as exc:
                fetch_errors.append({"quarter": quarter, "status": "error", "reason": _sanitize_secret_text(str(exc))})
                if source.get("stop_on_rate_limit", True) and _looks_like_rate_limit(str(exc)):
                    break
            if position < len(quarters_to_fetch):
                time.sleep(max(0.0, float(source.get("sleep_seconds") or 0.0)))

    record_items = [*cached_records, *fetched_records]
    record_items = _dedupe_record_items(record_items)
    record_items.sort(key=lambda item: str(item["record"].get("quarter") or ""))
    results = [
        _result_from_transcript_record(source=source, record_item=item, cache_dir=cache_dir)
        for item in record_items
    ]

    collected_quarters = {str(item["record"].get("quarter") or "").upper() for item in record_items}
    still_missing = [quarter for quarter in requested_quarters if quarter not in collected_quarters]
    if still_missing or fetch_errors or not results:
        summary = _base_result(source, offline=offline)
        summary.update(
            {
                "status": _alpha_summary_status(
                    has_records=bool(results),
                    offline=offline,
                    api_key_present=bool(api_key),
                    missing_quarters=still_missing,
                    fetch_errors=fetch_errors,
                ),
                "name": source.get("name") or "PDD Alpha Vantage earnings-call transcript backfill",
                "provider": "alpha_vantage",
                "symbol": symbol,
                "requested_quarter_count": len(requested_quarters),
                "cached_record_count": len(cached_records),
                "fetched_record_count": len(fetched_records),
                "collected_quarters": sorted(collected_quarters),
                "missing_quarters": still_missing,
                "fetch_errors": fetch_errors,
                "notes": [
                    "Backfill summary row. Per-quarter transcript records are represented as separate source results.",
                    "No live Alpha Vantage call is attempted when offline or when no Alpha Vantage API key is configured.",
                ],
            }
        )
        if not results:
            summary["business_model_question_results"] = question_results_without_transcript(
                _question_source(source),
                status=str(summary["status"]),
                limitation="No cached transcript records and no permitted live transcript response were available.",
            )
        results.append(summary)

    return results


def _collect_local_transcript_file_source(
    source: dict[str, Any],
    *,
    cache_dir: Path,
    offline: bool,
) -> dict[str, Any]:
    result = _base_result(source, offline=offline)
    transcript_path = str(source.get("local_transcript_path") or "").strip()
    if not transcript_path:
        result.update(
            {
                "status": "local_transcript_file_ready_no_path_configured",
                "notes": [
                    "Local transcript ingestion is available, but this registry row does not point to a transcript file.",
                ],
            }
        )
        result["business_model_question_results"] = question_results_without_transcript(
            _question_source(source),
            status=str(result["status"]),
            limitation="No local transcript path configured.",
        )
        return result

    path = Path(transcript_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        result.update(
            {
                "status": "local_transcript_file_missing",
                "local_transcript_path": str(path),
                "errors": [f"Local transcript file not found: {path}"],
            }
        )
        result["business_model_question_results"] = question_results_without_transcript(
            _question_source(source),
            status=str(result["status"]),
            limitation="The configured local transcript file was missing.",
        )
        return result

    text = path.read_text(encoding="utf-8")
    record = _normalize_local_transcript_record(source=source, text=text, source_path=path)
    record_dir = _record_dir(cache_dir / "local_transcripts", record)
    _write_transcript_record(record_dir, record)
    return _result_from_transcript_record(
        source=source,
        record_item={"record": record, "record_path": record_dir / "record.json"},
        cache_dir=cache_dir,
    )


def _collect_source_candidate_source(source: dict[str, Any], *, cache_dir: Path, offline: bool) -> dict[str, Any]:
    result = _base_result(source, offline=offline)
    source_dir = cache_dir / _slug(str(source.get("source_id") or "source_candidates"))
    candidates = list(source.get("candidates") or [])
    for path in _candidate_paths(source, cache_dir):
        payload = _read_json_if_exists(path)
        if not payload:
            continue
        candidates.extend(payload.get("candidates") or [])
    deduped = _dedupe_candidates(candidates)
    if deduped:
        write_json(
            source_dir / "source_candidates.json",
            {
                "source_id": source.get("source_id"),
                "generated_at": utc_now_iso(),
                "candidates": deduped,
                "policy": source.get("policy") or {},
            },
        )
    result.update(
        {
            "status": "source_candidates_recorded" if deduped else "source_candidates_ready_none_recorded",
            "source_candidate_count": len(deduped),
            "candidate_providers": sorted({str(item.get("provider") or "unknown") for item in deduped}),
            "cache_paths": [str(source_dir / "source_candidates.json")] if deduped else [],
            "notes": [
                "Source candidates are link-only evidence. Full third-party transcript text is not copied unless source rights permit storage.",
            ],
        }
    )
    return result


def _result_from_transcript_record(
    *,
    source: dict[str, Any],
    record_item: dict[str, Any],
    cache_dir: Path,
) -> dict[str, Any]:
    record = record_item["record"]
    record_path = Path(record_item["record_path"]) if record_item.get("record_path") else None
    record_dir = record_path.parent if record_path else _record_dir(cache_dir / "transcripts", record)
    quarter = str(record.get("quarter") or source.get("quarter") or "unknown").upper()
    source_id = f"{source.get('source_id')}_{quarter.lower()}"
    record_source = {
        **source,
        "source_id": source_id,
        "name": f"{record.get('ticker') or source.get('symbol') or 'PDD'} {quarter} earnings-call transcript",
        "period": quarter,
        "platform": str(record.get("provider") or source.get("platform") or "transcript_provider"),
        "url": record.get("source_url") or source.get("url"),
        "adapter": "earnings_call_transcript_record",
    }
    segments = _record_to_segments(record, source_id=source_id)
    question_results = business_model_question_results_from_segments(
        source=_question_source(record_source),
        segments=segments,
        period=quarter,
        limitation="Transcript evidence is provider-supplied management commentary/Q&A and should be cross-checked against filings and official releases.",
    )
    evidence_items = _evidence_items_from_segments(source=record_source, record=record, segments=segments)
    _persist_derived_outputs(record_dir, segments=segments, question_results=question_results, evidence_items=evidence_items)
    return {
        "source_id": source_id,
        "parent_source_id": source.get("source_id"),
        "name": record_source["name"],
        "adapter": "earnings_call_transcript_record",
        "provider": record.get("provider") or source.get("provider"),
        "platform": record_source["platform"],
        "period": quarter,
        "quarter": quarter,
        "url": record.get("source_url") or source.get("url"),
        "source_url": record.get("source_url") or source.get("url"),
        "source_type": record.get("source_type") or source.get("source_type"),
        "source_quality_tier": source.get("source_quality_tier", 2),
        "status": "transcript_record_collected",
        "transcript_method": str(record.get("provider") or "local_transcript_record"),
        "transcript_record_count": 1,
        "transcript_segment_count": len(segments),
        "evidence_items": evidence_items,
        "business_model_question_results": question_results,
        "transcript_records": [_record_summary(record, record_path=record_dir / "record.json", segments=segments)],
        "cache_paths": _existing_paths(
            [
                record_dir / "record.json",
                record_dir / "raw.json",
                record_dir / "transcript.md",
                record_dir / "segments.json",
                record_dir / "business_model_question_results.json",
                record_dir / "evidence_items.json",
            ]
        ),
        "errors": [],
        "notes": [
            "Imported from cached prototype output or collected through the production provider chain.",
            str(record.get("license_notes") or ""),
        ],
    }


def _load_cached_transcript_records(
    *,
    source: dict[str, Any],
    cache_dir: Path,
    symbol: str,
) -> list[dict[str, Any]]:
    paths: list[Path] = []
    patterns = source.get("cached_record_globs") or []
    if isinstance(patterns, str):
        patterns = [patterns]
    default_patterns = [
        str(cache_dir / "alpha_vantage" / "*" / "record.json"),
        str(cache_dir / _slug(str(source.get("source_id") or "alpha_vantage_backfill")) / "*" / "record.json"),
    ]
    for pattern in [*patterns, *default_patterns]:
        expanded = os.path.expanduser(str(pattern))
        if not os.path.isabs(expanded):
            expanded = str(Path.cwd() / expanded)
        paths.extend(Path(item) for item in glob.glob(expanded))

    items: list[dict[str, Any]] = []
    seen_paths: set[Path] = set()
    for path in sorted(paths):
        if path in seen_paths:
            continue
        seen_paths.add(path)
        record = _read_json_if_exists(path)
        if not record:
            continue
        if str(record.get("ticker") or "").upper() != symbol:
            continue
        if not str(record.get("transcript_text") or "").strip():
            continue
        items.append({"record": record, "record_path": path})
    return _dedupe_record_items(items)


def _dedupe_record_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for item in items:
        record = item["record"]
        key = str(record.get("id") or f"{record.get('ticker')}:{record.get('quarter')}:{record.get('provider')}")
        current = by_key.get(key)
        if current is None:
            by_key[key] = item
            continue
        current_len = len(str(current["record"].get("transcript_text") or ""))
        next_len = len(str(record.get("transcript_text") or ""))
        if next_len > current_len:
            by_key[key] = item
    return list(by_key.values())


def _fetch_alpha_vantage(symbol: str, quarter: str, api_key: str, *, timeout: int) -> dict[str, Any]:
    query = urlencode(
        {
            "function": "EARNINGS_CALL_TRANSCRIPT",
            "symbol": symbol.upper(),
            "quarter": quarter.upper(),
            "apikey": api_key,
        }
    )
    try:
        return fetch_json(
            f"{ALPHA_VANTAGE_URL}?{query}",
            headers={"User-Agent": OFFICIAL_EVENT_USER_AGENT},
            timeout=timeout,
            rate_limit_seconds=0,
        )
    except FetchError as exc:
        raise FetchError(_sanitize_secret_text(str(exc))) from exc


def _normalize_alpha_vantage_record(*, symbol: str, quarter: str, payload: dict[str, Any]) -> dict[str, Any]:
    fiscal_year, fiscal_quarter = _parse_quarter(quarter)
    blocks = payload.get("transcript") or []
    paragraphs = []
    for block in blocks:
        speaker = str(block.get("speaker") or "").strip()
        title = str(block.get("title") or "").strip()
        content = str(block.get("content") or "").strip()
        if not content:
            continue
        label = speaker
        if title and title != speaker:
            label = f"{speaker} ({title})" if speaker else title
        paragraphs.append(f"{label}: {content}" if label else content)
    now = utc_now_iso()
    return {
        "id": _stable_id(symbol, quarter, "alpha_vantage", "third_party_api"),
        "ticker": symbol.upper(),
        "company_name": None,
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
        "quarter": quarter.upper(),
        "call_date": None,
        "provider": "alpha_vantage",
        "source_url": _alpha_vantage_source_url(symbol, quarter),
        "source_type": "third_party_api",
        "transcript_text": "\n\n".join(paragraphs),
        "raw_json": payload,
        "is_official": False,
        "is_machine_generated": False,
        "confidence": "medium",
        "can_store": None,
        "can_redistribute": False,
        "license_notes": "Review Alpha Vantage terms for storage and redistribution. Use as provider-supplied management-commentary evidence.",
        "created_at": now,
        "updated_at": now,
    }


def _normalize_local_transcript_record(
    *,
    source: dict[str, Any],
    text: str,
    source_path: Path,
) -> dict[str, Any]:
    symbol = str(source.get("symbol") or source.get("ticker") or "PDD").upper()
    quarter = str(source.get("quarter") or "UNKNOWN").upper()
    fiscal_year, fiscal_quarter = _parse_quarter(quarter)
    provider = str(source.get("provider") or "local_transcript")
    source_type = str(source.get("source_type") or "local_user_provided_transcript")
    now = utc_now_iso()
    return {
        "id": _stable_id(symbol, quarter, provider, source_type),
        "ticker": symbol,
        "company_name": source.get("company_name"),
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
        "quarter": quarter,
        "call_date": source.get("call_date"),
        "provider": provider,
        "source_url": source.get("source_url") or str(source_path),
        "source_type": source_type,
        "transcript_text": text.strip(),
        "raw_json": None,
        "is_official": bool(source.get("is_official", False)),
        "is_machine_generated": bool(source.get("is_machine_generated", False)),
        "confidence": source.get("confidence") or "medium",
        "can_store": source.get("can_store"),
        "can_redistribute": source.get("can_redistribute", False),
        "license_notes": source.get("license_notes") or "User/local transcript ingestion; verify source rights before reuse.",
        "created_at": now,
        "updated_at": now,
    }


def _record_to_segments(record: dict[str, Any], *, source_id: str) -> list[dict[str, Any]]:
    raw_blocks = ((record.get("raw_json") or {}).get("transcript") or []) if isinstance(record.get("raw_json"), dict) else []
    segments: list[dict[str, Any]] = []
    if isinstance(raw_blocks, list) and raw_blocks:
        for index, block in enumerate(raw_blocks, start=1):
            content = str(block.get("content") or "").strip()
            if not content:
                continue
            speaker = str(block.get("speaker") or "").strip()
            title = str(block.get("title") or "").strip()
            label = speaker
            if title and title != speaker:
                label = f"{speaker} ({title})" if speaker else title
            segments.append(
                {
                    "source_id": source_id,
                    "segment_index": index,
                    "speaker": speaker or None,
                    "title": title or None,
                    "start_seconds": None,
                    "text": f"{label}: {content}" if label else content,
                    "source_url": record.get("source_url"),
                    "quarter": record.get("quarter"),
                    "transcript_method": record.get("provider"),
                }
            )
        return segments

    text = str(record.get("transcript_text") or "").strip()
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n+", text) if item.strip()]
    if not paragraphs and text:
        paragraphs = [text]
    for index, paragraph in enumerate(paragraphs, start=1):
        speaker = None
        match = re.match(r"^([A-Z][^:\n]{1,80}):\s+(.+)$", paragraph, flags=re.DOTALL)
        if match:
            speaker = match.group(1).strip()
        segments.append(
            {
                "source_id": source_id,
                "segment_index": index,
                "speaker": speaker,
                "title": None,
                "start_seconds": None,
                "text": paragraph,
                "source_url": record.get("source_url"),
                "quarter": record.get("quarter"),
                "transcript_method": record.get("provider"),
            }
        )
    return segments


def _evidence_items_from_segments(
    *,
    source: dict[str, Any],
    record: dict[str, Any],
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence_items: list[dict[str, Any]] = []
    for claim_id, terms in OFFICIAL_EVENT_TERM_GROUPS.items():
        matches = _segment_term_matches(segments, terms, limit=2)
        for match in matches:
            evidence_items.append(
                {
                    "claim_id": claim_id,
                    "claim": _claim_text(claim_id),
                    "source_id": source.get("source_id"),
                    "source_name": source.get("name"),
                    "source_url": record.get("source_url") or source.get("url"),
                    "source_locator": record.get("source_url") or source.get("url") or source.get("source_id"),
                    "source_quality_tier": source.get("source_quality_tier", 2),
                    "evidence_type": "earnings_call_transcript_segment",
                    "provider": record.get("provider"),
                    "quarter": record.get("quarter"),
                    "speaker": match.get("speaker"),
                    "segment_index": match.get("segment_index"),
                    "matched_terms": match.get("matched_terms", []),
                    "excerpt": match.get("excerpt"),
                    "confidence": record.get("confidence") or "medium",
                    "limitation": "Provider-supplied earnings-call transcript; use for management commentary/Q&A and reconcile with filings.",
                }
            )
    return evidence_items


def _segment_term_matches(segments: list[dict[str, Any]], terms: list[str], *, limit: int) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for segment in segments:
        text = str(segment.get("text") or "")
        lowered = text.lower()
        matched_terms = [term for term in terms if term and term.lower() in lowered]
        if not matched_terms:
            continue
        matches.append(
            {
                "segment_index": segment.get("segment_index"),
                "speaker": segment.get("speaker"),
                "matched_terms": matched_terms[:10],
                "excerpt": _trim_text(text, 520),
            }
        )
        if len(matches) >= limit:
            break
    return matches


def _persist_derived_outputs(
    record_dir: Path,
    *,
    segments: list[dict[str, Any]],
    question_results: list[dict[str, Any]],
    evidence_items: list[dict[str, Any]],
) -> None:
    write_json(record_dir / "segments.json", segments)
    write_json(record_dir / "business_model_question_results.json", question_results)
    write_json(record_dir / "evidence_items.json", evidence_items)


def _write_transcript_record(record_dir: Path, record: dict[str, Any]) -> None:
    record_dir.mkdir(parents=True, exist_ok=True)
    write_json(record_dir / "record.json", record)
    if record.get("raw_json") is not None:
        write_json(record_dir / "raw.json", record["raw_json"])
    (record_dir / "transcript.md").write_text(_record_to_markdown(record), encoding="utf-8")


def _record_to_markdown(record: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {record.get('ticker')} {record.get('quarter')} Earnings Call Transcript",
            "",
            f"- Provider: `{record.get('provider')}`",
            f"- Source type: `{record.get('source_type')}`",
            f"- Confidence: `{record.get('confidence')}`",
            f"- Official: `{record.get('is_official')}`",
            f"- Machine generated: `{record.get('is_machine_generated')}`",
            f"- Can store: `{record.get('can_store')}`",
            f"- Can redistribute: `{record.get('can_redistribute')}`",
            f"- License notes: {record.get('license_notes') or ''}",
            "",
            "## Transcript",
            "",
            str(record.get("transcript_text") or ""),
            "",
        ]
    )


def _record_summary(record: dict[str, Any], *, record_path: Path, segments: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "ticker": record.get("ticker"),
        "quarter": record.get("quarter"),
        "provider": record.get("provider"),
        "source_type": record.get("source_type"),
        "source_url": record.get("source_url"),
        "record_path": str(record_path),
        "transcript_path": str(record_path.parent / "transcript.md"),
        "raw_path": str(record_path.parent / "raw.json") if (record_path.parent / "raw.json").exists() else None,
        "segment_count": len(segments),
        "character_count": len(str(record.get("transcript_text") or "")),
        "confidence": record.get("confidence"),
        "is_official": record.get("is_official"),
        "can_store": record.get("can_store"),
        "can_redistribute": record.get("can_redistribute"),
        "license_notes": record.get("license_notes"),
    }


def _alpha_vantage_api_key() -> str | None:
    load_dotenv(".env")
    for name in ALPHA_VANTAGE_KEY_NAMES:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _alpha_vantage_miss(payload: dict[str, Any]) -> str | None:
    for key in ("Information", "Error Message", "Note"):
        if key in payload:
            return _sanitize_secret_text(str(payload[key]))
    transcript = payload.get("transcript")
    if not isinstance(transcript, list) or not transcript:
        return "No transcript list returned."
    return None


def _alpha_summary_status(
    *,
    has_records: bool,
    offline: bool,
    api_key_present: bool,
    missing_quarters: list[str],
    fetch_errors: list[dict[str, Any]],
) -> str:
    if has_records and (missing_quarters or fetch_errors):
        return "transcripts_collected_backfill_incomplete"
    if has_records:
        return "transcripts_collected"
    if offline:
        return "offline_provider_chain_ready"
    if not api_key_present:
        return "alpha_vantage_key_missing"
    if fetch_errors:
        return "alpha_vantage_fetch_failed"
    return "alpha_vantage_no_transcripts_collected"


def _looks_like_rate_limit(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ("rate", "frequency", "limit", "standard api call", "quota"))


def _alpha_vantage_source_url(symbol: str, quarter: str) -> str:
    return (
        f"{ALPHA_VANTAGE_URL}?"
        + urlencode(
            {
                "function": "EARNINGS_CALL_TRANSCRIPT",
                "symbol": symbol.upper(),
                "quarter": quarter.upper(),
                "apikey": "REDACTED",
            }
        )
    )


def _parse_quarter(quarter: str) -> tuple[int | None, str | None]:
    match = re.fullmatch(r"(\d{4})(Q[1-4])", str(quarter).upper())
    if not match:
        return None, None
    return int(match.group(1)), match.group(2)


def _quarter_to_index(quarter: str) -> int:
    year, q = _parse_quarter(quarter)
    if year is None or q is None:
        raise ValueError(f"Invalid quarter format: {quarter}. Expected YYYYQn.")
    return year * 4 + int(q[1]) - 1


def _index_to_quarter(index: int) -> str:
    year = index // 4
    q = index % 4 + 1
    return f"{year}Q{q}"


def _quarter_range(start: str, end: str) -> list[str]:
    start_index = _quarter_to_index(start)
    end_index = _quarter_to_index(end)
    if end_index < start_index:
        raise ValueError("end_quarter must be >= start_quarter")
    return [_index_to_quarter(index) for index in range(start_index, end_index + 1)]


def _stable_id(symbol: str, quarter: str, provider: str, source_type: str) -> str:
    return hashlib.sha256(f"{symbol.upper()}:{quarter.upper()}:{provider}:{source_type}".encode("utf-8")).hexdigest()[:24]


def _record_dir(root: Path, record: dict[str, Any]) -> Path:
    symbol = str(record.get("ticker") or "PDD").upper()
    quarter = str(record.get("quarter") or "UNKNOWN").upper()
    provider = _slug(str(record.get("provider") or "transcript"))
    return root / f"{symbol}-{quarter}-{provider}"


def _load_registry(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _manual_source_result(source: dict[str, Any], *, offline: bool) -> dict[str, Any]:
    result = _base_result(source, offline=offline)
    result.update(
        {
            "status": "offline_not_collected" if offline else source.get("status", "planned"),
            "notes": ["Source is registered, but no automated collector is configured for this adapter."],
        }
    )
    return result


def _base_result(source: dict[str, Any], *, offline: bool) -> dict[str, Any]:
    return {
        "source_id": source.get("source_id"),
        "name": source.get("name"),
        "adapter": source.get("adapter"),
        "platform": source.get("platform"),
        "status": "offline_registered" if offline else "registered",
        "source_quality_tier": source.get("source_quality_tier"),
        "url": source.get("url") or source.get("source_url"),
        "period": source.get("period"),
        "transcript_record_count": 0,
        "transcript_segment_count": 0,
        "source_candidate_count": 0,
        "business_model_question_results": [],
        "evidence_items": [],
        "cache_paths": [],
        "errors": [],
        "notes": [],
    }


def _question_source(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": source.get("source_id"),
        "name": source.get("name"),
        "url": source.get("url") or source.get("source_url"),
        "period": source.get("period") or source.get("quarter"),
        "platform": source.get("platform"),
    }


def _candidate_paths(source: dict[str, Any], cache_dir: Path) -> list[Path]:
    patterns = source.get("cached_candidate_globs") or []
    if isinstance(patterns, str):
        patterns = [patterns]
    patterns = [
        *patterns,
        str(cache_dir / "source_candidates" / "*" / "source_candidates.json"),
        str(cache_dir / _slug(str(source.get("source_id") or "source_candidates")) / "source_candidates.json"),
    ]
    paths: list[Path] = []
    for pattern in patterns:
        expanded = os.path.expanduser(str(pattern))
        if not os.path.isabs(expanded):
            expanded = str(Path.cwd() / expanded)
        paths.extend(Path(item) for item in glob.glob(expanded))
    return sorted(set(paths))


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        key = str(candidate.get("source_url") or candidate.get("url") or candidate.get("id") or "")
        if not key:
            key = hashlib.sha256(json.dumps(candidate, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        by_key[key] = candidate
    return list(by_key.values())


def _read_json_if_exists(path: str | Path) -> dict[str, Any] | None:
    target = Path(path)
    if not target.exists():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _existing_paths(paths: list[Path]) -> list[str]:
    return [str(path) for path in paths if path.exists()]


def _theme_summary(evidence_items: list[dict[str, Any]]) -> dict[str, Any]:
    claim_counts = Counter(str(item.get("claim_id") or "unknown") for item in evidence_items)
    source_counts = Counter(str(item.get("source_id") or "unknown") for item in evidence_items)
    return {
        "claim_counts": dict(sorted(claim_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
    }


def _claim_text(claim_id: str) -> str:
    return {
        "long_term_investment": "Management discusses long-term investment or high-quality development.",
        "customer_value": "Management discusses customer value, quality, trust, or shopping experience.",
        "merchant_support": "Management discusses merchant support, fee reductions, supply-chain support, or ecosystem health.",
        "competition_and_pressure": "Management acknowledges competition, margin pressure, or uncertainty.",
        "temu_global": "Management discusses Temu/global expansion, overseas operations, trade, or regulatory context.",
        "organization_and_people": "Management discusses organization, governance, talent, culture, or leadership changes.",
    }.get(claim_id, "Earnings-call transcript evidence item.")


def _trim_text(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 3)].rstrip() + "..."


def _sanitize_secret_text(text: str) -> str:
    sanitized = text
    for name in ALPHA_VANTAGE_KEY_NAMES:
        value = os.environ.get(name)
        if value and len(value) >= 8:
            sanitized = sanitized.replace(value, "REDACTED")
    return re.sub(r"(apikey=)[^&\s]+", r"\1REDACTED", sanitized, flags=re.IGNORECASE)


def _slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:120] or "source"


def _empty_video_manifest(company_id: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "company_id": company_id,
        "generated_at": utc_now_iso(),
        "registry_paths": [],
        "record_count": 0,
        "records": [],
        "excluded_sources": [],
        "key_policy": {
            "video_uid": "This earnings-call transcript provider-chain agent does not create video records.",
            "source_id": "Transcript source rows remain traceable through source_results and record_path.",
        },
    }


# Backward-compatible aliases intentionally left out: the previous Gemini/YouTube
# implementation was retired for this agent in favor of the transcript prototype.
