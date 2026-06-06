import unittest

from stock_research.alternative_data.temu_product_intelligence.normalizer import (
    compute_discount_pct,
    parse_count,
    parse_delivery_days,
    parse_money,
)


class NormalizerTest(unittest.TestCase):
    def test_parse_money(self) -> None:
        self.assertEqual(parse_money("$4.99"), 4.99)
        self.assertEqual(parse_money("USD 1,234.50"), 1234.50)
        self.assertIsNone(parse_money(None))

    def test_parse_count(self) -> None:
        self.assertEqual(parse_count("1,832 reviews"), 1832)
        self.assertEqual(parse_count("10K+ sold"), 10000)
        self.assertEqual(parse_count("3.5M ratings"), 3500000)

    def test_parse_delivery_days(self) -> None:
        self.assertEqual(parse_delivery_days("Delivery 6-10 days"), (6, 10))
        self.assertEqual(parse_delivery_days("Arrives in 5 to 8 days"), (5, 8))

    def test_compute_discount_pct(self) -> None:
        self.assertEqual(compute_discount_pct(4.99, 12.99), 61.59)
        self.assertIsNone(compute_discount_pct(12.99, 4.99))


if __name__ == "__main__":
    unittest.main()
