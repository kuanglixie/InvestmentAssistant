# Alternative Data Capture Plan V1

This note covers three near-term data extensions: competitor product baskets, TikTok/Meta creative monitoring, and merchant/regulatory monitoring.

## Competitor Product Basket Monitor

Best first implementation: fixed baskets, not broad search scraping.

Why: fixed baskets make Temu versus Amazon/Walmart/AliExpress/SHEIN comparisons stable enough to trend price, discount, delivery promise, review count, rating, and stock status over time.

Current implementation status:

- `src/stock_research/alternative_data/temu_product_intelligence/` can already fetch pages with Playwright or fixtures.
- Temu pages use `TemuProductParser`.
- Non-Temu competitor pages now use `GenericCommerceProductParser`, which extracts JSON-LD, Open Graph metadata, visible price text, rating/review count, delivery windows, shipping/free-shipping, stock status, and platform/product IDs.
- Sample competitor basket config: `config/alternative_data/temu_product_intelligence/competitor_basket.sample.yaml`.

Access routes by platform:

| Platform | Best route | Notes |
| --- | --- | --- |
| Amazon | Product Advertising API / Creators API if credentials are available; otherwise manual fixed URLs plus page snapshots | Official API supports product search and item lookup; page scraping is brittle and policy-sensitive. |
| Walmart | Walmart Marketplace item search API if credentials are available; otherwise manual fixed URLs plus page snapshots | Official item-search APIs are seller/catalog oriented but useful for candidate discovery and item attributes. |
| AliExpress | Affiliate/Open Platform access if available; otherwise manual fixed URLs plus page snapshots | Public pages are dynamic and prices may vary by region/account. |
| SHEIN | SHEIN Open Platform is seller/integration oriented; competitor monitoring likely starts with manual URLs or a licensed provider | Good public-product coverage may need rendered snapshots or a commercial data provider. |

MVP fields:

- `brand`, `category`, `tracking_id`, `url`
- `title`, `price`, `list_price`, `discount_pct`
- `rating`, `review_count`, `sold_count_estimate`
- `delivery_min_days`, `delivery_max_days`, `shipping_fee`
- `stock_status`, `source_platform`, `html_path`

## TikTok / Meta Creative And Ad Monitor

Best first implementation: credential-aware official APIs plus manual/export fallback.

Why: TikTok Shop and Temu demand can come from in-feed content and paid creative rather than Google Search. The useful question is not only "how many ads?" but "what products and promises are being pushed?"

Current source plan:

- `config/alternative_data/creative_ad_monitor/source_plan.v1.json`

Access routes:

| Source | Best route | Credential / limitation |
| --- | --- | --- |
| TikTok Commercial Content API - ads | Official API endpoint `/v2/research/adlib/ad/query/` | Requires approved research client, client key/secret, bearer token; max page size is limited and pagination uses `search_id`. |
| TikTok Commercial Content API - creator/commercial content | Official API endpoint `/v2/research/adlib/commercial_content/query/` | Useful for creator-led paid partnership/commercial content; coverage starts with EEA-style transparency data. |
| Meta Ad Library | API or public UI | API requires Meta developer token/access. Public UI can validate active ads, but bulk programmatic coverage and spend/reach fields are limited for ordinary commercial ads. |
| YouTube Shorts / haul/review videos | YouTube Data API | Requires Google API key; useful as organic/creator proxy rather than direct paid-ad evidence. |

MVP fields:

- `creative_id`, `platform`, `brand_id`, `country`
- `advertiser_name`, `creator_username`
- `first_seen_at`, `last_seen_at`, `creative_format`
- `creative_text`, `headline`, `landing_url`, `snapshot_url`
- `product_terms`, `promotion_terms`, `country_terms`
- `reach_bucket`, `source_url`

Derived metrics:

- `active_creative_count`
- `new_creative_count_7d`
- `video_creative_share`
- `discount_claim_share`
- `free_shipping_claim_share`
- `free_gift_claim_share`
- `category_term_distribution`
- `competitor_creative_share`

## Build Order

1. Run the competitor fixed basket with 3-5 manually selected comparable URLs per category and competitor.
2. Add source-specific parser improvements only after the generic parser shows which fields are consistently missing.
3. Build a creative CSV/JSON importer first, because Meta/TikTok credentials may not be available immediately.
4. Add live TikTok Commercial Content API once research-client credentials exist.
5. Add Meta API or manual UI snapshot bridge after choosing target countries and page IDs.
6. Add merchant/regulatory ingestion from public seller pages, merchant voice exports, CPSC recall JSON, CBP trade/de minimis pages, FTC actions, and European Commission DSA/Safety Gate pages.

## Merchant / Regulatory Monitor

Best first implementation: normalize official pages/API JSON and merchant text exports into issue events, not a broad crawler.

Why: the useful investment question is whether Temu's low-price cross-border model is facing pressure from seller economics, return/refund burdens, safety recalls, customs/de minimis rules, or platform-accountability regulation.

Current implementation status:

- Source plan: `config/alternative_data/merchant_regulatory_monitor/source_plan.v1.json`
- Package: `src/stock_research/alternative_data/merchant_regulatory_monitor/`
- CLI: `merchant-regulatory-snapshot`
- Test fixtures cover merchant-policy text and CPSC-style recall JSON.
- The Product / Pricing / Policy Collector V1 consumes this monitor's merchant/platform-policy events together with product-intelligence outputs.

Access routes:

| Source | Best route | Limitation |
| --- | --- | --- |
| Temu Seller Center | Public page snapshots plus seller-account exports later | Full policy and operational details may sit behind seller login. |
| Merchant voice | Existing Reddit/forum connector or manual JSON exports | Low confidence; use for leads and topic discovery. |
| CPSC recalls | Official recall API JSON | Querying by marketplace name can miss importer/seller-only recall records. |
| EU Safety Gate | Official portal snapshots or validated export path | Bulk API path still needs validation. |
| CBP Section 321 / trade stats | Official public pages/tables | Macro policy signal, not company-specific volume. |
| FTC / EU DSA actions | Official public pages | Event-driven; should be combined with source-watch searches. |

MVP fields:

- `source_group`, `source_id`, `source_type`, `source_url`
- `title`, `topic`, `severity`, `country`, `market`
- `published_at`, `collected_at`
- `evidence_excerpt`, `subject_entities`, `source_confidence`

Questions answered:

- Are seller economics tightening through fees, returns, payout timing, fulfillment requirements, or penalties?
- Is Temu leaning more on seller-funded ads, coupons, or logistics obligations to sustain growth?
- Are unsafe products, illegal goods, or consumer-protection issues increasing?
- Could de minimis, customs, tariff, or DSA rules impair Temu's cross-border model?

## V1 Collector Layer

These collectors sit above source-specific monitors. They answer investment questions and write stable packs that downstream agents can consume.

### Product / Pricing / Policy Collector

Package: `src/stock_research/alternative_data/collectors/product_pricing_policy.py`  
CLI: `product-pricing-policy-collector`

Inputs:

- Product snapshots from `temu_product_intelligence`
- Weekly product metrics from `temu_product_intelligence`
- Product signal pack and unit-economics pack
- Merchant/platform-policy events from `merchant_regulatory_monitor`

Outputs:

- `product_pricing_policy_pack.json`
- `product_pricing_policy_report.md`

V1 finding IDs:

- `promotion_intensity_watch`
- `delivery_promise_watch`
- `merchant_policy_pressure_watch`
- `product_supply_quality_watch`
- `product_policy_stable_v1`

### Competitor Source Collector

Package: `src/stock_research/alternative_data/collectors/competitor_source.py`  
CLI: `competitor-source-collector`

Inputs:

- Target product snapshots
- Competitor fixed-basket product snapshots
- Competitor filings, product-page, policy-page, seller-term, or manual text records

Outputs:

- `competitor_source_pack.json`
- `competitor_source_report.md`

V1 finding IDs:

- `relative_price_position`
- `relative_delivery_position`
- `competitor_strategy_overlap`
- `competitor_regulatory_context`
- `competitor_source_no_v1_threshold`
