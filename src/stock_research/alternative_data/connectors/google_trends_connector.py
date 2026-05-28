from __future__ import annotations

from typing import Any

from stock_research.alternative_data.connectors.base import AlternativeDataConnector, empty_connector_result
from stock_research.alternative_data.models import AlternativeDataRequest, ConnectorResult
from stock_research.alternative_data.normalization.confidence_scorer import score_confidence
from stock_research.alternative_data.normalization.metric_normalizer import metric_from_observation, observation_from_payload


class GoogleTrendsConnector(AlternativeDataConnector):
    connector_id = "google_trends"
    source = "google_trends"

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
                missing=["google_trends_api_or_manual_observations"],
                notes=[
                    "Google Trends live API is not configured in V1.",
                    "pytrends should be treated as best-effort because it is unofficial and can break.",
                ],
            )
        raw_observations = []
        metrics = []
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
            metric_name = payload.get("metric_name") or _metric_for_keyword(str(payload.get("keyword", "")))
            if "value" not in payload:
                continue
            metrics.append(
                metric_from_observation(
                    observation,
                    metric_name=metric_name,
                    value=payload["value"],
                    unit=payload.get("unit", "index_0_100"),
                    region=payload.get("region") or request.get("region", ""),
                    source=self.source,
                    confidence=score_confidence(source=self.source, sample_size=len(rows)),
                    date_value=payload.get("date") or row.get("collected_at", "")[:10],
                    time_window=request.get("time_window", "weekly"),
                    metadata={"keyword": payload.get("keyword")},
                )
            )
        return {
            "connector_id": self.connector_id,
            "status": "collected_from_seed_observations",
            "raw_observations": raw_observations,
            "metrics": metrics,
            "text_events": [],
            "notes": ["Normalized Google Trends search-interest observations."],
            "missing": [],
        }


def _metric_for_keyword(keyword: str) -> str:
    lower = keyword.lower()
    if "refund" in lower:
        return "demand.search.google_trends.refund"
    if "scam" in lower:
        return "demand.search.google_trends.scam"
    if "coupon" in lower:
        return "demand.search.google_trends.coupon"
    if "review" in lower:
        return "demand.search.google_trends.review"
    return "demand.search.google_trends.brand"


def _default_brand(request: AlternativeDataRequest) -> str:
    brands = request.get("brands") or [request.get("company", "")]
    return brands[0]
