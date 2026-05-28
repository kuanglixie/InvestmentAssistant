from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stock_research.alternative_data.models import RawObservation


def load_seed_observations(paths: list[str | Path]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for path_value in paths:
        path = Path(path_value)
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            observations.extend(item for item in payload if isinstance(item, dict))
        elif isinstance(payload, dict):
            rows = payload.get("observations")
            if isinstance(rows, list):
                observations.extend(item for item in rows if isinstance(item, dict))
    return observations


def write_raw_observations(run_dir: str | Path, observations: list[RawObservation]) -> str:
    path = Path(run_dir) / "alternative_data_raw_observations.json"
    path.write_text(json.dumps(observations, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return str(path)
