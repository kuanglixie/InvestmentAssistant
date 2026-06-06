import argparse
import json
import tempfile
import unittest
from pathlib import Path

from stock_research.alternative_data.collectors.competitor_source import build_competitor_source_pack
from stock_research.alternative_data.collectors.run_competitor_source import run


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_json(name: str):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class CompetitorSourceCollectorTest(unittest.TestCase):
    def test_build_pack_emits_comparison_and_text_findings(self) -> None:
        source_records = load_json("competitor_source_text_records.json")["records"]
        pack = build_competitor_source_pack(
            target_snapshots=load_json("target_snapshots.json"),
            competitor_snapshots=load_json("competitor_snapshots.json"),
            source_text_records=source_records,
        )

        finding_ids = {finding.finding_id for finding in pack.findings}
        self.assertIn("relative_price_position", finding_ids)
        self.assertIn("relative_delivery_position", finding_ids)
        self.assertIn("competitor_strategy_overlap", finding_ids)
        self.assertIn("competitor_regulatory_context", finding_ids)
        kitchen = next(metric for metric in pack.metrics if metric["comparison_id"] == "kitchen:amazon")
        self.assertLess(kitchen["relative_price_gap_pct"], -10)
        self.assertGreater(kitchen["delivery_gap_days"], 0)
        self.assertTrue(any(event["event_topic"] == "regulatory_risk" for event in pack.events))

    def test_cli_run_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args = argparse.Namespace(
                company="PDD",
                brand="Temu",
                source_plan="source_plan",
                target_snapshots_json=str(FIXTURE_DIR / "target_snapshots.json"),
                competitor_snapshots_json=[str(FIXTURE_DIR / "competitor_snapshots.json")],
                source_text_json=[str(FIXTURE_DIR / "competitor_source_text_records.json")],
                output_dir=temp_dir,
            )
            result = run(args)

            self.assertEqual(result["status"], "complete")
            self.assertTrue((Path(temp_dir) / "competitor_source_pack.json").exists())
            self.assertTrue((Path(temp_dir) / "competitor_source_report.md").exists())


if __name__ == "__main__":
    unittest.main()
