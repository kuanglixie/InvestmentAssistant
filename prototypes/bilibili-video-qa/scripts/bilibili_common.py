#!/usr/bin/env python3
"""Shared helpers for the Bilibili video QA prototype."""

from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import gzip
import zlib
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)

BVID_RE = re.compile(r"\b(BV[0-9A-Za-z]{8,})\b")
TIMESTAMP_RE = re.compile(
    r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})(?P<ms>[,.]\d{1,3})?"
)
CAPTION_RANGE_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}[,.]?\d{0,3})\s+-->\s+"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}[,.]?\d{0,3})"
)
TAG_RE = re.compile(r"<[^>]+>")


class PrototypeError(RuntimeError):
    pass


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_dotenv() -> None:
    env_path = project_root() / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def default_artifact_root() -> Path:
    return project_root() / "artifacts" / "bilibili-video-qa"


def safe_slug(value: str | None, fallback: str = "bilibili-video") -> str:
    value = value or fallback
    slug = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:90] or fallback


def make_run_dir(output_dir: Path, title: str | None = None) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = output_dir / f"{safe_slug(title)}-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def fetch_text(url: str, timeout: int = 20, referer: str | None = None) -> tuple[str, str]:
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    cookie = os.environ.get("BILIBILI_COOKIE")
    if cookie:
        headers["Cookie"] = cookie
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read()
            encoding = (response.headers.get("Content-Encoding") or "").lower()
            if encoding == "gzip" or raw.startswith(b"\x1f\x8b"):
                raw = gzip.decompress(raw)
            elif encoding in {"deflate", "br"} or raw[:1] in {b"x", b"L"}:
                for window_bits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
                    try:
                        raw = zlib.decompress(raw, window_bits)
                        break
                    except zlib.error:
                        continue
            return raw.decode(charset, errors="replace"), response.geturl()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise PrototypeError(f"HTTP {exc.code} while fetching {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise PrototypeError(f"Network error while fetching {url}: {exc.reason}") from exc


def fetch_json(url: str, timeout: int = 20, referer: str | None = None) -> dict[str, Any]:
    text, _ = fetch_text(url, timeout=timeout, referer=referer)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PrototypeError(f"Response was not JSON: {url}") from exc
    return payload


def extract_bvid(value: str) -> str | None:
    match = BVID_RE.search(value)
    return match.group(1) if match else None


def normalize_bilibili_url(value: str, timeout: int = 20) -> tuple[str | None, str]:
    if value.startswith(("http://", "https://")):
        try:
            _, final_url = fetch_text(value, timeout=timeout)
        except PrototypeError:
            final_url = value
        return extract_bvid(final_url) or extract_bvid(value), final_url
    return extract_bvid(value), value


def normalize_asset_url(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    return url


def seconds_to_stamp(seconds: float | int | None) -> str:
    if seconds is None:
        return ""
    total_ms = int(round(float(seconds) * 1000))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def parse_timestamp(value: str) -> float | None:
    match = TIMESTAMP_RE.search(value)
    if not match:
        return None
    h = int(match.group("h"))
    m = int(match.group("m"))
    s = int(match.group("s"))
    ms_raw = match.group("ms")
    ms = 0
    if ms_raw:
        digits = ms_raw[1:].ljust(3, "0")[:3]
        ms = int(digits)
    return h * 3600 + m * 60 + s + ms / 1000


def clean_caption_text(value: str) -> str:
    value = TAG_RE.sub("", value)
    value = html.unescape(value)
    return " ".join(value.strip().split())


def parse_plain_transcript(path: Path) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for index, raw_line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        start = None
        stamp_match = re.match(r"^\[([0-9:.,]+)\]\s*(.*)$", line)
        if stamp_match:
            start = parse_timestamp(stamp_match.group(1))
            line = stamp_match.group(2).strip()
        segments.append(
            {
                "index": len(segments) + 1,
                "page": 1,
                "start": start,
                "end": None,
                "text": clean_caption_text(line),
                "source": "local_text",
                "line": index,
            }
        )
    return segments


def parse_caption_file(path: Path) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    pending_start: float | None = None
    pending_end: float | None = None
    pending_text: list[str] = []

    def flush() -> None:
        nonlocal pending_start, pending_end, pending_text
        text = clean_caption_text(" ".join(pending_text))
        if text:
            segments.append(
                {
                    "index": len(segments) + 1,
                    "page": 1,
                    "start": pending_start,
                    "end": pending_end,
                    "text": text,
                    "source": "local_caption",
                }
            )
        pending_start = None
        pending_end = None
        pending_text = []

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            continue
        if line.upper().startswith(("WEBVTT", "STYLE", "REGION", "NOTE")):
            continue
        if line.isdigit():
            continue
        range_match = CAPTION_RANGE_RE.search(line)
        if range_match:
            flush()
            pending_start = parse_timestamp(range_match.group("start"))
            pending_end = parse_timestamp(range_match.group("end"))
            continue
        pending_text.append(line)

    flush()
    return segments


def parse_json_transcript(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        candidates = payload.get("segments") or payload.get("body") or payload.get("transcript_segments")
    else:
        candidates = payload
    if not isinstance(candidates, list):
        raise PrototypeError("JSON transcript should be a list or contain segments/body/transcript_segments.")

    segments: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        text = item.get("text") or item.get("content") or item.get("txt")
        if not text:
            continue
        segments.append(
            {
                "index": len(segments) + 1,
                "page": item.get("page", 1),
                "start": item.get("start", item.get("from")),
                "end": item.get("end", item.get("to")),
                "text": clean_caption_text(str(text)),
                "source": "local_json",
            }
        )
    return segments


def load_local_transcript(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".vtt", ".srt"}:
        return parse_caption_file(path)
    if suffix == ".json":
        return parse_json_transcript(path)
    return parse_plain_transcript(path)


def transcript_to_markdown(context: dict[str, Any]) -> str:
    title = context.get("metadata", {}).get("title") or context.get("source", {}).get("local_transcript") or "Video"
    lines = [f"# Transcript: {title}", ""]
    current_page = None
    for segment in context.get("transcript_segments", []):
        page = segment.get("page")
        if page != current_page:
            current_page = page
            page_title = segment.get("page_title") or f"Part {page}"
            lines.extend([f"## {page_title}", ""])
        stamp = seconds_to_stamp(segment.get("start"))
        prefix = f"[{stamp}] " if stamp else ""
        lines.append(prefix + segment.get("text", ""))
    lines.append("")
    return "\n".join(lines)


def save_context(context: dict[str, Any], run_dir: Path) -> None:
    (run_dir / "context.json").write_text(json.dumps(context, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_dir / "transcript.md").write_text(transcript_to_markdown(context), encoding="utf-8")


def format_context_for_prompt(context: dict[str, Any], question: str, max_chars: int, mode: str) -> str:
    metadata = context.get("metadata", {})
    warnings = context.get("warnings", [])
    header = [
        f"Title: {metadata.get('title', '')}",
        f"Owner: {metadata.get('owner_name', '')}",
        f"Duration seconds: {metadata.get('duration', '')}",
        f"Publish timestamp: {metadata.get('pubdate', '')}",
        f"View count: {metadata.get('view_count', '')}",
        f"Danmaku count: {metadata.get('danmaku_count', '')}",
        f"Description: {metadata.get('description', '')[:1200]}",
        "Warnings: " + ("; ".join(str(item) for item in warnings) if warnings else "none"),
        "",
        "Transcript:",
    ]

    segments = context.get("transcript_segments", [])
    segment_lines = []
    for segment in segments:
        stamp = seconds_to_stamp(segment.get("start"))
        page = segment.get("page", 1)
        prefix = f"[P{page} {stamp}]" if stamp else f"[P{page}]"
        segment_lines.append(f"{prefix} {segment.get('text', '')}")

    transcript = "\n".join(segment_lines)
    budget = max_chars - len("\n".join(header))
    if mode == "full" or len(transcript) <= budget:
        selected = transcript[: max(0, budget)]
    else:
        selected = retrieve_relevant_lines(segment_lines, question, budget)

    danmaku = context.get("danmaku", [])
    danmaku_text = ""
    if danmaku:
        compact = []
        for item in danmaku[:80]:
            stamp = seconds_to_stamp(item.get("time"))
            compact.append(f"[{stamp}] {item.get('text', '')}")
        danmaku_text = "\n\nSelected danmaku/audience comments:\n" + "\n".join(compact)

    return "\n".join(header) + "\n" + selected + danmaku_text


def retrieve_relevant_lines(lines: list[str], question: str, max_chars: int) -> str:
    terms = {term.lower() for term in re.findall(r"[\w\u4e00-\u9fff]+", question) if len(term) > 1}
    if not terms:
        return "\n".join(lines[:200])[:max_chars]

    scored: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        lowered = line.lower()
        score = sum(1 for term in terms if term in lowered)
        if score:
            scored.append((score, index, line))

    selected_indexes = {0, 1, len(lines) - 1}
    for _, index, _ in sorted(scored, reverse=True)[:120]:
        selected_indexes.update({max(0, index - 1), index, min(len(lines) - 1, index + 1)})

    selected = [lines[index] for index in sorted(selected_indexes) if 0 <= index < len(lines)]
    text = "\n".join(selected)
    return text[:max_chars]


def write_markdown_answer(path: Path, question: str, answer: str, context_path: Path | None = None) -> None:
    lines = ["# Video QA Answer", "", f"## Question", "", question, "", "## Answer", "", answer, ""]
    if context_path:
        lines.extend(["## Context", "", f"`{context_path}`", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def print_error(exc: Exception) -> int:
    print(f"error: {exc}", file=sys.stderr)
    return 2
