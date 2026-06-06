"""Run the Product / Pricing / Policy Collector V1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .common import alt_data_runtime_root, project_root, read_json_if_exists, render_pack_markdown, write_json
from .product_pricing_policy import build_product_pricing_policy_pack


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    root = alt_data_runtime_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company", default="PDD")
    parser.add_argument("--brand", default="Temu")
    parser.add_argument("--source-plan", default=str(project_root() / "config" / "alternative_data" / "collectors" / "product_pricing_policy.v1.json"))
    parser.add_argument("--product-snapshots-json", default=str(root / "temu_product_intelligence" / "latest" / "latest_snapshots.json"))
    parser.add_argument("--product-metrics-json", default=str(root / "temu_product_intelligence" / "latest" / "weekly_metrics.json"))
    parser.add_argument("--product-signal-pack-json", default=str(root / "temu_product_intelligence" / "latest" / "product_signal_pack.json"))
    parser.add_argument("--unit-economics-json", default=str(root / "temu_product_intelligence" / "latest" / "unit_economics_pack.json"))
    parser.add_argument("--policy-events-json", default=str(root / "merchant_regulatory_monitor" / "live_temu" / "merchant_regulatory_events.json"))
    parser.add_argument("--output-dir", default=str(root / "collectors" / "product_pricing_policy" / "latest"))
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> dict[str, Any]:
    source_inputs = {
        "source_plan": args.source_plan,
        "product_snapshots_json": args.product_snapshots_json,
        "product_metrics_json": args.product_metrics_json,
        "product_signal_pack_json": args.product_signal_pack_json,
        "unit_economics_json": args.unit_economics_json,
        "policy_events_json": args.policy_events_json,
    }
    pack = build_product_pricing_policy_pack(
        company=args.company,
        brand=args.brand,
        product_snapshots=read_json_if_exists(args.product_snapshots_json, []),
        product_metrics=read_json_if_exists(args.product_metrics_json, []),
        product_signal_pack=read_json_if_exists(args.product_signal_pack_json, {}),
        unit_economics_pack=read_json_if_exists(args.unit_economics_json, {}),
        policy_events=read_json_if_exists(args.policy_events_json, []),
        source_inputs=source_inputs,
    )
    output_dir = Path(args.output_dir)
    write_json(output_dir / "product_pricing_policy_pack.json", pack)
    (output_dir / "product_pricing_policy_report.md").write_text(
        render_pack_markdown(pack, "Product / Pricing / Policy Collector V1"),
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
