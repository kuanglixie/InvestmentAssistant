import argparse
import json
import tempfile
import unittest
from pathlib import Path

from stock_research.alternative_data.digital_demand_monitor.run_monitor import config_root, run_pipeline


class PipelineTest(unittest.TestCase):
    def test_fixture_pipeline_outputs_signals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            args = argparse.Namespace(
                watchlist=str(config_root() / "watchlists" / "pdd_temu.yaml"),
                db=str(temp / "demand.sqlite"),
                output_dir=str(temp / "latest"),
                app_snapshots_json=None,
                reviews_json=None,
                search_csv=None,
                web_csv=None,
                ads_csv=None,
                product_metrics_json=None,
                use_fixtures=True,
                live_apple_lookup=False,
                live_apple_rss_rank=False,
                live_apple_reviews=False,
                apple_review_pages=1,
                live_google_play_details=False,
                live_google_play_visible_reviews=False,
                live_tranco_web_rank=False,
                reset_db=False,
                markets=None,
            )
            result = run_pipeline(args)
            self.assertEqual(result["status"], "complete")
            pack_path = temp / "latest" / "demand_signal_pack.json"
            report_path = temp / "latest" / "weekly_demand_report.md"
            self.assertTrue(pack_path.exists())
            self.assertTrue(report_path.exists())
            pack = json.loads(pack_path.read_text(encoding="utf-8"))
            signals = {item["signal"] for item in pack["signals"]}
            self.assertIn("demand_accelerating", signals)
            self.assertIn("complaint_topic_watchlist", signals)
            self.assertIn("experience_risk_rising", signals)
            self.assertIn("promotion_driven_growth", signals)
            review_metrics = [metric for metric in pack["metrics"] if metric["source_type"] == "review"]
            self.assertTrue(review_metrics)
            self.assertTrue(all(metric["confidence"] == "low" for metric in review_metrics))


if __name__ == "__main__":
    unittest.main()
