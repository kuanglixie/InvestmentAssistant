from datetime import datetime, timezone
from pathlib import Path
import unittest

from stock_research.alternative_data.temu_product_intelligence.models import ProductConfig, RawFetchResult
from stock_research.alternative_data.temu_product_intelligence.parser import TemuProductParser


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _fetch_result(name: str) -> RawFetchResult:
    html = (FIXTURE_DIR / name).read_text(encoding="utf-8")
    return RawFetchResult(
        tracking_id="temu_kitchen_001",
        url=f"fixture://{name}",
        fetched_at=datetime(2026, 5, 27, tzinfo=timezone.utc),
        final_url=f"fixture://{name}",
        html=html,
        status_code=200,
    )


class TemuProductParserTest(unittest.TestCase):
    def test_parse_sample_product(self) -> None:
        product = ProductConfig(
            tracking_id="temu_kitchen_001",
            category="kitchen",
            url="fixture://temu_product_sample.html",
        )
        snapshot = TemuProductParser().parse(product, _fetch_result("temu_product_sample.html"))

        self.assertTrue(snapshot.parse_success)
        self.assertEqual(snapshot.title, "Silicone Kitchen Utensil Set - Heat Resistant")
        self.assertEqual(snapshot.price, 4.99)
        self.assertEqual(snapshot.list_price, 12.99)
        self.assertEqual(snapshot.discount_pct, 62.0)
        self.assertIs(snapshot.coupon_available, True)
        self.assertEqual(snapshot.coupon_value, 2.0)
        self.assertEqual(snapshot.rating, 4.6)
        self.assertEqual(snapshot.review_count, 1832)
        self.assertEqual(snapshot.sold_count_estimate, 10000)
        self.assertEqual(snapshot.delivery_min_days, 6)
        self.assertEqual(snapshot.delivery_max_days, 10)
        self.assertEqual(snapshot.shipping_fee, 0.0)
        self.assertEqual(snapshot.stock_status, "in_stock")
        self.assertEqual(snapshot.seller_name, "Value Home Store")

    def test_parse_variant_no_coupon(self) -> None:
        product = ProductConfig(
            tracking_id="temu_tools_002",
            category="tools",
            url="fixture://temu_product_variant.html",
        )
        snapshot = TemuProductParser().parse(product, _fetch_result("temu_product_variant.html"))

        self.assertTrue(snapshot.parse_success)
        self.assertEqual(snapshot.price, 2.79)
        self.assertEqual(snapshot.rating, 4.4)
        self.assertEqual(snapshot.review_count, 947)
        self.assertIs(snapshot.coupon_available, False)
        self.assertEqual(snapshot.delivery_min_days, 5)
        self.assertEqual(snapshot.delivery_max_days, 8)


if __name__ == "__main__":
    unittest.main()
