# Business Model Evidence Agent Data Source Coverage Tracker

Last updated: 2026-06-02 UTC

This tracker is the saved checklist for Business Model Evidence Agent data sources. It separates three things that are easy to mix together:

- what the agent needs,
- what is already downloaded or prototyped,
- what is already strong enough to appear in the current Business Model Evidence report.

Status labels:

- `covered_in_current_output`: already used by `business_model_evidence_agent_v0.1`.
- `downloaded_or_cached`: raw or processed data exists locally, but it may not yet be used in the current report.
- `prototype_connected`: code or prototype exists and is connected to the repo, but current run output may be empty or fixture-only.
- `registry_ready`: source targets are listed in config, but collection/parser/output is not robust yet.
- `missing_or_deferred`: not meaningfully collected yet, or intentionally deferred.

Key current outputs:

- Business Model Evidence JSON: `data/runs/20260530T033052Z-pdd/business_model_evidence.json`
- Business Model Evidence report: `data/runs/20260530T033052Z-pdd/business_model_evidence_report.md`
- Financial Evidence pack: `data/runs/20260530T033052Z-pdd/financial_report_pack.json`
- Source registry: `config/qualitative/pdd_business_model_source_coverage.v1.json`

Important repo note:

- The consolidated repo keeps code, configs, docs, and processed run artifacts.
- Heavy raw caches are mostly still in the original source repo: `/Users/ajing/Documents/Codex/2026-05-24/are-you-able-to-help-me/data/raw/`.

## Priority Source Coverage

| Priority | Source family | Business-model use | Reliability | Current status | Existing data / prototype evidence | Current gap / next step |
|---|---|---|---|---|---|---|
| P0 | Annual report / 20-F / 10-K | Official business description, issuer structure, revenue streams, risk factors, official management discussion | high | `covered_in_current_output` | PDD run has 295 documents in state; original raw SEC cache at `/Users/ajing/Documents/Codex/2026-05-24/are-you-able-to-help-me/data/raw/sec/0001737806/documents/`; current outputs include `financial_report_pack.json`, `official_report_evidence_pack.json`, and `business_model_evidence.json` | Keep raw cache path documented; copy selected raw filings into consolidated repo only if needed. |
| P0 | Revenue recognition notes | Who pays, for what service, when revenue is recognized, service/product economics | high | `covered_in_current_output` | Current Business Model Evidence report marks `revenue_recognition_notes = covered`; Q1 uses PDD 2025 20-F revenue recognition / business overview evidence | Add a more explicit revenue-recognition subtable: payer, service, recognition basis, gross/net clue, source excerpt. |
| P0 | Segment / geography disclosure | Separates Pinduoduo vs Temu, domestic vs international, product/geography economics, platform profitability | high | `covered_in_current_output` as a negative/partial finding | Current Business Model Evidence report marks `segment_geography_disclosure = partial_or_missing`; latest 20-F reader found `segment_structure = not_disclosed` | Need investor materials, earnings-call Q&A, and competitor/alternative data to partially infer what official segment disclosure does not provide. |
| P0 | Financial Evidence Agent output | Cross-checks claims about operating leverage, cash generation, capital intensity, working-capital quality, growth quality | high | `covered_in_current_output` | `data/runs/20260530T033052Z-pdd/financial_report_pack.json`; current Business Model Evidence Q8 uses diagnostics and financial health | Keep as mandatory input for every Business Model Evidence run. |
| P1 | Quarterly filings / 6-K / earnings releases | Latest revenue/margin trend, strategic investment pressure, recent business updates | high_to_medium | `covered_in_current_output` for financial trend; `downloaded_or_cached` for broader 6-K archive | Original PDD SEC cache has many 6-K files; current run uses latest quarterly/annual financial facts and material-event scan | Need clearer extraction of non-financial business-model updates from 6-K exhibits and earnings releases. |
| P1 | Merchant fee / seller terms / platform policy | Seller obligations, fees, penalties, returns/logistics burden, platform power, subsidy dependence | high_for_policy_facts | `registry_ready` plus original raw web-reader evidence | Registry group `merchant_platform_policy`; original raw public voice/web-reader includes `temu-seller-center-official.json` and seller-fee/search artifacts under `/Users/ajing/Documents/Codex/2026-05-24/are-you-able-to-help-me/data/raw/public_voice/pdd/` | Build dedicated policy-page parser and snapshot table; promote only official seller-center/policy facts to evidence. |
| P1 | Official customer policy pages | Shipping, returns, refunds, customer promises, friction points | high_for_policy_facts | `registry_ready` plus original raw web-reader evidence | Registry group `official_customer_policy`; original raw web-reader includes `temu-support-shipping-returns.json` | Parse policy pages into effective-date, promise, obligation, refund/return condition, geography. |
| P1 | Government / regulator / customs / consumer-protection sources | Trade, de minimis/customs exposure, DSA/platform obligations, FTC/consumer-protection risk | high_for_rule_or_enforcement_facts | `registry_ready` | Registry group `regulatory_trade_policy` has CBP, FTC, EU DSA, USCC targets | Add official-page/PDF snapshot collector; mark enforcement vs rule vs commentary. |
| P1 | Company product pages / app / website | Actual product surface, customer journey, price/value proposition, delivery promise, discount visibility | high_for_product_facts | `prototype_connected` | `src/stock_research/alternative_data/temu_product_intelligence/`; `data/comparator_evidence/pdd-comparator-mvp/comparator_evidence_pack.json` | Current Business Model Evidence run did not use fresh product-page observations; add product-surface evidence cards. |
| P2 | Earnings call transcripts | Management Q&A, strategy framing, margin/growth explanation, analyst pressure | medium | `covered_in_current_output` and `downloaded_or_cached` | Current state: `earnings_call_transcripts_collected`, 24 transcript records, 582 segments, 285 evidence items; original Alpha Vantage cache covers 2020Q1-2025Q4 plus local 2026Q1/webcast caches | Improve source-rights handling and add latest-call summary table by question. |
| P2 | Management interviews / public executive videos | Founder/management philosophy, business-model intent, customer/merchant framing, consistency over time | medium_for_management_claims | `covered_in_current_output` as management-context evidence; Gemini adapter still pending | Current state: executive transcript evidence collected, 4 transcript sources, 185 segments, 18 evidence items; original cache under `/Users/ajing/Documents/Codex/2026-05-24/are-you-able-to-help-me/data/raw/executive_transcripts/pdd/` | Add optional `gemini_youtube_video_understanding` adapter; label outputs as non-verbatim management claims. |
| P2 | Investor presentations / investor day | Management KPI narrative, strategic priorities, business-model slides, growth/margin framework | medium | `registry_ready` | Registry group `investor_presentations_and_events`; no current local investor-presentation raw cache found in consolidated repo | Add IR deck discovery/local PDF ingest and a slide/parser report section. |
| P2 | Competitor filings | Industry economics, alternative revenue model, margin/capital structure, copyability, disclosure comparison | medium_high | `registry_ready` | Registry group `competitor_official_filings`; comparator output exists at `data/comparator_evidence/pdd-comparator-mvp/comparator_evidence_pack.json` | Build official competitor filing parser for Alibaba, JD, Amazon, SHEIN/Shein-related sources before using as strong evidence. |
| P2 | Competitor product / pricing pages | Customer alternatives, price parity, delivery/service comparison, feature copyability | medium_high | `prototype_connected` / `registry_ready` | Registry group `competitor_product_pricing`; Temu product intelligence has fixed-basket extension point; comparator MVP output exists | Add controlled competitor basket snapshots and price/product comparison table. |
| P2 | Paid acquisition / promotion / search / web-rank signals | Whether growth is organic vs bought through ads/coupons; promotion dependence; demand momentum | medium_or_low | `prototype_connected` but not current evidence | Registry group `paid_acquisition_and_promotion_signals`; `src/stock_research/alternative_data/digital_demand_monitor/`; current run status shows alternative data configured but pending collection | Run live/public monitor when needed; keep as pattern evidence, not CAC proof. |
| P3 | App Store / Google Play reviews and ratings | App-level customer happiness, refund/delivery/quality complaints, demand quality clues | low_medium_to_medium | `prototype_connected` but not current evidence | Registry group `app_store_demand_quality`; app-store connector and digital demand monitor exist | Add current review/rating snapshots and topic summary; triangulate with official policy and financial evidence. |
| P3 | Public customer discussion / review sites / Reddit / forums | Customer trust, delivery/refund/product-quality issues, repeat behavior, promotion dependence | low_medium | `downloaded_or_cached` and `prototype_connected`; not core evidence | Original public voice cache includes many Reddit search/comment JSON files and web-reader review pages under `/Users/ajing/Documents/Codex/2026-05-24/are-you-able-to-help-me/data/raw/public_voice/pdd/` | Normalize into customer-evidence cards; keep as lead/pattern evidence. |
| P3 | Merchant / seller forums and complaint platforms | Seller profitability, ad ROI, penalties, returns/logistics burden, platform policy pain | low_medium | `downloaded_or_cached` as lead evidence; no strong collector yet | Original Reddit/public voice cache includes seller-fee/profit/search artifacts such as `search-temu-seller-fees-profit.json` and `search-temusellercenter-seller-fees-returns-penalties-profit.json` | Build merchant-economics collector with strict quality labels; do not treat anonymous claims as final evidence. |
| P3 | Alternative demand data: app rank, search trends, web/domain rank, product-surface metrics | Demand momentum, paid-acquisition intensity, promotion dependence, competitor pressure | medium_or_low | `prototype_connected` | `src/stock_research/alternative_data/digital_demand_monitor/`; `alternative_data_*` artifacts exist in current run but are mostly empty/pending | Run selected live/public snapshots; integrate only as supporting signal. |
| P4 | Analyst reports / expert networks / paid datasets | Hypotheses, industry context, channel checks, expert views | low_medium_to_medium depending source | `missing_or_deferred` | No production workflow in current repo | Defer until license/compliance workflow exists. |

## Current PDD Snapshot

| Area | Snapshot |
|---|---|
| Business Model Evidence Agent output | `business_model_evidence.json` and `business_model_evidence_report.md` generated for PDD from cached run `20260530T033052Z-pdd`. |
| P0 source status in current report | `revenue_recognition_notes = covered`; `financial_evidence_agent_output = covered`; `segment_geography_disclosure = partial_or_missing`. |
| Financial-report cache | Original raw SEC cache has PDD filings under `/Users/ajing/Documents/Codex/2026-05-24/are-you-able-to-help-me/data/raw/sec/0001737806/documents/`; consolidated run state has 295 documents. |
| Earnings calls | Current state records 24 transcript records, 582 segments, 285 evidence items. Original Alpha Vantage/local/webcast cache is under `/Users/ajing/Documents/Codex/2026-05-24/are-you-able-to-help-me/data/raw/official_event_transcripts/pdd/`. |
| Executive interviews | Current state records 4 collected transcript/interview sources, 185 segments, 18 evidence items. Original cache is under `/Users/ajing/Documents/Codex/2026-05-24/are-you-able-to-help-me/data/raw/executive_transcripts/pdd/`. |
| Public voice / customer / merchant lead evidence | Original cache has Reddit search/comment files and web-reader review/policy pages under `/Users/ajing/Documents/Codex/2026-05-24/are-you-able-to-help-me/data/raw/public_voice/pdd/`. |
| Alternative data | Current run has alternative-data artifact files, but collection status is pending/mostly empty. Code prototypes exist under `src/stock_research/alternative_data/`. |
| Investor presentations | Registry targets exist, but no current local investor-presentation cache was found in the consolidated repo. |
| Competitor evidence | Registry targets and comparator MVP artifact exist; robust competitor filing/product parser is still pending. |

## Next Update Rules

When a source line improves, update `Current status` conservatively:

1. Use `registry_ready` only when target URLs/config exist.
2. Use `downloaded_or_cached` only when local raw or processed files exist.
3. Use `prototype_connected` only when code can collect or normalize that source family.
4. Use `covered_in_current_output` only when the Business Model Evidence JSON/report actually consumes it.
5. Never upgrade management interviews, public voice, anonymous seller discussions, or alternative data above their evidence role unless a stronger source confirms the same claim.
