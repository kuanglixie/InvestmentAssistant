#!/usr/bin/env python3
"""Prepare structured context for asking questions about a Bilibili video."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from bilibili_common import (
    PrototypeError,
    clean_caption_text,
    default_artifact_root,
    fetch_json,
    fetch_text,
    load_local_transcript,
    make_run_dir,
    normalize_asset_url,
    normalize_bilibili_url,
    print_error,
    save_context,
)


VIEW_API = "https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
PLAYER_API = "https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}"
DANMAKU_API = "https://comment.bilibili.com/{cid}.xml"


def fetch_view_metadata(bvid: str, timeout: int) -> dict[str, Any]:
    payload = fetch_json(VIEW_API.format(bvid=bvid), timeout=timeout, referer=f"https://www.bilibili.com/video/{bvid}/")
    if payload.get("code") != 0:
        raise PrototypeError(f"Bilibili view API returned code={payload.get('code')}: {payload.get('message')}")
    return payload["data"]


def select_subtitles(subtitles: list[dict[str, Any]], preferred_lang: str | None) -> list[dict[str, Any]]:
    if not subtitles:
        return []
    if preferred_lang:
        exact = [
            item
            for item in subtitles
            if preferred_lang.lower() in str(item.get("lan", "")).lower()
            or preferred_lang.lower() in str(item.get("lan_doc", "")).lower()
        ]
        if exact:
            return exact[:1]
    return subtitles[:1]


def fetch_page_subtitles(
    bvid: str,
    page: dict[str, Any],
    preferred_lang: str | None,
    timeout: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    cid = page["cid"]
    payload = fetch_json(
        PLAYER_API.format(bvid=bvid, cid=cid),
        timeout=timeout,
        referer=f"https://www.bilibili.com/video/{bvid}/",
    )
    if payload.get("code") != 0:
        warnings.append(f"player API returned code={payload.get('code')} for cid={cid}: {payload.get('message')}")
        return [], warnings

    subtitle_data = (payload.get("data") or {}).get("subtitle") or {}
    subtitles = subtitle_data.get("subtitles") or []
    selected = select_subtitles(subtitles, preferred_lang)
    if not selected:
        warnings.append(f"no public subtitles found for cid={cid}")
        return [], warnings

    segments: list[dict[str, Any]] = []
    for subtitle in selected:
        subtitle_url = normalize_asset_url(subtitle.get("subtitle_url", ""))
        if not subtitle_url:
            continue
        body_payload = fetch_json(subtitle_url, timeout=timeout, referer=f"https://www.bilibili.com/video/{bvid}/")
        body = body_payload.get("body") or []
        for item in body:
            text = item.get("content")
            if not text:
                continue
            segments.append(
                {
                    "index": len(segments) + 1,
                    "page": page.get("page", 1),
                    "page_title": page.get("part"),
                    "start": item.get("from"),
                    "end": item.get("to"),
                    "text": clean_caption_text(str(text)),
                    "source": "bilibili_subtitle",
                    "language": subtitle.get("lan"),
                    "language_name": subtitle.get("lan_doc"),
                    "subtitle_url": subtitle_url,
                }
            )

    if not segments:
        warnings.append(f"subtitle metadata existed but no subtitle body text was parsed for cid={cid}")
    return segments, warnings


def fetch_danmaku(cid: int, timeout: int, limit: int) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    try:
        text, _ = fetch_text(DANMAKU_API.format(cid=cid), timeout=timeout)
    except PrototypeError as exc:
        return [], [str(exc)]

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return [], [f"could not parse danmaku XML for cid={cid}: {exc}"]

    comments: list[dict[str, Any]] = []
    for node in root.findall("d"):
        raw_p = node.attrib.get("p", "")
        parts = raw_p.split(",")
        try:
            timestamp = float(parts[0]) if parts else None
        except ValueError:
            timestamp = None
        comments.append({"time": timestamp, "text": clean_caption_text(node.text or ""), "raw_p": raw_p})
        if len(comments) >= limit:
            break
    return comments, warnings


def build_context_from_bilibili(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    bvid, final_url = normalize_bilibili_url(args.url or args.bvid, timeout=args.timeout)
    if not bvid:
        raise PrototypeError("Could not find a BVID. Pass --bvid BV... or a Bilibili video URL.")

    view = fetch_view_metadata(bvid, args.timeout)
    pages = view.get("pages") or []
    if args.page:
        pages = [page for page in pages if int(page.get("page", 0)) == args.page]
    if args.max_pages:
        pages = pages[: args.max_pages]
    if not pages:
        raise PrototypeError("No pages found for this video.")

    warnings: list[str] = []
    transcript_segments: list[dict[str, Any]] = []
    danmaku: list[dict[str, Any]] = []

    for page in pages:
        segments, segment_warnings = fetch_page_subtitles(bvid, page, args.lang, args.timeout)
        warnings.extend(segment_warnings)
        transcript_segments.extend(segments)
        if args.include_danmaku:
            comments, comment_warnings = fetch_danmaku(page["cid"], args.timeout, args.danmaku_limit)
            warnings.extend(comment_warnings)
            danmaku.extend(comments)

    for index, segment in enumerate(transcript_segments, start=1):
        segment["index"] = index

    context = {
        "source": {
            "type": "bilibili",
            "url": final_url,
            "bvid": bvid,
        },
        "metadata": {
            "title": view.get("title"),
            "description": view.get("desc"),
            "owner_name": (view.get("owner") or {}).get("name"),
            "owner_mid": (view.get("owner") or {}).get("mid"),
            "duration": view.get("duration"),
            "pubdate": view.get("pubdate"),
            "view_count": (view.get("stat") or {}).get("view"),
            "danmaku_count": (view.get("stat") or {}).get("danmaku"),
        },
        "pages": pages,
        "transcript_segments": transcript_segments,
        "danmaku": danmaku,
        "warnings": warnings,
    }
    return context, view.get("title") or bvid


def build_context_from_local(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    path = args.local_transcript.expanduser().resolve()
    if not path.exists():
        raise PrototypeError(f"local transcript not found: {path}")
    segments = load_local_transcript(path)
    context = {
        "source": {
            "type": "local_transcript",
            "local_transcript": str(path),
        },
        "metadata": {
            "title": args.title or path.stem,
            "description": "",
            "owner_name": "",
        },
        "pages": [{"page": 1, "part": path.name}],
        "transcript_segments": segments,
        "danmaku": [],
        "warnings": [],
    }
    return context, args.title or path.stem


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Bilibili video URL.")
    source.add_argument("--bvid", help="Bilibili BVID, e.g. BV...")
    source.add_argument("--local-transcript", type=Path, help="Local .txt/.vtt/.srt/.json transcript.")
    parser.add_argument("--title", help="Title override for local transcript input.")
    parser.add_argument("--lang", default=None, help="Preferred subtitle language, e.g. zh, en, ai-zh.")
    parser.add_argument("--page", type=int, help="Only fetch one video page/part.")
    parser.add_argument("--max-pages", type=int, help="Limit number of pages/parts.")
    parser.add_argument("--include-danmaku", action="store_true")
    parser.add_argument("--danmaku-limit", type=int, default=300)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--output-dir", type=Path, default=default_artifact_root())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.local_transcript:
            context, title = build_context_from_local(args)
        else:
            context, title = build_context_from_bilibili(args)
        run_dir = make_run_dir(args.output_dir.expanduser().resolve(), title)
        save_context(context, run_dir)
    except Exception as exc:
        return print_error(exc)

    print(json.dumps({"run_dir": str(run_dir), "context": str(run_dir / "context.json")}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

