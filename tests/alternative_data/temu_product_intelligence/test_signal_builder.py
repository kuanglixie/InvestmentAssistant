import unittest

from stock_research.alternative_data.temu_product_intelligence.models import WeeklyMetric
from stock_research.alternative_data.temu_product_intelligence.signal_builder import (
    build_signal_pack,
    build_unit_economics_pack,
)


def metric(name, value, change_1w=None, change_4w=None):
    return WeeklyMetric(
        company="PDD",
        brand="Temu",
        period="2026-W22",
        category="all",
        metric_name=name,
        value=value,
        change_1w=change_1w,
        change_4w=change_4w,
        trend_direction="up",
        confidence="medium",
    )


class ProductSignalBuilderTest(unittest.TestCase):
    def test_build_signal_pack(self) -> None:
        pack = build_signal_pack(
            [
                metric("coupon_availability_rate", 0.48, change_4w=0.12),
                metric("median_delivery_max_days", 11, change_4w=2.0),
                metric("average_rating", 4.2, change_4w=-0.2),
            ],
            company="PDD",
            brand="Temu",
            period="2026-W22",
        )

        signals = {signal.signal for signal in pack.product_signals}
        self.assertIn("promotion_intensity_rising", signals)
        self.assertIn("delivery_worsening", signals)
        self.assertIn("rating_deteriorating", signals)

    def test_build_unit_economics_pack(self) -> None:
        pack = build_unit_economics_pack(
            [
                metric("coupon_availability_rate", 0.48),
                metric("median_coupon_value", 1.25),
                metric("median_discount_pct", 57.6),
                metric("shipping_fee_rate", 0.08),
                metric("median_delivery_max_days", 9),
            ],
            company="PDD",
            brand="Temu",
            period="2026-W22",
        )

        self.assertEqual(pack.unit_economics_proxies["coupon_availability_rate"], 0.48)
        self.assertEqual(pack.unit_economics_proxies["median_delivery_max_days"], 9)


if __name__ == "__main__":
    unittest.main()
