from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stock_research.alternative_data.connectors import (
    AppStoreConnector,
    EcommerceCrawler,
    GoogleTrendsConnector,
    RedditConnector,
    YouTubeConnector,
)
from stock_research.alternative_data.models import AlternativeDataRequest
from stock_research.alternative_data.output.signal_pack_builder import build_signal_pack
from stock_research.alternative_data.storage.metric_store import write_metric_store
from stock_research.alternative_data.storage.raw_observation_store import load_seed_observations, write_raw_observations
from stock_research.alternative_data.storage.text_event_store import write_text_event_store
from stock_research.state import ResearchState


DEFAULT_COMPANY_CONFIG = Path("config/alternative_data/company_universe.v1.json")
DEFAULT_SOURCE_CONFIG = Path("config/alternative_data/source_config.v1.json")
DEFAULT_KEYWORD_TAXONOMY = Path("config/alternative_data/keyword_taxonomy.v1.json")


def collect_alternative_data_signals(
    state: ResearchState,
    *,
    company_config_path: str | Path = DEFAULT_COMPANY_CONFIG,
    source_config_path: str | Path = DEFAULT_SOURCE_CONFIG,
    keyword_taxonomy_path: str | Path = DEFAULT_KEYWORD_TAXONOMY,
) -> dict[str, Any]:
    request = request_from_state(
        state,
        company_config_path=company_config_path,
        keyword_taxonomy_path=keyword_taxonomy_path,
    )
    return collect_alternative_data_signals_for_request(
        request,
        run_dir=state["run_dir"],
        source_config_path=source_config_path,
    )


def collect_alternative_data_signals_for_request(
    request: dict[str, Any],
    *,
    run_dir: str,
    source_config_path: str | Path = DEFAULT_SOURCE_CONFIG,
) -> dict[str, Any]:
    typed_request: AlternativeDataRequest = {
        "company": str(request.get("company", "")),
        "brands": [str(item) for item in request.get("brands", [])],
        "competitors": [str(item) for item in request.get("competitors", [])],
        "region": str(request.get("region", "US")),
        "time_window": str(request.get("time_window", "weekly")),
        "lookback_weeks": int(request.get("lookback_weeks", 52)),
        "keywords": [str(item) for item in request.get("keywords", [])],
    }
    source_config = _load_json(source_config_path)
    seed_paths = [Path(run_dir) / "alternative_data_seed_observations.json"]
    seed_paths.extend(Path(path) for path in source_config.get("seed_observation_paths", []))
    seed_observations = load_seed_observations(seed_paths)
    connectors = [
        GoogleTrendsConnector(),
        YouTubeConnector(),
        RedditConnector(),
        AppStoreConnector(),
        EcommerceCrawler(),
    ]
    connector_results = [
        connector.collect(typed_request, seed_observations=seed_observations)
        for connector in connectors
        if _connector_enabled(source_config, connector.connector_id)
    ]
    signal_pack = build_signal_pack(request=typed_request, connector_results=connector_results)
    signal_pack["raw_observation_store_path"] = write_raw_observations(
        run_dir,
        signal_pack.get("raw_observations", []),
    )
    signal_pack["metric_store_path"] = write_metric_store(
        run_dir,
        signal_pack.get("normalized_metrics", []),
        signal_pack.get("metric_summaries", []),
    )
    signal_pack["text_event_store_path"] = write_text_event_store(
        run_dir,
        signal_pack.get("text_events", []),
    )
    return signal_pack


def request_from_state(
    state: ResearchState,
    *,
    company_config_path: str | Path = DEFAULT_COMPANY_CONFIG,
    keyword_taxonomy_path: str | Path = DEFAULT_KEYWORD_TAXONOMY,
) -> AlternativeDataRequest:
    company = state.get("canonical_company") or {}
    company_id = str(company.get("company_id") or state.get("company_query", "")).lower()
    universe = _load_json(company_config_path)
    taxonomy = _load_json(keyword_taxonomy_path)
    configured = (universe.get("companies") or {}).get(company_id, {})
    brands = configured.get("brands") or company.get("common_names") or [state.get("company_query", "")]
    keywords = configured.get("keywords") or _keywords_for_brands(brands, taxonomy)
    return {
        "company": configured.get("company") or str(state.get("company_query", "")),
        "brands": [str(item) for item in brands],
        "competitors": [str(item) for item in configured.get("competitors", [])],
        "region": str(configured.get("region", "US")),
        "time_window": str(configured.get("time_window", "weekly")),
        "lookback_weeks": int(configured.get("lookback_weeks", 52)),
        "keywords": [str(item) for item in keywords],
    }


def _load_json(path_value: str | Path) -> dict[str, Any]:
    path = Path(path_value)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _connector_enabled(source_config: dict[str, Any], connector_id: str) -> bool:
    connectors = source_config.get("connectors") or {}
    if connector_id not in connectors:
        return True
    return bool(connectors[connector_id].get("enabled", True))


def _keywords_for_brands(brands: list[str], taxonomy: dict[str, Any]) -> list[str]:
    suffixes = taxonomy.get("default_keyword_suffixes") or ["", "review", "refund", "scam"]
    keywords = []
    for brand in brands:
        for suffix in suffixes:
            keyword = f"{brand} {suffix}".strip()
            if keyword:
                keywords.append(keyword)
    return keywords
