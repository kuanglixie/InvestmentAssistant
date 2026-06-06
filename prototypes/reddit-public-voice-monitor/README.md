# Reddit Public Voice Monitor

Small prototype wrapper around the main PDD public-voice Reddit adapter.

It answers one narrow question for the alternative-data system: what are Reddit users saying about Temu/PDD around shipping, refunds, quality, trust, value, repeat purchase, and merchant economics?

## What It Does

- Reuses the main `stock_research.qualitative.public_voice` collector when live collection is requested.
- Can also import an existing `state.json` or direct `public_voice_findings.json` file.
- Filters Reddit evidence from broader public-voice findings.
- Exports Reddit comments as `demand_monitor_reviews.json`, which the digital demand monitor can ingest with `--reviews-json`.
- Labels each item with a relevance context such as `brand_subreddit`, `brand_thread`, or `brand_mention` so broad Reddit noise is easier to separate from Temu-specific communities.
- Writes a compact summary with top themes, subreddits, queries, and collector status.

## Run From Repo Root

Use the existing PDD run state, which already contains collected Reddit evidence:

```bash
PYTHONPATH=prototypes/reddit-public-voice-monitor/src:src \
  python3 -m reddit_public_voice.run_snapshot \
  --state-json data/runs/20260530T033052Z-pdd/state.json \
  --output-dir prototypes/reddit-public-voice-monitor/artifacts/from_existing_run
```

Attempt a fresh live collection through the main adapter:

```bash
PYTHONPATH=prototypes/reddit-public-voice-monitor/src:src \
  python3 -m reddit_public_voice.run_snapshot \
  --live-collect \
  --output-dir prototypes/reddit-public-voice-monitor/artifacts/live_attempt
```

Reddit often blocks unauthenticated public JSON requests with HTTP 403. When that happens, use cached findings, a prior `state.json`, or later replace the backend with official Reddit OAuth credentials.

## Bridge Into Digital Demand Monitor

```bash
PYTHONPATH=src python3 -m stock_research.alternative_data.digital_demand_monitor.run_monitor \
  --reviews-json prototypes/reddit-public-voice-monitor/artifacts/from_existing_run/demand_monitor_reviews.json \
  --output-dir data/alternative_data/digital_demand_monitor/with_reddit_public_voice \
  --db data/alternative_data/digital_demand_monitor/with_reddit_public_voice.sqlite
```

## Outputs

- `public_voice_findings.json`: full imported or collected findings.
- `reddit_evidence_items.json`: Reddit-only evidence items.
- `demand_monitor_reviews.json`: review-style records consumable by the demand monitor.
- `reddit_review_samples.csv`: flat sample table for quick inspection.
- `reddit_public_voice_summary.json`: machine-readable summary.
- `reddit_public_voice_summary.md`: human-readable summary.
