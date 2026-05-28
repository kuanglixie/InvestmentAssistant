from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse, urlunparse

from stock_research.state import utc_now_iso


YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def build_video_manifest(
    *,
    company_id: str,
    sources: list[dict[str, Any]],
    source_results: list[dict[str, Any]],
    source_family: str,
    agent_id: str,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    result_by_source_id = {
        str(result.get("source_id")): result
        for result in source_results
        if result.get("source_id")
    }
    records = []
    excluded_sources = []
    for source in sources:
        record = video_manifest_record_from_source(
            company_id=company_id,
            source=source,
            result=result_by_source_id.get(str(source.get("source_id")), {}),
            source_family=source_family,
            agent_id=agent_id,
        )
        if not record.get("native_video_id") and not record.get("canonical_url"):
            excluded_sources.append(
                {
                    "source_id": source.get("source_id"),
                    "reason": "missing_url_or_native_video_id",
                    "status": (result_by_source_id.get(str(source.get("source_id")), {}) or source).get("status"),
                }
            )
            continue
        records.append(record)
    manifest = merge_video_manifests(
        {
            "schema_version": 1,
            "company_id": company_id,
            "generated_at": utc_now_iso(),
            "registry_paths": [str(registry_path)] if registry_path else [],
            "key_policy": {
                "video_uid": "Stable internal content key. Prefer platform native video/event id; otherwise use canonical URL hash.",
                "source_id": "Registry row id. Multiple source_ids can point to the same video_uid.",
                "collection_attempts": "Per-agent/per-source collection status, including transcript availability and cache paths.",
            },
            "records": records,
            "excluded_sources": excluded_sources,
        }
    )
    manifest["registry_paths"] = [str(registry_path)] if registry_path else []
    manifest["excluded_sources"] = excluded_sources
    return manifest


def video_manifest_record_from_source(
    *,
    company_id: str,
    source: dict[str, Any],
    result: dict[str, Any] | None,
    source_family: str,
    agent_id: str,
) -> dict[str, Any]:
    result = result or {}
    platform = str(source.get("platform") or result.get("platform") or "unknown").strip() or "unknown"
    url = str(source.get("url") or result.get("url") or "").strip()
    native_id, native_id_type = native_video_id(source, url=url, platform=platform)
    canonical_url = canonicalize_url(url)
    video_uid = build_video_uid(platform=platform, native_id=native_id, canonical_url=canonical_url)
    now = utc_now_iso()
    attempt = {
        "agent_id": agent_id,
        "source_family": source_family,
        "source_id": source.get("source_id") or result.get("source_id"),
        "adapter": source.get("adapter") or result.get("adapter"),
        "status": result.get("status") or source.get("status") or "registered",
        "transcript_method": result.get("transcript_method"),
        "transcript_segment_count": int(result.get("transcript_segment_count") or 0),
        "evidence_item_count": len(result.get("evidence_items") or []),
        "cache_paths": sorted({str(path) for path in result.get("cache_paths", [])}),
        "errors": [str(error) for error in result.get("errors", [])],
        "collected_at": result.get("generated_at") or now,
    }
    return {
        "video_uid": video_uid,
        "company_id": company_id,
        "platform": platform,
        "native_video_id": native_id,
        "native_id_type": native_id_type,
        "canonical_url": canonical_url,
        "source_ids": [source.get("source_id") or result.get("source_id")],
        "source_families": [source_family],
        "agent_ids": [agent_id],
        "name": source.get("name") or result.get("name"),
        "media_kind": media_kind_for_source(source, platform=platform),
        "event_type": source.get("event_type") or result.get("event_type"),
        "period": source.get("period") or result.get("period"),
        "language": source.get("language") or result.get("language"),
        "source_owner": source.get("source_owner"),
        "source_quality_tier": source.get("source_quality_tier") or result.get("source_quality_tier"),
        "rights_status": source.get("rights_status") or default_rights_status(source),
        "allowed_uses": source.get("allowed_uses") or default_allowed_uses(source),
        "use_case_tags": sorted({str(tag) for tag in source.get("use_case_tags", []) if tag}),
        "created_at": now,
        "updated_at": now,
        "collection_attempts": [attempt],
        "latest_collection_status": attempt["status"],
        "latest_transcript_method": attempt["transcript_method"],
        "total_transcript_segments": attempt["transcript_segment_count"],
        "total_evidence_items": attempt["evidence_item_count"],
    }


def merge_video_manifests(*manifests: dict[str, Any] | None) -> dict[str, Any]:
    by_uid: dict[str, dict[str, Any]] = {}
    registry_paths: list[str] = []
    excluded_sources: list[dict[str, Any]] = []
    company_id = "unknown"
    for manifest in manifests:
        if not manifest:
            continue
        company_id = str(manifest.get("company_id") or company_id)
        for path in manifest.get("registry_paths") or []:
            if path and path not in registry_paths:
                registry_paths.append(str(path))
        excluded_sources.extend(manifest.get("excluded_sources") or [])
        for record in manifest.get("records") or []:
            uid = str(record.get("video_uid") or "")
            if not uid:
                continue
            if uid not in by_uid:
                by_uid[uid] = {**record}
                continue
            by_uid[uid] = merge_video_records(by_uid[uid], record)

    records = sorted(by_uid.values(), key=lambda item: str(item.get("video_uid") or ""))
    return {
        "schema_version": 1,
        "company_id": company_id,
        "generated_at": utc_now_iso(),
        "registry_paths": registry_paths,
        "record_count": len(records),
        "records": records,
        "excluded_sources": excluded_sources,
        "key_policy": {
            "video_uid": "Stable internal content key. Prefer platform native video/event id; otherwise use canonical URL hash.",
            "source_id": "Registry row id. Multiple source_ids can point to the same video_uid.",
            "collection_attempts": "Per-agent/per-source collection status, including transcript availability and cache paths.",
        },
    }


def merge_video_records(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = {**left}
    for key in ("source_ids", "source_families", "agent_ids", "use_case_tags"):
        merged[key] = _unique_sorted([*(left.get(key) or []), *(right.get(key) or [])])
    attempts = [*(left.get("collection_attempts") or []), *(right.get("collection_attempts") or [])]
    merged["collection_attempts"] = _dedupe_attempts(attempts)
    for key in (
        "name",
        "media_kind",
        "event_type",
        "period",
        "language",
        "source_owner",
        "source_quality_tier",
        "rights_status",
        "allowed_uses",
        "native_video_id",
        "native_id_type",
        "canonical_url",
        "platform",
    ):
        if not merged.get(key) and right.get(key):
            merged[key] = right.get(key)
    latest_attempt = merged["collection_attempts"][-1] if merged["collection_attempts"] else {}
    merged["latest_collection_status"] = latest_attempt.get("status")
    merged["latest_transcript_method"] = latest_attempt.get("transcript_method")
    merged["total_transcript_segments"] = sum(
        int(attempt.get("transcript_segment_count") or 0)
        for attempt in merged["collection_attempts"]
    )
    merged["total_evidence_items"] = sum(
        int(attempt.get("evidence_item_count") or 0)
        for attempt in merged["collection_attempts"]
    )
    merged["updated_at"] = utc_now_iso()
    return merged


def attach_video_uids(records: list[dict[str, Any]], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    uid_by_source_id: dict[str, str] = {}
    for manifest_record in manifest.get("records") or []:
        uid = str(manifest_record.get("video_uid") or "")
        for source_id in manifest_record.get("source_ids") or []:
            if uid and source_id:
                uid_by_source_id[str(source_id)] = uid
    for record in records:
        source_id = str(record.get("source_id") or "")
        if source_id in uid_by_source_id:
            record["video_uid"] = uid_by_source_id[source_id]
    return records


def native_video_id(source: dict[str, Any], *, url: str, platform: str) -> tuple[str | None, str | None]:
    lowered_platform = platform.lower()
    if "youtube" in lowered_platform:
        return source.get("video_id") or youtube_video_id(url), "youtube_video_id"
    if "bilibili" in lowered_platform:
        return source.get("bvid") or bilibili_bvid(url), "bilibili_bvid"
    if "edge_media_server" in lowered_platform or "media-server" in url:
        return source.get("player_hash") or edge_media_server_player_hash(url), "edge_media_server_player_hash"
    return source.get("native_video_id"), source.get("native_id_type")


def build_video_uid(*, platform: str, native_id: str | None, canonical_url: str) -> str:
    platform_key = slug(platform or "unknown")
    if native_id:
        return f"video:{platform_key}:{slug(str(native_id))}"
    url_hash = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:16]
    return f"content:{platform_key}:{url_hash}"


def media_kind_for_source(source: dict[str, Any], *, platform: str) -> str:
    adapter = str(source.get("adapter") or "")
    if source.get("event_type"):
        return "official_event_video_or_webcast"
    if "web_reader" in adapter or "web_interview" in platform:
        return "web_interview_text"
    if "youtube" in platform.lower() or "bilibili" in platform.lower():
        return "video"
    return "media_or_text_source"


def default_rights_status(source: dict[str, Any]) -> str:
    tier = source.get("source_quality_tier")
    if tier == 1:
        return "official_public_metadata_transcript_only_if_available_or_permitted"
    return "third_party_public_metadata_evidence_digest_only"


def default_allowed_uses(source: dict[str, Any]) -> list[str]:
    if source.get("source_quality_tier") == 1:
        return [
            "store_source_metadata",
            "store_public_caption_transcript_when_available_or_permitted",
            "store_evidence_digest",
        ]
    return [
        "store_source_metadata",
        "store_evidence_digest",
        "do_not_bulk_archive_full_transcript_without_license_or_user_provided_file",
    ]


def canonicalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or parsed.path
    query = parse_qs(parsed.query, keep_blank_values=True)
    if host in YOUTUBE_HOSTS:
        video_id = youtube_video_id(url)
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
    if "bilibili.com" in host:
        bvid = bilibili_bvid(url)
        if bvid:
            return f"https://www.bilibili.com/video/{bvid}"
    if "edge.media-server.com" in host:
        player_hash = edge_media_server_player_hash(url)
        if player_hash:
            return f"https://edge.media-server.com/mmc/p/{player_hash}"
    clean_query = ""
    if "id" in query:
        clean_query = f"id={query['id'][0]}"
    return urlunparse((parsed.scheme or "https", host, path, "", clean_query, ""))


def youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host == "youtu.be":
        return parsed.path.strip("/") or None
    query_id = parse_qs(parsed.query).get("v")
    if query_id:
        return query_id[0]
    match = re.search(r"/(?:shorts|embed|live)/([A-Za-z0-9_-]{6,})", parsed.path)
    if match:
        return match.group(1)
    return None


def bilibili_bvid(url: str) -> str | None:
    match = re.search(r"(BV[A-Za-z0-9]+)", url)
    if match:
        return match.group(1)
    return None


def edge_media_server_player_hash(url: str) -> str | None:
    match = re.search(r"/mmc/p/([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)
    return None


def slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower() or "unknown"


def _unique_sorted(values: list[Any]) -> list[str]:
    return sorted({str(value) for value in values if value})


def _dedupe_attempts(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    order: list[tuple[str, str, str]] = []
    for attempt in attempts:
        key = (
            str(attempt.get("agent_id") or ""),
            str(attempt.get("source_id") or ""),
            str(attempt.get("status") or ""),
        )
        if key not in by_key:
            order.append(key)
        by_key[key] = attempt
    return [by_key[key] for key in order]
