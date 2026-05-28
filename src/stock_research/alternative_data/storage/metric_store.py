from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stock_research.alternative_data.models import NormalizedMetric


def write_metric_store(
    run_dir: str | Path,
    metrics: list[NormalizedMetric],
    metric_summaries: list[dict[str, Any]],
) -> str:
    path = Path(run_dir) / "alternative_data_metrics.json"
    path.write_text(
        json.dumps(
            {"metrics": metrics, "metric_summaries": metric_summaries},
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return str(path)
