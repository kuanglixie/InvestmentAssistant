# PDD External Moat Source Prototype V1

Generated: 2026-05-26

## Purpose

This document records the first external-source prototype for testing PDD's business model and moat. It is intentionally separate from the official financial-report pipeline.

Official reports can show how PDD describes the model and whether financial results support a strong business. They cannot prove customer happiness, merchant profitability, competitive durability, or regulatory risk. This prototype defines where those missing evidence lines should come from.

## Current Scope

Company: PDD Holdings Inc.

Products / businesses in scope:

- Pinduoduo.
- Temu.
- PDD / PDD Holdings as the listed parent-company context.

The current implementation is a source plan only. It does not yet scrape, summarize, or score external sources.

## Hypotheses To Test

The prototype tests five PDD moat hypotheses:

- Buyer-merchant marketplace network effect.
- Low-price / supply-chain cost advantage.
- Customer engagement advantage from interactive or social shopping behavior.
- Merchant value proposition.
- Trust, quality, regulatory, and reputation risk.

## Source Lines

The source registry lives at `config/qualitative/pdd_external_moat_sources.v1.json`.

The V1 source lines are:

- App reviews and app-store aggregate reception.
- Customer public discussion and product experience.
- Merchant and seller economics.
- Competitor public materials.
- Regulatory, trade, and reputation risk.
- Independent business reporting and free industry context.

## Source Quality Rules

External sources are divided into four quality tiers:

- Tier 1: official company, regulator, government, court/enforcement, and competitor filing sources.
- Tier 2: reputable aggregate sources, app-store aggregate data, reputable media, and free industry reports with visible methodology.
- Tier 3: direct customer or merchant voices such as Reddit, forums, seller communities, complaint platforms, Zhihu, Xiaohongshu, YouTube, and Bilibili.
- Tier 4: anonymous or influencer opinion with weak provenance.

Tier 3 and Tier 4 sources may create leads and repeated-pattern evidence, but they should not support important investment conclusions alone.

## Decisions Recorded For Review

These decisions are recorded in the registry:

- V1 does not run live scraping or automatic summarization of public discussion yet.
- Tier 3 and Tier 4 source claims are limited to leads/patterns unless independently repeated or supported by higher-quality sources. This is marked for user review.
- PDD external moat research should be bilingual because Pinduoduo and Temu evidence appears in different markets and languages.
- Competitor source lines are not a final competitor comparison; final comparison still requires competitors to run through the full workflow.

## How It Appears In Reports

The workflow now adds an `external_moat_validation` agent after the official Business Model / Moat Agent.

The final Markdown report includes:

- source-plan status,
- registry path,
- source-line count,
- quality-tier coverage,
- source-line table,
- decisions/assumptions,
- official-report gaps this plan is designed to test,
- external-source audit rules.

## What This Does Not Do Yet

This V1 source prototype does not:

- collect live Reddit, YouTube, Bilibili, app-store, or forum evidence,
- score customer happiness,
- score merchant satisfaction,
- decide whether PDD has a durable moat,
- use external sources for financial numbers,
- replace official financial-report evidence.

## Next Implementation Step

The next step is to build a controlled collector for one source line at a time. The safest order is:

1. Regulatory / official source collector.
2. App-store aggregate collector.
3. Competitor official-report collector.
4. Merchant-feedback collector.
5. Customer/community discussion collector.

This order starts with higher-quality sources before moving into noisy public discussion.
