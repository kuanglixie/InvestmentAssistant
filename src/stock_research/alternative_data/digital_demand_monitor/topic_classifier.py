"""Rule-based Temu review topic and sentiment classification."""

from __future__ import annotations

import re


TOPIC_KEYWORDS: dict[str, list[str]] = {
    "delivery_delay": ["late", "delay", "delayed", "shipping", "delivery", "arrived", "weeks", "tracking"],
    "refund_return": ["refund", "return", "returned", "chargeback", "money back", "cancel"],
    "product_quality": ["quality", "broken", "cheap", "defective", "damaged", "fake", "material"],
    "trust_scam": ["scam", "fraud", "unsafe", "stolen", "counterfeit", "suspicious", "trust", "deceptive", "lie", "lies", "bait", "falso", "mentira", "estafaron"],
    "customs_tax": ["customs", "duty", "import fee", "tax", "tariff", "border"],
    "payment_issue": ["payment", "card", "paypal", "charged", "billing", "checkout"],
    "customer_service": ["support", "service", "agent", "help", "chat", "response"],
    "app_bug": ["bug", "crash", "freeze", "login", "log in", "error", "glitch", "app", "wishlist", "unusable"],
    "ads_promotion": ["ads", "ad", "advertising", "notification", "spam", "promo", "popup", "pop up", "intrusive", "animation", "spin", "wheel"],
    "pricing_coupon": ["coupon", "discount", "price", "pricing", "deal", "promo code", "free gift", "gift", "claim", "redeem", "reward", "gimmick", "offer"],
}

NEGATIVE_WORDS = [
    "bad",
    "terrible",
    "awful",
    "worst",
    "never",
    "scam",
    "fake",
    "broken",
    "late",
    "refund",
    "defective",
    "angry",
    "disappointed",
]

POSITIVE_WORDS = [
    "great",
    "good",
    "excellent",
    "love",
    "fast",
    "cheap",
    "happy",
    "useful",
    "smooth",
]


def classify_topic(text: str, default: str = "other") -> str:
    normalized = text.lower()
    scores: dict[str, int] = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            score += len(re.findall(r"\b" + re.escape(keyword) + r"\b", normalized))
        if score:
            scores[topic] = score
    if not scores:
        return default
    return max(scores.items(), key=lambda item: item[1])[0]


def classify_sentiment(text: str, rating: float | None = None) -> str:
    if rating is not None:
        if rating <= 2:
            return "negative"
        if rating >= 4:
            return "positive"
    normalized = text.lower()
    negative = sum(1 for word in NEGATIVE_WORDS if re.search(r"\b" + re.escape(word) + r"\b", normalized))
    positive = sum(1 for word in POSITIVE_WORDS if re.search(r"\b" + re.escape(word) + r"\b", normalized))
    if negative > positive:
        return "negative"
    if positive > negative:
        return "positive"
    return "neutral"
