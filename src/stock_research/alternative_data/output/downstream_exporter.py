from __future__ import annotations

from typing import Any


def export_for_downstream_agents(signal_pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric_summaries": signal_pack.get("metric_summaries", []),
        "text_events": signal_pack.get("text_events", []),
        "connector_status": signal_pack.get("connector_status", {}),
        "rules": signal_pack.get("rules", []),
    }
