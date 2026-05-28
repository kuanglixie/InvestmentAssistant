from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from statistics import mean, median, pstdev
from typing import Any

from stock_research.alternative_data.models import NormalizedMetric


def period_for_date(date_value: str, *, time_window: str) -> str:
    parsed = _parse_date(date_value)
    if time_window == "weekly":
        year, week, _weekday = parsed.isocalendar()
        return f"{year}-W{week:02d}"
    if time_window == "daily":
        return parsed.isoformat()
    if time_window == "monthly":
        return f"{parsed.year}-{parsed.month:02d}"
    return parsed.isoformat()


def aggregate_metric_series(metrics: list[NormalizedMetric]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[NormalizedMetric]] = defaultdict(list)
    for metric in metrics:
        key = (
            metric.get("company", ""),
            metric.get("brand", ""),
            metric.get("metric_name", ""),
            metric.get("region", ""),
        )
        grouped[key].append(metric)

    summaries = []
    for (company, brand, metric_name, region), rows in sorted(grouped.items()):
        ordered = sorted(rows, key=lambda item: str(item.get("period", "")))
        values = [float(item["value"]) for item in ordered if isinstance(item.get("value"), int | float)]
        if not values:
            continue
        current = values[-1]
        summaries.append(
            {
                "company": company,
                "brand": brand,
                "metric_name": metric_name,
                "region": region,
                "period": ordered[-1].get("period"),
                "current": current,
                "unit": ordered[-1].get("unit"),
                "source": ordered[-1].get("source"),
                "confidence": _lowest_confidence([str(item.get("confidence", "low")) for item in ordered]),
                "change_1w": _change(values, 1),
                "change_4w": _change(values, 4),
                "change_13w": _change(values, 13),
                "percentile_52w": _percentile(values[-52:], current),
                "z_score_52w": _z_score(values[-52:], current),
                "interpretation_hint": _interpretation_hint(metric_name, values),
                "sample_size": len(values),
            }
        )
    return summaries


def _parse_date(date_value: str) -> date:
    if "T" in date_value:
        return datetime.fromisoformat(date_value.replace("Z", "+00:00")).date()
    return date.fromisoformat(date_value[:10])


def _change(values: list[float], periods: int) -> float | None:
    if len(values) <= periods:
        return None
    previous = values[-1 - periods]
    if previous == 0:
        return None
    return (values[-1] - previous) / previous


def _percentile(values: list[float], current: float) -> float | None:
    if not values:
        return None
    below_or_equal = sum(1 for value in values if value <= current)
    return below_or_equal / len(values)


def _z_score(values: list[float], current: float) -> float | None:
    if len(values) < 2:
        return None
    std = pstdev(values)
    if std == 0:
        return None
    return (current - mean(values)) / std


def _lowest_confidence(confidences: list[str]) -> str:
    order = {"high": 3, "medium": 2, "low": 1}
    return min(confidences, key=lambda item: order.get(item, 0)) if confidences else "low"


def _interpretation_hint(metric_name: str, values: list[float]) -> str | None:
    if len(values) < 5:
        return None
    recent = median(values[-4:])
    prior = median(values[-8:-4]) if len(values) >= 8 else median(values[:-4])
    if prior == 0:
        return None
    change = (recent - prior) / prior
    if "coupon" in metric_name or "discount" in metric_name:
        if change > 0.1:
            return "promotion_intensity_rising"
        if change < -0.1:
            return "promotion_intensity_falling"
    if "negative_keyword" in metric_name or metric_name.endswith(".refund") or metric_name.endswith(".scam"):
        if change > 0.1:
            return "negative_signal_rising"
        if change < -0.1:
            return "negative_signal_falling"
    if change > 0.1:
        return "activity_rising"
    if change < -0.1:
        return "activity_falling"
    return "stable"
