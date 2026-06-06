import json
import unittest
from pathlib import Path

from stock_research.alternative_data.merchant_regulatory_monitor.normalizer import (
    build_summary,
    classify_topics,
    normalize_cpsc_recalls,
    normalize_text_record,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"


class MerchantRegulatoryNormalizerTest(unittest.TestCase):
    def test_classify_topics(self) -> None:
        topics = classify_topics("Sellers use Product Ads, pay fees, and face refund disputes.")
        self.assertIn("ads_traffic", topics)
        self.assertIn("seller_fees", topics)
        self.assertIn("returns_refunds", topics)

    def test_classify_topics_avoids_substring_false_positive(self) -> None:
        topics = classify_topics("It feels like seller growth is just getting started.")
        self.assertNotIn("seller_fees", topics)

    def test_normalize_text_record_emits_merchant_events(self) -> None:
        payload = json.loads((FIXTURE_DIR / "merchant_policy_sample.json").read_text(encoding="utf-8"))
        events = []
        for record in payload["records"]:
            events.extend(normalize_text_record(record))

        topics = {event.topic for event in events}
        self.assertIn("ads_traffic", topics)
        self.assertIn("logistics_fulfillment", topics)
        self.assertIn("payout_cashflow", topics)
        self.assertTrue(any(event.source_confidence == "low" for event in events if event.source_group == "merchant_voice"))

    def test_normalize_cpsc_recalls_filters_to_temu_product_safety(self) -> None:
        payload = json.loads((FIXTURE_DIR / "cpsc_recalls_sample.json").read_text(encoding="utf-8"))
        events = normalize_cpsc_recalls(payload, query_terms=["temu"])

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].topic, "product_safety")
        self.assertEqual(events[0].severity, "high")
        self.assertEqual(events[0].source_group, "regulatory_product_safety")

    def test_build_summary_adds_investment_questions(self) -> None:
        payload = json.loads((FIXTURE_DIR / "merchant_policy_sample.json").read_text(encoding="utf-8"))
        events = []
        for record in payload["records"]:
            events.extend(normalize_text_record(record))
        summary = build_summary(events)

        self.assertGreater(summary.event_count, 0)
        self.assertIn("ads_traffic", summary.topic_counts)
        self.assertTrue(any("merchant economics" in question.lower() for question in summary.investment_questions))


if __name__ == "__main__":
    unittest.main()
