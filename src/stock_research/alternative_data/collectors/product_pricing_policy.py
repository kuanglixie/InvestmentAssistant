"""Product / pricing / policy collector V1."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from .common import CollectorFinding, CollectorPack, JsonDict, median, rate, utc_now


MERCHANT_POLICY_TOPICS = {
    "seller_fees",
    "ads_traffic",
    "returns_refunds",
    "logistics_fulfillment",
    "payout_cashflow",
    "penalties_enforcement",
    "merchant_profitability",
}


def build_product_pricing_policy_pack(
    *,
    company: str = "PDD",
    brand: str = "Temu",
    product_snapshots: list[JsonDict] | None = None,
    product_metrics: list[JsonDict] | None = None,
    product_signal_pack: JsonDict | None = None,
    unit_economics_pack: JsonDict | None = None,
    policy_events: list[JsonDict] | None = None,
    source_inputs: JsonDict | None = None,
) -> CollectorPack:
    snapshots = product_snapshots or []
    metrics = _latest_metrics(product_metrics or [])
    unit_metrics = dict((unit_economics_pack or {}).get("unit_economics_proxies") or {})
    product_signals = list((product_signal_pack or {}).get("product_signals") or [])
    policy = _policy_events(policy_events or [])

    collector_metrics = _collector_metrics(snapshots, metrics, unit_metrics)
    collector_metrics.extend(_policy_topic_metrics(policy))
    findings = _findings(metrics, unit_metrics, product_signals, policy, collector_metrics)

    return CollectorPack(
        collector_id="product_pricing_policy_v1",
        company=company,
        brand=brand,
        generated_at=utc_now(),
        source_inputs=source_inputs or {},
        metrics=collector_metrics,
        events=policy[:50],
        findings=findings,
        limitations=[
            "Product metrics depend on the configured fixed basket; changing the basket changes comparability.",
            "Public merchant and policy pages can miss seller-console-only terms unless seller credentials or exports are available.",
            "Price, coupon, and delivery promises can vary by region, account state, and time of day.",
        ],
    )


def _latest_metrics(product_metrics: list[JsonDict]) -> dict[str, JsonDict]:
    if not product_metrics:
        return {}
    latest_period = max(str(metric.get("period") or "") for metric in product_metrics)
    selected = [
        metric
        for metric in product_metrics
        if str(metric.get("period") or "") == latest_period and metric.get("category", "all") == "all"
    ]
    return {str(metric.get("metric_name")): metric for metric in selected if metric.get("metric_name")}


def _policy_events(events: list[JsonDict]) -> list[JsonDict]:
    selected = []
    for event in events:
        topic = str(event.get("topic") or "")
        if event.get("source_group") == "merchant_platform_policy" or topic in MERCHANT_POLICY_TOPICS:
            selected.append(event)
    return selected


def _collector_metrics(snapshots: list[JsonDict], metrics: dict[str, JsonDict], unit_metrics: JsonDict) -> list[JsonDict]:
    output: list[JsonDict] = []
    for metric_name in (
        "median_price",
        "median_discount_pct",
        "coupon_availability_rate",
        "median_coupon_value",
        "median_delivery_max_days",
        "stockout_rate",
        "active_product_rate",
        "shipping_fee_rate",
        "average_rating",
    ):
        value = unit_metrics.get(metric_name)
        source = "unit_economics_pack"
        if value is None and metric_name in metrics:
            value = metrics[metric_name].get("value")
            source = "weekly_metrics"
        if value is None:
            continue
        output.append(
            {
                "metric_name": metric_name,
                "value": value,
                "source": source,
                "change_1w": (metrics.get(metric_name) or {}).get("change_1w"),
                "change_4w": (metrics.get(metric_name) or {}).get("change_4w"),
                "confidence": (metrics.get(metric_name) or {}).get("confidence", "medium"),
            }
        )

    parsed_snapshots = [snapshot for snapshot in snapshots if snapshot.get("parse_success", True)]
    if parsed_snapshots:
        output.extend(
            [
                {
                    "metric_name": "snapshot_median_price",
                    "value": median([snapshot.get("price") for snapshot in parsed_snapshots]),
                    "source": "latest_snapshots",
                    "confidence": "medium" if len(parsed_snapshots) >= 5 else "low",
                },
                {
                    "metric_name": "snapshot_discount_rate",
                    "value": rate([bool(snapshot.get("discount_pct")) for snapshot in parsed_snapshots]),
                    "source": "latest_snapshots",
                    "confidence": "medium" if len(parsed_snapshots) >= 5 else "low",
                },
                {
                    "metric_name": "snapshot_count",
                    "value": len(parsed_snapshots),
                    "source": "latest_snapshots",
                    "confidence": "medium" if len(parsed_snapshots) >= 5 else "low",
                },
            ]
        )
    return output


def _policy_topic_metrics(policy_events: list[JsonDict]) -> list[JsonDict]:
    counts = Counter(str(event.get("topic") or "unknown") for event in policy_events)
    return [
        {
            "metric_name": f"policy_topic_count:{topic}",
            "value": count,
            "source": "policy_events",
            "confidence": "medium",
        }
        for topic, count in sorted(counts.items())
    ]


def _findings(
    metrics: dict[str, JsonDict],
    unit_metrics: JsonDict,
    product_signals: list[JsonDict],
    policy_events: list[JsonDict],
    collector_metrics: list[JsonDict],
) -> list[CollectorFinding]:
    findings: list[CollectorFinding] = []
    by_name = {str(metric.get("metric_name")): metric for metric in collector_metrics}

    discount = _metric_value(by_name, "median_discount_pct")
    coupon = _metric_value(by_name, "coupon_availability_rate")
    promotion_signals = [signal for signal in product_signals if signal.get("signal") == "promotion_intensity_rising"]
    if (discount is not None and discount >= 45) or (coupon is not None and coupon >= 0.35) or promotion_signals:
        findings.append(
            CollectorFinding(
                finding_id="promotion_intensity_watch",
                question="Is growth becoming more discount- or coupon-driven?",
                summary="Product data shows elevated discount, coupon, or promotion intensity.",
                severity="high" if (discount or 0) >= 60 or (coupon or 0) >= 0.60 else "medium",
                confidence=_max_confidence([by_name.get("median_discount_pct"), by_name.get("coupon_availability_rate")]),
                evidence={
                    "median_discount_pct": discount,
                    "coupon_availability_rate": coupon,
                    "promotion_signal_count": len(promotion_signals),
                },
                next_steps=[
                    "Compare against competitor basket price gaps.",
                    "Check whether app/search demand is rising at the same time as discounts.",
                ],
            )
        )

    delivery = _metric_value(by_name, "median_delivery_max_days")
    delivery_signal = [signal for signal in product_signals if signal.get("signal") == "delivery_worsening"]
    if (delivery is not None and delivery >= 10) or delivery_signal:
        findings.append(
            CollectorFinding(
                finding_id="delivery_promise_watch",
                question="Is fulfillment improving or worsening?",
                summary="Delivery promise metrics or product signals suggest fulfillment should be checked.",
                severity="high" if (delivery or 0) >= 14 else "medium",
                confidence=(by_name.get("median_delivery_max_days") or {}).get("confidence", "medium"),
                evidence={"median_delivery_max_days": delivery, "delivery_signal_count": len(delivery_signal)},
                next_steps=["Compare stated delivery promise with App Store and public-voice delivery complaints."],
            )
        )

    topic_counts = Counter(str(event.get("topic") or "unknown") for event in policy_events)
    pressure_topics = {
        topic: count
        for topic, count in topic_counts.items()
        if topic in {"seller_fees", "returns_refunds", "payout_cashflow", "penalties_enforcement", "logistics_fulfillment"}
    }
    if pressure_topics:
        findings.append(
            CollectorFinding(
                finding_id="merchant_policy_pressure_watch",
                question="Is the platform changing merchant economics or obligations?",
                summary="Merchant or platform policy evidence touches fees, returns, payout, penalties, or fulfillment obligations.",
                severity="high" if pressure_topics.get("penalties_enforcement") or pressure_topics.get("payout_cashflow") else "medium",
                confidence="medium",
                evidence={"topic_counts": pressure_topics, "event_count": sum(pressure_topics.values())},
                next_steps=["Diff the relevant policy pages and look for dated seller-announcement changes."],
            )
        )

    stockout = _metric_value(by_name, "stockout_rate")
    active_rate = _metric_value(by_name, "active_product_rate")
    rating_signals = [signal for signal in product_signals if signal.get("signal") == "rating_deteriorating"]
    if (stockout is not None and stockout >= 0.10) or (active_rate is not None and active_rate < 0.80) or rating_signals:
        findings.append(
            CollectorFinding(
                finding_id="product_supply_quality_watch",
                question="Are supply availability or quality signals deteriorating?",
                summary="Availability, active-product, or rating signals crossed the V1 watch threshold.",
                severity="high" if (stockout or 0) >= 0.20 or (active_rate is not None and active_rate < 0.65) else "medium",
                confidence=_max_confidence([by_name.get("stockout_rate"), by_name.get("active_product_rate")]),
                evidence={"stockout_rate": stockout, "active_product_rate": active_rate, "rating_signal_count": len(rating_signals)},
                next_steps=["Check category-level snapshots to see whether the issue is broad or concentrated."],
            )
        )

    if not findings:
        findings.append(
            CollectorFinding(
                finding_id="product_policy_stable_v1",
                question="Did any V1 product, pricing, or policy threshold fire?",
                summary="No V1 product/pricing/policy threshold finding was triggered.",
                severity="low",
                confidence="low" if not collector_metrics else "medium",
                evidence={"metric_count": len(collector_metrics), "policy_event_count": len(policy_events)},
            )
        )
    return findings


def _metric_value(by_name: dict[str, JsonDict], metric_name: str) -> float | None:
    value = (by_name.get(metric_name) or {}).get("value")
    if value is None:
        return None
    return float(value)


def _max_confidence(metrics: list[JsonDict | None]) -> str:
    rank = {"low": 0, "medium": 1, "high": 2}
    confidence = "low"
    for metric in metrics:
        if not metric:
            continue
        candidate = str(metric.get("confidence") or "medium")
        if rank.get(candidate, 1) > rank.get(confidence, 0):
            confidence = candidate
    return confidence
