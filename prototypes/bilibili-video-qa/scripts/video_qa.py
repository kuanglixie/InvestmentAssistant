#!/usr/bin/env python3
"""One-command Bilibili/local-video transcript QA."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ask_video import build_prompt, extract_answer, gemini_generate
from bilibili_common import default_artifact_root, make_run_dir, print_error, save_context, write_markdown_answer
from prepare_video_context import build_context_from_bilibili, build_context_from_local


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Bilibili video URL.")
    source.add_argument("--bvid", help="Bilibili BVID.")
    source.add_argument("--local-transcript", type=Path, help="Local .txt/.vtt/.srt/.json transcript.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--title")
    parser.add_argument("--lang", default=None)
    parser.add_argument("--page", type=int)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--include-danmaku", action="store_true")
    parser.add_argument("--danmaku-limit", type=int, default=300)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--fetch-timeout", type=int, default=20)
    parser.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"))
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-context-chars", type=int, default=120_000)
    parser.add_argument("--context-mode", choices=["auto", "full", "retrieve"], default="auto")
    parser.add_argument("--output-dir", type=Path, default=default_artifact_root())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        llm_timeout = args.timeout
        if args.local_transcript:
            context, title = build_context_from_local(args)
        else:
            args.timeout = args.fetch_timeout
            context, title = build_context_from_bilibili(args)
            args.timeout = llm_timeout

        run_dir = make_run_dir(args.output_dir.expanduser().resolve(), title)
        save_context(context, run_dir)
        mode = "retrieve" if args.context_mode == "auto" else args.context_mode
        prompt = build_prompt(context, args.question, args.max_context_chars, mode)
        raw = gemini_generate(prompt, args.model, args.temperature, args.timeout)
        answer = extract_answer(raw)
        raw_path = run_dir / "answer.raw.json"
        raw_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        write_markdown_answer(run_dir / "answer.md", args.question, answer, run_dir / "context.json")
    except Exception as exc:
        return print_error(exc)

    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "context": str(run_dir / "context.json"),
                "answer": str(run_dir / "answer.md"),
                "model": args.model,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
