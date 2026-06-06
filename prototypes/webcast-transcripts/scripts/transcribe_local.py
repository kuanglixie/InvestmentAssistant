#!/usr/bin/env python3
"""Transcribe a local earnings-call audio/video capture."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"


class TranscriptError(RuntimeError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_output_dir() -> Path:
    return repo_root() / "artifacts" / "webcast-transcripts"


def make_run_dir(input_path: Path, output_dir: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe_stem = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in input_path.stem)
    run_dir = output_dir / f"{safe_stem}-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def choose_backend(requested: str) -> str:
    if requested != "auto":
        return requested
    if shutil.which("whisper"):
        return "whisper-cli"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    raise TranscriptError("No backend found. Install `whisper` or set OPENAI_API_KEY.")


def encode_multipart(fields: dict[str, str], file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = "----codex-webcast-" + uuid.uuid4().hex
    chunks: list[bytes] = []

    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(str(value).encode())
        chunks.append(b"\r\n")

    filename = file_path.name
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    chunks.append(f"--{boundary}\r\n".encode())
    chunks.append(
        (
            f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode()
    )
    chunks.append(file_path.read_bytes())
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def transcribe_openai(input_path: Path, model: str, language: str | None) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise TranscriptError("OPENAI_API_KEY is required for --backend openai.")

    fields = {
        "model": model,
        "response_format": "verbose_json",
    }
    if language:
        fields["language"] = language

    body, boundary = encode_multipart(fields, "file", input_path)
    request = urllib.request.Request(
        OPENAI_TRANSCRIPTIONS_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise TranscriptError(f"OpenAI transcription failed: HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise TranscriptError(f"OpenAI transcription network error: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise TranscriptError("OpenAI transcription response was not JSON.") from exc


def transcribe_whisper_cli(input_path: Path, model: str, language: str | None, run_dir: Path) -> dict[str, Any]:
    whisper = shutil.which("whisper")
    if not whisper:
        raise TranscriptError("`whisper` CLI is not installed or not on PATH.")

    command = [
        whisper,
        str(input_path),
        "--model",
        model,
        "--output_dir",
        str(run_dir),
        "--output_format",
        "all",
    ]
    if language:
        command.extend(["--language", language])

    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise TranscriptError(
            "`whisper` failed.\n"
            f"stdout:\n{completed.stdout}\n\n"
            f"stderr:\n{completed.stderr}"
        )

    json_files = sorted(run_dir.glob("*.json"))
    if json_files:
        try:
            return json.loads(json_files[0].read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    text_files = sorted(run_dir.glob("*.txt"))
    text = text_files[0].read_text(encoding="utf-8") if text_files else completed.stdout
    return {"text": text, "backend_stdout": completed.stdout, "backend_stderr": completed.stderr}


def extract_text(result: dict[str, Any]) -> str:
    if isinstance(result.get("text"), str):
        return result["text"].strip()
    segments = result.get("segments")
    if isinstance(segments, list):
        lines = []
        for segment in segments:
            text = segment.get("text") if isinstance(segment, dict) else None
            if text:
                lines.append(text.strip())
        return "\n".join(lines).strip()
    return json.dumps(result, indent=2, ensure_ascii=False)


def write_outputs(run_dir: Path, input_path: Path, backend: str, model: str, result: dict[str, Any]) -> None:
    raw_path = run_dir / "transcript.raw.json"
    raw_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    text = extract_text(result)
    md = [
        f"# Transcript: {input_path.name}",
        "",
        f"- Source file: `{input_path}`",
        f"- Backend: `{backend}`",
        f"- Model: `{model}`",
        "",
        "## Text",
        "",
        text,
        "",
    ]
    (run_dir / "transcript.md").write_text("\n".join(md), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Local audio/video file to transcribe.")
    parser.add_argument("--backend", choices=["auto", "openai", "whisper-cli"], default="auto")
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Transcription model. For openai defaults to OPENAI_TRANSCRIBE_MODEL or whisper-1. "
            "For whisper-cli defaults to base."
        ),
    )
    parser.add_argument("--language", default="en", help="Optional language hint. Use '' to omit.")
    parser.add_argument("--output-dir", type=Path, default=default_output_dir())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    if not input_path.exists():
        print(f"error: input file not found: {input_path}", file=sys.stderr)
        return 2

    try:
        backend = choose_backend(args.backend)
        model = args.model
        if model is None:
            model = os.environ.get("OPENAI_TRANSCRIBE_MODEL", "whisper-1") if backend == "openai" else "base"
        language = args.language or None

        run_dir = make_run_dir(input_path, args.output_dir.expanduser().resolve())
        if backend == "openai":
            result = transcribe_openai(input_path, model, language)
        elif backend == "whisper-cli":
            result = transcribe_whisper_cli(input_path, model, language, run_dir)
        else:
            raise TranscriptError(f"Unsupported backend: {backend}")

        write_outputs(run_dir, input_path, backend, model, result)
    except TranscriptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({"run_dir": str(run_dir), "backend": backend, "model": model}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

