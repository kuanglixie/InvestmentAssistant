# Investment Assistant Repo Map

This is the consolidated working repo for the investment assistant. It copies the maintainable source files from the earlier project folders while leaving heavy runtime outputs, caches, virtual environments, and raw downloaded data in the original locations.

## Primary System

- `src/stock_research/` - main multi-agent research system.
- `config/` - company registry, source policy, watchlists, learning registry, qualitative source configs, and manual market inputs.
- `docs/` - system design notes, agent instructions, methodology drafts, and research playbooks.
- `tests/` - regression tests for the core scaffold.
- `tools/` - small local helper scripts.

## Key Agent Areas

- `src/stock_research/official_evidence/` - official report evidence pack builder.
- `src/stock_research/reports/` - Markdown and easy-reading report renderers.
- `src/stock_research/qualitative/` - business model, moat, right-people, public-voice, executive-transcript, and official-event evidence modules.
- `src/stock_research/comparator_evidence/` - competitor-as-evidence pipeline for mapping competitive battlefields, source reliability, comparison matrices, and target-company implications.
- `src/stock_research/alternative_data/` - alternative-data collection, normalization, storage, and signal-pack output.
- `src/stock_research/alternative_data/collectors/` - investment-question-level collectors, including Product/Pricing/Policy and Competitor Source V1 packs.
- `src/stock_research/alternative_data/digital_demand_monitor/` - PDD/Temu demand, app, web, review, ads, and promotion signal monitor.
- `src/stock_research/alternative_data/temu_product_intelligence/` - Temu product-card, fixed-basket, and surface-intelligence monitor.
- `src/stock_research/alternative_data/merchant_regulatory_monitor/` - Temu merchant-policy, merchant-voice, product-safety, trade-policy, and consumer-protection event monitor.
- `src/stock_research/valuation/` - market and valuation input handling.

## Prototypes

- `prototypes/reddit-public-voice-monitor/` - Reddit/public-voice wrapper that exports Temu discussion evidence into demand-monitor review records.
- `prototypes/earnings-call-transcripts/` - transcript fetching and local ingestion scripts.
- `prototypes/webcast-transcripts/` - webcast inspection and transcript conversion scripts.
- `prototypes/bilibili-video-qa/` - video transcript Q&A prototype.

The PDD digital demand monitor and Temu product intelligence monitor have been promoted out of `prototypes/` into the main `stock_research.alternative_data` package.

## Runtime Data

- `data/runs/` - research run outputs.
- `data/raw/` - downloaded filings and raw source cache.
- `data/monitoring/` - monitor outputs.
- `data/automation/` - automation-local outputs.
- `data/alternative_data/` - local runtime outputs for integrated alternative-data monitors.

These directories are recreated by the CLI and ignored by git.

## Provenance

Main source copied from:

- `/Users/ajing/Documents/Codex/2026-05-24/are-you-able-to-help-me`

Prototype source copied from:

- `/Users/ajing/Documents/Codex/2026-05-25/langchain-investment-prototypes`

Historical prototype notes are preserved under `docs/prototype-history/`.
