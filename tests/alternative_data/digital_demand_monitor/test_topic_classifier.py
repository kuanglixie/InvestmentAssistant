import unittest

from stock_research.alternative_data.digital_demand_monitor.topic_classifier import classify_sentiment, classify_topic


class TopicClassifierTest(unittest.TestCase):
    def test_delivery_topic(self):
        self.assertEqual(classify_topic("Order was delayed for weeks and tracking failed"), "delivery_delay")

    def test_refund_topic(self):
        self.assertEqual(classify_topic("Refund and return support was terrible"), "refund_return")

    def test_sentiment_rating_wins(self):
        self.assertEqual(classify_sentiment("good app", rating=1), "negative")


if __name__ == "__main__":
    unittest.main()
