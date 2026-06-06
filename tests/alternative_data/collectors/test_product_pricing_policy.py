import argparse
import json
import tempfile
import unittest
from pathlib import Path

from stock_research.alternative_data.collectors.product_pricing_policy import build_product_pricing_policy_pack
from stock_research.alternative_data.collectors.run_product_pricing_policy import run


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_json(name: str):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class ProductPricingPolicyCollectorTest(unittest.TestCase):
    def test_build_pack_emits_product_and_policy_findings(self) -> None:
        pack = build_product_pricing_policy_pack(
            product_snapshots=load_json("target_snapshots.json"),
            product_metrics=load_json("product_weekly_metrics.json"),
            product_signal_pack=load_json("product_signal_pack.json"),
            unit_economics_pack=load_json("unit_economics_pack.json"),
            policy_events=load_json("policy_events.json"),
        )

        finding_ids = {finding.finding_id for finding in pack.findings}
        self.assertIn("promotion_intensity_watch", finding_ids)
        self.assertIn("delivery_promise_watch", finding_ids)
        self.assertIn("merchant_policy_pressure_watch", finding_ids)
        self.assertTrue(any(metric["metric_name"] == "median_discount_pct" for metric in pack.metrics))
        self.assertEqual(len(pack.events), 2)

    def test_cli_run_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args = argparse.Namespace(
                company="PDD",
                brand="Temu",
                source_plan="source_plan",
                product_snapshots_json=str(FIXTURE_DIR / "target_snapshots.json"),
                product_metrics_json=str(FIXTURE_DIR / "product_weekly_metrics.json"),
                product_signal_pack_json=str(FIXTURE_DIR / "product_signal_pack.json"),
                unit_economics_json=str(FIXTURE_DIR / "unit_economics_pack.json"),
                policy_events_json=str(FIXTURE_DIR / "policy_events.json"),
                output_dir=temp_dir,
            )
            result = run(args)

            self.assertEqual(result["status"], "complete")
            self.assertTrue((Path(temp_dir) / "product_pricing_policy_pack.json").exists())
            self.assertTrue((Path(temp_dir) / "product_pricing_policy_report.md").exists())


if __name__ == "__main__":
    unittest.main()
