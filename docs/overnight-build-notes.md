# Overnight Build Notes

> Status: Archived historical planning note.
> This document is retained for context, but it should not be used as the primary design source. Current active references are `docs/financial-results-report-methodology-v1.md`, `docs/metrics-formula-requirements-v1.md`, `docs/human-involved-decision-points.md`, `docs/technical-architecture-v1.md`, and `docs/agent-improvement-backlog.md`.

Generated: 2026-05-25

## What Is Working

- PDD research run is executable through `PYTHONPATH=src python3 -m stock_research.cli research --company PDD --market us-adr`.
- The graph runs as a LangGraph `StateGraph` when LangGraph is installed, and falls back to the local sequential runner when dependencies are unavailable.
- PDD SEC identity and cached filing metadata are working.
- PDD cached official documents include 8 annual 20-F filings and 266 historical 6-K package files.
- SEC documents are now categorized into annual reports, interim earnings, governance, financing/capital-markets, wrapper metadata, and SEC helper files.
- The final report now includes a quarterly financial table extracted from official 6-K earnings-release exhibits.
- The final report now includes annual source lineage for key facts, including source document and XBRL tag or extraction method.
- Financial extraction reads locally cached SEC inline XBRL and selects official facts.
- Verification flags duplicate official facts with mismatches above the 2% materiality rule; the latest PDD run has no material conflicts.
- IR annual-report/PDF cross-validation now compares official annual-report text against SEC extracted facts and can fill missing fields with separate lineage.
- Metrics currently calculate Owner Earnings V1, cash conversion, unlevered ROIC, EV, owner earnings yield, and FCF yield where facts exist.
- The Market Data Agent now calculates PDD market cap from Google Finance ADS price, Google Finance USD/CNY, and official PDD 20-F share structure, with Yahoo Finance and Google market-cap cross-checks.
- The final Markdown report includes a bilingual learning section and right business / right people / right price checklist.
- Candidate learning lessons from the user's Drive notes are stored in `config/learning/user_lessons.v1.json`.
- The learning registry report is generated at `data/learning_lessons_report.md`.
- Business model/moat and leadership/people agents now collect annual-report evidence markers from the latest cached 20-F.
- Watchlist monitoring skeleton is available through `PYTHONPATH=src python3 -m stock_research.cli monitor`.
- Tencent now has a first official-source pipeline: Tencent IR financial report indexing, PDF caching, and latest annual-report financial extraction.
- The Market Data Agent now calculates Tencent market cap from Google Finance 0700:HKG, Google Finance HKD/CNY, and official Tencent annual-report issued shares, with Yahoo Finance quote cross-checking.
- Alphabet/Google has identity and source metadata in `config/company_registry.json`.

## Current Latest PDD Run

- Run directory: `data/runs/20260526T005147Z-pdd`
- Final report: `data/runs/20260526T005147Z-pdd/final_report.md`
- Graph backend: local sequential fallback
- Human review required: false; only tiny diluted-share rounding differences remain.
- Latest calculated valuation metrics: EV RMB 805.3B, owner earnings yield 12.2%, FCF yield 13.1%.

## Current Latest Tencent Run

- Run directory: `data/runs/20260526T015358Z-tencent`
- Final report: `data/runs/20260526T015358Z-tencent/final_report.md`
- Graph backend: local sequential fallback
- Human review required: false.
- Official Tencent IR documents cached: 22 annual reports and 22 interim reports.
- V1 extraction uses the latest annual report's five-year financial summary plus latest two-year audited statement tables.
- Latest calculated metrics: EV RMB 3690.3B, owner earnings yield 5.7%, FCF yield 5.2%, Owner Earnings V1 RMB 211.4B, cash conversion 1.35, unlevered ROIC 14.6%.

## Important Recorded Issues

- PDD IR home fetch is currently unavailable or timing out in this environment; SEC filings are the usable official source.
- The configured PDD 2025 IR annual-report PDF URL is correct, but the cross-validation agent currently falls back to the cached SEC HTML copy of the same 20-F when direct IR access fails.
- The previous three official duplicate-fact conflicts were resolved by separating accounting concepts:
  - Pretax income before equity-method results is now distinct from pretax income after equity-method results.
  - Stock-based compensation now uses the cash-flow addback tag instead of mixing in the operating-expense allocation table.
- Recent direct CapEx tags were missing from the initial XBRL mapper; the IR cross-validation agent now fills 2023-2025 CapEx from the official annual-report line for purchases of property, equipment, software and intangible assets.
- Some older quarterly rows have blanks where the cached 6-K exhibit did not expose that item cleanly through the V1 table parser; missing values remain blank rather than inferred.
- Market-price-dependent PDD metrics now calculate from live quote/FX data. If Google/Yahoo price mismatch exceeds 1% or calculated market cap differs from Google market cap by more than 3%, the valuation is flagged for review.
- Tencent HKEX cross-validation is not implemented yet; Tencent V1 currently uses Tencent IR as the official source.
- Tencent market-data/yield valuation now calculates from quote, FX, and official issued shares. Google Finance shares outstanding differs from Tencent's official issued share count, so V1 uses Tencent's annual-report share count and records the vendor-share-count difference as a warning.
- Alphabet/Google source downloader is not implemented yet; only identity/source metadata is configured.
- Management-change monitoring is only a skeleton. It records the trigger but does not scan leadership sources yet.

## Assumptions Used Without Asking

- No candidate lesson is activated automatically. All lessons remain `candidate`.
- The monitor uses cached local data only and does not ask for network access.
- Tencent V1 starts with Tencent IR as official source and plans HKEX as the next official-source cross-check.
- Alphabet/Google is configured as a U.S. SEC filer under Alphabet Inc.
- Watchlist triggers remain `new_filing` and `management_change`; price-drop monitoring is omitted.

## Suggested Next Engineering Work

- Add Tencent HKEX cross-validation against the cached Tencent IR annual report facts.
- Add source collectors for business model/moat from annual report text.
- Add leadership source collection from filings, IR pages, interviews, and transcripts with source-quality labels.
- Add a source-corpus pruning command to archive or hide SEC helper files from the default review surface while keeping audit traceability.
