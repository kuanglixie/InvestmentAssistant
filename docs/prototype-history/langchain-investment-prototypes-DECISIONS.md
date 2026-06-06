# Prototype Decision Log

This workspace is for fast investment-agent prototyping.

## Operating Rule

Codex should use best judgment and proceed without asking for approval on ordinary prototype decisions.

Record important decisions here instead of blocking progress, especially when they affect:

- provider choice
- source/licensing assumptions
- data schema
- confidence labels
- fallback order
- storage format
- future migration into the main agent

Ask for user involvement only when a decision is unusually consequential, such as:

- spending money or committing to a paid vendor
- destructive file or git operations
- handling credentials in a new way
- scraping or storing data where terms/licensing look risky
- changing the main project instead of the prototype workspace

## Decisions

- Use dedicated prototype folders under `prototypes/`, with outputs under `artifacts/`, so experiments stay separate from the main LangChain investment project.
- Preserve source and rights metadata from day one for transcript-related prototypes.
- Prefer public APIs and official sources before scraping web pages.
- Treat machine-generated transcripts as lower-confidence and clearly label them.
- Full transcript text should be downloaded and stored for authorized API, official, local/user-provided, or permitted machine-transcribed sources. Third-party web transcript pages stay link-only until storage rights are confirmed.
- Backfill jobs should support a strict mode (`--require-all`) so the main agent can reject partial historical coverage instead of silently accepting gaps.
- Temu product intelligence should start as a fixed-basket tracker, not a broad crawler. Use hand-picked product URLs, weekly cadence, modest rate limits, raw HTML audit storage, and parser confidence flags before scaling toward 200 products.
- Temu live tests should distinguish direct product detail pages from product-linked feed pages. In an unauthenticated fresh browser, direct detail pages may redirect to login; feed pages may still expose partial product-card data that is useful for price/discount monitoring but not enough for full review/delivery signals.
- PDD digital demand monitoring should start PDD/Temu-first but keep ticker-neutral fields (`company_id`, `brand_id`, `market`, `platform`) so the same prototype can later support other app/web-exposed companies.
- For the first digital demand monitor MVP, use app data as the primary demand signal and use search trends, web/domain ranks, reviews, and product tracker metrics as confirmation/cross-check layers.
- Google Trends and web traffic sources should support CSV/manual imports first. Programmatic connectors can be added after the signal pipeline and report format prove useful.
- Review topic classification should start with transparent keyword rules for Temu-specific risks such as delivery, refunds, quality, trust/scam, customs/tax, payment, customer service, app bugs, and promotion/coupon complaints.
- Apple App Store collection should treat `market` as the research-facing market label and translate it to Apple storefront codes at fetch time, e.g. `UK` -> `gb`; collect countries separately rather than treating Europe or Asia as single App Store markets.
- Google Play collection should start from public app detail pages as Android coverage, using `gl` per market. Treat install buckets and review counts as coarse public indicators; they can be global or rounded and should not be read as precise country-level downloads.
- Google Ads Transparency should be stored as a separate ad-intensity source, not an app-demand source. The current implementation records domain-level ads pointing to `temu.com`; advertiser-level filtering should be added later because some small markets include non-official advertisers alongside Temu entities.
- Competitor baselines should be collected alongside Temu whenever the source supports it. Use SHEIN and AliExpress as the core cross-border comparison set across markets; keep Amazon/Walmart as broader retail baselines mainly in US/CA; treat TikTok Shop separately because its demand loop is largely in-app/platform-native rather than Google-search or Google-ads driven.
- Review monitoring should use Apple App Store review RSS as the stable text source and Google Play visible public review snippets as a best-effort supplement. Non-English markets currently produce higher `other` topic shares because the V1 keyword classifier is mostly English; negative share is more reliable than topic attribution there.
- Meta Ad Library is useful as a US keyword-level creative monitor. V1 records public result counts and visible ad samples for Temu and competitors; TikTok Creative Center public pages are lower-coverage without login/API access, so TikTok should remain a special case until a commercial-content API or authenticated workflow is available.
- Temu website/product monitoring should first use landing/feed/search page product cards as a surface-level signal. These pages are more accessible than unauthenticated product detail pages and can expose price band, discount intensity, coupon/free-shipping/gamified promo cues, and product-density signals even when rating/delivery details are missing.
- The alternative-data analyst should be deterministic first, not an LLM black box. It consumes one or more `demand_signal_pack.json` files and emits question-oriented answers with evidence, limitations, coverage, and market watchlists. LLM summarization can be layered on top after the structured brief proves useful.
