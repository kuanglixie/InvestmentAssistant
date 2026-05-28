# Alternative Data Agent V1

## Purpose

The Alternative Data Agent collects non-financial-report evidence and normalizes it into time-series metrics for downstream agents.

It does not make investment conclusions, moat judgments, sentiment interpretations, valuation calls, or buy/sell recommendations.

## Current V1 Behavior

- Reads a controlled company request from `config/alternative_data/company_universe.v1.json`.
- Reads connector settings from `config/alternative_data/source_config.v1.json`.
- Reads cached/manual observations from `data/runs/<run_id>/alternative_data_seed_observations.json` when present.
- Runs five connector adapters:
  - Google Trends
  - YouTube
  - Reddit / forum
  - app store
  - fixed-basket e-commerce crawler
- Writes:
  - `alternative_data_raw_observations.json`
  - `alternative_data_metrics.json`
  - `alternative_data_text_events.json`

## Output Contract

Main output lives in `state["alternative_data_findings"]` and contains:

- `raw_observations`
- `normalized_metrics`
- `metric_summaries`
- `text_events`
- `connector_status`

Every normalized metric keeps:

- metric name
- value
- unit
- period
- region
- source
- confidence
- metadata

Every metric summary adds:

- current value
- 1-week change
- 4-week change
- 13-week change
- 52-week percentile
- 52-week z-score
- source confidence
- interpretation hint

## Important Limits

- Live API connectors are intentionally pending until credentials, rate limits, and retention policies are configured.
- Google Trends is treated as medium confidence and production-unstable unless using an official API path.
- YouTube search collection must cache aggressively because search quota is expensive.
- Reddit/forum text is stored as evidence for the Customer Sentiment Agent; this agent only counts and routes it.
- E-commerce price/delivery metrics require a fixed product basket. Changing the basket breaks time-series comparability.

## Targeted Rerun

```bash
PYTHONPATH=src .venv/bin/python -m stock_research.cli rerun-alternative-data <run_id>
```

For example:

```bash
PYTHONPATH=src .venv/bin/python -m stock_research.cli rerun-alternative-data 20260527T223631Z-pdd
```
