"""Watchlist configuration loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import WatchlistConfig


def _load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
    except ModuleNotFoundError:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping config in {path}")
    return data


def load_watchlist(path: str | Path) -> WatchlistConfig:
    return WatchlistConfig.from_dict(_load_mapping(Path(path)))

