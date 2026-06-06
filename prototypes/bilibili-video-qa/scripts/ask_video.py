#!/usr/bin/env python3
"""Ask Gemini questions over a prepared Bilibili video context."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from bilibili_common import (
    PrototypeError,
    format_context_for_prompt,
    load_dotenv,
    print_error,
    write_markdown_answer,
)


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def gemini_generate(
    prompt: str,
    model: str,
    temperature: float,
    timeout: int,
) -> dict[str, Any]:
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise PrototypeError("Set GEMINI_API_KEY or GOOGLE_API_KEY in the prototype .env.")

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": temperature,
        },
    }
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        GEMINI_URL.format(model=model),
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise PrototypeError(f"Gemini request failed: HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise PrototypeError(f"Gemini network error: {exc.reason}") from exc


def extract_answer(payload: dict[str, Any]) -> str:
    parts = (
        ((payload.get("candidates") or [{}])[0].get("content") or {}).get("parts")
        if payload.get("candidates")
        else None
    )
    if not parts:
        return json.dumps(payload, indent=2, ensure_ascii=False)
    texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    return "\n".join(text for text in texts if text).strip()


def build_prompt(context: dict[str, Any], question: str, max_chars: int, context_mode: str) -> str:
    context_text = format_context_for_prompt(context, question, max_chars=max_chars, mode=context_mode)
    return f"""You are an investment research assistant analyzing a Bilibili video.

Answer the user's question using only the supplied video context.
If the context is insufficient, say what is missing.
When possible, cite timestamps or part markers from the transcript.
Be concise, concrete, and separate facts from inference.

User question:
{question}

Video context:
{context_text}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, type=Path, help="Path to context.json from prepare_video_context.py.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"))
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-context-chars", type=int, default=120_000)
    parser.add_argument("--context-mode", choices=["auto", "full", "retrieve"], default="auto")
    parser.add_argument("--out", type=Path, help="Markdown answer path. Defaults to answer.md beside context.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        context_path = args.context.expanduser().resolve()
        context = json.loads(context_path.read_text(encoding="utf-8"))
        mode = "retrieve" if args.context_mode == "auto" else args.context_mode
        prompt = build_prompt(context, args.question, args.max_context_chars, mode)
        raw = gemini_generate(prompt, args.model, args.temperature, args.timeout)
        answer = extract_answer(raw)
        out_path = args.out.expanduser().resolve() if args.out else context_path.parent / "answer.md"
        raw_path = out_path.with_suffix(".raw.json")
        raw_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        write_markdown_answer(out_path, args.question, answer, context_path)
    except Exception as exc:
        return print_error(exc)

    print(json.dumps({"answer": str(out_path), "raw": str(raw_path), "model": args.model}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

