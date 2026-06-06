import unittest

from stock_research.alternative_data.digital_demand_monitor.models import (
    BrandConfig,
    DemandMetric,
    WatchlistConfig,
)
from stock_research.alternative_data.digital_demand_monitor.signal_builder import build_signals


def watchlist() -> WatchlistConfig:
    return WatchlistConfig(
        company_id="pdd",
        ticker="PDD",
        company_name="PDD",
        primary_brand_id="temu",
        markets=["US"],
        brands=[BrandConfig(brand_id="temu", display_name="Temu")],
    )


def metric(name: str, current: float | None, source_type: str = "review", change: float | None = None) -> DemandMetric:
    return DemandMetric(
        company_id="pdd",
        ticker="PDD",
        brand_id="temu",
        market="US",
        metric_name=name,
        current_value=current,
        previous_value=current - change if current is not None and change is not None else None,
        change=change,
        change_pct=None,
        direction="worsening" if change and change < 0 else "unknown",
        source_type=source_type,
        confidence="low" if source_type == "review" else "medium",
    )


class ComplaintLeadTest(unittest.TestCase):
    def test_ugc_only_creates_low_confidence_watchlist_not_experience_risk(self) -> None:
        signals = build_signals(
            [
                metric("negative_review_share", 0.50),
                metric("negative_review_topic_share:refund_return", 0.22),
            ],
            watchlist(),
        )

        by_name = {signal.signal: signal for signal in signals}
        self.assertIn("complaint_topic_watchlist", by_name)
        self.assertEqual(by_name["complaint_topic_watchlist"].status, "lead_only")
        self.assertEqual(by_name["complaint_topic_watchlist"].confidence, "low")
        self.assertNotIn("experience_risk_rising", by_name)

    def test_complaint_topics_upgrade_when_corroborated_by_rating_decline(self) -> None:
        signals = build_signals(
            [
                metric("negative_review_share", 0.50),
                metric("negative_review_topic_share:refund_return", 0.22),
                metric("ios_app_rating", 4.45, source_type="app", change=-0.08),
            ],
            watchlist(),
        )

        by_name = {signal.signal: signal for signal in signals}
        self.assertIn("complaint_topic_watchlist", by_name)
        self.assertIn("experience_risk_rising", by_name)
        self.assertIn("app_rating_down", by_name["experience_risk_rising"].drivers)


if __name__ == "__main__":
    unittest.main()
