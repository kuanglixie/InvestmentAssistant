#!/usr/bin/env python3
"""Ingest a local/manual transcript into the normalized transcript record format."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from transcript_common import (
    add_common_source_args,
    make_run_dir,
    normalize_local_transcript,
    print_error,
    write_record,
)


def parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.lower()
    if lowered in {"true", "1", "yes", "y"}:
        return True
    if lowered in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Expected true/false/unknown, got {value}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_source_args(parser)
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--company-name")
    parser.add_argument("--provider", required=True)
    parser.add_argument(
        "--source-type",
        required=True,
        choices=["official", "third_party_api", "third_party_web", "machine_transcribed_audio", "manual_note"],
    )
    parser.add_argument("--source-url")
    parser.add_argument("--confidence", default="medium", choices=["high", "medium", "low"])
    parser.add_argument("--official", action="store_true")
    parser.add_argument("--machine-generated", action="store_true")
    parser.add_argument("--can-store", type=parse_bool, default=None)
    parser.add_argument("--can-redistribute", type=parse_bool, default=False)
    parser.add_argument("--license-notes")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        path = args.file.expanduser().resolve()
        text = path.read_text(encoding="utf-8", errors="replace")
        record = normalize_local_transcript(
            symbol=args.symbol,
            quarter=args.quarter,
            company_name=args.company_name,
            text=text,
            provider=args.provider,
            source_url=args.source_url,
            source_type=args.source_type,
            confidence=args.confidence,
            is_official=args.official,
            is_machine_generated=args.machine_generated,
            can_store=args.can_store,
            can_redistribute=args.can_redistribute,
            license_notes=args.license_notes,
        )
        run_dir = make_run_dir(args.symbol, args.quarter, args.provider)
        write_record(run_dir, record)
    except Exception as exc:
        return print_error(exc)

    print(json.dumps({"run_dir": str(run_dir), "record": str(run_dir / "record.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
