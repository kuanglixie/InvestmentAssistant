from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from stock_research.alternative_data.models import AlternativeDataRequest, ConnectorResult, NormalizedMetric, RawObservation, TextEvent
from stock_research.alternative_data.normalization.deduplicator import dedupe_by_key
from stock_research.alternative_data.normalization.time_series_builder import aggregate_metric_series


def build_signal_pack(
    *,
    request: AlternativeDataRequest,
    connector_results: list[ConnectorResult],
) -> dict[str, Any]:
    raw_observations: list[RawObservation] = []
    metrics: list[NormalizedMetric] = []
    text_events: list[TextEvent] = []
    for result in connector_results:
        raw_observations.extend(result.get("raw_observations", []))
        metrics.extend(result.get("metrics", []))
        text_events.extend(result.get("text_events", []))

    raw_observations = dedupe_by_key(raw_observations, "observation_id")  # type: ignore[arg-type]
    metrics = dedupe_by_key(metrics, "metric_id")  # type: ignore[arg-type]
    text_events = dedupe_by_key(text_events, "text_event_id")  # type: ignore[arg-type]
    metric_summaries = aggregate_metric_series(metrics)
    source_counts = Counter(metric.get("source", "unknown") for metric in metrics)
    connector_status = {
        result.get("connector_id", "unknown"): {
            "status": result.get("status"),
            "missing": result.get("missing", []),
            "notes": result.get("notes", []),
            "raw_observations": len(result.get("raw_observations", [])),
            "metrics": len(result.get("metrics", [])),
            "text_events": len(result.get("text_events", [])),
        }
        for result in connector_results
    }
    company = request.get("company", "")
    brands = request.get("brands") or [company]
    return {
        "agent_id": "alternative_data",
        "status": "collected" if metrics or text_events else "configured_pending_collection",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "request": request,
        "company": company,
        "brands": brands,
        "as_of_date": datetime.now(UTC).date().isoformat(),
        "region": request.get("region", ""),
        "time_window": request.get("time_window", "weekly"),
        "raw_observation_count": len(raw_observations),
        "normalized_metric_count": len(metrics),
        "text_event_count": len(text_events),
        "metric_summary_count": len(metric_summaries),
        "source_counts": dict(sorted(source_counts.items())),
        "connector_status": connector_status,
        "raw_observations": raw_observations,
        "normalized_metrics": metrics,
        "text_events": text_events,
        "metric_summaries": metric_summaries,
        "rules": [
            "Agent does not make investment conclusions.",
            "Agent does not judge moat, sentiment, valuation, or buy/sell.",
            "Text events are passed downstream for customer sentiment analysis.",
            "E-commerce metrics require a fixed product basket for comparable time series.",
        ],
    }
