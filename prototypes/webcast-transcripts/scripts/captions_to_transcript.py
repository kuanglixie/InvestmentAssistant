#!/usr/bin/env python3
"""Convert WebVTT/SRT captions into a plain research transcript."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


TIMESTAMP_RE = re.compile(r"\d{1,2}:\d{2}:\d{2}[,.]\d{3}\s+-->\s+\d{1,2}:\d{2}:\d{2}[,.]\d{3}")
TAG_RE = re.compile(r"<[^>]+>")


def clean_line(line: str) -> str:
    line = TAG_RE.sub("", line)
    line = html.unescape(line)
    return " ".join(line.strip().split())


def captions_to_lines(text: str) -> list[str]:
    lines: list[str] = []
    skip_note = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            skip_note = False
            continue
        if line.upper().startswith(("WEBVTT", "STYLE", "REGION")):
            continue
        if line.upper().startswith("NOTE"):
            skip_note = True
            continue
        if skip_note:
            continue
        if TIMESTAMP_RE.search(line):
            continue
        if line.isdigit():
            continue

        cleaned = clean_line(line)
        if cleaned and (not lines or lines[-1] != cleaned):
            lines.append(cleaned)

    return lines


def lines_to_paragraphs(lines: list[str]) -> str:
    paragraphs: list[str] = []
    current: list[str] = []

    for line in lines:
        current.append(line)
        if line.endswith((".", "?", "!", ":")):
            paragraphs.append(" ".join(current))
            current = []

    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs).strip()


def convert_caption_file(input_path: Path) -> str:
    text = input_path.read_text(encoding="utf-8", errors="replace")
    return lines_to_paragraphs(captions_to_lines(text))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--title", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    transcript = convert_caption_file(args.input.expanduser().resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)

    if args.output.suffix.lower() == ".md":
        title = args.title or args.input.name
        content = f"# Transcript: {title}\n\n{transcript}\n"
    else:
        content = transcript + "\n"

    args.output.write_text(content, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

