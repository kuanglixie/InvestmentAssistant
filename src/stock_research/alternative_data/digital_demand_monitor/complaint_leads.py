"""Low-confidence complaint lead generation from biased UGC/review data."""

from __future__ import annotations

from .models import DemandMetric, DemandSignal, WatchlistConfig


COMPLAINT_TOPIC_THRESHOLD = 0.10
NEGATIVE_SHARE_THRESHOLD = 0.30


def build_complaint_lead_signal(
    metrics: list[DemandMetric],
    watchlist: WatchlistConfig,
    market: str,
) -> DemandSignal | None:
    """Build a lead-only signal from complaint topics.

    UGC/review complaints are biased toward unhappy users. This signal is meant
    to route investigation, not to measure customer satisfaction.
    """

    negative_share = _metric_by_name(metrics, "negative_review_share")
    topic_metrics = [
        metric
        for metric in metrics
        if metric.metric_name.startswith("negative_review_topic_share:")
        and metric.current_value is not None
        and metric.current_value >= COMPLAINT_TOPIC_THRESHOLD
    ]
    if not topic_metrics and not (negative_share and (negative_share.current_value or 0) >= NEGATIVE_SHARE_THRESHOLD):
        return None

    topic_metrics = sorted(topic_metrics, key=lambda metric: metric.current_value or 0, reverse=True)
    top_topics = [metric.metric_name.removeprefix("negative_review_topic_share:") for metric in topic_metrics[:5]]
    sample_metric = negative_share or topic_metrics[0]
    severity = "medium" if any((metric.current_value or 0) >= 0.20 for metric in topic_metrics) else "low"

    return DemandSignal(
        company_id=watchlist.company_id,
        ticker=watchlist.ticker,
        brand_id=watchlist.primary_brand_id,
        market=market,
        signal="complaint_topic_watchlist",
        status="lead_only",
        severity=severity,
        confidence="low",
        summary="UGC/review complaints surfaced topics to investigate; do not treat this as a customer-satisfaction score.",
        drivers=[
            f"negative_review_share={negative_share.current_value:.2f}" if negative_share and negative_share.current_value is not None else "negative_review_share=na",
            *[f"topic:{topic}={metric.current_value:.2f}" for topic, metric in zip(top_topics, topic_metrics[:5])],
            "source_bias=complaint_selection_bias",
        ],
        evidence={
            "metric_count": len(metrics),
            "sample_metric": sample_metric.metric_name,
            "top_complaint_topics": top_topics,
            "recommended_use": "investigation_trigger_only",
            "do_not_use_as": "absolute_satisfaction_or_churn_score",
        },
    )


def complaint_corroborators(metrics: list[DemandMetric], complaint_topics: list[str]) -> list[str]:
    corroborators: list[str] = []
    rating_down = any(
        metric.source_type == "app"
        and metric.metric_name.endswith("_app_rating")
        and metric.change is not None
        and metric.change <= -0.05
        for metric in metrics
    )
    if rating_down:
        corroborators.append("app_rating_down")

    if "delivery_delay" in complaint_topics and _product_metric_worsening(metrics, ("delivery", "shipping")):
        corroborators.append("product_delivery_metric_worsening")
    if "refund_return" in complaint_topics and _product_metric_worsening(metrics, ("return", "refund")):
        corroborators.append("product_return_or_refund_metric_worsening")
    if any(topic in complaint_topics for topic in ("ads_promotion", "pricing_coupon")):
        if _product_metric_worsening(metrics, ("discount", "coupon")):
            corroborators.append("promotion_or_coupon_metric_up")
        if any(metric.source_type == "ad" and (metric.change or 0) > 0 for metric in metrics):
            corroborators.append("ad_intensity_up")
    return corroborators


def complaint_topics(metrics: list[DemandMetric]) -> list[str]:
    topic_metrics = [
        metric
        for metric in metrics
        if metric.metric_name.startswith("negative_review_topic_share:")
        and metric.current_value is not None
        and metric.current_value >= COMPLAINT_TOPIC_THRESHOLD
    ]
    ordered = sorted(topic_metrics, key=lambda metric: metric.current_value or 0, reverse=True)
    return [metric.metric_name.removeprefix("negative_review_topic_share:") for metric in ordered]


def _metric_by_name(metrics: list[DemandMetric], name: str) -> DemandMetric | None:
    return next((metric for metric in metrics if metric.metric_name == name), None)


def _product_metric_worsening(metrics: list[DemandMetric], tokens: tuple[str, ...]) -> bool:
    for metric in metrics:
        if metric.source_type != "product":
            continue
        if not any(token in metric.metric_name for token in tokens):
            continue
        if metric.direction == "worsening" or (metric.change or 0) > 0:
            return True
    return False
