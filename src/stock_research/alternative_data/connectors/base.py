from __future__ import annotations

from typing import Any

from stock_research.alternative_data.models import AlternativeDataRequest, ConnectorResult


class AlternativeDataConnector:
    connector_id = "base"
    source = "unknown"
    live_status = "configured_pending_live_connector"

    def collect(
        self,
        request: AlternativeDataRequest,
        *,
        seed_observations: list[dict[str, Any]] | None = None,
    ) -> ConnectorResult:
        raise NotImplementedError


def empty_connector_result(
    *,
    connector_id: str,
    missing: list[str],
    notes: list[str] | None = None,
) -> ConnectorResult:
    return {
        "connector_id": connector_id,
        "status": "configured_pending_collection",
        "raw_observations": [],
        "metrics": [],
        "text_events": [],
        "notes": notes or [],
        "missing": missing,
    }
