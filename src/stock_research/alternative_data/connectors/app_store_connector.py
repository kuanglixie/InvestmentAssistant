from __future__ import annotations

from typing import Any

from stock_research.alternative_data.connectors.base import AlternativeDataConnector, empty_connector_result
from stock_research.alternative_data.models import AlternativeDataRequest, ConnectorResult
from stock_research.alternative_data.normalization.confidence_scorer import score_confidence
from stock_research.alternative_data.normalization.metric_normalizer import metric_from_observation, observation_from_payload


class AppStoreConnector(AlternativeDataConnector):
    connector_id = "app_store"
    source = "official_app_store"

    def collect(
        self,
        request: AlternativeDataRequest,
        *,
        seed_observations: list[dict[str, Any]] | None = None,
    ) -> ConnectorResult:
        rows = [row for row in seed_observations or [] if row.get("source") in {"official_app_store", "app_store"}]
        if not rows:
            return empty_connector_result(
                connector_id=self.connector_id,
                missing=["app_store_cached_pages_or_ranking_api"],
                notes=["App-store live collection is not configured in V1."],
            )
        raw_observations = []
        metrics = []
        metric_specs = [
            ("demand.app.rank.shopping", "rank_shopping", "rank"),
            ("trust.rating.average", "rating", "stars"),
            ("demand.app.review_count", "review_count", "count"),
            ("demand.app.version_update_frequency", "version_update_frequency", "updates_per_period"),
        ]
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
            for metric_name, payload_key, unit in metric_specs:
                if payload_key not in payload:
                    continue
                metrics.append(
                    metric_from_observation(
                        observation,
                        metric_name=metric_name,
                        value=payload[payload_key],
                        unit=unit,
                        region=payload.get("region") or request.get("region", ""),
                        source=self.source,
                        confidence=score_confidence(source=self.source, sample_size=len(rows)),
                        date_value=payload.get("date") or row.get("collected_at", "")[:10],
                        time_window=request.get("time_window", "weekly"),
                        metadata={"store": payload.get("store"), "category": payload.get("category")},
                    )
                )
        return {
            "connector_id": self.connector_id,
            "status": "collected_from_seed_observations",
            "raw_observations": raw_observations,
            "metrics": metrics,
            "text_events": [],
            "notes": ["Normalized app-store rank/rating/review observations."],
            "missing": [],
        }


def _default_brand(request: AlternativeDataRequest) -> str:
    brands = request.get("brands") or [request.get("company", "")]
    return brands[0]
