# Public Voice Evidence Agent V1

Generated: 2026-05-26

## Purpose

The Public Voice Evidence Agent collects or organizes customer, merchant, creator, complaint, and investor forum evidence for business-model and moat validation.

For PDD, the agent is meant to test questions that official reports cannot answer:

- Are customers happy enough to repeat purchases?
- Are complaints isolated or structural?
- Do merchants make money after ads, returns, logistics, discounts, and platform rules?
- Is low price creating loyalty or only one-time bargain hunting?
- Do public discussions reveal trust, privacy, quality, or regulatory risk?

## Current PDD Source Registry

Registry: `config/qualitative/pdd_public_voice_sources.v1.json`

Registered source lines:

- Reddit Temu customer discussions.
- Trustpilot Temu reviews.
- BBB Temu complaints.
- Sitejabber Temu reviews.
- YouTube Temu review comments.
- Bilibili Temu / Pinduoduo comments.
- Zhihu Pinduoduo / Temu discussions.
- Xiaohongshu Pinduoduo / Temu discussions.
- 黑猫投诉 Pinduoduo / Temu complaints.
- 雪球 PDD investor discussions.
- Temu seller / ecommerce merchant forums.

## Adapter Status

Implemented in V1:

- Reddit public JSON adapter, when network access allows it.
- Sitejabber public review-page adapter through a cached web-reader page.

Registered but not yet fully collected:

- Trustpilot and BBB.
- YouTube and Bilibili comments.
- Zhihu, Xiaohongshu, 黑猫投诉, 雪球.
- Seller forums and merchant communities.

These require either source-specific collectors, platform APIs, or manual URL ingestion. The agent records them honestly as pending/manual rather than pretending it collected them.

## Evidence Themes

The agent maps comments/posts into these themes:

- product quality,
- shipping/delivery,
- refund/customer service,
- repeat purchase / loyalty,
- trust/safety,
- merchant/seller economics,
- value for money.

## Audit Rules

Public voice evidence is Tier 3 or Tier 4 evidence.

It can:

- reveal repeated customer/merchant themes,
- identify questions for deeper research,
- provide examples of trust, quality, shipping, or refund issues,
- create hypotheses for customer happiness and anti-moat analysis.

It cannot:

- provide official financial numbers,
- prove customer happiness by itself,
- prove or disprove a moat by itself,
- override official reports or audited financial statements.

Important claims from forums/comments require human review and triangulation with stronger sources.

## Output

The report shows:

- source registry path,
- registered sources,
- which adapters collected evidence,
- evidence item count,
- collection breadth and filter counts,
- theme counts,
- source aggregate summaries where available,
- representative short excerpts,
- blocked/manual sources,
- audit notes.

## Next Improvements

Recommended next steps:

1. Add manual URL ingestion for forum/review pages the user wants to inspect.
2. Add app-store review collection.
3. Add Trustpilot/BBB source-specific collectors or acceptable API/manual ingestion paths.
4. Add Chinese platform collectors where access is stable and compliant.
5. Add cross-source theme triangulation before any customer happiness conclusion.

## Current PDD Deep Run Notes

Latest tested PDD run: `data/runs/20260526T150842Z-pdd/final_report.md`

- Total public-voice evidence items: 63.
- Reddit: 41 comment evidence items from cached/previously accessible public JSON pages.
- Sitejabber: 22 review-site evidence items, including aggregate profile data.
- Sitejabber aggregate profile captured 1.8/5 rating from 1,757 reviews, 33% reviewer recommendation, and category counts for service, value, shipping, returns, and quality.
- Reddit new-query expansion is configured, but many new Reddit JSON searches returned HTTP 403 in the current environment. The agent keeps cached evidence and records blocked searches instead of silently failing.
