# Bilibili Video QA Prototype

Prototype for asking questions about Bilibili videos.

The workflow is:

1. Build a structured context from a Bilibili URL or a local transcript/subtitle file.
2. Ask Gemini questions against that context.
3. Save the context, transcript, and answer artifacts for later use by the main investment agent.

This prototype does not bypass login, paywalls, region restrictions, or private content. If a Bilibili video has no public subtitle data, use a local transcript/subtitle file from an approved capture/transcription workflow.

## Quick Start

Ask over a local transcript:

```bash
python3 scripts/video_qa.py \
  --local-transcript examples/sample_transcript.txt \
  --question "What are the main points?"
```

Prepare context from a Bilibili URL:

```bash
python3 scripts/prepare_video_context.py \
  --url "https://www.bilibili.com/video/BV..." \
  --include-danmaku
```

Ask a question over a saved context:

```bash
python3 scripts/ask_video.py \
  --context ../../artifacts/bilibili-video-qa/<run>/context.json \
  --question "Summarize the argument and cite timestamps."
```

One-command Bilibili URL QA:

```bash
python3 scripts/video_qa.py \
  --url "https://www.bilibili.com/video/BV..." \
  --question "What does this video say about PDD's competitive advantage?"
```

## Inputs

- Bilibili URL or BVID.
- Local `.txt`, `.vtt`, `.srt`, or simple JSON transcript.
- Optional danmaku comments from public Bilibili XML endpoint.

## Outputs

Outputs are written under:

```text
../../artifacts/bilibili-video-qa/
```

Each run can contain:

- `context.json` - metadata, transcript segments, and optional danmaku.
- `transcript.md` - readable transcript export.
- `answer.md` - Gemini answer for the question.
- `answer.raw.json` - raw Gemini response.

## Notes

- Gemini API key is loaded from the prototype workspace `.env` using `GEMINI_API_KEY` or `GOOGLE_API_KEY`.
- If public subtitle metadata is unavailable but your normal browser session can access it, set `BILIBILI_COOKIE` in `.env` with an authorized Bilibili cookie string.
- Default model is `gemini-2.5-flash`, matching Google's Gemini REST examples.
- For videos without public subtitles, pair this prototype with the webcast/audio transcription prototype or another approved ASR pipeline.
