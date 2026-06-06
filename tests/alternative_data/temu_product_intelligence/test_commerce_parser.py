from datetime import datetime, timezone
from pathlib import Path
import unittest

from stock_research.alternative_data.temu_product_intelligence.commerce_parser import GenericCommerceProductParser
from stock_research.alternative_data.temu_product_intelligence.models import ProductConfig, RawFetchResult


FIXTURE_DIR = Path(__file__).parent / "fixtures"


class GenericCommerceProductParserTest(unittest.TestCase):
    def test_parse_jsonld_product_page(self) -> None:
        html = (FIXTURE_DIR / "generic_product_jsonld_sample.html").read_text(encoding="utf-8")
        product = ProductConfig(
            tracking_id="amazon_kitchen_001",
            category="kitchen",
            url="https://www.amazon.com/dp/B0TEST1234",
        )
        fetch = RawFetchResult(
            tracking_id=product.tracking_id,
            url=product.url,
            final_url=product.url,
            fetched_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            html=html,
            status_code=200,
        )

        snapshot = GenericCommerceProductParser().parse(product, fetch)

        self.assertTrue(snapshot.parse_success)
        self.assertEqual(snapshot.product_id, "B0TEST1234")
        self.assertEqual(snapshot.title, "Silicone Kitchen Utensil Set, 12 Piece")
        self.assertEqual(snapshot.price, 14.99)
        self.assertEqual(snapshot.list_price, 19.99)
        self.assertEqual(snapshot.discount_pct, 25.01)
        self.assertEqual(snapshot.rating, 4.5)
        self.assertEqual(snapshot.review_count, 2140)
        self.assertEqual(snapshot.delivery_min_days, 3)
        self.assertEqual(snapshot.delivery_max_days, 5)
        self.assertEqual(snapshot.shipping_fee, 0.0)
        self.assertEqual(snapshot.stock_status, "in_stock")
        self.assertEqual(snapshot.raw_payload_json["source_platform"], "amazon")


if __name__ == "__main__":
    unittest.main()
