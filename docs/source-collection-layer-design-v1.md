# Source Collection Layer Design V1

Status: living design draft
Last updated: 2026-06-05

This document defines Layer 1 of the Investment Assistant.

Layer 1 is the source collection layer. It is not an analysis layer.

## Core Principle

Layer 1 only does three things:

1. find sources,
2. download, cache, and parse sources,
3. normalize source metadata.

Layer 1 must not decide whether a company is good or bad. It must not make moat, management, valuation, risk, or investment conclusions. Its job is to preserve provenance so later agents can do evidence-backed work.

## Boundary Rules

Allowed:

- Identify issuer, ticker, CIK, exchange identifier, official IR URL, brand aliases, and business-unit aliases.
- Search official source locations.
- Download, cache, fingerprint, and parse documents.
- Extract table-of-contents and section availability.
- Normalize source metadata.
- Label source type, reliability tier, coverage period, collection status, and rights constraints.
- Record missing or inaccessible sources.

Not allowed:

- Decide whether the company is attractive.
- Decide whether growth quality is good or bad.
- Interpret customer happiness, moat durability, management quality, or price attractiveness.
- Convert third-party opinions into facts.
- Upgrade lower-tier sources into high-confidence evidence without downstream validation.

## Source Tiers

### Tier 1: Official Company Sources

These are the primary sources for the issuer's own numbers and official narrative.

Examples:

- `10-K`, `20-F`, annual report.
- `10-Q`, `6-K`, quarterly results.
- Earnings release and official earnings exhibit.
- Earnings call transcript when sourced from official IR or a clearly registered transcript provider.
- Investor presentation, investor day, capital markets day.
- Shareholder letter.
- Official company newsroom or IR announcement.

For financial facts, Tier 1 is the default source tier.

### Tier 2: Official External Sources

These are official sources outside the company.

Examples:

- Competitor filings.
- Government and regulatory sources.
- Court documents.
- Exchange notices.
- Customs or import-export data, if available and legally usable.

Tier 2 is useful for cross-checks, competitive context, legal/regulatory facts, and external constraints.

### Tier 3: Market / Alternative Data

These sources may provide operational signals, but they are usually noisy and should be treated as evidence leads.

Examples:

- App ranking.
- Google Trends.
- Website traffic.
- Product price and review count.
- Reddit, YouTube, TikTok, Bilibili, and other public voice data.
- Job postings.
- Merchant and customer reviews.

Layer 1 can collect these sources, but downstream agents must label them as alternative signals or lead evidence unless corroborated by stronger sources.

### Tier 4: Third-Party Opinions

These sources can help discover issues, but they should not become core facts without independent verification.

Examples:

- Analyst reports.
- News.
- Blogs.
- Podcasts.
- Investment commentary.

Tier 4 is mainly useful for idea generation, question discovery, and triangulation. It should not be used as the primary basis for financial facts.

## Source Metadata Schema

Every collected source should be registered before downstream agents use it.

```json
{
  "source_id": "pdd_2024_20f",
  "source_name": "PDD Holdings 2024 Form 20-F",
  "source_type": "20-F",
  "source_tier": 1,
  "source_group": "official_company",
  "issuer": "PDD Holdings Inc.",
  "ticker": "PDD",
  "market": "us_adr",
  "period": "FY2024",
  "publication_date": "2025-04-28",
  "filing_date": "2025-04-28",
  "url": "https://www.sec.gov/...",
  "local_path": "data/sources/pdd/...",
  "content_hash": "sha256:...",
  "collection_status": "available",
  "parse_status": "parsed",
  "rights_status": "usable_for_internal_research",
  "sections": [
    "business_description",
    "risk_factors",
    "mda",
    "financial_statements",
    "footnotes",
    "share_based_compensation",
    "related_party_transactions",
    "cash_flow",
    "segment_discussion"
  ],
  "notes": ""
}
```

Recommended `collection_status` values:

- `available`
- `missing`
- `partial`
- `stale`
- `rights_limited`
- `blocked`

Recommended `parse_status` values:

- `not_started`
- `metadata_only`
- `parsed`
- `partial_parse`
- `parse_failed`

Recommended `source_group` values:

- `official_company`
- `official_external`
- `market_alternative_data`
- `third_party_opinion`

## Section Taxonomy

Layer 1 should record which sections are available. It does not need to understand them yet.

Common sections:

- `business_description`
- `risk_factors`
- `mda`
- `financial_statements`
- `footnotes`
- `income_statement`
- `balance_sheet`
- `cash_flow`
- `segment_discussion`
- `revenue_breakdown`
- `cost_breakdown`
- `share_based_compensation`
- `related_party_transactions`
- `auditor_report`
- `internal_controls`
- `governance`
- `shareholder_meeting`
- `capital_allocation`
- `earnings_prepared_remarks`
- `earnings_q_and_a`
- `investor_presentation`
- `product_policy`
- `pricing`
- `customer_reviews`
- `merchant_reviews`
- `regulatory_action`
- `court_record`

## Layer 1 Pack

The durable output should be a machine-readable pack:

```json
{
  "company_input": {
    "raw_input": "PDD",
    "resolved_issuer": "PDD Holdings Inc.",
    "tickers": ["PDD"],
    "brands": ["Pinduoduo", "Temu"],
    "market": "us_adr"
  },
  "source_inventory": [],
  "acquisition_log": [],
  "missing_source_log": [],
  "rights_constraints": [],
  "quality_flags": []
}
```

The human-readable render can summarize coverage, but the `source_inventory` is the core asset.

## Handoff To Layer 2

Layer 2 workpaper agents consume Layer 1's source inventory and decide which sources answer which investment questions.

Layer 1 should hand off:

- sources found,
- sources missing,
- sources blocked by rights or access limits,
- source tier and source type,
- local paths and URLs,
- section availability,
- collection and parse status,
- freshness and period coverage.

Layer 1 should not hand off:

- investment conclusions,
- moat conclusions,
- management quality conclusions,
- valuation conclusions,
- sentiment judgments.

## Acceptance Criteria

A Layer 1 run is acceptable when:

1. Every source has a stable `source_id`.
2. Every source has a source tier and source group.
3. Every source has URL or local path provenance.
4. Missing and blocked sources are explicitly recorded.
5. Source rights and usage constraints are preserved when relevant.
6. Section availability is recorded when parseable.
7. No investment judgment is included in the Layer 1 pack.

