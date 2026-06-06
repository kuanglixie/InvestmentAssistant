#!/usr/bin/env python3
"""One-command webcast-to-transcript prototype.

Flow:
1. Inspect official webcast metadata.
2. If public captions exist, download and convert them.
3. Otherwise, optionally transcribe a supplied local capture.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from captions_to_transcript import convert_caption_file
from inspect_webcast import download_caption_assets, inspect, write_json
from transcribe_local import (
    TranscriptError,
    choose_backend,
    extract_text,
    transcribe_openai,
    transcribe_whisper_cli,
    write_outputs,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_output_dir() -> Path:
    return repo_root() / "artifacts" / "webcast-transcripts"


def safe_name(value: str | None) -> str:
    value = value or "webcast"
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value)[:80].strip("-") or "webcast"


def make_run_dir(output_dir: Path, title: str | None) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = output_dir / f"{safe_name(title)}-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_next_steps(run_dir: Path, inspected: dict[str, object]) -> None:
    content = [
        "# Next Steps",
        "",
        f"Inspection status: `{inspected.get('status')}`",
        "",
        "No public transcript, caption, audio, or video candidate was exposed by the inspected metadata.",
        "",
        "Recommended path:",
        "",
        "1. Open the official webcast page and register/login normally.",
        "2. Capture or download the replay audio through approved means.",
        "3. Re-run this pipeline with `--audio-file /path/to/capture.m4a`.",
        "",
        "Example:",
        "",
        "```bash",
        "OPENAI_API_KEY=... python3 scripts/webcast_to_transcript.py \\",
        f"  {json.dumps(str(inspected.get('source_url')))} \\",
        "  --audio-file /path/to/capture.m4a \\",
        "  --backend openai",
        "```",
        "",
    ]
    (run_dir / "NEXT_STEPS.md").write_text("\n".join(content), encoding="utf-8")


def transcribe_audio_file(
    audio_file: Path,
    backend_arg: str,
    model_arg: str | None,
    language: str | None,
    run_dir: Path,
) -> tuple[str, str, dict[str, object]]:
    backend = choose_backend(backend_arg)
    model = model_arg
    if model is None:
        model = os.environ.get("OPENAI_TRANSCRIBE_MODEL", "whisper-1") if backend == "openai" else "base"

    if backend == "openai":
        result = transcribe_openai(audio_file, model, language)
    elif backend == "whisper-cli":
        result = transcribe_whisper_cli(audio_file, model, language, run_dir)
    else:
        raise TranscriptError(f"Unsupported backend: {backend}")

    write_outputs(run_dir, audio_file, backend, model, result)
    return backend, model, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Official webcast/player/event URL.")
    parser.add_argument("--audio-file", type=Path, help="Local audio/video capture to transcribe if no captions are public.")
    parser.add_argument("--backend", choices=["auto", "openai", "whisper-cli"], default="auto")
    parser.add_argument("--model", default=None)
    parser.add_argument("--language", default="en")
    parser.add_argument("--output-dir", type=Path, default=default_output_dir())
    parser.add_argument("--timeout", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inspected = inspect(args.url, args.timeout)
    run_dir = make_run_dir(args.output_dir.expanduser().resolve(), inspected.get("title"))
    write_json(run_dir / "inspect.json", inspected)

    summary: dict[str, object] = {
        "run_dir": str(run_dir),
        "title": inspected.get("title"),
        "inspection_status": inspected.get("status"),
        "mode": None,
    }

    captions = inspected.get("caption_candidates") or []
    if captions:
        caption_dir = run_dir / "captions"
        downloaded = download_caption_assets(captions, caption_dir, args.timeout)
        summary["downloaded_captions"] = downloaded
        if downloaded:
            first_caption = Path(downloaded[0])
            transcript = convert_caption_file(first_caption)
            (run_dir / "transcript.txt").write_text(transcript + "\n", encoding="utf-8")
            (run_dir / "transcript.md").write_text(
                f"# Transcript: {inspected.get('title') or first_caption.name}\n\n{transcript}\n",
                encoding="utf-8",
            )
            summary["mode"] = "public_caption_converted"
            write_json(run_dir / "summary.json", summary)
            print(json.dumps(summary, indent=2))
            return 0

    if args.audio_file:
        audio_file = args.audio_file.expanduser().resolve()
        if not audio_file.exists():
            raise SystemExit(f"error: audio file not found: {audio_file}")
        try:
            backend, model, result = transcribe_audio_file(
                audio_file, args.backend, args.model, args.language or None, run_dir
            )
        except TranscriptError as exc:
            raise SystemExit(f"error: {exc}") from exc
        summary.update(
            {
                "mode": "local_audio_transcribed",
                "backend": backend,
                "model": model,
                "text_preview": extract_text(result)[:500],
            }
        )
        write_json(run_dir / "summary.json", summary)
        print(json.dumps(summary, indent=2))
        return 0

    summary["mode"] = "manual_capture_required"
    write_next_steps(run_dir, inspected)
    write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

