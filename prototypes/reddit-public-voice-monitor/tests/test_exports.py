from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from reddit_public_voice.exports import (
    build_reddit_summary,
    export_demand_monitor_reviews,
    findings_from_json_payload,
    load_json,
    reddit_evidence_items,
)
from reddit_public_voice.run_snapshot import run


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "public_voice_findings_sample.json"


class RedditPublicVoiceExportTest(unittest.TestCase):
    def test_exports_reddit_items_as_demand_monitor_reviews(self) -> None:
        findings = findings_from_json_payload(load_json(FIXTURE))
        items = reddit_evidence_items(findings)
        reviews = export_demand_monitor_reviews(items)

        self.assertEqual(len(items), 2)
        self.assertEqual(len(reviews), 2)
        self.assertEqual(reviews[0]["platform"], "reddit")
        self.assertEqual(reviews[0]["market"], "GLOBAL")
        self.assertEqual(reviews[0]["topic"], "delivery_delay")
        self.assertEqual(reviews[0]["sentiment"], "negative")
        self.assertEqual(reviews[0]["source_context"], "brand_subreddit")
        self.assertEqual(reviews[1]["topic"], "pricing_coupon")
        self.assertEqual(reviews[1]["sentiment"], "positive")

    def test_build_summary_counts_reddit_only(self) -> None:
        findings = load_json(FIXTURE)
        items = reddit_evidence_items(findings)
        summary = build_reddit_summary(findings, items)

        self.assertEqual(summary["reddit_evidence_item_count"], 2)
        self.assertEqual(summary["theme_counts"]["shipping_delivery"], 1)
        self.assertEqual(summary["relevance_counts"]["brand_subreddit"], 2)
        self.assertEqual(summary["subreddit_counts"]["TemuThings"], 1)
        self.assertEqual(summary["source_results"][0]["comments_collected"], 3)

    def test_run_snapshot_writes_bridge_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run(
                Namespace(
                    state_json=str(FIXTURE),
                    findings_json=None,
                    live_collect=False,
                    offline=False,
                    registry="",
                    cache_root="",
                    output_dir=tmpdir,
                    brand_id="temu",
                    market="US",
                    max_items=None,
                )
            )
            self.assertEqual(result["demand_monitor_reviews"], 2)
            reviews_path = Path(tmpdir) / "demand_monitor_reviews.json"
            self.assertTrue(reviews_path.exists())
            reviews = json.loads(reviews_path.read_text(encoding="utf-8"))
            self.assertEqual(reviews[0]["source_name"], "reddit_public_voice")


if __name__ == "__main__":
    unittest.main()
