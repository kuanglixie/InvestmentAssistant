"""Build investment-relevant product signal tags from weekly metrics."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import ProductSignal, SignalPack, UnitEconomicsPack, WeeklyMetric


INVESTMENT_QUESTIONS = {
    "median_price": "Is Temu's low-price advantage sustainable?",
    "median_discount_pct": "Is Temu relying on headline discounting?",
    "coupon_availability_rate": "Is growth becoming more subsidy-driven?",
    "median_delivery_max_days": "Is fulfillment improving or worsening?",
    "total_review_count": "Are reviews and demand signals accumulating?",
    "average_rating": "Is customer trust stable?",
    "stockout_rate": "Is availability deteriorating?",
}


def _metrics_by_category(metrics: list[WeeklyMetric]) -> dict[tuple[str, str], dict[str, WeeklyMetric]]:
    grouped: dict[tuple[str, str], dict[str, WeeklyMetric]] = defaultdict(dict)
    for metric in metrics:
        grouped[(metric.period, metric.category)][metric.metric_name] = metric
    return grouped


def _severity(change: float | None, medium: float, high: float) -> str:
    if change is None:
        return "low"
    absolute = abs(change)
    if absolute >= high:
        return "high"
    if absolute >= medium:
        return "medium"
    return "low"


def _signal(metric: WeeklyMetric, tag: str, severity: str = "medium", evidence: dict[str, Any] | None = None) -> ProductSignal:
    return ProductSignal(
        company=metric.company,
        brand=metric.brand,
        period=metric.period,
        category=metric.category,
        signal=tag,
        metric=metric.metric_name,
        current_value=metric.value,
        change_1w=metric.change_1w,
        change_4w=metric.change_4w,
        investment_question=INVESTMENT_QUESTIONS.get(metric.metric_name, "What product-market signal changed?"),
        severity=severity,
        confidence=metric.confidence,
        evidence=evidence or {},
    )


def build_signal_pack(metrics: list[WeeklyMetric], company: str, brand: str, period: str | None = None) -> SignalPack:
    if not metrics:
        return SignalPack(company=company, brand=brand, period=period or "unknown", product_signals=[])
    target_period = period or max(metric.period for metric in metrics)
    grouped = _metrics_by_category([metric for metric in metrics if metric.period == target_period])
    signals: list[ProductSignal] = []

    for (_period, category), by_name in sorted(grouped.items()):
        price = by_name.get("median_price")
        discount = by_name.get("median_discount_pct")
        coupon = by_name.get("coupon_availability_rate")
        delivery = by_name.get("median_delivery_max_days")
        reviews = by_name.get("total_review_count")
        rating = by_name.get("average_rating")
        stockout = by_name.get("stockout_rate")

        price_change = price.change_4w if price else None
        discount_change = discount.change_4w if discount else None
        if price and price_change is not None:
            if price_change > 0.5 or (discount_change is not None and discount_change < -5):
                signals.append(_signal(price, "price_advantage_weakening", _severity(price_change, 0.5, 1.0), {"median_discount_pct_change_4w": discount_change}))
            elif abs(price_change) <= 0.25 and (discount_change is None or abs(discount_change) <= 5):
                signals.append(_signal(price, "price_advantage_stable", "low", {"median_discount_pct_change_4w": discount_change}))

        if coupon and coupon.change_4w is not None:
            if coupon.change_4w >= 0.10:
                signals.append(_signal(coupon, "promotion_intensity_rising", _severity(coupon.change_4w, 0.10, 0.20)))
            elif coupon.change_4w <= -0.10:
                signals.append(_signal(coupon, "promotion_intensity_falling", _severity(coupon.change_4w, 0.10, 0.20)))

        if delivery and delivery.change_4w is not None:
            if delivery.change_4w <= -1:
                signals.append(_signal(delivery, "delivery_improving", _severity(delivery.change_4w, 1, 3)))
            elif delivery.change_4w >= 1:
                signals.append(_signal(delivery, "delivery_worsening", _severity(delivery.change_4w, 1, 3)))

        if reviews and reviews.change_1w is not None and reviews.change_4w is not None:
            four_week_weekly = reviews.change_4w / 4 if reviews.change_4w else 0
            if reviews.change_1w > four_week_weekly * 1.25:
                signals.append(_signal(reviews, "review_growth_accelerating", "medium", {"four_week_weekly_growth": four_week_weekly}))
            elif reviews.change_1w < four_week_weekly * 0.75:
                signals.append(_signal(reviews, "review_growth_slowing", "medium", {"four_week_weekly_growth": four_week_weekly}))

        if rating and rating.change_4w is not None:
            if rating.change_4w <= -0.10:
                signals.append(_signal(rating, "rating_deteriorating", _severity(rating.change_4w, 0.10, 0.25)))
            elif abs(rating.change_4w) < 0.05:
                signals.append(_signal(rating, "rating_stable", "low"))

        if stockout and stockout.change_4w is not None and stockout.change_4w >= 0.05:
            signals.append(_signal(stockout, "stockout_rate_rising", _severity(stockout.change_4w, 0.05, 0.15)))

    return SignalPack(company=company, brand=brand, period=target_period, product_signals=signals)


def build_unit_economics_pack(metrics: list[WeeklyMetric], company: str, brand: str, period: str | None = None, category: str = "all") -> UnitEconomicsPack:
    target_period = period or (max(metric.period for metric in metrics) if metrics else "unknown")
    selected = {
        metric.metric_name: metric.value
        for metric in metrics
        if metric.period == target_period and metric.category == category
    }
    return UnitEconomicsPack(
        company=company,
        brand=brand,
        period=target_period,
        unit_economics_proxies={
            "coupon_availability_rate": selected.get("coupon_availability_rate"),
            "median_coupon_value": selected.get("median_coupon_value"),
            "median_discount_pct": selected.get("median_discount_pct"),
            "shipping_fee_rate": selected.get("shipping_fee_rate"),
            "median_delivery_max_days": selected.get("median_delivery_max_days"),
        },
    )
