"""Weekly metric aggregation for fixed-basket Temu snapshots."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from .models import WeeklyMetric
from .normalizer import iso_week_period, median_or_none, rate, trend_direction
from .storage import ProductStore


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _latest_by_product(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row["product_tracking_id"]
        if key not in latest or row["collected_at"] > latest[key]["collected_at"]:
            latest[key] = row
    return list(latest.values())


def _metric_values(rows: list[dict[str, Any]]) -> dict[str, float | None]:
    active = [row for row in rows if row.get("parse_success")]
    total = len(rows)
    if not rows:
        return {}

    review_counts = [row.get("review_count") or 0 for row in active]
    stockouts = [row.get("stock_status") == "out_of_stock" for row in rows]
    shipping_fee_positive = [(row.get("shipping_fee") or 0) > 0 for row in active]

    return {
        "median_price": median_or_none(row.get("price") for row in active),
        "median_discount_pct": median_or_none(row.get("discount_pct") for row in active),
        "coupon_availability_rate": rate(bool(row.get("coupon_available")) for row in active),
        "median_coupon_value": median_or_none(row.get("coupon_value") for row in active if row.get("coupon_available")),
        "median_delivery_min_days": median_or_none(row.get("delivery_min_days") for row in active),
        "median_delivery_max_days": median_or_none(row.get("delivery_max_days") for row in active),
        "average_rating": (
            sum(float(row["rating"]) for row in active if row.get("rating") is not None)
            / max(1, sum(1 for row in active if row.get("rating") is not None))
            if any(row.get("rating") is not None for row in active)
            else None
        ),
        "total_review_count": float(sum(review_counts)) if review_counts else None,
        "active_product_rate": len(active) / total if total else None,
        "stockout_rate": rate(stockouts),
        "shipping_fee_rate": rate(shipping_fee_positive),
        "category_coverage": float(len({row.get("category") for row in active})),
    }


def _confidence(rows: list[dict[str, Any]]) -> str:
    count = len([row for row in rows if row.get("parse_success")])
    if count >= 20:
        return "high"
    if count >= 5:
        return "medium"
    return "low"


def aggregate_weekly(store: ProductStore, company: str, brand: str) -> list[WeeklyMetric]:
    raw_rows = [dict(row) for row in store.snapshot_rows()]
    if not raw_rows:
        return []

    rows_by_period_category: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    rows_by_period_all: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in raw_rows:
        row["collected_dt"] = _parse_dt(row["collected_at"])
        row["period"] = iso_week_period(row["collected_dt"])
        rows_by_period_category[(row["period"], row["category"])].append(row)
        rows_by_period_all[row["period"]].append(row)

    periods = sorted(rows_by_period_all)
    metrics_by_key: dict[tuple[str, str, str], float | None] = {}
    row_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for period in periods:
        all_rows = _latest_by_product(rows_by_period_all[period])
        row_groups[(period, "all")] = all_rows
        for metric_name, value in _metric_values(all_rows).items():
            metrics_by_key[(period, "all", metric_name)] = value

    for (period, category), rows in rows_by_period_category.items():
        latest_rows = _latest_by_product(rows)
        row_groups[(period, category)] = latest_rows
        for metric_name, value in _metric_values(latest_rows).items():
            metrics_by_key[(period, category, metric_name)] = value

    category_periods = sorted({(period, category) for period, category, _ in metrics_by_key})
    output: list[WeeklyMetric] = []

    for period, category in category_periods:
        period_index = periods.index(period)
        previous_period = periods[period_index - 1] if period_index >= 1 else None
        four_week_period = periods[period_index - 4] if period_index >= 4 else None

        metric_names = sorted(name for p, c, name in metrics_by_key if p == period and c == category)
        for metric_name in metric_names:
            value = metrics_by_key[(period, category, metric_name)]
            prev = metrics_by_key.get((previous_period, category, metric_name)) if previous_period else None
            prev4 = metrics_by_key.get((four_week_period, category, metric_name)) if four_week_period else None
            change_1w = value - prev if value is not None and prev is not None else None
            change_4w = value - prev4 if value is not None and prev4 is not None else None
            output.append(
                WeeklyMetric(
                    company=company,
                    brand=brand,
                    period=period,
                    category=category,
                    metric_name=metric_name,
                    value=value,
                    change_1w=change_1w,
                    change_4w=change_4w,
                    trend_direction=trend_direction(change_4w if change_4w is not None else change_1w),
                    confidence=_confidence(row_groups.get((period, category), [])),
                )
            )

    return output
