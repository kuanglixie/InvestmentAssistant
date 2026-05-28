from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from stock_research.alternative_data.models import NormalizedMetric, RawObservation, TextEvent
from stock_research.alternative_data.normalization.time_series_builder import period_for_date


def stable_hash(payload: Any) -> str:
    serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def observation_from_payload(
    *,
    company: str,
    brand: str,
    source: str,
    payload: dict[str, Any],
    source_url: str = "",
    collected_at: str | None = None,
) -> RawObservation:
    content_hash = stable_hash({"source": source, "source_url": source_url, "payload": payload})
    return {
        "observation_id": str(uuid.uuid5(uuid.NAMESPACE_URL, content_hash)),
        "company": company,
        "brand": brand,
        "source": source,
        "source_url": source_url,
        "collected_at": collected_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "raw_payload": payload,
        "content_hash": content_hash,
    }


def metric_from_observation(
    observation: RawObservation,
    *,
    metric_name: str,
    value: float | int,
    unit: str,
    region: str,
    source: str,
    confidence: str,
    date_value: str,
    time_window: str,
    metadata: dict[str, Any] | None = None,
) -> NormalizedMetric:
    period = period_for_date(date_value, time_window=time_window)
    metric_key = {
        "observation_id": observation["observation_id"],
        "metric_name": metric_name,
        "period": period,
        "region": region,
    }
    return {
        "metric_id": str(uuid.uuid5(uuid.NAMESPACE_URL, stable_hash(metric_key))),
        "company": observation["company"],
        "brand": observation["brand"],
        "metric_name": metric_name,
        "value": value,
        "unit": unit,
        "period": period,
        "region": region,
        "source": source,
        "confidence": confidence,  # type: ignore[typeddict-item]
        "metadata": metadata or {},
    }


def text_event_from_observation(
    observation: RawObservation,
    *,
    text: str,
    created_at: str,
    author_id: str = "",
    engagement: dict[str, Any] | None = None,
    topic_hint: list[str] | None = None,
) -> TextEvent:
    event_key = stable_hash(
        {
            "observation_id": observation["observation_id"],
            "text": text,
            "created_at": created_at,
            "author_id": author_id,
        }
    )
    author_hash = hashlib.sha256(author_id.encode("utf-8")).hexdigest() if author_id else ""
    return {
        "text_event_id": str(uuid.uuid5(uuid.NAMESPACE_URL, event_key)),
        "company": observation["company"],
        "brand": observation["brand"],
        "source": observation["source"],
        "text": text,
        "author_id_hash": author_hash,
        "created_at": created_at,
        "engagement": engagement or {},
        "topic_hint": topic_hint or [],
    }
