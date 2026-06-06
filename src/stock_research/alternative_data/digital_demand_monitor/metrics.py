"""Metric construction from raw digital demand snapshots."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Iterable

from .models import DemandMetric, WatchlistConfig


def build_metrics(store, watchlist: WatchlistConfig) -> list[DemandMetric]:
    metrics: list[DemandMetric] = []
    metrics.extend(_app_metrics([dict(row) for row in store.rows("app_snapshot")]))
    metrics.extend(_review_metrics([dict(row) for row in store.rows("review_snapshot")]))
    metrics.extend(_search_metrics([dict(row) for row in store.rows("search_snapshot")], watchlist))
    metrics.extend(_web_metrics([dict(row) for row in store.rows("web_snapshot")]))
    metrics.extend(_ad_metrics([dict(row) for row in store.rows("ad_snapshot")]))
    metrics.extend(_product_metrics([dict(row) for row in store.rows("product_metric_snapshot")]))
    return metrics


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _direction(change: float | None, lower_is_better: bool = False) -> str:
    if change is None:
        return "unknown"
    if abs(change) < 1e-9:
        return "flat"
    improving = change < 0 if lower_is_better else change > 0
    return "improving" if improving else "worsening"


def _pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / abs(previous) * 100


def _latest_pair(rows: list[dict[str, Any]], time_key: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    ordered = sorted(rows, key=lambda row: row[time_key])
    latest = ordered[-1]
    previous = ordered[-2] if len(ordered) >= 2 else None
    return latest, previous


def _metric(
    row: dict[str, Any],
    name: str,
    current: float | None,
    previous: float | None,
    source_type: str,
    lower_is_better: bool = False,
    evidence: dict[str, Any] | None = None,
    confidence: str = "medium",
) -> DemandMetric:
    change = current - previous if current is not None and previous is not None else None
    return DemandMetric(
        company_id=row["company_id"],
        ticker=row["ticker"],
        brand_id=row["brand_id"],
        market=row["market"],
        metric_name=name,
        current_value=current,
        previous_value=previous,
        change=change,
        change_pct=_pct_change(current, previous),
        direction=_direction(change, lower_is_better=lower_is_better),
        source_type=source_type,
        confidence=confidence,
        evidence=evidence or {},
    )


def _app_metrics(rows: list[dict[str, Any]]) -> list[DemandMetric]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("fetch_success"):
            grouped[(row["brand_id"], row["market"], row["platform"])].append(row)

    output: list[DemandMetric] = []
    for (_brand, _market, platform), group in grouped.items():
        for field_name, metric_name, lower_is_better in (
            ("rank", f"{platform}_app_rank", True),
            ("rating", f"{platform}_app_rating", False),
            ("review_count", f"{platform}_review_count", False),
            ("download_count_lower_bound", f"{platform}_download_count_lower_bound", False),
        ):
            field_rows = [row for row in group if row.get(field_name) is not None]
            if not field_rows:
                continue
            latest, previous = _latest_pair(field_rows, "collected_at")
            evidence = {
                "platform": platform,
                "app_id": latest.get("app_id"),
                "collected_at": latest.get("collected_at"),
                "source_name": latest.get("source_name"),
            }
            output.append(
                _metric(
                    latest,
                    metric_name,
                    latest.get(field_name),
                    previous.get(field_name) if previous else None,
                    "app",
                    lower_is_better=lower_is_better,
                    evidence=evidence,
                )
            )
    return [metric for metric in output if metric.current_value is not None]


def _review_metrics(rows: list[dict[str, Any]]) -> list[DemandMetric]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["brand_id"], row["market"])].append(row)

    output: list[DemandMetric] = []
    for (_brand, _market), group in grouped.items():
        latest = max(group, key=lambda row: row["collected_at"])
        total = len(group)
        negative = [row for row in group if row.get("sentiment") == "negative" or (row.get("rating") is not None and row["rating"] <= 2)]
        topic_counts = Counter(row.get("topic") or "other" for row in negative)
        negative_share = len(negative) / total if total else None
        output.append(
            _metric(
                latest,
                "negative_review_share",
                negative_share,
                None,
                "review",
                evidence={
                    "review_count": total,
                    "top_negative_topics": dict(topic_counts.most_common(5)),
                    "recommended_use": "complaint_lead_only",
                    "bias_warning": "UGC/review data is selection-biased toward unhappy users.",
                },
                confidence="low",
            )
        )
        for topic, count in topic_counts.most_common(5):
            output.append(
                _metric(
                    latest,
                    f"negative_review_topic_share:{topic}",
                    count / total if total else None,
                    None,
                    "review",
                    evidence={
                        "negative_count": count,
                        "review_count": total,
                        "recommended_use": "topic_watchlist_only",
                        "bias_warning": "Use within-source trend and corroboration, not absolute satisfaction.",
                    },
                    confidence="low",
                )
            )
    return output


def _search_metrics(rows: list[dict[str, Any]], watchlist: WatchlistConfig) -> list[DemandMetric]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["brand_id"], row["market"], row["term"])].append(row)

    output: list[DemandMetric] = []
    by_brand_market_latest: dict[tuple[str, str], list[float]] = defaultdict(list)
    by_brand_market_previous: dict[tuple[str, str], list[float]] = defaultdict(list)
    for (_brand, _market, term), group in grouped.items():
        latest, previous = _latest_pair(group, "date")
        by_brand_market_latest[(latest["brand_id"], latest["market"])].append(latest["value"])
        if previous:
            by_brand_market_previous[(latest["brand_id"], latest["market"])].append(previous["value"])
        output.append(_metric(latest, f"search_interest:{term}", latest["value"], previous.get("value") if previous else None, "search", evidence={"term": term}))

    for (brand_id, market), current_values in by_brand_market_latest.items():
        previous_values = by_brand_market_previous.get((brand_id, market), [])
        current = sum(current_values) / len(current_values) if current_values else None
        previous = sum(previous_values) / len(previous_values) if previous_values else None
        sample = next(row for row in rows if row["brand_id"] == brand_id and row["market"] == market)
        output.append(_metric(sample, "search_interest_avg", current, previous, "search", evidence={"brand_id": brand_id, "market": market}))

    primary = watchlist.primary_brand_id
    for market in watchlist.markets:
        primary_metric = next((metric for metric in output if metric.brand_id == primary and metric.market == market and metric.metric_name == "search_interest_avg"), None)
        competitor_metrics = [
            metric
            for metric in output
            if metric.market == market and metric.metric_name == "search_interest_avg" and metric.brand_id != primary
        ]
        if primary_metric and competitor_metrics:
            competitor_avg = sum(metric.current_value or 0 for metric in competitor_metrics) / len(competitor_metrics)
            previous_competitor_avg = sum(metric.previous_value or 0 for metric in competitor_metrics) / len(competitor_metrics)
            output.append(
                DemandMetric(
                    company_id=primary_metric.company_id,
                    ticker=primary_metric.ticker,
                    brand_id=primary,
                    market=market,
                    metric_name="relative_search_share_vs_competitors",
                    current_value=(primary_metric.current_value or 0) - competitor_avg,
                    previous_value=(primary_metric.previous_value or 0) - previous_competitor_avg,
                    change=((primary_metric.current_value or 0) - competitor_avg) - ((primary_metric.previous_value or 0) - previous_competitor_avg),
                    change_pct=None,
                    direction="improving" if ((primary_metric.current_value or 0) - competitor_avg) >= ((primary_metric.previous_value or 0) - previous_competitor_avg) else "worsening",
                    source_type="search",
                    confidence="medium",
                    evidence={"competitor_count": len(competitor_metrics)},
                )
            )
    return output


def _web_metrics(rows: list[dict[str, Any]]) -> list[DemandMetric]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["brand_id"], row["market"], row["domain"])].append(row)
    output: list[DemandMetric] = []
    for (_brand, _market, domain), group in grouped.items():
        latest, previous = _latest_pair(group, "collected_at")
        output.append(_metric(latest, f"web_rank:{domain}", latest.get("rank"), previous.get("rank") if previous else None, "web", lower_is_better=True, evidence={"domain": domain}))
    return [metric for metric in output if metric.current_value is not None]


def _ad_metrics(rows: list[dict[str, Any]]) -> list[DemandMetric]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["brand_id"], row["market"], row["source_name"], row["domain"])].append(row)

    output: list[DemandMetric] = []
    for (_brand, _market, source_name, domain), group in grouped.items():
        latest, previous = _latest_pair(group, "collected_at")
        for field_name, metric_name in (
            ("ad_count_lower_bound", f"{source_name}_ad_count_lower_bound"),
            ("visible_ad_cards", f"{source_name}_visible_ad_cards"),
            ("visible_video_cards", f"{source_name}_visible_video_cards"),
        ):
            if latest.get(field_name) is None:
                continue
            output.append(
                _metric(
                    latest,
                    metric_name,
                    latest.get(field_name),
                    previous.get(field_name) if previous else None,
                    "ad",
                    evidence={
                        "domain": domain,
                        "advertiser_name": latest.get("advertiser_name"),
                        "ad_count_label": latest.get("ad_count_label"),
                        "source_url": latest.get("source_url"),
                    },
                )
            )
    return output


def _product_metrics(rows: list[dict[str, Any]]) -> list[DemandMetric]:
    output: list[DemandMetric] = []
    for row in rows:
        current = row.get("value")
        previous = current - row["change_4w"] if current is not None and row.get("change_4w") is not None else None
        lower_is_better = any(
            token in row["metric_name"]
            for token in ("delivery", "stockout", "shipping_fee", "return_rate", "refund_rate")
        )
        output.append(
            DemandMetric(
                company_id=row["company_id"],
                ticker=row["ticker"],
                brand_id=row["brand_id"],
                market=row["market"],
                metric_name=f"product_{row['metric_name']}",
                current_value=current,
                previous_value=previous,
                change=row.get("change_4w"),
                change_pct=_pct_change(current, previous),
                direction=_direction(row.get("change_4w"), lower_is_better=lower_is_better),
                source_type="product",
                confidence="medium",
                evidence={"period": row.get("period"), "source_path": row.get("source_path")},
            )
        )
    return output
