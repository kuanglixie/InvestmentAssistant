import json
import tempfile
import unittest
from pathlib import Path

from stock_research.alternative_data.digital_demand_monitor.agent import (
    build_alternative_data_brief,
    write_agent_outputs,
)


class AlternativeDataAgentTest(unittest.TestCase):
    def test_builds_question_oriented_brief(self):
        pack = {
            "ticker": "PDD",
            "company_name": "PDD Holdings",
            "primary_brand_id": "temu",
            "markets": ["US", "CA"],
            "metrics": [
                {
                    "brand_id": "temu",
                    "market": "US",
                    "metric_name": "android_app_rank",
                    "current_value": 5,
                    "change": -2,
                    "direction": "improving",
                    "source_type": "app",
                },
                {
                    "brand_id": "temu",
                    "market": "US",
                    "metric_name": "negative_review_share",
                    "current_value": 0.52,
                    "source_type": "review",
                },
                {
                    "brand_id": "temu",
                    "market": "CA",
                    "metric_name": "product_surface_card_count",
                    "current_value": 101,
                    "source_type": "product",
                },
                {
                    "brand_id": "temu",
                    "market": "CA",
                    "metric_name": "product_surface_median_discount_pct",
                    "current_value": 21.53,
                    "source_type": "product",
                },
                {
                    "brand_id": "shein",
                    "market": "US",
                    "metric_name": "google_ads_transparency_ad_count_lower_bound",
                    "current_value": 20000,
                    "source_type": "ad",
                },
                {
                    "brand_id": "temu",
                    "market": "US",
                    "metric_name": "google_ads_transparency_ad_count_lower_bound",
                    "current_value": 200000,
                    "source_type": "ad",
                },
            ],
            "signals": [
                {
                    "brand_id": "temu",
                    "market": "US",
                    "signal": "experience_risk_rising",
                    "severity": "high",
                    "summary": "Review risk is elevated.",
                }
            ],
        }

        brief = build_alternative_data_brief([pack])

        self.assertEqual(brief["agent_name"], "alternative_data_analyst")
        self.assertEqual(len(brief["questions"]), 5)
        self.assertIn("ad", brief["coverage"]["source_type_counts"])
        self.assertTrue(any(item["market"] == "US" for item in brief["market_watchlist"]))

    def test_writes_markdown_and_json(self):
        pack = {
            "ticker": "PDD",
            "company_name": "PDD Holdings",
            "primary_brand_id": "temu",
            "markets": ["US"],
            "metrics": [],
            "signals": [],
        }
        brief = build_alternative_data_brief([pack])
        with tempfile.TemporaryDirectory() as temp_dir:
            write_agent_outputs(temp_dir, brief)
            self.assertTrue((Path(temp_dir) / "alternative_data_brief.md").exists())
            data = json.loads((Path(temp_dir) / "alternative_data_brief.json").read_text(encoding="utf-8"))
            self.assertEqual(data["ticker"], "PDD")


if __name__ == "__main__":
    unittest.main()
