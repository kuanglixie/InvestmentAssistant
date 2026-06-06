# Webcast Transcript Prototype

Prototype for turning official earnings-call webcasts into research-ready transcripts.

The prototype has two stages:

1. Inspect the official webcast/player page and discover whether public transcript, caption, audio, or video assets are exposed.
2. If no official transcript/caption asset exists, transcribe a local audio/video capture.

It does not bypass registration, paywalls, guestbooks, or access controls.

## Quick Start

From this folder:

```bash
python3 scripts/webcast_to_transcript.py "https://edge.media-server.com/mmc/p/6iz2hdu6/"
```

If the inspection shows `registration_required_or_no_public_item`, access the webcast normally, capture or download the replay audio through approved means, then transcribe the local file:

```bash
OPENAI_API_KEY=... python3 scripts/webcast_to_transcript.py "https://edge.media-server.com/mmc/p/6iz2hdu6/" --audio-file /path/to/pdd-q4-2025.m4a --backend openai
```

Or, if local Whisper is installed:

```bash
python3 scripts/webcast_to_transcript.py "https://edge.media-server.com/mmc/p/6iz2hdu6/" --audio-file /path/to/pdd-q4-2025.m4a --backend whisper-cli
```

## Files

- `scripts/inspect_webcast.py` - fetches webcast/player metadata and reports public transcript/caption/media candidates.
- `scripts/captions_to_transcript.py` - converts `.vtt` / `.srt` captions into plain text or Markdown.
- `scripts/transcribe_local.py` - transcribes a local audio/video file using either OpenAI audio transcription or a local `whisper` CLI.
- `scripts/webcast_to_transcript.py` - one-command pipeline: inspect, convert captions if public, or transcribe supplied local audio.
- `examples/pdd_webcasts.txt` - PDD webcast URLs observed during the initial investigation.

## Expected PDD Behavior

Recent PDD official webcast pages appear to be registration-gated. Public metadata currently exposes event title and registration fields, but not the replay media stream or transcript/caption asset. In that case the prototype should report that a local capture is required.

## Output

Default generated files go under:

```text
../../artifacts/webcast-transcripts/
```

The transcript output includes:

- raw JSON response when available
- a Markdown transcript file
- metadata about backend, source file, and timestamp
