#!/usr/bin/env python3
"""Fetch and normalize an earnings-call transcript from Alpha Vantage."""

from __future__ import annotations

import argparse
import json

from transcript_common import (
    ALPHA_VANTAGE_URL,
    TranscriptError,
    add_common_source_args,
    alpha_vantage_key,
    build_alpha_vantage_url,
    fetch_json,
    is_alpha_vantage_miss,
    make_run_dir,
    normalize_alpha_vantage,
    print_error,
    write_record,
)


def fetch_alpha_vantage(symbol: str, quarter: str, api_key: str, timeout: int) -> dict:
    return fetch_json(
        ALPHA_VANTAGE_URL,
        {
            "function": "EARNINGS_CALL_TRANSCRIPT",
            "symbol": symbol.upper(),
            "quarter": quarter.upper(),
            "apikey": api_key,
        },
        timeout=timeout,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_source_args(parser)
    parser.add_argument("--demo", action="store_true", help="Use Alpha Vantage demo key. Works for documented demo symbols.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        api_key = alpha_vantage_key(args.demo)
        payload = fetch_alpha_vantage(args.symbol, args.quarter, api_key, args.timeout)
        miss_reason = is_alpha_vantage_miss(payload)
        if miss_reason:
            raise TranscriptError(miss_reason)
        record = normalize_alpha_vantage(args.symbol, args.quarter, payload)
        run_dir = make_run_dir(args.symbol, args.quarter, "alpha_vantage")
        write_record(run_dir, record)
    except Exception as exc:
        return print_error(exc)

    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "record": str(run_dir / "record.json"),
                "transcript": str(run_dir / "transcript.md"),
                "source_url": build_alpha_vantage_url(args.symbol, args.quarter, "REDACTED"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

