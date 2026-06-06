"""Run the alternative data analyst agent on one or more signal packs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import build_alternative_data_brief, load_signal_pack, write_agent_outputs


def project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists() and (parent / "src").exists():
            return parent
    raise RuntimeError("Could not locate investment-assistant project root")


def runtime_root() -> Path:
    return project_root() / "data" / "alternative_data" / "digital_demand_monitor"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pack",
        action="append",
        dest="packs",
        help="Path to a demand_signal_pack.json. Repeat to merge multiple packs.",
    )
    parser.add_argument("--primary-brand-id", default=None)
    parser.add_argument("--output-dir", default=str(runtime_root() / "alternative_data_agent"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pack_paths = args.packs or [str(runtime_root() / "latest" / "demand_signal_pack.json")]
    packs = [load_signal_pack(path) for path in pack_paths]
    brief = build_alternative_data_brief(packs, primary_brand_id=args.primary_brand_id)
    write_agent_outputs(args.output_dir, brief)
    print(
        json.dumps(
            {
                "status": "complete",
                "packs": pack_paths,
                "questions": len(brief["questions"]),
                "output_dir": args.output_dir,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
