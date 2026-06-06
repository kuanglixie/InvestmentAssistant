from datetime import datetime, timezone
from pathlib import Path
import unittest

from stock_research.alternative_data.temu_product_intelligence.models import BasketConfig, ProductConfig, RawFetchResult
from stock_research.alternative_data.temu_product_intelligence.surface import build_surface_snapshot, surface_metric_rows


FIXTURE_DIR = Path(__file__).parent / "fixtures"


class SurfaceSnapshotTest(unittest.TestCase):
    def test_build_surface_snapshot_from_feed_cards(self) -> None:
        html = (FIXTURE_DIR / "temu_feed_surface_sample.html").read_text(encoding="utf-8")
        product = ProductConfig(
            tracking_id="temu_surface_us_001",
            category="kitchen",
            url="https://www.temu.com/us/feed.html",
        )
        fetch = RawFetchResult(
            tracking_id=product.tracking_id,
            url=product.url,
            fetched_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
            final_url=product.url,
            html=html,
            status_code=200,
        )
        basket = BasketConfig(region="US", currency="USD", products=[product])

        surface = build_surface_snapshot(
            basket=basket,
            product=product,
            fetch=fetch,
            collected_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
        )

        self.assertEqual(surface.card_count, 2)
        self.assertEqual(surface.unique_product_count, 2)
        self.assertEqual(surface.priced_card_count, 2)
        self.assertEqual(surface.median_price, 3.745)
        self.assertEqual(surface.median_discount_pct, 56.0)
        self.assertEqual(surface.discount_card_rate, 1.0)
        self.assertEqual(surface.free_shipping_rate, 0.5)
        self.assertEqual(surface.promo_messages[:2], ["Get $100 coupon bundle!", "$100 coupon"])
        self.assertEqual(surface.cards[0].product_id, "601111111111111")
        self.assertEqual(surface.cards[0].sold_count_estimate, 10000)

    def test_surface_metric_rows_are_demand_monitor_compatible(self) -> None:
        html = (FIXTURE_DIR / "temu_feed_surface_sample.html").read_text(encoding="utf-8")
        product = ProductConfig(
            tracking_id="temu_surface_us_001",
            category="kitchen",
            url="https://www.temu.com/us/feed.html",
        )
        fetch = RawFetchResult(
            tracking_id=product.tracking_id,
            url=product.url,
            fetched_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
            final_url=product.url,
            html=html,
            status_code=200,
        )
        surface = build_surface_snapshot(
            BasketConfig(region="US", currency="USD", products=[product]),
            product,
            fetch,
            collected_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
        )

        rows = surface_metric_rows([surface])

        self.assertGreaterEqual(
            {row["metric_name"] for row in rows},
            {
                "surface_card_count",
                "surface_median_price",
                "surface_discount_card_rate",
            },
        )
        self.assertEqual(rows[0]["market"], "US")
        self.assertEqual(rows[0]["period"], "2026-W22")


if __name__ == "__main__":
    unittest.main()
