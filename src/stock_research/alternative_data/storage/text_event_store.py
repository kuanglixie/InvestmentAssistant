from __future__ import annotations

import json
from pathlib import Path

from stock_research.alternative_data.models import TextEvent


def write_text_event_store(run_dir: str | Path, text_events: list[TextEvent]) -> str:
    path = Path(run_dir) / "alternative_data_text_events.json"
    path.write_text(json.dumps(text_events, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return str(path)
