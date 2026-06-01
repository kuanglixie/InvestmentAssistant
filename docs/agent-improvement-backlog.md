# Agent Improvement Backlog

Generated: 2026-05-26

## Purpose

This document is the central backlog for potential improvements to each agent in the stock research system.

Use it to record:

- current status,
- next improvements,
- priority,
- dependencies,
- decisions that need user review.

Detailed design notes can still live in agent-specific docs, but this file should be the first place to check when deciding what to build next.

## Priority Scale

- P0: reliability, source accuracy, or auditability blocker.
- P1: high-value capability for PDD/Tencent V1.
- P2: useful next capability after the core workflow is stable.
- P3: scalability, polish, or later generalization.

## Agent Summary

| Agent | Current Status | Main Gap | Priority |
| --- | --- | --- | --- |
| Company Resolver | Working for PDD, Tencent, Google | More robust entity/listing/share-class resolution | P2 |
| Source Discovery | Working with company-specific paths | Registry-based source selection and China/HK source hierarchy | P1 |
| Document Acquisition | Working for PDD SEC and Tencent IR PDFs | Better incremental refresh and source-specific retries | P1 |
| Financial Extraction | Stronger for PDD; usable for Tencent | Broader line-item coverage and PDF robustness | P0 |
| IR PDF Cross-Validation | PDD official report fallback exists | Tencent HKEX/company official cross-validation | P0 |
| Financial Verification | Official duplicate checks done | Third-party financial-statement sanity checks | P0 |
| Market Data | PDD/Tencent quote and FX paths exist | More explicit source freshness and quote fallback policy | P1 |
| Metrics | V1 metrics working | Better maintenance CapEx, excess cash, invested capital choices | P1 |
| Learning Materials | Candidate lesson registry works | Approval/activation workflow | P1 |
| Business Model / Moat | Official-report V1 working | Unit economics, industry map, moat scoring, kill criteria | P1 |
| External Moat Validation | PDD source plan exists | Turn source plan into actual collected evidence | P1 |
| Public Voice Evidence | Reddit/Sitejabber working for PDD | More source adapters and triangulation | P1 |
| Leadership / People | Scaffold plus annual-report markers | Real leadership source collection and incentive analysis | P1 |
| Video Transcript | PDD executive transcript V1 exists | Generalize YouTube/Bilibili transcript collection for all agents | P1 |
| Valuation | Yield-style V1 working | Scenario valuation and margin-of-safety framework | P1 |
| Customer Happiness | Scaffold; public voice adjacent evidence exists | Dedicated customer/product reception synthesis | P1 |
| Competitor Comparison | Scaffold | Run comparable workflows for Tencent/Google and compare | P2 |
| Report Builder | Main, financial-results, business-model, and data-linkage reports work | Right-people report and better evidence confidence display | P2 |
| Audit Review | Basic review gates work | More structured blocking gates and review dashboard | P1 |

## Backlog By Agent

### Company Resolver

Current status:

- Resolves PDD, Tencent, and Google from local registry.
- Handles basic legal name, ticker, market, exchange, CIK where available, and IR URL.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| CR-001 | Add share-class/listing resolver for ADR, HK, A-share, and dual-listed companies. | P2 | Important before adding more China/HK companies. |
| CR-002 | Record holding-company, operating-company, VIE, ADR, and exchange context as separate structured fields. | P1 | Useful for PDD/Tencent ownership-risk analysis. |
| CR-003 | Add identity conflict checks against SEC/HKEX/company IR metadata. | P2 | Prevent wrong-company research. |

### Source Discovery

Current status:

- PDD uses SEC EDGAR plus PDD IR source records.
- Tencent uses Tencent IR source metadata; HKEX cross-checking is planned.
- Google/Alphabet identity scaffolding exists.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| SD-001 | Add HKEX official source discovery for Tencent. | P0 | Needed for official-source cross-validation. |
| SD-002 | Formalize source hierarchy for US, ADR, HK, and China-listed companies. | P1 | Should include SEC, HKEX, company IR, 巨潮资讯, exchanges, and free sanity-check sources. |
| SD-003 | Move source selection toward a registry keyed by listing type and document type. | P3 | Scalability task after PDD/Tencent are stable. |
| SD-004 | Add source freshness and retry diagnostics to the run report. | P2 | Helps explain blocked IR/Reddit/third-party fetches. |

### Document Acquisition

Current status:

- Downloads/caches PDD SEC filings.
- Downloads/caches Tencent official IR PDF reports.
- Stores local paths and checksums.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| DA-001 | Add incremental refresh so runs avoid rechecking unchanged documents unnecessarily. | P2 | Helpful for weekly monitoring. |
| DA-002 | Add document-type sampling controls for 6-Ks and non-core SEC documents. | P2 | Prevent noisy 200+ document caches from obscuring core reports. |
| DA-003 | Add source-specific retry/backoff and clearer blocked-source classification. | P1 | Needed for Reddit/IR/web sources too. |
| DA-004 | Add cache inventory command for useful vs non-useful documents. | P2 | User asked earlier for document usefulness scanning. |

### Financial Extraction

Current status:

- PDD extraction is strong for SEC inline XBRL and selected 6-Ks.
- Tencent extraction reads official IR PDF annual/interim tables.
- Extracts core annual and quarterly facts.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| FE-001 | Expand mapped financial line items beyond the current core metrics. | P1 | Useful for deeper accounting and owner-earnings work. |
| FE-002 | Improve older PDD 6-K quarterly extraction where fields are blank. | P1 | Requires mapping more exhibit/table layouts. |
| FE-003 | Improve Tencent PDF extraction across older annual/interim layout changes. | P0 | Needed before all-history Tencent confidence. |
| FE-004 | Add KPI extraction from annual reports and MD&A. | P1 | Supports business-model and unit-economics agents. |
| FE-005 | Add quality-of-earnings flags: one-time gains, net/gross revenue, subsidies, investment income, classification changes. | P1 | From learning materials; should remain evidence-linked. |

### IR PDF Cross-Validation

Current status:

- PDD can cross-validate with official annual-report/PDF text where accessible, with SEC HTML fallback.
- Missing fields can be filled from official annual-report text with separate lineage.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| IR-001 | Add Tencent official annual/interim report cross-validation against HKEX filings. | P0 | Best next reliability task for Tencent. |
| IR-002 | Add clearer mismatch summaries by metric, year, source, and materiality. | P1 | Easier human review. |
| IR-003 | Add table-level source coordinates for PDFs where feasible. | P2 | Helps audit PDF extraction. |

### Financial Verification

Current status:

- Detects duplicate official-fact conflicts and accepts clear rounding differences under the 2% rule.
- Official sources remain source of record.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| FV-001 | Add third-party financial-statement sanity checks from reputable free sources. | P0 | Use only as sanity check, not source of record. |
| FV-002 | Add per-metric materiality policy where needed. | P2 | Some share-count or per-share fields may need different thresholds. |
| FV-003 | Add reconciliation status to data-linkage report for every key annual fact. | P1 | Makes audit stronger. |

### Market Data

Current status:

- PDD market data uses ADS price, Yahoo quote validation, USD/CNY, and official share structure.
- Tencent market data uses 0700.HK price, HKD/CNY, ordinary shares, and quote cross-checking.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| MD-001 | Add explicit quote freshness rules and stale-data warnings. | P1 | Important for valuation metrics. |
| MD-002 | Add fallback source policy for Yahoo/Google failures. | P1 | Avoid silent valuation gaps. |
| MD-003 | Add historical price context only when needed for valuation/monitoring. | P3 | Price-drop trigger is intentionally disabled for now. |

### Metrics

Current status:

- Calculates financial-quality metrics such as Owner Earnings V1, cash conversion, margins, capital intensity, SBC burden, balance-sheet risk, ROIC, and incremental ROIC.
- EV, FCF yield, owner-earnings yield, and investment-adjusted operating yield have been moved to the Valuation Agent.
- Does not apply ROIC thresholds.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| ME-001 | Improve maintenance CapEx estimate beyond the current D&A placeholder. | P1 | Formula change requires user approval; should distinguish maintenance vs growth CapEx where evidence allows. |
| ME-002 | Improve owner earnings quality by adjusting for SBC, maintenance CapEx, working-capital quality, one-time items, and non-operating gains/losses. | P1 | Should keep raw accounting facts separate from owner-earnings adjustments. |
| ME-003 | Separate excess cash from operating, restricted, trapped, or strategically necessary cash. | P1 | Important for China/ADR companies; should connect to holding-company/VIE/capital-control risk. |
| ME-004 | Add ROIC variants and disclose choices around cash, goodwill, acquired intangibles, R&D capitalization, tax rate, SBC, impairments, and beginning/average/ending invested capital. | P1 | Formula change requires user approval; no hard ROIC threshold. |
| ME-005 | Add incremental ROIC over multi-year windows. | P1 | Better test of whether growth reinvestment creates value; depends on clean NOPAT and invested-capital bridge. |
| ME-006 | Add unit economics and business-model KPI dashboard by industry. | P1 | Depends on KPI extraction; examples include take rate, ARPU, active customers, merchants, order frequency, retention/cohort signals, fulfillment cost, CAC/payback where disclosed. |
| ME-007 | Add revenue-quality metrics such as segment mix, recurring/repeat revenue, customer concentration, price/volume/mix, and take-rate changes where disclosed. | P2 | Supports business-model durability analysis. |
| ME-008 | Add per-share owner economics and dilution burden. | P1 | Should track SBC, diluted shares, buybacks/issuance, and owner earnings per share. |

### Learning Materials

Current status:

- Candidate lesson registry exists.
- User-provided Google Docs and thread playbooks are tracked.
- Candidate lessons do not change behavior automatically.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| LM-001 | Add approval workflow to promote candidate lessons to approved. | P1 | User control required. |
| LM-002 | Add lesson impact mapping: which agent behavior would change if approved. | P1 | Prevent hidden behavior drift. |
| LM-003 | Add retired/rejected rationale fields. | P2 | Useful as learning library grows. |

### Business Model / Moat

Current status:

- Official-report-only V1 works.
- Reads business overview, MD&A/operating review, segment notes, revenue notes, risk factors, and extracted metrics.
- PDD has deep evidence cards and a dedicated design doc.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| BM-001 | Add formal decision-criteria object: clarity, viability, durability, capital efficiency, governance, accounting trust, valuation sufficiency. | P1 | Based on user playbooks. |
| BM-002 | Add unit-economics / driver-tree scaffold from official reports. | P1 | Depends on KPI extraction and revenue/cost mapping. |
| BM-003 | Add industry-structure mapper and profit-pool / value-chain analysis. | P1 | Needed before final moat judgment. |
| BM-004 | Add scale-economies-shared hypothesis template. | P1 | Especially relevant to PDD/Temu. |
| BM-005 | Link moat hypotheses to financial, public voice, competitor, and fieldwork evidence. | P1 | Requires evidence schema alignment. |
| BM-006 | Add explicit anti-moat and kill criteria. | P1 | Should appear in main report and data linkage. |
| BM-007 | Upgrade Official Report Reader from thin section detection to a structured official-report dossier. | P1 | Include legal/reporting scope, business description, segments, revenue model, customer groups, dependencies, cost/capital drivers, disclosed KPIs, management framing, risk map, business evolution, and missing disclosures. |
| BM-008 | Add strict accuracy controls for Official Report Reader fields. | P1 | Every field should have source snippets/document/section or be marked `not_disclosed`; separate directly stated facts from inferred items. |

### External Moat Validation

Current status:

- PDD external moat source plan exists.
- It is collection-ready but mostly planned-only.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| EM-001 | Convert planned source lines into actual source collectors or manual ingestion paths. | P1 | Start with sources that are stable/free. |
| EM-002 | Add hypothesis-to-evidence matrix. | P1 | Each source should test a specific moat hypothesis. |
| EM-003 | Add source-quality scoring and triangulation rules. | P1 | Prevent low-quality sources from becoming conclusions. |

### Public Voice Evidence

Current status:

- PDD Reddit public JSON works when accessible, with cache fallback.
- Sitejabber review-page collection works through cached web-reader extraction.
- Latest run can collect larger public voice evidence but Reddit frequently blocks new searches.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| PV-001 | Add manual URL ingestion for Reddit/forum/review pages. | P1 | Helps when search endpoints block collection. |
| PV-002 | Add Trustpilot/BBB adapters or manual ingestion. | P1 | Free public pages may require special handling. |
| PV-003 | Add YouTube/Bilibili/Zhihu/Xiaohongshu/黑猫投诉 collectors where stable and compliant. | P2 | Important for Chinese/consumer companies. |
| PV-004 | Add app-store review collection. | P2 | Useful for consumer apps and platforms. |
| PV-005 | Add cross-source theme triangulation before customer happiness conclusions. | P1 | Necessary for evidence quality. |

### Leadership / People

Current status:

- Scaffold exists.
- Annual-report leadership evidence markers are collected.
- Candidate learning lessons are attached.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| LP-001 | Extract proxy/annual-report incentive and ownership data where available. | P1 | For PDD/Tencent, adapt to 20-F/HK annual-report disclosure. |
| LP-002 | Add capital-allocation history: buybacks, dilution, M&A, dividends, reinvestment. | P1 | Supports “right people.” |
| LP-003 | Add earnings-call, shareholder-letter, interview, YouTube/Bilibili/podcast source plan. | P2 | Source-quality labels required. |
| LP-004 | Add management-change monitoring source scanner. | P2 | Current trigger exists but scanner is not real yet. |

### Video Transcript

Current status:

- PDD executive transcript V1 exists in `src/stock_research/qualitative/executive_transcripts.py`.
- It supports curated source registries, YouTube caption-track parsing, Bilibili subtitle JSON parsing, and public interview-page text extraction.
- Executive videos and interview pages now run the shared business-model question pack when subtitle/transcript text is available, with Chinese and English matching terms.
- Video manifest V1 exists in `src/stock_research/qualitative/video_manifest.py` and writes `video_manifest.json` per run.
- Official event reader now has a business-model question pack for earnings-call / investor-day videos and a seeded PDD Q4 2025 YouTube source.
- Latest PDD run collected transcript/interview text from 3 sources, 88 segments, and 14 evidence items.
- Detailed research/design note: `docs/video-transcript-agent-research.md`.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| VT-001 | Refactor PDD-specific executive transcript collector into a shared `Video Transcript Agent`. | P1 | Should feed business model, leadership, customer happiness, merchant, and competitor agents. |
| VT-001A | Extend future video/interview agents to carry `video_uid` directly on every evidence item. | P1 | Current executive and official-event transcript collectors already do this; future customer/merchant/competitor video collectors should follow the same rule. |
| VT-002 | Add optional `yt-dlp` adapter for YouTube/Bilibili caption extraction when installed. | P1 | Keep direct parsers as fallback; record extractor version and cache raw metadata. |
| VT-003 | Add official YouTube metadata/search adapter when API key is configured. | P2 | Official caption download only works for owned/authorized videos, so use mainly for discovery and metadata. |
| VT-004 | Add conservative Bilibili subtitle status handling and language/source labels. | P1 | Use public subtitle metadata only; do not bypass login, captcha, or risk controls. |
| VT-005 | Add OpenAI speech-to-text fallback behind an explicit policy gate. | P2 | Needed when captions are missing; must track cost, audio source, model, chunking, and ASR confidence. |
| VT-006 | Add transcript evidence routing by use-case tags. | P1 | Example tags: business_model, leadership, customer_happiness, merchant_sustainability, competitor_comparison. |
| VT-007 | Add optional Gemini video-understanding adapter for public YouTube URLs and policy-approved local video files. | P1 | Implemented for PDD official-event YouTube sources when `GEMINI_API_KEY` or `GOOGLE_API_KEY` is set; expand into the shared video agent next. |
| VT-008 | Add YouTube discovery adapter for all available PDD earnings-call videos. | P1 | Use YouTube Data API when configured or curated URL intake; current question pack is ready but discovery is manual. |
| VT-009 | Add optional Bilibili transcript/analysis adapters beyond public subtitles. | P1 | Candidate paths: user-provided transcript export, BibiGPT API/MCP/manual export, or permitted ASR from a local media file. Preserve BVID/video UID and source-quality labels. |

### Valuation

Current status:

- First-pass yield valuation exists through EV, FCF yield, owner-earnings yield, and investment-adjusted operating yield.
- The Valuation Agent consumes financial metrics such as owner earnings, cash/debt, cash conversion, and ROIC, but owns the price-dependent calculations.
- No full intrinsic value model yet.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| VA-001 | Add base/bear/bull scenario framework. | P1 | Important valuation assumptions require review. |
| VA-002 | Add reverse DCF / implied expectations. | P1 | Helps locate variant perception. |
| VA-003 | Add margin-of-safety policy tied to uncertainty. | P1 | User playbook emphasizes this. |
| VA-004 | Add downside impairment and kill-criteria linkage. | P1 | Should connect to business model and balance sheet. |

### Customer Happiness

Current status:

- Scaffold exists.
- Public Voice Evidence agent collects adjacent customer/forum evidence.
- Dedicated customer happiness synthesis is not complete.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| CH-001 | Build customer happiness synthesis from public voice, app reviews, product reviews, and official complaint sources. | P1 | Needs triangulation rules. |
| CH-002 | Separate customer, merchant, supplier, and employee evidence. | P1 | Especially important for PDD/Temu marketplace economics. |
| CH-003 | Add scuttlebutt interview/source schema for future manual evidence. | P2 | Include compliance/MNPI flags. |
| CH-004 | Add product-test protocol and scorecard. | P2 | Useful for platforms/products the user can personally test. |

### Competitor Comparison

Current status:

- Scaffold exists.
- Next expansion target Tencent is recorded.
- The system can run Tencent, but full comparable workflow is still less mature than PDD.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| CC-001 | Bring Tencent pipeline closer to PDD reliability. | P1 | Requires HKEX cross-validation and stronger PDF extraction. |
| CC-002 | Add competitor candidate selection rules by business line. | P2 | PDD competitors may differ for Pinduoduo vs Temu. |
| CC-003 | Add side-by-side metrics with accounting/reporting caveats. | P2 | Needed for fair comparison. |
| CC-004 | Add moat hypothesis comparison: what is easy/hard to copy. | P2 | Depends on Business Model / Moat outputs. |

### Report Builder

Current status:

- Main report and data-linkage appendix are split.
- Dedicated financial-results and business-model report artifacts are generated by separate report agents.
- Main report is readable; linkage report carries audit trails.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| RB-001 | Add executive summary focused on right business, right people, right price. | P2 | Should avoid final buy/sell conclusion. |
| RB-002 | Add confidence labels for major claims in main report. | P1 | Requires claim/evidence schema. |
| RB-003 | Add bilingual report sections more systematically. | P2 | User requested bilingual reporting. |
| RB-004 | Add evidence IDs linking main report claims to data-linkage rows. | P1 | Strong auditability improvement. |
| RB-005 | Add dedicated Right People / Leadership report. | P1 | Should use leadership sources, incentives, capital allocation, executive transcripts, and management-change evidence. |

### Audit Review

Current status:

- Checks material financial conflicts.
- Records basic audit status.
- Uses 2% mismatch materiality rule and human-review gates.

Potential improvements:

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| AR-001 | Add structured review dashboard: blockers, warnings, accepted assumptions, source conflicts. | P1 | Improves user review. |
| AR-002 | Add blocking rules for unapproved formula changes and low-quality sources used for important claims. | P1 | Matches user approval rules. |
| AR-003 | Add automated check that every major claim has source linkage. | P1 | Depends on claim/evidence schema. |

## Cross-Cutting Improvements

| ID | Improvement | Priority | Dependency / Notes |
| --- | --- | --- | --- |
| X-001 | Introduce LangGraph more fully when branching, retries, human-review gates, or parallel tasks become complex. | P3 | Current sequential fallback is acceptable for V1. |
| X-002 | Move from company-specific branches to source/extractor registries. | P3 | Wait until more companies create duplication pressure. |
| X-003 | Add manual evidence ingestion for user-provided notes, links, screenshots, interview notes, and product tests. | P1 | Useful for qualitative agents. |
| X-004 | Add compliance/MNPI labels for primary research and expert-network evidence. | P1 | Required before serious scuttlebutt/expert workflow. |
| X-005 | Add weekly monitoring automation later for watchlist filings and management changes. | P2 | Current monitor is a skeleton. |

## Recommended Build Order

The highest-value next sequence is:

1. FV-001: third-party financial-statement sanity checks.
2. IR-001 / SD-001: Tencent HKEX official cross-validation.
3. BM-001 / BM-002: business-model decision criteria and unit-economics scaffold.
4. PV-001 / CH-001: manual public evidence ingestion and customer-happiness synthesis.
5. LP-001 / LP-002: leadership incentives and capital-allocation history.
6. VA-001 / VA-002 / VA-003: scenario valuation, reverse DCF, and margin-of-safety framework.
