#!/usr/bin/env python3
"""Inspect an official webcast page for transcript/caption/media assets.

This script is intentionally conservative:
- it only uses public page/player metadata;
- it does not submit guestbook forms;
- it does not bypass authentication or registration gates.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)

MEDIA_PATTERNS = (
    ".m3u8",
    ".mp4",
    ".m4a",
    ".mp3",
    ".aac",
    ".wav",
    ".vtt",
    ".srt",
    "captions_url",
    "webvtt",
)

INTERESTING_KEYS = (
    "transcript",
    "caption",
    "captions",
    "subtitle",
    "subtitles",
    "texttrack",
    "texttracks",
    "webvtt",
    "summary",
    "media_sets",
    "media",
    "assets",
    "playlists",
    "clip",
)


class FetchError(RuntimeError):
    pass


def fetch_text(url: str, timeout: int) -> tuple[str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            text = response.read().decode(charset, errors="replace")
            return text, response.geturl()
    except urllib.error.HTTPError as exc:
        raise FetchError(f"HTTP {exc.code} while fetching {url}") from exc
    except urllib.error.URLError as exc:
        raise FetchError(f"Network error while fetching {url}: {exc.reason}") from exc


def extract_first_webcast_url(html: str) -> str | None:
    match = re.search(r"https?://edge\.media-server\.com/mmc/p/[A-Za-z0-9_-]+/?", html)
    if match:
        return match.group(0)
    match = re.search(r"edge\.media-server\.com/mmc/p/[A-Za-z0-9_-]+/?", html)
    if match:
        return "https://" + match.group(0)
    return None


def extract_player_hash(url: str, html: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    path_match = re.search(r"/mmc/p/([A-Za-z0-9_-]+)", parsed.path)
    if path_match:
        return path_match.group(1)

    env_match = re.search(r"PLAYER_HASH\s*=\s*['\"]([^'\"]+)['\"]", html)
    if env_match:
        return env_match.group(1)

    param_match = re.search(r"params\.P\s*=\s*['\"]([^'\"]+)['\"]", html)
    if param_match:
        return param_match.group(1)

    return None


def extract_version_time(html: str) -> str | None:
    match = re.search(r"VERSIONTIME\s*=\s*['\"]?([0-9]+)['\"]?", html)
    if match:
        return match.group(1)
    match = re.search(r"/version/([0-9]+)/mmc/", html)
    if match:
        return match.group(1)
    return None


def build_metadata_url(player_hash: str, version_time: str) -> str:
    linkrnd = str(int(time.time() * 1000))
    return (
        f"https://edge.media-server.com/version/{version_time}/mmc/d/"
        f"linkrnd/{linkrnd}/p/{player_hash}/load_content/true/html5/true/"
    )


def is_media_like(value: str) -> bool:
    lowered = value.lower()
    return any(pattern in lowered for pattern in MEDIA_PATTERNS)


def compact(value: Any, limit: int = 600) -> Any:
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + "..."
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [compact(item, limit=180) for item in value[:8]]
    if isinstance(value, dict):
        return {str(key): compact(val, limit=180) for key, val in list(value.items())[:16]}
    return str(value)


def walk_interesting(data: Any, path: str = "$") -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    interesting: list[dict[str, Any]] = []
    media_candidates: list[dict[str, str]] = []

    def visit(value: Any, current_path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                key_path = f"{current_path}.{key}"
                lowered_key = str(key).lower()
                if any(token in lowered_key for token in INTERESTING_KEYS):
                    interesting.append({"path": key_path, "value": compact(child)})
                visit(child, key_path)
            return

        if isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{current_path}[{index}]")
            return

        if isinstance(value, str) and is_media_like(value):
            media_candidates.append({"path": current_path, "url_or_value": value})

    visit(data, path)
    return interesting[:80], media_candidates[:80]


def caption_candidates(media_candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        item
        for item in media_candidates
        if any(token in item["url_or_value"].lower() for token in (".vtt", ".srt", "caption", "subtitle"))
    ]


def infer_status(metadata: dict[str, Any], media_candidates: list[dict[str, str]]) -> str:
    if media_candidates:
        return "public_media_or_caption_candidate_found"
    if metadata.get("authentication_required") or metadata.get("remember_auth_enabled"):
        return "registration_required_or_no_public_item"
    if metadata.get("playlists") == [] and "item" not in metadata:
        return "no_public_item_in_metadata"
    return "no_transcript_or_media_candidate_found"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def download_caption_assets(candidates: list[dict[str, str]], output_dir: Path, timeout: int) -> list[str]:
    downloaded: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, candidate in enumerate(candidates, start=1):
        value = candidate["url_or_value"]
        if not value.startswith(("http://", "https://")):
            continue
        suffix = ".vtt" if ".vtt" in value.lower() else ".srt" if ".srt" in value.lower() else ".txt"
        target = output_dir / f"caption-{index}{suffix}"
        text, _ = fetch_text(value, timeout)
        target.write_text(text, encoding="utf-8")
        downloaded.append(str(target))
    return downloaded


def inspect(url: str, timeout: int) -> dict[str, Any]:
    initial_html, final_url = fetch_text(url, timeout)

    player_url = final_url
    if "edge.media-server.com/mmc/p/" not in final_url:
        discovered = extract_first_webcast_url(initial_html)
        if discovered:
            player_url = discovered
            initial_html, final_url = fetch_text(player_url, timeout)
            player_url = final_url

    player_hash = extract_player_hash(player_url, initial_html)
    version_time = extract_version_time(initial_html)

    if not player_hash:
        raise FetchError("Could not find a media-server player hash in the supplied page.")
    if not version_time:
        raise FetchError("Could not find media-server version metadata in the player page.")

    metadata_url = build_metadata_url(player_hash, version_time)
    metadata_text, metadata_final_url = fetch_text(metadata_url, timeout)
    try:
        metadata = json.loads(metadata_text)
    except json.JSONDecodeError as exc:
        raise FetchError(f"Player metadata was not JSON: {metadata_final_url}") from exc

    interesting, media_candidates = walk_interesting(metadata)
    captions = caption_candidates(media_candidates)

    return {
        "source_url": url,
        "player_page_url": player_url,
        "player_hash": player_hash,
        "version_time": version_time,
        "metadata_url": metadata_url,
        "title": metadata.get("default_title"),
        "default_item_mode": metadata.get("default_item_mode"),
        "authentication_required": metadata.get("authentication_required"),
        "remember_auth_enabled": metadata.get("remember_auth_enabled"),
        "playlists_count": len(metadata.get("playlists") or []),
        "has_item": "item" in metadata,
        "status": infer_status(metadata, media_candidates),
        "caption_candidates": captions,
        "media_candidates": media_candidates,
        "interesting_fields": interesting,
        "next_steps": [
            "If caption_candidates contains a .vtt or .srt URL, download it and convert to a transcript.",
            "If status is registration_required_or_no_public_item, access the webcast normally and create a local audio capture.",
            "Run transcribe_local.py on the captured audio/video file.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Official webcast/player/event URL.")
    parser.add_argument("--out", type=Path, help="Where to write inspection JSON.")
    parser.add_argument("--download-captions", type=Path, help="Directory for public .vtt/.srt candidates.")
    parser.add_argument("--timeout", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = inspect(args.url, args.timeout)
        if args.download_captions:
            result["downloaded_captions"] = download_caption_assets(
                result["caption_candidates"], args.download_captions, args.timeout
            )
    except FetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.out:
        write_json(args.out, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

