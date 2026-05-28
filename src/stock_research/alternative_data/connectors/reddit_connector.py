from __future__ import annotations

from typing import Any

from stock_research.alternative_data.connectors.base import AlternativeDataConnector, empty_connector_result
from stock_research.alternative_data.models import AlternativeDataRequest, ConnectorResult
from stock_research.alternative_data.normalization.confidence_scorer import score_confidence
from stock_research.alternative_data.normalization.metric_normalizer import (
    metric_from_observation,
    observation_from_payload,
    text_event_from_observation,
)


KEYWORD_TOPICS = {
    "refund": ["refund", "return", "customer_service"],
    "shipping": ["shipping", "delivery", "logistics"],
    "quality": ["quality", "product_quality"],
    "scam": ["scam", "trust"],
    "repeat_purchase": ["again", "repeat_purchase", "reorder"],
}


class RedditConnector(AlternativeDataConnector):
    connector_id = "reddit_forum"
    source = "reddit"

    def collect(
        self,
        request: AlternativeDataRequest,
        *,
        seed_observations: list[dict[str, Any]] | None = None,
    ) -> ConnectorResult:
        rows = [row for row in seed_observations or [] if row.get("source") in {"reddit", "forum"}]
        if not rows:
            return empty_connector_result(
                connector_id=self.connector_id,
                missing=["reddit_api_credentials_or_cached_forum_observations"],
                notes=[
                    "Reddit/forum live collection is not configured in V1.",
                    "Text should be retained with source logging and passed to Customer Sentiment Agent.",
                ],
            )
        raw_observations = []
        text_events = []
        metrics = []
        aggregate_counts: dict[tuple[str, str, str], int] = {}
        for row in rows:
            payload = row.get("raw_payload", row)
            source = row.get("source", "reddit")
            observation = observation_from_payload(
                company=request["company"],
                brand=row.get("brand") or _default_brand(request),
                source=source,
                payload=payload,
                source_url=row.get("source_url", ""),
                collected_at=row.get("collected_at"),
            )
            raw_observations.append(observation)
            text = str(payload.get("text") or payload.get("title") or "")
            created_at = payload.get("created_at") or row.get("collected_at", "")
            if text:
                topics = _topic_hints(text)
                text_events.append(
                    text_event_from_observation(
                        observation,
                        text=text,
                        created_at=created_at,
                        author_id=str(payload.get("author_id", "")),
                        engagement={
                            "upvotes": payload.get("upvotes"),
                            "comments": payload.get("comments"),
                        },
                        topic_hint=topics,
                    )
                )
                period_date = created_at[:10] or row.get("collected_at", "")[:10]
                for topic in topics:
                    aggregate_counts[(period_date, source, topic)] = aggregate_counts.get((period_date, source, topic), 0) + 1
                aggregate_counts[(period_date, source, "post_count")] = aggregate_counts.get((period_date, source, "post_count"), 0) + 1
                aggregate_counts[(period_date, source, "comment_count")] = aggregate_counts.get((period_date, source, "comment_count"), 0) + int(payload.get("comments") or 0)

        for (period_date, source, topic), count in aggregate_counts.items():
            metric_name = _topic_metric_name(topic, source=source)
            observation = raw_observations[0]
            metrics.append(
                metric_from_observation(
                    observation,
                    metric_name=metric_name,
                    value=count,
                    unit="count",
                    region=request.get("region", ""),
                    source=source,
                    confidence=score_confidence(source=source, sample_size=len(rows)),
                    date_value=period_date,
                    time_window=request.get("time_window", "weekly"),
                    metadata={"topic": topic},
                )
            )
        return {
            "connector_id": self.connector_id,
            "status": "collected_from_seed_observations",
            "raw_observations": raw_observations,
            "metrics": metrics,
            "text_events": text_events,
            "notes": ["Normalized Reddit/forum metadata and text events."],
            "missing": [],
        }


def _topic_hints(text: str) -> list[str]:
    lower = text.lower()
    topics = []
    for topic, terms in KEYWORD_TOPICS.items():
        if any(term in lower for term in terms):
            topics.append(topic)
    return topics


def _topic_metric_name(topic: str, *, source: str) -> str:
    if topic == "post_count":
        return f"demand.social.{source}.post_count"
    if topic == "comment_count":
        return f"demand.social.{source}.comment_count"
    return f"trust.negative_keyword.{topic}"


def _default_brand(request: AlternativeDataRequest) -> str:
    brands = request.get("brands") or [request.get("company", "")]
    return brands[0]
