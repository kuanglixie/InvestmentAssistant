# Stock Research System Limitations V1

Generated: 2026-05-26

## Purpose

This document records known limitations in the current multi-agent stock research system so that they are visible, intentional, and not mistaken for finished capability.

V1 is optimized for deep research on a small watchlist, not broad-scale coverage. This matches the current investment workflow: one or two deep company researches per day at most, with ongoing monitoring for a small number of companies.

## Scalability Position

Scalability can be handled later.

For V1, reliability is more important than generality. It is acceptable for PDD and Tencent to use company-specific source paths while the system proves the core research workflow.

The design should be revisited when any of the following happens:

- A third or fourth company is added with materially different filing/report formats.
- Multiple Hong Kong or China-listed companies need the same PDF extraction logic.
- The watchlist grows beyond roughly 20 companies.
- Monitoring becomes daily or intraday rather than weekly.
- The same source/extractor logic is duplicated in more than two places.

At that point, the system should move from company-specific branching toward a registry-based design:

```text
Company identity
-> listing type / filing system / document type
-> source policy
-> extractor registry
-> validation rules
```

## Current Architecture Limitation

The current system uses the same agent pipeline for PDD and Tencent, but some agents choose tools through explicit code branches.

Examples:

- PDD uses SEC EDGAR, SEC inline XBRL, 20-Fs, and 6-K earnings releases.
- Tencent uses Tencent IR PDF annual/interim reports.
- PDD market data uses ADS price, USD/CNY, and ADS/share structure.
- Tencent market data uses 0700.HK price, HKD/CNY, and ordinary share count.

This is controlled and auditable, but not yet fully scalable.

Target future state:

- Agents stay shared.
- Source adapters are selected by source type.
- Extractors are selected by document type and report profile.
- Company configuration controls allowed sources and source hierarchy.
- LLM reasoning is used for interpretation, not uncontrolled financial-number sourcing.

## Financial Extraction Limitations

### PDD

PDD is currently the stronger prototype because SEC filings provide inline XBRL and structured HTML.

Known limitations:

- Some older 6-K quarterly rows have blanks where the exhibit parser cannot safely extract the item.
- IR PDF direct access may fail in the local environment; the system can fall back to cached official SEC HTML copies.
- Third-party full financial-statement sanity checks are not implemented yet.
- Current extraction focuses on mapped core metrics, not every disclosed financial line item.

### Tencent

Tencent works as a V1 Hong Kong-listed company prototype, but it is less mature than PDD.

Known limitations:

- Tencent currently relies on Tencent IR PDFs as the main official source.
- HKEX official cross-validation is planned but not implemented yet.
- PDF extraction is inherently more fragile than SEC XBRL extraction.
- Latest annual extraction uses the five-year summary plus audited annual statement tables.
- Latest interim extraction is supported, but older interim PDF history is intentionally limited until older report scale/layout differences are mapped safely.
- Third-party full financial-statement sanity checks are not implemented yet.

## Source Validation Limitations

The current source hierarchy is strict for financial numbers:

- Tier 1: official regulator, exchange, and company investor-relations sources.
- Tier 2: reputable free financial databases for sanity checks only.
- Low-quality or social sources are not allowed for official financial numbers.

Limitations:

- PDD has official SEC and partial IR cross-validation.
- Tencent has internal official PDF cross-checking, but not yet HKEX cross-validation.
- Yahoo/Google are used for market quote sanity checks, not full income statement / balance sheet validation.
- If official sources conflict materially, the system flags review rather than deciding silently.

## Market Data And Valuation Limitations

Current valuation is only a first-pass yield-style valuation.

Implemented:

- Market cap collection.
- FX conversion.
- Enterprise value.
- Owner Earnings V1.
- FCF yield.
- Owner earnings yield.
- Cash conversion.
- ROIC without thresholds.

Limitations:

- V1 subtracts all cash rather than estimating excess cash.
- Owner Earnings V1 uses D&A as a maintenance CapEx approximation.
- No full intrinsic value model exists yet.
- No scenario analysis, discount rate model, terminal value model, or margin-of-safety framework exists yet.
- Formula changes require human approval.
- Important valuation assumptions require human approval.

## Qualitative Agent Limitations

The following agents are currently scaffolds or early evidence collectors:

- Business Model / Moat Agent.
- Leadership / People Agent.
- Customer Happiness Agent.
- Competitor Comparison Agent.

Current capability:

- They can collect evidence markers from annual reports.
- They can load candidate learning lessons.
- They can prepare evidence categories for later research.
- PDD now has an external moat-validation source plan at `config/qualitative/pdd_external_moat_sources.v1.json`.
- PDD now has a public voice/forum source registry at `config/qualitative/pdd_public_voice_sources.v1.json`.
- PDD public voice now collects Reddit evidence where accessible and Sitejabber review-page evidence through a cached web-reader adapter.

Not yet complete:

- They do not produce final moat conclusions.
- They do not yet deeply summarize business model evolution.
- They do not yet comprehensively inspect customer/merchant feedback from YouTube, Bilibili, forums, app reviews, or Chinese platforms; Reddit and Sitejabber are the first live adapters, while most other public voice sources are registered but need source-specific collectors or manual URL ingestion.
- They do not yet evaluate leadership quality from interviews, earnings calls, shareholder letters, podcasts, or media reports.
- They do not yet run full competitor workflows before comparison.

External source prototype notes:

- External sources are divided into quality tiers.
- Tier 3/Tier 4 sources are lead and pattern evidence only unless independently repeated or supported by stronger sources.
- External sources are not allowed for official financial numbers.
- Important claims relying on low-quality sources still require human review.

Public voice/forum notes:

- Reddit public JSON collection can pull posts/comments when network access and Reddit allow it.
- Expanded Reddit queries and subreddit-specific searches may still be blocked by Reddit HTTP 403 responses; cached evidence is used when available, and blocked searches are logged.
- Sitejabber review-page collection is implemented and cached, including aggregate profile parsing and individual review evidence extraction.
- Other sources such as Trustpilot, BBB, YouTube, Bilibili, Zhihu, Xiaohongshu, 黑猫投诉, 雪球, and seller forums are registered for the same evidence schema but are not fully automated yet.
- Forum/comment evidence is Tier 3/Tier 4 evidence and should be used for patterns and leads, not final conclusions.

## Learning Material Limitations

Learning material support is intentionally conservative.

Current capability:

- Candidate lessons from user-provided materials are stored in `config/learning/user_lessons.v1.json`.
- Candidate lessons can be shown in reports.

Limitations:

- Candidate lessons do not automatically change agent behavior.
- Only approved lessons should influence agent decisions.
- Lesson provenance and status tracking exist, but lesson activation workflow is still manual.

Allowed lesson statuses:

- candidate
- approved
- rejected
- retired

## Monitoring Limitations

Current monitoring is a skeleton.

Implemented:

- Watchlist structure for PDD, Tencent, and Google / Alphabet.
- Weekly monitoring intent.
- New filing and management-change trigger categories.

Limitations:

- Management-change monitoring is recorded as a trigger but does not yet scan leadership sources.
- Price-drop trigger was intentionally removed for now.
- Monitoring uses cached/local data unless source fetchers are added.
- No automated alerting or recurring automation is configured in this repo.

## LangGraph Limitation

The workflow is LangGraph-style and can run through LangGraph when available.

Current limitation:

- The system still supports a local sequential fallback.
- Some recent runs used `local_sequential_fallback`.

This is acceptable for V1 because the current priority is correctness and auditability. LangGraph becomes more important when:

- agent branching becomes more complex,
- retries and human-review gates need stronger orchestration,
- parallel research tasks are added,
- long-running monitoring workflows become real.

## Report Limitation

Generated reports are research artifacts, not investment recommendations.

Current reports are useful for:

- extracted official facts,
- source lineage,
- metric calculation,
- audit status,
- open issues,
- right business / right people / right price checklist structure.

They are not yet sufficient for:

- final buy/sell decisions,
- complete moat judgment,
- complete people/organization judgment,
- full intrinsic valuation,
- full competitor comparison.

## Human Review Gates

The system should stop or flag review for:

- formula changes,
- material source conflicts,
- low-quality sources used for important claims,
- important valuation assumptions.

Current materiality rule:

- financial-number mismatches above 2% are material,
- clear rounding differences at or below 2% can be accepted and logged.

## Near-Term Priority

Detailed per-agent improvement items are tracked in `docs/agent-improvement-backlog.md`.

The next best improvements are:

1. Add Tencent HKEX official cross-validation.
2. Add full third-party financial-statement sanity checks.
3. Build the Business Model / Moat Agent using official annual reports first.
4. Add external validation sources for customer happiness and leadership.
5. Refactor toward source/extractor registries when more companies are added.
