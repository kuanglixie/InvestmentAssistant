from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any

from stock_research.alternative_data.connectors.base import AlternativeDataConnector, empty_connector_result
from stock_research.alternative_data.models import AlternativeDataRequest, ConnectorResult
from stock_research.alternative_data.normalization.confidence_scorer import score_confidence
from stock_research.alternative_data.normalization.metric_normalizer import metric_from_observation, observation_from_payload


class EcommerceCrawler(AlternativeDataConnector):
    connector_id = "ecommerce_product_basket"
    source = "ecommerce_crawler"

    def collect(
        self,
        request: AlternativeDataRequest,
        *,
        seed_observations: list[dict[str, Any]] | None = None,
    ) -> ConnectorResult:
        rows = [row for row in seed_observations or [] if row.get("source") == self.source]
        if not rows:
            return empty_connector_result(
                connector_id=self.connector_id,
                missing=["fixed_product_basket_observations"],
                notes=[
                    "E-commerce crawler live collection is not configured in V1.",
                    "Production collection must use a fixed product basket to avoid noisy time series.",
                ],
            )
        raw_observations = []
        bucketed: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            payload = row.get("raw_payload", row)
            observation = observation_from_payload(
                company=request["company"],
                brand=row.get("brand") or _default_brand(request),
                source=self.source,
                payload=payload,
                source_url=row.get("source_url", ""),
                collected_at=row.get("collected_at"),
            )
            raw_observations.append(observation)
            date_value = payload.get("date") or row.get("collected_at", "")[:10]
            bucketed[(date_value, payload.get("region") or request.get("region", ""))].append(payload)

        metrics = []
        for (date_value, region), payloads in bucketed.items():
            observation = raw_observations[0]
            sample_size = len(payloads)
            confidence = score_confidence(source=self.source, sample_size=sample_size)
            metric_values = _basket_metrics(payloads)
            for metric_name, value_unit in metric_values.items():
                value, unit = value_unit
                metrics.append(
                    metric_from_observation(
                        observation,
                        metric_name=metric_name,
                        value=value,
                        unit=unit,
                        region=region,
                        source=self.source,
                        confidence=confidence,
                        date_value=date_value,
                        time_window=request.get("time_window", "weekly"),
                        metadata={"sample_size": sample_size, "basket_rule": "fixed_product_basket_required"},
                    )
                )
        return {
            "connector_id": self.connector_id,
            "status": "collected_from_seed_observations",
            "raw_observations": raw_observations,
            "metrics": metrics,
            "text_events": [],
            "notes": ["Normalized fixed-basket product-price, delivery, rating, and review observations."],
            "missing": [],
        }


def _basket_metrics(payloads: list[dict[str, Any]]) -> dict[str, tuple[float, str]]:
    prices = _numeric_values(payloads, "price")
    discounts = _numeric_values(payloads, "discount_pct")
    delivery_midpoints = [
        (float(item["delivery_min_days"]) + float(item["delivery_max_days"])) / 2
        for item in payloads
        if isinstance(item.get("delivery_min_days"), int | float)
        and isinstance(item.get("delivery_max_days"), int | float)
    ]
    ratings = _numeric_values(payloads, "rating")
    review_counts = _numeric_values(payloads, "review_count")
    coupon_count = sum(1 for item in payloads if item.get("coupon_available"))
    metrics: dict[str, tuple[float, str]] = {}
    if prices:
        metrics["value.price.median"] = (median(prices), "currency")
    if discounts:
        metrics["value.discount.median_pct"] = (median(discounts), "ratio")
    if payloads:
        metrics["value.coupon.intensity"] = (coupon_count / len(payloads), "ratio")
    if delivery_midpoints:
        metrics["value.delivery.median_days"] = (median(delivery_midpoints), "days")
    if ratings:
        metrics["trust.rating.average"] = (sum(ratings) / len(ratings), "stars")
    if review_counts:
        metrics["trust.review.count"] = (sum(review_counts), "count")
    return metrics


def _numeric_values(payloads: list[dict[str, Any]], key: str) -> list[float]:
    return [float(item[key]) for item in payloads if isinstance(item.get(key), int | float)]


def _default_brand(request: AlternativeDataRequest) -> str:
    brands = request.get("brands") or [request.get("company", "")]
    return brands[0]
