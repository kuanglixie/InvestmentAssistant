from __future__ import annotations

from stock_research.alternative_data.normalization.time_series_builder import aggregate_metric_series


def run_weekly_aggregation_job(metrics: list[dict]) -> list[dict]:
    return aggregate_metric_series(metrics)
