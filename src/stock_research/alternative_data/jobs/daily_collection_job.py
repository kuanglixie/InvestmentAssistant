from __future__ import annotations

from typing import Any

from stock_research.alternative_data.agent import collect_alternative_data_signals_for_request


def run_daily_collection_job(request: dict[str, Any], *, run_dir: str) -> dict[str, Any]:
    return collect_alternative_data_signals_for_request(request, run_dir=run_dir)
