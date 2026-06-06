"""Configuration loading helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import BasketConfig, CrawlerSettings


def _load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
    except ModuleNotFoundError:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


def load_basket_config(path: str | Path) -> BasketConfig:
    return BasketConfig.model_validate(_load_mapping(Path(path)))


def load_crawler_settings(path: str | Path | None) -> CrawlerSettings:
    if path is None:
        return CrawlerSettings()
    return CrawlerSettings.model_validate(_load_mapping(Path(path)))
