"""Run a Reddit public-voice snapshot and export monitor-friendly artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .exports import (
    build_reddit_summary,
    export_demand_monitor_reviews,
    findings_from_json_payload,
    load_json,
    reddit_evidence_items,
    render_summary_markdown,
    write_json,
    write_reviews_csv,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def prototype_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    default_state = repo_root() / "data" / "runs" / "20260530T033052Z-pdd" / "state.json"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-json", default=str(default_state) if default_state.exists() else None)
    parser.add_argument("--findings-json", help="Direct public_voice_findings JSON file.")
    parser.add_argument("--live-collect", action="store_true", help="Attempt live collection through the main public_voice adapter.")
    parser.add_argument("--offline", action="store_true", help="Run the main collector in source-plan/offline mode.")
    parser.add_argument("--registry", default=str(repo_root() / "config" / "qualitative" / "pdd_public_voice_sources.v1.json"))
    parser.add_argument("--cache-root", default=str(repo_root() / "data" / "raw" / "public_voice"))
    parser.add_argument("--output-dir", default=str(prototype_root() / "artifacts" / "latest"))
    parser.add_argument("--brand-id", default="temu")
    parser.add_argument("--market", default="GLOBAL")
    parser.add_argument("--max-items", type=int)
    return parser.parse_args()


def load_or_collect_findings(args: argparse.Namespace) -> dict[str, Any]:
    if args.findings_json:
        return findings_from_json_payload(load_json(args.findings_json))
    if args.state_json and Path(args.state_json).exists() and not args.live_collect:
        return findings_from_json_payload(load_json(args.state_json))
    if not args.live_collect:
        raise SystemExit("No --state-json/--findings-json found. Pass --live-collect to attempt a fresh Reddit collection.")

    main_src = repo_root() / "src"
    if str(main_src) not in sys.path:
        sys.path.insert(0, str(main_src))
    from stock_research.qualitative.public_voice import collect_public_voice_evidence

    return collect_public_voice_evidence(
        company={"company_id": "pdd", "legal_name": "PDD Holdings Inc."},
        cache_root=args.cache_root,
        offline=args.offline,
        registry_path=args.registry,
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    findings = load_or_collect_findings(args)
    items = reddit_evidence_items(findings)
    reviews = export_demand_monitor_reviews(
        items,
        brand_id=args.brand_id,
        market=args.market,
        max_items=args.max_items,
    )
    if args.max_items is not None:
        items = items[: args.max_items]
    summary = build_reddit_summary(findings, items)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "public_voice_findings.json", findings)
    write_json(output_dir / "reddit_evidence_items.json", items)
    write_json(output_dir / "reddit_public_voice_summary.json", summary)
    write_json(output_dir / "demand_monitor_reviews.json", reviews)
    write_reviews_csv(output_dir / "reddit_review_samples.csv", reviews)
    (output_dir / "reddit_public_voice_summary.md").write_text(render_summary_markdown(summary), encoding="utf-8")

    return {
        "status": "complete",
        "output_dir": str(output_dir),
        "reddit_evidence_items": len(items),
        "demand_monitor_reviews": len(reviews),
        "summary_path": str(output_dir / "reddit_public_voice_summary.md"),
        "demand_monitor_reviews_path": str(output_dir / "demand_monitor_reviews.json"),
    }


def main() -> int:
    result = run(parse_args())
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
