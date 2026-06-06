"""Rule-based signal scoring for digital demand monitoring."""

from __future__ import annotations

from collections import defaultdict

from .complaint_leads import build_complaint_lead_signal, complaint_corroborators, complaint_topics
from .models import DemandMetric, DemandSignal, WatchlistConfig


def build_signals(metrics: list[DemandMetric], watchlist: WatchlistConfig) -> list[DemandSignal]:
    by_brand_market: dict[tuple[str, str], list[DemandMetric]] = defaultdict(list)
    for metric in metrics:
        by_brand_market[(metric.brand_id, metric.market)].append(metric)

    signals: list[DemandSignal] = []
    for (brand_id, market), group in sorted(by_brand_market.items()):
        if brand_id != watchlist.primary_brand_id:
            continue
        signals.extend(_market_signals(group, watchlist, market))
    return signals


def _market_signals(metrics: list[DemandMetric], watchlist: WatchlistConfig, market: str) -> list[DemandSignal]:
    output: list[DemandSignal] = []
    app_rank_up = _any(metrics, lambda metric: metric.source_type == "app" and metric.metric_name.endswith("_app_rank") and (metric.change or 0) < 0)
    app_rank_down = _any(metrics, lambda metric: metric.source_type == "app" and metric.metric_name.endswith("_app_rank") and (metric.change or 0) > 0)
    search_up = _metric_change(metrics, "search_interest_avg") > 5
    search_down = _metric_change(metrics, "search_interest_avg") < -5
    web_up = _any(metrics, lambda metric: metric.source_type == "web" and (metric.change or 0) < 0)
    web_down = _any(metrics, lambda metric: metric.source_type == "web" and (metric.change or 0) > 0)
    review_growth_up = _any(metrics, lambda metric: metric.source_type == "app" and metric.metric_name.endswith("_review_count") and (metric.change_pct or 0) > 3)

    accelerating_points = [app_rank_up, search_up, web_up, review_growth_up]
    softening_points = [app_rank_down, search_down, web_down]
    if sum(bool(item) for item in accelerating_points) >= 2:
        output.append(
            _signal(
                metrics,
                watchlist,
                market,
                "demand_accelerating",
                "active",
                "medium",
                "Demand signals improved across at least two app/search/web inputs.",
                drivers=_driver_names([
                    ("app_rank_improving", app_rank_up),
                    ("search_interest_up", search_up),
                    ("web_rank_improving", web_up),
                    ("review_count_growth_up", review_growth_up),
                ]),
                contradicting=_driver_names([
                    ("app_rank_worsening", app_rank_down),
                    ("search_interest_down", search_down),
                    ("web_rank_worsening", web_down),
                ]),
            )
        )
    elif sum(bool(item) for item in softening_points) >= 2:
        output.append(
            _signal(
                metrics,
                watchlist,
                market,
                "demand_softening",
                "active",
                "medium",
                "Demand signals weakened across at least two app/search/web inputs.",
                drivers=_driver_names([
                    ("app_rank_worsening", app_rank_down),
                    ("search_interest_down", search_down),
                    ("web_rank_worsening", web_down),
                ]),
                contradicting=_driver_names([
                    ("app_rank_improving", app_rank_up),
                    ("search_interest_up", search_up),
                    ("web_rank_improving", web_up),
                ]),
            )
        )
    else:
        output.append(
            _signal(
                metrics,
                watchlist,
                market,
                "demand_stable_or_mixed",
                "active",
                "low",
                "Demand signals are mixed or below the threshold for a clear directional call.",
                drivers=_driver_names([
                    ("app_rank_improving", app_rank_up),
                    ("search_interest_up", search_up),
                    ("web_rank_improving", web_up),
                    ("app_rank_worsening", app_rank_down),
                    ("search_interest_down", search_down),
                    ("web_rank_worsening", web_down),
                ]),
            )
        )

    negative_share = _metric_value(metrics, "negative_review_share")
    rating_down = _any(metrics, lambda metric: metric.source_type == "app" and metric.metric_name.endswith("_app_rating") and (metric.change or 0) <= -0.05)
    complaint_lead = build_complaint_lead_signal(metrics, watchlist, market)
    if complaint_lead:
        output.append(complaint_lead)
    review_topic_risk = complaint_topics(metrics)[:3]
    corroborators = complaint_corroborators(metrics, review_topic_risk)
    if ((negative_share is not None and negative_share >= 0.35) and corroborators) or (rating_down and review_topic_risk):
        output.append(
            _signal(
                metrics,
                watchlist,
                market,
                "experience_risk_rising",
                "active",
                "high" if negative_share is not None and negative_share >= 0.45 else "medium",
                "Complaint topics are corroborated by app, product, ad, or other non-UGC signals.",
                drivers=_dedupe([
                    *_driver_names([
                        ("negative_review_share_high", negative_share is not None and negative_share >= 0.35),
                        ("app_rating_down", rating_down),
                    ]),
                    *[f"complaint_topic:{topic}" for topic in review_topic_risk],
                    *corroborators,
                ]),
            )
        )

    discount_up = _metric_change(metrics, "product_median_discount_pct") > 2
    coupon_up = _metric_change(metrics, "product_coupon_availability_rate") > 0.05
    coupon_search_up = _any(metrics, lambda metric: metric.metric_name.startswith("search_interest:") and "coupon" in metric.metric_name.lower() and (metric.change_pct or 0) > 5)
    demand_positive = sum(bool(item) for item in accelerating_points) >= 2
    if demand_positive and (discount_up or coupon_up or coupon_search_up):
        output.append(
            _signal(
                metrics,
                watchlist,
                market,
                "promotion_driven_growth",
                "active",
                "medium",
                "Demand improved while discount, coupon, or coupon-search intensity also rose.",
                drivers=_driver_names([
                    ("demand_positive", demand_positive),
                    ("discount_intensity_up", discount_up),
                    ("coupon_availability_up", coupon_up),
                    ("coupon_search_interest_up", coupon_search_up),
                ]),
            )
        )

    relative_search = _metric_by_name(metrics, "relative_search_share_vs_competitors")
    if relative_search and relative_search.change is not None:
        output.append(
            _signal(
                metrics,
                watchlist,
                market,
                "competitive_position_improving" if relative_search.change >= 0 else "competitive_position_weakening",
                "active",
                "medium",
                "Temu relative search position versus configured competitors moved "
                + ("up." if relative_search.change >= 0 else "down."),
                drivers=[f"relative_search_share_change={relative_search.change:.2f}"],
            )
        )

    return output


def _metric_by_name(metrics: list[DemandMetric], name: str) -> DemandMetric | None:
    return next((metric for metric in metrics if metric.metric_name == name), None)


def _metric_value(metrics: list[DemandMetric], name: str) -> float | None:
    metric = _metric_by_name(metrics, name)
    return metric.current_value if metric else None


def _metric_change(metrics: list[DemandMetric], name: str) -> float:
    metric = _metric_by_name(metrics, name)
    if not metric:
        return 0.0
    if metric.change_pct is not None:
        return metric.change_pct
    return metric.change or 0.0


def _any(metrics: list[DemandMetric], predicate) -> bool:
    return any(predicate(metric) for metric in metrics)


def _top_negative_topics(metrics: list[DemandMetric]) -> list[str]:
    topics: list[str] = []
    for metric in metrics:
        if metric.metric_name.startswith("negative_review_topic_share:") and metric.current_value is not None and metric.current_value >= 0.10:
            topics.append(metric.metric_name.removeprefix("negative_review_topic_share:"))
    return topics[:3]


def _driver_names(items: list[tuple[str, bool]]) -> list[str]:
    return [name for name, active in items if active]


def _dedupe(items: list[str]) -> list[str]:
    output = []
    seen = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _signal(
    metrics: list[DemandMetric],
    watchlist: WatchlistConfig,
    market: str,
    name: str,
    status: str,
    severity: str,
    summary: str,
    drivers: list[str] | None = None,
    contradicting: list[str] | None = None,
) -> DemandSignal:
    first = metrics[0]
    return DemandSignal(
        company_id=watchlist.company_id,
        ticker=watchlist.ticker,
        brand_id=watchlist.primary_brand_id,
        market=market,
        signal=name,
        status=status,
        severity=severity,
        confidence="medium" if len(metrics) >= 3 else "low",
        summary=summary,
        drivers=drivers or [],
        contradicting_signals=contradicting or [],
        evidence={"metric_count": len(metrics), "sample_metric": first.metric_name},
    )
