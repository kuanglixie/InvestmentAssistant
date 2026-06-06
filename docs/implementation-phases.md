# Implementation Phases

> Status: Archived historical planning note.
> This document is retained for context, but it should not be used as the primary design source. Current active references are `docs/financial-results-report-methodology-v1.md`, `docs/metrics-formula-requirements-v1.md`, `docs/human-involved-decision-points.md`, `docs/technical-architecture-v1.md`, and `docs/agent-improvement-backlog.md`.

## Phase 1: Runnable Scaffold

Status: done.

Output:

- CLI entrypoint.
- Placeholder V1 agents.
- Shared state.
- Run folders.
- Audit log.
- Markdown report.
- Basic tests.

## Phase 2: Real PDD Source Pipeline

Status: done for SEC cache; PDD IR fetch remains best-effort.

Goal:

Resolve PDD and fetch official source documents.

Output:

- PDD company resolver with SEC identity where available.
- SEC submissions metadata.
- PDD investor-relations source records.
- All available PDD filing metadata indexed.
- Real financial reports downloaded and cached locally.
- Prioritize all available 20-F annual reports and important 6-K financial-result filings.
- Do not download every ownership or administrative filing unless it becomes relevant.

Confirmed rules:

- SEC User-Agent: `stock-research-system/0.1 your_email@example.com`
- Live public SEC and PDD IR fetches are approved.
- Raw cache under `data/raw/` is approved.

## Phase 3: Financial Fact Extraction

Status: first pass done for cached SEC inline XBRL annual and selected 6-K documents.

Goal:

Extract real financial facts from official PDD reports.

Initial facts:

- Revenue.
- Gross profit.
- Operating income.
- Net income.
- Operating cash flow.
- CapEx.
- Free cash flow.
- Cash.
- Debt.
- Stock-based compensation.
- Diluted shares / ADS context.
- Total assets.
- Total liabilities.

Scope:

- Extract both annual fiscal-year data and quarterly data from relevant 6-Ks.

## Phase 4: Verification And Reconciliation

Status: first pass done for duplicate official facts.

Goal:

Cross-check extracted facts and flag conflicts.

Rules:

- Official filings and company IR are source of record.
- Third-party databases may be used only as sanity checks.
- Material mismatch threshold: more than 2%.
- Rounding differences are accepted automatically if clearly explained.
- Material conflicts require human review.
- Official IR annual-report PDFs are now configured for cross-validation where available.
- If a PDF is unreachable locally, the agent falls back to the cached SEC HTML copy of the same official 20-F and records that fallback.
- Missing fields can be filled from official annual-report text with separate data lineage.

## Phase 5: Metrics Engine

Status: first pass done for Owner Earnings V1, cash conversion, and unlevered ROIC.

Goal:

Calculate metrics from verified facts.

Confirmed V1 choices:

- Owner Earnings V1 uses D&A as maintenance CapEx approximation:
  `Owner Earnings = OCF - SBC - D&A`
- EV V1 subtracts all cash:
  `EV = Market Cap + Debt - Cash`
- EV report must flag that not all cash may be excess, freely distributable, or usable.
- ROIC should be calculated but no threshold should be applied.

## Phase 6: Bilingual Markdown Report

Status: partially done.

Goal:

Produce a more useful bilingual Markdown research report.

Rules:

- Report should be bilingual.
- Every report should end with a checklist:
  - Right business model.
  - Right people.
  - Right price.
- Do not produce a final investment conclusion yet.
- Checklist items may be marked `not assessed yet` until later agents exist.

## Phase 7: Learning-Material Ingestion

Status: scaffold done.

Goal:

Ingest the user's Google Drive investment notes and create candidate lessons.

Source:

- Google Drive folder: https://drive.google.com/drive/u/0/folders/1wjHQ2QXtY--p9Q0iotipCxK4NyVEqo-1

Rules:

- Lessons should be grouped by agent.
- Statuses: `candidate`, `approved`, `rejected`, `retired`.
- Only `approved` lessons can change agent behavior.

Implemented artifacts:

- `config/learning/user_lessons.v1.json`
- `data/learning_lessons_report.md`
- `learning_materials` agent in the research graph.

## Phase 8: Watchlist Monitoring Skeleton

Status: scaffold done.

Goal:

Support weekly watchlist monitoring.

Companies:

- PDD.
- Tencent.
- Google / Alphabet.

Cadence:

- Weekly.

Triggers:

- New filing.
- Management change.

No price-drop trigger for now.

Implemented artifacts:

- `config/watchlist.json`
- `src/stock_research/monitoring/watchlist.py`
- CLI command: `monitor`

## Phase 9: Tencent Expansion

Status: identity/source metadata scaffold done.

Goal:

Add Tencent after PDD.

Output:

- Tencent company identity.
- HKEX and Tencent IR source handling.
- Chinese and English source metadata.

## Phase 10: Google Expansion

Status: identity/source metadata scaffold done.

Goal:

Add Google / Alphabet after Tencent.

Output:

- Google company identity.
- SEC and Alphabet IR source handling.

## Phase 11: Full Research Agents

Status: separate agent skeletons done; annual-report evidence markers added for business model/moat and leadership/people. Deeper source collectors and analysis logic still pending.

Goal:

Add non-financial agents as separate agents.

Implementation order:

1. Business Model / Moat Agent.
2. Leadership / People Agent.
3. Valuation Agent.
4. Customer Happiness Agent.
5. Competitor Comparison Agent.

Source rules:

- Leadership sources may include interviews, earnings calls, shareholder letters, YouTube, Bilibili, podcasts, and media reports with source-quality labels.
- Customer happiness sources may include Reddit, YouTube, Bilibili, forums, app reviews, product reviews, and other customer/community channels with source-quality labels.
