"""Run the Competitor Source Collector V1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .common import alt_data_runtime_root, project_root, read_json_if_exists, render_pack_markdown, write_json
from .competitor_source import build_competitor_source_pack


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    root = alt_data_runtime_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company", default="PDD")
    parser.add_argument("--brand", default="Temu")
    parser.add_argument("--source-plan", default=str(project_root() / "config" / "alternative_data" / "collectors" / "competitor_source.v1.json"))
    parser.add_argument("--target-snapshots-json", default=str(root / "temu_product_intelligence" / "latest" / "latest_snapshots.json"))
    parser.add_argument("--competitor-snapshots-json", action="append", default=[])
    parser.add_argument("--source-text-json", action="append", default=[])
    parser.add_argument("--output-dir", default=str(root / "collectors" / "competitor_source" / "latest"))
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> dict[str, Any]:
    competitor_snapshots = []
    for path in args.competitor_snapshots_json:
        competitor_snapshots.extend(read_json_if_exists(path, []))
    source_text_records = []
    for path in args.source_text_json:
        payload = read_json_if_exists(path, [])
        if isinstance(payload, dict):
            payload = payload.get("records") or payload.get("source_text_records") or []
        source_text_records.extend(payload)

    source_inputs = {
        "source_plan": args.source_plan,
        "target_snapshots_json": args.target_snapshots_json,
        "competitor_snapshots_json": args.competitor_snapshots_json,
        "source_text_json": args.source_text_json,
    }
    pack = build_competitor_source_pack(
        company=args.company,
        brand=args.brand,
        target_snapshots=read_json_if_exists(args.target_snapshots_json, []),
        competitor_snapshots=competitor_snapshots,
        source_text_records=source_text_records,
        source_inputs=source_inputs,
    )
    output_dir = Path(args.output_dir)
    write_json(output_dir / "competitor_source_pack.json", pack)
    (output_dir / "competitor_source_report.md").write_text(
        render_pack_markdown(pack, "Competitor Source Collector V1"),
        encoding="utf-8",
    )
    return {
        "status": "complete",
        "collector_id": pack.collector_id,
        "metrics": len(pack.metrics),
        "events": len(pack.events),
        "findings": len(pack.findings),
        "output_dir": str(output_dir),
    }


def main(argv: list[str] | None = None) -> int:
    result = run(parse_args(argv))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
