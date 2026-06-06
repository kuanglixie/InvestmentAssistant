"""Markdown and JSON report generation."""

from __future__ import annotations

import json
from pathlib import Path

from .models import DemandMetric, DemandSignal, DemandSignalPack, WatchlistConfig, to_jsonable


def write_outputs(output_dir: str | Path, pack: DemandSignalPack, watchlist: WatchlistConfig) -> None:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "demand_signal_pack.json").write_text(
        json.dumps(to_jsonable(pack), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (path / "weekly_demand_report.md").write_text(render_markdown_report(pack, watchlist), encoding="utf-8")


def render_markdown_report(pack: DemandSignalPack, watchlist: WatchlistConfig) -> str:
    lines = [
        f"# {pack.ticker} / {watchlist.brand_by_id()[watchlist.primary_brand_id].display_name} Digital Demand Monitor",
        "",
        f"- Generated at: `{pack.generated_at.isoformat()}`",
        f"- Markets: `{', '.join(pack.markets)}`",
        "",
        "## Bottom Line",
        "",
    ]
    for market in pack.markets:
        lines.extend(_market_bottom_line(market, pack.signals))

    lines.extend(["", "## Key Signals", ""])
    for signal in pack.signals:
        lines.append(
            f"- `{signal.market}` `{signal.signal}` "
            f"(severity={signal.severity}, confidence={signal.confidence}): {signal.summary}"
        )
        if signal.drivers:
            lines.append(f"  Drivers: {', '.join(signal.drivers)}")
        if signal.contradicting_signals:
            lines.append(f"  Contradicting signals: {', '.join(signal.contradicting_signals)}")

    lines.extend(["", "## Metric Highlights", ""])
    for metric in _highlight_metrics(pack.metrics):
        value = _fmt(metric.current_value)
        change = _fmt(metric.change_pct if metric.change_pct is not None else metric.change)
        suffix = "pct" if metric.change_pct is not None else "abs"
        lines.append(
            f"- `{metric.market}` `{metric.brand_id}` `{metric.metric_name}`: "
            f"current={value}, change_{suffix}={change}, direction={metric.direction}"
        )

    lines.extend(["", "## Complaint Lead Watchlist", ""])
    topic_metrics = [metric for metric in pack.metrics if metric.metric_name.startswith("negative_review_topic_share:")]
    if topic_metrics:
        for metric in sorted(topic_metrics, key=lambda item: (item.market, -(item.current_value or 0)))[:10]:
            lines.append(
                f"- `{metric.market}` `{metric.brand_id}` "
                f"`{metric.metric_name.removeprefix('negative_review_topic_share:')}`: {_fmt(metric.current_value)}"
            )
    else:
        lines.append("- No complaint-topic lead metrics were available.")

    lines.extend(["", "## What To Investigate Next", ""])
    lines.extend(_next_steps(pack.signals))
    lines.append("")
    return "\n".join(lines)


def _market_bottom_line(market: str, signals: list[DemandSignal]) -> list[str]:
    market_signals = [signal for signal in signals if signal.market == market]
    demand = "stable/mixed"
    risk = "low"
    promotion = "low"
    competitive = "stable"
    if any(signal.signal == "demand_accelerating" for signal in market_signals):
        demand = "improving"
    if any(signal.signal == "demand_softening" for signal in market_signals):
        demand = "softening"
    if any(signal.signal == "experience_risk_rising" and signal.severity == "high" for signal in market_signals):
        risk = "high"
    elif any(signal.signal == "experience_risk_rising" for signal in market_signals):
        risk = "medium"
    if any(signal.signal == "promotion_driven_growth" for signal in market_signals):
        promotion = "medium"
    if any(signal.signal == "competitive_position_improving" for signal in market_signals):
        competitive = "improving"
    if any(signal.signal == "competitive_position_weakening" for signal in market_signals):
        competitive = "weakening"
    return [
        f"### {market}",
        "",
        f"- Demand: **{demand}**",
        f"- Experience risk: **{risk}**",
        f"- Promotion dependence: **{promotion}**",
        f"- Competitive position: **{competitive}**",
        "",
    ]


def _highlight_metrics(metrics: list[DemandMetric]) -> list[DemandMetric]:
    important = (
        "ios_app_rank",
        "ios_app_rating",
        "ios_review_count",
        "android_app_rank",
        "android_app_rating",
        "android_review_count",
        "android_download_count_lower_bound",
        "search_interest_avg",
        "relative_search_share_vs_competitors",
        "google_ads_transparency_ad_count_lower_bound",
        "google_ads_transparency_visible_video_cards",
        "negative_review_share",
        "product_median_discount_pct",
        "product_coupon_availability_rate",
        "product_surface_card_count",
        "product_surface_priced_card_count",
        "product_surface_median_price",
        "product_surface_median_discount_pct",
        "product_surface_discount_card_rate",
        "product_surface_coupon_card_rate",
    )
    selected = [metric for metric in metrics if metric.metric_name in important or metric.metric_name.startswith("web_rank:")]
    ad_metrics = [metric for metric in selected if metric.source_type == "ad"]
    non_ad_metrics = [metric for metric in selected if metric.source_type != "ad"]
    return non_ad_metrics[:30] + ad_metrics[:30]


def _next_steps(signals: list[DemandSignal]) -> list[str]:
    steps = []
    if any(signal.signal == "promotion_driven_growth" for signal in signals):
        steps.append("- Check whether demand improvement is being bought through discounts, coupons, or paid acquisition.")
    if any(signal.signal == "experience_risk_rising" for signal in signals):
        steps.append("- Drill into recent negative reviews and compare delivery/refund complaints against product tracker delivery metrics.")
    if any(signal.signal == "demand_softening" for signal in signals):
        steps.append("- Compare app rank softness with search and web data before treating it as real demand deterioration.")
    if any(signal.signal == "competitive_position_weakening" for signal in signals):
        steps.append("- Compare Temu against SHEIN, AliExpress, and TikTok Shop by market to identify where the weakness is concentrated.")
    if not steps:
        steps.append("- Continue monitoring; no high-priority anomaly crossed V1 thresholds.")
    return steps


def _fmt(value: float | None) -> str:
    if value is None:
        return "na"
    return f"{value:.2f}"
