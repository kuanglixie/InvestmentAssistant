import json
import tempfile
import unittest
from pathlib import Path

from stock_research.alternative_data.merchant_regulatory_monitor.run_snapshot import main


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = Path(__file__).parent / "fixtures"


class MerchantRegulatorySnapshotTest(unittest.TestCase):
    def test_run_snapshot_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            status = main(
                [
                    "--source-plan",
                    str(PROJECT_ROOT / "config" / "alternative_data" / "merchant_regulatory_monitor" / "source_plan.v1.json"),
                    "--merchant-text-json",
                    str(FIXTURE_DIR / "merchant_policy_sample.json"),
                    "--merchant-html-file",
                    str(FIXTURE_DIR / "merchant_policy_sample.html"),
                    "--cpsc-json",
                    str(FIXTURE_DIR / "cpsc_recalls_sample.json"),
                    "--query-term",
                    "temu",
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(status, 0)
            events_path = output_dir / "merchant_regulatory_events.json"
            summary_path = output_dir / "merchant_regulatory_summary.json"
            markdown_path = output_dir / "merchant_regulatory_summary.md"
            self.assertTrue(events_path.exists())
            self.assertTrue(summary_path.exists())
            self.assertTrue(markdown_path.exists())
            events = json.loads(events_path.read_text(encoding="utf-8"))
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(events), 3)
            self.assertGreaterEqual(summary["high_severity_count"], 1)


if __name__ == "__main__":
    unittest.main()
