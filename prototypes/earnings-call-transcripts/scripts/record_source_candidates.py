#!/usr/bin/env python3
"""Record source candidates when a transcript cannot be fetched/stored automatically."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from transcript_common import artifact_root, print_error, safe_slug


def stable_id(symbol: str, quarter: str, provider: str, url: str) -> str:
    key = f"{symbol.upper()}:{quarter.upper()}:{provider}:{url}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def make_run_dir(symbol: str, quarter: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    path = artifact_root() / f"{safe_slug(symbol.upper())}-{quarter.upper()}-source-candidates-{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_source(value: str) -> dict:
    parts = value.split("|")
    if len(parts) < 4:
        raise argparse.ArgumentTypeError(
            "--source must be provider|source_type|access_type|url|optional notes"
        )
    provider, source_type, access_type, url = parts[:4]
    notes = parts[4] if len(parts) > 4 else ""
    return {
        "provider": provider,
        "source_type": source_type,
        "access_type": access_type,
        "source_url": url,
        "notes": notes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--quarter", required=True)
    parser.add_argument("--source", action="append", type=parse_source, required=True)
    parser.add_argument("--can-store", choices=["true", "false", "unknown"], default="unknown")
    parser.add_argument("--can-redistribute", choices=["true", "false", "unknown"], default="false")
    parser.add_argument("--license-notes", default="")
    parser.add_argument("--reason", default="")
    return parser.parse_args()


def tri_bool(value: str):
    if value == "unknown":
        return None
    return value == "true"


def markdown(symbol: str, quarter: str, reason: str, candidates: list[dict]) -> str:
    lines = [
        f"# Transcript Source Candidates: {symbol.upper()} {quarter.upper()}",
        "",
        f"Reason: {reason or 'Recorded as source candidates.'}",
        "",
        "These are pointers for manual review or licensed ingestion. The prototype intentionally does not copy full third-party transcript text unless the source/license permits storage.",
        "",
        "## Candidates",
        "",
    ]
    for item in candidates:
        lines.extend(
            [
                f"### {item['provider']}",
                "",
                f"- URL: {item['source_url']}",
                f"- Source type: `{item['source_type']}`",
                f"- Access type: `{item['access_type']}`",
                f"- Can store: `{item['can_store']}`",
                f"- Can redistribute: `{item['can_redistribute']}`",
                f"- License notes: {item.get('license_notes') or ''}",
                f"- Notes: {item.get('notes') or ''}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        run_dir = make_run_dir(args.symbol, args.quarter)
        candidates = []
        for source in args.source:
            item = {
                "id": stable_id(args.symbol, args.quarter, source["provider"], source["source_url"]),
                "ticker": args.symbol.upper(),
                "quarter": args.quarter.upper(),
                "provider": source["provider"],
                "source_url": source["source_url"],
                "source_type": source["source_type"],
                "access_type": source["access_type"],
                "can_store": tri_bool(args.can_store),
                "can_redistribute": tri_bool(args.can_redistribute),
                "license_notes": args.license_notes,
                "notes": source.get("notes"),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            candidates.append(item)
        payload = {
            "ticker": args.symbol.upper(),
            "quarter": args.quarter.upper(),
            "reason": args.reason,
            "candidates": candidates,
        }
        (run_dir / "source_candidates.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (run_dir / "source_candidates.md").write_text(
            markdown(args.symbol, args.quarter, args.reason, candidates),
            encoding="utf-8",
        )
    except Exception as exc:
        return print_error(exc)

    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "sources": str(run_dir / "source_candidates.json"),
                "summary": str(run_dir / "source_candidates.md"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

