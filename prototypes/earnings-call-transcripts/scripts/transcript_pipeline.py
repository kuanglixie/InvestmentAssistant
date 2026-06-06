#!/usr/bin/env python3
"""Provider-chain MVP for earnings-call transcript sourcing."""

from __future__ import annotations

import argparse
import json

from fetch_alpha_vantage import fetch_alpha_vantage
from transcript_common import (
    TranscriptError,
    add_common_source_args,
    alpha_vantage_key,
    is_alpha_vantage_miss,
    make_run_dir,
    normalize_alpha_vantage,
    print_error,
    write_next_steps,
    write_record,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_source_args(parser)
    parser.add_argument("--demo", action="store_true", help="Use Alpha Vantage demo key.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = make_run_dir(args.symbol, args.quarter, "pipeline")
    try:
        api_key = alpha_vantage_key(args.demo)
        payload = fetch_alpha_vantage(args.symbol, args.quarter, api_key, args.timeout)
        miss_reason = is_alpha_vantage_miss(payload)
        if miss_reason:
            write_next_steps(run_dir, args.symbol, args.quarter, miss_reason)
            print(json.dumps({"run_dir": str(run_dir), "status": "missing", "reason": miss_reason}, indent=2))
            return 1

        record = normalize_alpha_vantage(args.symbol, args.quarter, payload)
        write_record(run_dir, record)
    except Exception as exc:
        write_next_steps(run_dir, args.symbol, args.quarter, str(exc))
        return print_error(exc)

    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "status": "fetched",
                "provider": "alpha_vantage",
                "record": str(run_dir / "record.json"),
                "transcript": str(run_dir / "transcript.md"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

