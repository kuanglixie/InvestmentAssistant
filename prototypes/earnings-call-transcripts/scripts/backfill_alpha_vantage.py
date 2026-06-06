#!/usr/bin/env python3
"""Backfill full earnings-call transcripts from Alpha Vantage over many quarters."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from fetch_alpha_vantage import fetch_alpha_vantage
from transcript_common import (
    TranscriptError,
    alpha_vantage_key,
    artifact_root,
    is_alpha_vantage_miss,
    make_run_dir,
    normalize_alpha_vantage,
    parse_quarter,
    print_error,
    safe_slug,
    write_next_steps,
    write_record,
)


def quarter_to_index(quarter: str) -> int:
    year, q = parse_quarter(quarter)
    if year is None or q is None:
        raise TranscriptError(f"Invalid quarter format: {quarter}. Expected YYYYQn, e.g. 2024Q1.")
    return year * 4 + (int(q[1]) - 1)


def index_to_quarter(index: int) -> str:
    year = index // 4
    q = index % 4 + 1
    return f"{year}Q{q}"


def quarter_range(start: str, end: str) -> list[str]:
    start_index = quarter_to_index(start)
    end_index = quarter_to_index(end)
    if end_index < start_index:
        raise TranscriptError("--end must be >= --start")
    return [index_to_quarter(index) for index in range(start_index, end_index + 1)]


def make_backfill_dir(symbol: str, start: str, end: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = artifact_root() / f"{safe_slug(symbol.upper())}-{start.upper()}-to-{end.upper()}-alpha-backfill-{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--start", required=True, help="Start quarter, e.g. 2020Q1.")
    parser.add_argument("--end", required=True, help="End quarter, e.g. 2026Q1.")
    parser.add_argument("--demo", action="store_true", help="Use Alpha Vantage demo key.")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--sleep", type=float, default=13.0, help="Seconds between requests; free tier is rate limited.")
    parser.add_argument("--max-requests", type=int, help="Optional cap for test runs.")
    parser.add_argument("--stop-on-rate-limit", action="store_true")
    parser.add_argument("--require-all", action="store_true", help="Exit non-zero if any requested quarter is missing or errors.")
    parser.add_argument("--newest-first", action="store_true", help="Fetch the newest quarter first while keeping the requested date range.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        api_key = alpha_vantage_key(args.demo)
        quarters = quarter_range(args.start, args.end)
        if args.newest_first:
            quarters = list(reversed(quarters))
        if args.max_requests:
            quarters = quarters[: args.max_requests]

        backfill_dir = make_backfill_dir(args.symbol, args.start, args.end)
        manifest = {
            "symbol": args.symbol.upper(),
            "start": args.start.upper(),
            "end": args.end.upper(),
            "provider": "alpha_vantage",
            "mode": "full_transcript_backfill",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "results": [],
        }

        for position, quarter in enumerate(quarters, start=1):
            item = {"quarter": quarter, "status": None, "run_dir": None, "reason": None}
            try:
                payload = fetch_alpha_vantage(args.symbol, quarter, api_key, args.timeout)
                miss_reason = is_alpha_vantage_miss(payload)
                if miss_reason:
                    item.update({"status": "missing", "reason": miss_reason})
                    run_dir = make_run_dir(args.symbol, quarter, "alpha_vantage_missing")
                    write_next_steps(run_dir, args.symbol, quarter, miss_reason)
                    item["run_dir"] = str(run_dir)
                    rate_limited = any(
                        token in miss_reason.lower()
                        for token in ("rate", "standard api call frequency", "demo")
                    )
                    if args.stop_on_rate_limit and rate_limited:
                        manifest["results"].append(item)
                        break
                else:
                    record = normalize_alpha_vantage(args.symbol, quarter, payload)
                    run_dir = make_run_dir(args.symbol, quarter, "alpha_vantage")
                    write_record(run_dir, record)
                    item.update(
                        {
                            "status": "fetched",
                            "run_dir": str(run_dir),
                            "chars": len(record.get("transcript_text") or ""),
                            "blocks": len(payload.get("transcript") or []),
                        }
                    )
            except Exception as exc:
                item.update({"status": "error", "reason": str(exc)})

            manifest["results"].append(item)
            print(f"[{position}/{len(quarters)}] {quarter}: {item.get('status')}", file=sys.stderr, flush=True)
            if position < len(quarters):
                time.sleep(max(0, args.sleep))

        (backfill_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        lines = [
            f"# Alpha Vantage Backfill: {args.symbol.upper()} {args.start.upper()} to {args.end.upper()}",
            "",
            "| Quarter | Status | Chars | Blocks | Notes |",
            "|---|---:|---:|---:|---|",
        ]
        for item in manifest["results"]:
            lines.append(
                f"| {item['quarter']} | {item.get('status')} | {item.get('chars', '')} | {item.get('blocks', '')} | {item.get('reason', '') or item.get('run_dir', '')} |"
            )
        (backfill_dir / "manifest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

        status_counts: dict[str, int] = {}
        for item in manifest["results"]:
            status = item.get("status") or "unknown"
            status_counts[status] = status_counts.get(status, 0) + 1

        failures = [item for item in manifest["results"] if item.get("status") != "fetched"]
        output = {
            "status": "complete" if not failures else "partial",
            "status_counts": status_counts,
            "backfill_dir": str(backfill_dir),
            "manifest": str(backfill_dir / "manifest.json"),
            "summary": str(backfill_dir / "manifest.md"),
        }
        if failures:
            output["failed_quarters"] = [
                {"quarter": item.get("quarter"), "status": item.get("status"), "reason": item.get("reason")}
                for item in failures
            ]

        print(json.dumps(output, indent=2))
        if args.require_all and failures:
            return 1
    except Exception as exc:
        return print_error(exc)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
