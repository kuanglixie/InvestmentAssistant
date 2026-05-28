from __future__ import annotations

from typing import Any, Literal, TypedDict


Confidence = Literal["high", "medium", "low"]


class AlternativeDataRequest(TypedDict, total=False):
    company: str
    brands: list[str]
    competitors: list[str]
    region: str
    time_window: str
    lookback_weeks: int
    keywords: list[str]


class RawObservation(TypedDict, total=False):
    observation_id: str
    company: str
    brand: str
    source: str
    source_url: str
    collected_at: str
    raw_payload: dict[str, Any]
    content_hash: str


class NormalizedMetric(TypedDict, total=False):
    metric_id: str
    company: str
    brand: str
    metric_name: str
    value: float | int
    unit: str
    period: str
    region: str
    source: str
    confidence: Confidence
    metadata: dict[str, Any]


class TextEvent(TypedDict, total=False):
    text_event_id: str
    company: str
    brand: str
    source: str
    text: str
    author_id_hash: str
    created_at: str
    engagement: dict[str, Any]
    topic_hint: list[str]


class ConnectorResult(TypedDict, total=False):
    connector_id: str
    status: str
    raw_observations: list[RawObservation]
    metrics: list[NormalizedMetric]
    text_events: list[TextEvent]
    notes: list[str]
    missing: list[str]
