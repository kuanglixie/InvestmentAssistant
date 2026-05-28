from __future__ import annotations

from typing import Any

from stock_research.alternative_data.connectors.base import AlternativeDataConnector, empty_connector_result
from stock_research.alternative_data.models import AlternativeDataRequest, ConnectorResult
from stock_research.alternative_data.normalization.confidence_scorer import score_confidence
from stock_research.alternative_data.normalization.metric_normalizer import metric_from_observation, observation_from_payload


class YouTubeConnector(AlternativeDataConnector):
    connector_id = "youtube"
    source = "youtube"

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
                missing=["youtube_data_api_key_or_cached_search_results"],
                notes=[
                    "YouTube Data API is not configured in V1.",
                    "search.list costs quota, so production collection must cache query results aggressively.",
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
            metric_specs = [
                ("demand.social.youtube.video_count", "video_count", "count"),
                ("demand.social.youtube.view_count", "view_count_sum", "count"),
                ("demand.social.youtube.like_count", "like_count_sum", "count"),
                ("demand.social.youtube.comment_count", "comment_count_sum", "count"),
                ("demand.social.youtube.haul_video_count", "haul_video_count", "count"),
                ("trust.negative_keyword.youtube.video_count", "negative_keyword_video_count", "count"),
            ]
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
                        confidence=score_confidence(source=self.source, sample_size=int(payload.get("video_count", len(rows)) or 1)),
                        date_value=payload.get("date") or row.get("collected_at", "")[:10],
                        time_window=request.get("time_window", "weekly"),
                        metadata={"query": payload.get("query"), "lookback_days": payload.get("lookback_days")},
                    )
                )
        return {
            "connector_id": self.connector_id,
            "status": "collected_from_seed_observations",
            "raw_observations": raw_observations,
            "metrics": metrics,
            "text_events": [],
            "notes": ["Normalized YouTube search/engagement observations."],
            "missing": [],
        }


def _default_brand(request: AlternativeDataRequest) -> str:
    brands = request.get("brands") or [request.get("company", "")]
    return brands[0]
