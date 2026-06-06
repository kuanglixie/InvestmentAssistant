# Earnings Call Transcript Prototype

Prototype for sourcing, normalizing, and storing earnings-call transcripts for an investment assistant.

Provider chain for this MVP:

1. Alpha Vantage `EARNINGS_CALL_TRANSCRIPT` API.
2. Manual/local transcript ingest for StockAnalysis, Seeking Alpha, Motley Fool, Quartr exports, or company IR text.
3. Audio transcription fallback can reuse the existing `webcast-transcripts` prototype and then ingest the generated transcript here.

This prototype emphasizes source hygiene: every transcript carries provider, source type, confidence, and storage/redistribution flags.

## Quick Start

Alpha Vantage demo:

```bash
python3 scripts/fetch_alpha_vantage.py --symbol IBM --quarter 2024Q1 --demo
```

With your own API key:

```bash
ALPHA_VANTAGE_API_KEY=... python3 scripts/fetch_alpha_vantage.py --symbol AAPL --quarter 2024Q3
```

Provider-chain MVP:

```bash
python3 scripts/transcript_pipeline.py --symbol IBM --quarter 2024Q1 --demo
```

Backfill full transcripts for all quarters in a range:

```bash
ALPHA_VANTAGE_API_KEY=... python3 scripts/backfill_alpha_vantage.py \
  --symbol PDD \
  --start 2018Q3 \
  --end 2026Q1 \
  --newest-first \
  --stop-on-rate-limit \
  --require-all
```

Use `--require-all` when the main agent should reject a partial backfill. Without it, the script still writes a manifest for every requested quarter and marks each one as `fetched`, `missing`, or `error`.
Use `--newest-first` for research workflows where recent calls matter most and the free daily quota may stop the job before the full historical range is done.

Manual/local transcript ingest:

```bash
python3 scripts/ingest_local_transcript.py \
  --symbol PDD \
  --quarter 2025Q4 \
  --company-name "PDD Holdings" \
  --file examples/sample_transcript.txt \
  --provider manual_sample \
  --source-type third_party_web \
  --confidence medium \
  --license-notes "Sample only; replace with reviewed source notes."
```

## Output

Artifacts are written under:

```text
../../artifacts/earnings-call-transcripts/
```

Each run includes:

- `record.json` - normalized transcript record.
- `transcript.md` - readable transcript.
- `raw.json` - raw provider response when available.
- `next_steps.md` - fallback instructions when the automated source is missing.
- `source_candidates.json` / `.md` - link-only source registry when copying full transcript text is not appropriate.
- `manifest.json` / `.md` - backfill result table for all requested quarters.

## Full Text Policy

The prototype stores full transcript text when the source is one of:

- Alpha Vantage API response under an API key you are authorized to use.
- Official company IR transcript/PDF that permits storage for your use.
- Local/user-provided transcript file.
- Machine-generated transcript from permitted webcast/audio capture.

For third-party web pages such as Motley Fool, Seeking Alpha, Benzinga, or StockAnalysis, the prototype records links and metadata by default rather than copying full text, unless storage rights have been confirmed.

## Schema

See:

```text
schema.sql
```

The schema is intentionally rights-aware. Do not mix official transcripts, third-party web transcripts, API transcripts, and machine-generated audio transcripts without preserving source metadata.

## Official Alpha Vantage Endpoint

Alpha Vantage documents `function=EARNINGS_CALL_TRANSCRIPT` with required `symbol`, `quarter`, and `apikey` parameters. The quarter format is `YYYYQn`, for example `2024Q1`.
