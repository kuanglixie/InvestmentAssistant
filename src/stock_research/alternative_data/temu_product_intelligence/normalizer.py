"""Normalization helpers for product-page values."""

from __future__ import annotations

import re
from datetime import datetime
from statistics import median
from typing import Iterable


_COUNT_MULTIPLIERS = {
    "k": 1_000,
    "m": 1_000_000,
    "b": 1_000_000_000,
}


def parse_money(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = str(value).strip()
    match = re.search(r"([$€£]?\s*)?([0-9][0-9,]*(?:\.[0-9]+)?)", text)
    if not match:
        return None
    return round(float(match.group(2).replace(",", "")), 2)


def parse_percent(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", str(value))
    return float(match.group(1)) if match else None


def compute_discount_pct(price: float | None, list_price: float | None) -> float | None:
    if price is None or list_price is None or list_price <= 0 or price > list_price:
        return None
    return round((list_price - price) / list_price * 100, 2)


def parse_count(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).lower().replace(",", "").strip()
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([kmb])?\+?", text)
    if not match:
        return None
    number = float(match.group(1))
    multiplier = _COUNT_MULTIPLIERS.get(match.group(2) or "", 1)
    return int(number * multiplier)


def parse_delivery_days(text: str, collected_at: datetime | None = None) -> tuple[int | None, int | None]:
    normalized = " ".join(text.split())

    patterns = [
        r"(?:delivery|arrives?|arrival|ships?)\D{0,40}([0-9]{1,2})\s*(?:-|to|~)\s*([0-9]{1,2})\s*days?",
        r"([0-9]{1,2})\s*(?:-|to|~)\s*([0-9]{1,2})\s*(?:business\s*)?days?",
        r"(?:delivery|arrives?|arrival|ships?)\D{0,40}([0-9]{1,2})\s*(?:business\s*)?days?",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            first = int(match.group(1))
            second = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else first
            return min(first, second), max(first, second)

    if collected_at:
        date_match = re.search(
            r"(?:arrives?|delivery)\D{0,40}([A-Z][a-z]{2,8})\.?\s+([0-9]{1,2})\s*(?:-|to)\s*([A-Z][a-z]{2,8})?\.?\s*([0-9]{1,2})?",
            normalized,
        )
        if date_match:
            try:
                start_month = date_match.group(1)
                start_day = int(date_match.group(2))
                end_month = date_match.group(3) or start_month
                end_day = int(date_match.group(4) or start_day)
                start = datetime.strptime(f"{start_month} {start_day} {collected_at.year}", "%b %d %Y")
                end = datetime.strptime(f"{end_month} {end_day} {collected_at.year}", "%b %d %Y")
                return max(0, (start.date() - collected_at.date()).days), max(0, (end.date() - collected_at.date()).days)
            except ValueError:
                return None, None

    return None, None


def median_or_none(values: Iterable[float | int | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return float(median(clean)) if clean else None


def rate(values: Iterable[bool]) -> float | None:
    clean = list(values)
    if not clean:
        return None
    return sum(1 for value in clean if value) / len(clean)


def trend_direction(change: float | None, epsilon: float = 1e-9) -> str:
    if change is None:
        return "unknown"
    if change > epsilon:
        return "up"
    if change < -epsilon:
        return "down"
    return "flat"


def iso_week_period(value: datetime) -> str:
    year, week, _ = value.isocalendar()
    return f"{year}-W{week:02d}"
