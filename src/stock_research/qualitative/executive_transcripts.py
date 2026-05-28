from __future__ import annotations

import html
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

from stock_research.sources.http import FetchError, fetch_bytes, fetch_json, write_json
from stock_research.state import utc_now_iso
from stock_research.qualitative.business_model_video_questions import (
    business_model_question_pack_summary,
    business_model_question_results_from_segments,
    question_results_without_transcript,
)
from stock_research.qualitative.video_manifest import attach_video_uids, build_video_manifest


DEFAULT_PDD_EXECUTIVE_VIDEO_REGISTRY = Path("config/qualitative/pdd_executive_video_sources.v1.json")
EXECUTIVE_VIDEO_USER_AGENT = "stock-research-system/0.1 executive-transcript-research"
SPACE_PATTERN = re.compile(r"\s+")
YOUTUBE_PLAYER_MARKER = "ytInitialPlayerResponse"
WEB_READER_PREFIX = "https://r.jina.ai/"
HTML_ARTICLE_TEXT_PATTERN = re.compile(r"<(h1|h2|h3|p)\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


EXECUTIVE_TRANSCRIPT_TERM_GROUPS = {
    "business_model": [
        "business model",
        "platform",
        "ecosystem",
        "merchant",
        "seller",
        "consumer",
        "customer",
        "商业模式",
        "平台",
        "生态",
        "商家",
        "消费者",
        "用户",
    ],
    "operating_values": [
        "long-term",
        "long term",
        "value",
        "trust",
        "responsibility",
        "Ben Fen",
        "本分",
        "长期",
        "价值",
        "信任",
        "责任",
    ],
    "price_and_quality": [
        "price",
        "quality",
        "cost",
        "affordable",
        "value-for-money",
        "价格",
        "质量",
        "成本",
        "性价比",
        "便宜",
    ],
    "competition": [
        "competition",
        "competitor",
        "copy",
        "竞争",
        "对手",
        "模仿",
    ],
    "leadership_and_org": [
        "Colin Huang",
        "Huang Zheng",
        "Zheng Huang",
        "Chen Lei",
        "Jiazhen Zhao",
        "founder",
        "CEO",
        "黄峥",
        "陈磊",
        "赵佳臻",
        "创始人",
        "组织",
    ],
}


def collect_executive_video_transcripts(
    *,
    company: dict[str, Any],
    cache_root: str | Path = "data/raw/executive_transcripts",
    offline: bool | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    company_id = str(company.get("company_id") or "").lower()
    if company_id != "pdd":
        return {
            "status": "not_configured_for_company_v1",
            "company_id": company_id or "unknown",
            "source_results": [],
            "evidence_items": [],
            "audit_notes": ["Executive transcript collection is currently configured for PDD only."],
        }

    if offline is None:
        offline = os.environ.get("STOCK_RESEARCH_OFFLINE") == "1"

    registry = _load_registry(registry_path or DEFAULT_PDD_EXECUTIVE_VIDEO_REGISTRY)
    cache_dir = Path(cache_root) / company_id
    source_results = []
    evidence_items: list[dict[str, Any]] = []
    for source in registry.get("sources", []):
        adapter = source.get("adapter")
        if adapter == "youtube_caption_tracks":
            result = _collect_youtube_source(source, registry=registry, cache_dir=cache_dir, offline=offline)
        elif adapter == "bilibili_subtitle_api":
            result = _collect_bilibili_source(source, registry=registry, cache_dir=cache_dir, offline=offline)
        elif adapter == "manual_transcript_file":
            result = _collect_manual_transcript_file_source(source, registry=registry, cache_dir=cache_dir, offline=offline)
        elif adapter == "web_reader_interview_page":
            result = _collect_web_reader_interview_source(source, registry=registry, cache_dir=cache_dir, offline=offline)
        else:
            result = _manual_source_result(source, offline=offline)
        if _should_queue_business_model_questions(source) and not result.get("business_model_question_results"):
            result["business_model_question_results"] = question_results_without_transcript(
                source,
                status=str(result.get("status") or "not_collected"),
            )
        source_results.append(result)
        evidence_items.extend(result.get("evidence_items", []))

    status_counts = Counter(str(result.get("status") or "unknown") for result in source_results)
    transcript_sources = [
        result for result in source_results if result.get("transcript_segment_count", 0) > 0
    ]
    errors = [
        error
        for result in source_results
        for error in result.get("errors", [])
    ]
    status = "transcript_evidence_collected" if evidence_items else "source_plan_ready_no_transcripts_collected"
    if offline:
        status = "offline_source_plan_ready"
    elif transcript_sources and not evidence_items:
        status = "transcripts_collected_no_relevant_claims"

    video_manifest = build_video_manifest(
        company_id=company_id,
        sources=registry.get("sources", []),
        source_results=source_results,
        source_family="executive_interviews_and_video_transcripts",
        agent_id="executive_transcripts",
        registry_path=registry_path or DEFAULT_PDD_EXECUTIVE_VIDEO_REGISTRY,
    )
    attach_video_uids(source_results, video_manifest)
    attach_video_uids(evidence_items, video_manifest)
    for result in source_results:
        for item in result.get("business_model_question_results") or []:
            if result.get("video_uid") and not item.get("video_uid"):
                item["video_uid"] = result.get("video_uid")

    return {
        "status": status,
        "company_id": company_id,
        "registry_path": str(registry_path or DEFAULT_PDD_EXECUTIVE_VIDEO_REGISTRY),
        "generated_at": utc_now_iso(),
        "offline": offline,
        "source_count": len(registry.get("sources", [])),
        "collectable_source_count": sum(1 for source in registry.get("sources", []) if _is_collectable_adapter(source)),
        "manual_or_pending_source_count": sum(1 for source in registry.get("sources", []) if not _is_collectable_adapter(source)),
        "source_status_counts": dict(sorted(status_counts.items())),
        "transcript_source_count": len(transcript_sources),
        "transcript_segment_count": sum(int(result.get("transcript_segment_count") or 0) for result in source_results),
        "evidence_item_count": len(evidence_items),
        "business_model_question_pack": business_model_question_pack_summary(source_results),
        "source_results": source_results,
        "evidence_items": evidence_items,
        "video_manifest": video_manifest,
        "theme_summary": _theme_summary(evidence_items),
        "audit_policy": registry.get("audit_policy", {}),
        "audit_notes": [
            "Executive videos and interviews explain management thinking; they do not override filings or audited numbers.",
            "The collector records transcript availability, source provenance, platform, language, and cache paths.",
            "If captions/subtitles are missing or blocked, the agent records that state and produces no synthetic transcript.",
            "Business-model questions are run over collected captions/subtitles or queued with a clear missing-transcript status.",
            "External interview/video material should be cross-checked against filings, financial outcomes, customer evidence, and merchant evidence.",
        ],
        "errors": errors,
    }


def _load_registry(path: str | Path) -> dict[str, Any]:
    registry_path = Path(path)
    return json.loads(registry_path.read_text(encoding="utf-8"))


def _is_collectable_adapter(source: dict[str, Any]) -> bool:
    return source.get("adapter") in {
        "youtube_caption_tracks",
        "bilibili_subtitle_api",
        "manual_transcript_file",
        "web_reader_interview_page",
    }


def _should_queue_business_model_questions(source: dict[str, Any]) -> bool:
    tags = {str(tag).lower() for tag in source.get("use_case_tags", [])}
    return "business_model" in tags


def _manual_source_result(source: dict[str, Any], *, offline: bool) -> dict[str, Any]:
    result = {
        "source_id": source.get("source_id"),
        "name": source.get("name"),
        "adapter": source.get("adapter"),
        "platform": source.get("platform"),
        "status": "offline_not_collected" if offline else source.get("status", "planned"),
        "source_quality_tier": source.get("source_quality_tier"),
        "language": source.get("language"),
        "url": source.get("url"),
        "transcript_segment_count": 0,
        "evidence_items": [],
        "errors": [],
        "notes": [
            "Source is registered, but this V1 collector only automates YouTube caption tracks and Bilibili subtitle APIs.",
        ],
    }
    if _should_queue_business_model_questions(source):
        result["business_model_question_results"] = question_results_without_transcript(
            source,
            status=str(result["status"]),
        )
    return result


def _collect_youtube_source(
    source: dict[str, Any],
    *,
    registry: dict[str, Any],
    cache_dir: Path,
    offline: bool,
) -> dict[str, Any]:
    result = _base_result(source, offline=offline)
    if offline:
        return result

    url = str(source.get("url") or "").strip()
    video_id = source.get("video_id") or _youtube_video_id(url)
    if not url or not video_id:
        result["status"] = "missing_youtube_url_or_video_id"
        result["errors"].append(f"Missing YouTube URL/video id for {source.get('source_id')}")
        return result

    source_dir = cache_dir / _slug(str(source.get("source_id") or video_id))
    watch_path = source_dir / "watch_page.html"
    transcript_path = source_dir / "transcript.json"
    try:
        html_text = fetch_bytes(
            url,
            headers={"User-Agent": EXECUTIVE_VIDEO_USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
            timeout=35,
            rate_limit_seconds=float(source.get("rate_limit_seconds", registry.get("default_rate_limit_seconds", 1.5))),
        ).decode("utf-8", errors="replace")
        _write_text(watch_path, html_text)
    except FetchError as exc:
        result["status"] = "collection_failed_or_blocked"
        result["errors"].append(str(exc))
        return result

    track = _select_youtube_caption_track(html_text, preferred_languages=source.get("preferred_languages") or [])
    if not track:
        result["status"] = "metadata_collected_no_caption_tracks"
        result["cache_paths"].append(str(watch_path))
        result["notes"].append("Watch page was fetched, but no captionTracks entry was found.")
        return result

    caption_url = html.unescape(str(track.get("baseUrl") or ""))
    if not caption_url:
        result["status"] = "caption_track_missing_base_url"
        result["cache_paths"].append(str(watch_path))
        return result
    try:
        payload = fetch_bytes(
            caption_url,
            headers={"User-Agent": EXECUTIVE_VIDEO_USER_AGENT},
            timeout=35,
            rate_limit_seconds=float(source.get("rate_limit_seconds", registry.get("default_rate_limit_seconds", 1.5))),
        )
    except FetchError as exc:
        result["status"] = "caption_fetch_failed_or_blocked"
        result["errors"].append(str(exc))
        result["cache_paths"].append(str(watch_path))
        return result

    segments = parse_youtube_transcript_payload(payload)
    transcript = _transcript_payload(
        source=source,
        platform="youtube",
        transcript_method="youtube_caption_tracks",
        segments=segments,
        extra={"video_id": video_id, "caption_track": _safe_caption_track(track)},
    )
    write_json(transcript_path, transcript)
    result.update(_result_from_transcript(source, transcript, registry=registry))
    result["status"] = "transcript_collected" if segments else "caption_track_fetched_no_segments"
    result["cache_paths"].extend([str(watch_path), str(transcript_path)])
    return result


def _collect_bilibili_source(
    source: dict[str, Any],
    *,
    registry: dict[str, Any],
    cache_dir: Path,
    offline: bool,
) -> dict[str, Any]:
    result = _base_result(source, offline=offline)
    if offline:
        return result

    url = str(source.get("url") or "").strip()
    bvid = source.get("bvid") or _bilibili_bvid(url)
    if not url or not bvid:
        result["status"] = "missing_bilibili_url_or_bvid"
        result["errors"].append(f"Missing Bilibili URL/BVID for {source.get('source_id')}")
        return result

    headers = {
        "User-Agent": EXECUTIVE_VIDEO_USER_AGENT,
        "Referer": f"https://www.bilibili.com/video/{bvid}/",
        "Accept": "application/json,text/plain,*/*",
    }
    source_dir = cache_dir / _slug(str(source.get("source_id") or bvid))
    pagelist_path = source_dir / "pagelist.json"
    player_path = source_dir / "player_v2.json"
    transcript_path = source_dir / "transcript.json"
    question_path = source_dir / "business_model_question_results.json"
    reader_path = source_dir / "reader_page.json"
    rate_limit = float(source.get("rate_limit_seconds", registry.get("default_rate_limit_seconds", 1.5)))

    try:
        pagelist = fetch_json(
            f"https://api.bilibili.com/x/player/pagelist?bvid={quote(str(bvid))}",
            headers=headers,
            timeout=35,
            rate_limit_seconds=rate_limit,
        )
        write_json(pagelist_path, pagelist)
    except FetchError as exc:
        result["status"] = "collection_failed_or_blocked"
        result["errors"].append(str(exc))
        return result

    cid = _bilibili_first_cid(pagelist)
    if not cid:
        result["status"] = "bilibili_pagelist_missing_cid"
        result["cache_paths"].append(str(pagelist_path))
        result["errors"].append(f"Bilibili pagelist did not expose cid for {bvid}")
        return result

    try:
        player = fetch_json(
            f"https://api.bilibili.com/x/player/v2?bvid={quote(str(bvid))}&cid={quote(str(cid))}",
            headers=headers,
            timeout=35,
            rate_limit_seconds=rate_limit,
        )
        write_json(player_path, player)
    except FetchError as exc:
        result["status"] = "bilibili_player_fetch_failed_or_blocked"
        result["errors"].append(str(exc))
        result["cache_paths"].append(str(pagelist_path))
        return result

    subtitles = (((player.get("data") or {}).get("subtitle") or {}).get("subtitles") or [])
    if not subtitles:
        result["status"] = "metadata_collected_no_subtitles"
        result["cache_paths"].extend([str(pagelist_path), str(player_path)])
        result["business_model_question_results"] = question_results_without_transcript(
            source,
            status=result["status"],
        )
        write_json(question_path, result["business_model_question_results"])
        result["cache_paths"].append(str(question_path))
        reader = _fetch_web_reader_metadata(url, cache_path=reader_path, rate_limit_seconds=rate_limit)
        if reader.get("status") == "reader_page_collected":
            result["cache_paths"].append(str(reader_path))
            result["notes"].append("Bilibili subtitle API exposed no subtitles; cached web-reader page as metadata only.")
        else:
            result["notes"].append("Bilibili subtitle API exposed no subtitles.")
            if reader.get("error"):
                result["errors"].append(str(reader["error"]))
        return result

    subtitle = _select_bilibili_subtitle(subtitles, preferred_languages=source.get("preferred_languages") or [])
    subtitle_url = _normalize_bilibili_subtitle_url(str(subtitle.get("subtitle_url") or ""), url)
    if not subtitle_url:
        result["status"] = "bilibili_subtitle_missing_url"
        result["cache_paths"].extend([str(pagelist_path), str(player_path)])
        return result

    try:
        subtitle_payload = fetch_json(
            subtitle_url,
            headers=headers,
            timeout=35,
            rate_limit_seconds=rate_limit,
        )
    except FetchError as exc:
        result["status"] = "bilibili_subtitle_fetch_failed_or_blocked"
        result["errors"].append(str(exc))
        result["cache_paths"].extend([str(pagelist_path), str(player_path)])
        return result

    segments = parse_bilibili_subtitle_payload(subtitle_payload)
    transcript = _transcript_payload(
        source=source,
        platform="bilibili",
        transcript_method="bilibili_subtitle_api",
        segments=segments,
        extra={
            "bvid": bvid,
            "cid": cid,
            "subtitle": {
                "id": subtitle.get("id"),
                "lan": subtitle.get("lan"),
                "lan_doc": subtitle.get("lan_doc"),
                "is_lock": subtitle.get("is_lock"),
            },
        },
    )
    transcript_result = _result_from_transcript(source, transcript, registry=registry)
    write_json(transcript_path, transcript)
    write_json(question_path, transcript_result.get("business_model_question_results", []))
    result.update(transcript_result)
    result["status"] = "transcript_collected" if segments else "subtitle_fetched_no_segments"
    result["cache_paths"].extend([str(pagelist_path), str(player_path), str(transcript_path), str(question_path)])
    return result


def _collect_web_reader_interview_source(
    source: dict[str, Any],
    *,
    registry: dict[str, Any],
    cache_dir: Path,
    offline: bool,
) -> dict[str, Any]:
    result = _base_result(source, offline=offline)
    if offline:
        return result

    url = str(source.get("url") or "").strip()
    if not url:
        result["status"] = "missing_interview_page_url"
        result["errors"].append(f"Missing URL for {source.get('source_id')}")
        return result

    source_dir = cache_dir / _slug(str(source.get("source_id") or url))
    page_path = source_dir / "web_reader_page.json"
    html_path = source_dir / "direct_article_page.json"
    transcript_path = source_dir / "transcript.json"
    rate_limit = float(source.get("rate_limit_seconds", registry.get("default_rate_limit_seconds", 1.5)))
    reader_url = WEB_READER_PREFIX + url
    try:
        markdown = fetch_bytes(
            reader_url,
            headers={"User-Agent": EXECUTIVE_VIDEO_USER_AGENT, "Accept": "text/plain"},
            timeout=35,
            rate_limit_seconds=rate_limit,
        ).decode("utf-8", errors="replace")
        write_json(page_path, {"url": url, "reader_url": reader_url, "markdown": markdown})
    except FetchError as exc:
        result["status"] = "interview_page_fetch_failed_or_blocked"
        result["errors"].append(str(exc))
        return result

    if _looks_like_blocked_page(markdown):
        result["status"] = "interview_page_fetch_failed_or_blocked"
        result["errors"].append(f"Reader page appears blocked for {url}")
        result["cache_paths"].append(str(page_path))
        return result

    max_segments = int(source.get("max_segments", 120))
    segments = _markdown_to_segments(markdown, max_segments=max_segments)
    transcript_method = "web_reader_interview_page"
    if source.get("direct_html_fallback"):
        try:
            direct_html = fetch_bytes(
                url,
                headers={"User-Agent": EXECUTIVE_VIDEO_USER_AGENT, "Accept": "text/html"},
                timeout=35,
                rate_limit_seconds=rate_limit,
            ).decode("utf-8", errors="replace")
            direct_segments = _html_article_to_segments(direct_html, max_segments=max_segments)
            write_json(
                html_path,
                {
                    "url": url,
                    "transcript_method": "direct_html_article_fallback",
                    "segment_count": len(direct_segments),
                    "segments": direct_segments,
                },
            )
            if _segments_text_length(direct_segments) > _segments_text_length(segments):
                segments = direct_segments
                transcript_method = "web_reader_interview_page_direct_html_fallback"
                result["cache_paths"].append(str(html_path))
                result["notes"].append("Reader page was thin; used direct HTML article fallback.")
        except FetchError as exc:
            result["errors"].append(f"Direct HTML fallback failed for {url}: {exc}")

    transcript = _transcript_payload(
        source=source,
        platform=str(source.get("platform") or "web"),
        transcript_method=transcript_method,
        segments=segments,
        extra={"reader_url": reader_url},
    )
    write_json(transcript_path, transcript)
    result.update(_result_from_transcript(source, transcript, registry=registry))
    result["status"] = "interview_page_text_collected" if result.get("evidence_items") else "interview_page_collected_no_relevant_claims"
    result["cache_paths"].extend([str(page_path), str(transcript_path)])
    return result


def _collect_manual_transcript_file_source(
    source: dict[str, Any],
    *,
    registry: dict[str, Any],
    cache_dir: Path,
    offline: bool,
) -> dict[str, Any]:
    result = _base_result(source, offline=offline)
    local_path = str(source.get("local_transcript_path") or "").strip()
    if not local_path:
        result["status"] = "manual_transcript_file_not_configured"
        result["business_model_question_results"] = question_results_without_transcript(
            source,
            status=result["status"],
        )
        result["notes"].append(
            "Configure local_transcript_path after exporting a Bilibili/BibiGPT/ASR transcript file."
        )
        return result

    path = Path(local_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        result["status"] = "manual_transcript_file_missing"
        result["business_model_question_results"] = question_results_without_transcript(
            source,
            status=result["status"],
        )
        result["errors"].append(f"Manual transcript file does not exist: {path}")
        return result

    source_dir = cache_dir / _slug(str(source.get("source_id") or path.stem))
    transcript_path = source_dir / "transcript.json"
    try:
        segments = _manual_transcript_file_to_segments(path, max_segments=int(source.get("max_segments", 500)))
    except (OSError, json.JSONDecodeError) as exc:
        result["status"] = "manual_transcript_file_parse_failed"
        result["errors"].append(str(exc))
        return result

    transcript = _transcript_payload(
        source=source,
        platform=str(source.get("platform") or "manual_transcript"),
        transcript_method=str(source.get("transcript_method") or "manual_transcript_file"),
        segments=segments,
        extra={
            "local_transcript_path": str(path),
            "manual_transcript_source": source.get("manual_transcript_source"),
        },
    )
    write_json(transcript_path, transcript)
    result.update(_result_from_transcript(source, transcript, registry=registry))
    result["status"] = "manual_transcript_file_collected" if segments else "manual_transcript_file_empty"
    result["cache_paths"].extend([str(path), str(transcript_path)])
    return result


def _base_result(source: dict[str, Any], *, offline: bool) -> dict[str, Any]:
    return {
        "source_id": source.get("source_id"),
        "name": source.get("name"),
        "adapter": source.get("adapter"),
        "platform": source.get("platform"),
        "status": "offline_not_collected" if offline else "collection_attempted",
        "source_quality_tier": source.get("source_quality_tier"),
        "language": source.get("language"),
        "url": source.get("url"),
        "executive_names": source.get("executive_names", []),
        "transcript_segment_count": 0,
        "evidence_items": [],
        "cache_paths": [],
        "errors": [],
        "notes": source.get("notes", []),
    }


def _result_from_transcript(
    source: dict[str, Any],
    transcript: dict[str, Any],
    *,
    registry: dict[str, Any],
) -> dict[str, Any]:
    evidence_items = _extract_transcript_evidence_items(
        source=source,
        transcript=transcript,
        max_items=int(source.get("max_evidence_items", registry.get("default_max_evidence_items", 12))),
    )
    segments = transcript.get("segments") or []
    question_results = business_model_question_results_from_segments(
        source=source,
        segments=segments,
        limitation=(
            "V1 answers by matching business-model questions to collected transcript/subtitle spans. "
            "Use this as source-linked evidence, not as a final investment conclusion."
        ),
    )
    return {
        "transcript_method": transcript.get("transcript_method"),
        "transcript_segment_count": len(segments),
        "transcript_text_length": len(transcript.get("transcript_text") or ""),
        "evidence_items": evidence_items,
        "business_model_question_results": question_results,
        "question_answer_count": sum(1 for item in question_results if item.get("answer_status") == "evidence_found"),
    }


def _transcript_payload(
    *,
    source: dict[str, Any],
    platform: str,
    transcript_method: str,
    segments: list[dict[str, Any]],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "source_id": source.get("source_id"),
        "source_name": source.get("name"),
        "source_url": source.get("url"),
        "source_quality_tier": source.get("source_quality_tier"),
        "platform": platform,
        "language": source.get("language"),
        "executive_names": source.get("executive_names", []),
        "generated_at": utc_now_iso(),
        "transcript_method": transcript_method,
        "segments": segments,
        "transcript_text": _segments_to_text(segments),
    }
    if extra:
        payload.update(extra)
    return payload


def _extract_transcript_evidence_items(
    *,
    source: dict[str, Any],
    transcript: dict[str, Any],
    max_items: int,
) -> list[dict[str, Any]]:
    segments = transcript.get("segments") or []
    evidence_items: list[dict[str, Any]] = []
    seen_groups: set[str] = set()
    for group_id, terms in EXECUTIVE_TRANSCRIPT_TERM_GROUPS.items():
        if len(evidence_items) >= max_items:
            break
        match = _first_matching_segment_window(segments, terms)
        if not match:
            continue
        seen_groups.add(group_id)
        evidence_items.append(
            {
                "source_id": source.get("source_id"),
                "source_name": source.get("name"),
                "source_url": source.get("url"),
                "source_quality_tier": source.get("source_quality_tier"),
                "platform": transcript.get("platform"),
                "language": source.get("language"),
                "executive_names": source.get("executive_names", []),
                "evidence_type": "executive_video_transcript_excerpt",
                "transcript_method": transcript.get("transcript_method"),
                "claim_id": group_id,
                "claim": _claim_from_group_id(group_id),
                "excerpt": match["excerpt"],
                "start_seconds": match.get("start_seconds"),
                "matched_terms": match.get("matched_terms", []),
                "evidence_direction": "management_context_or_claim",
                "confidence": "low_until_cross_checked",
                "limitation": "Transcript excerpts show executive framing; they need source/date verification and cross-checking against filings and outcomes.",
                "requires_human_review": True,
            }
        )

    if not evidence_items and segments:
        first = next((segment for segment in segments if segment.get("text")), {})
        if first:
            evidence_items.append(
                {
                    "source_id": source.get("source_id"),
                    "source_name": source.get("name"),
                    "source_url": source.get("url"),
                    "source_quality_tier": source.get("source_quality_tier"),
                    "platform": transcript.get("platform"),
                    "language": source.get("language"),
                    "executive_names": source.get("executive_names", []),
                    "evidence_type": "executive_video_transcript_presence",
                    "transcript_method": transcript.get("transcript_method"),
                    "claim_id": "transcript_presence",
                    "claim": "Executive video transcript was collected, but no configured business-model keyword group matched strongly.",
                    "excerpt": _trim_excerpt(str(first.get("text") or "")),
                    "start_seconds": first.get("start_seconds"),
                    "matched_terms": [],
                    "evidence_direction": "context_only",
                    "confidence": "low",
                    "limitation": "This record proves collection only, not a business-model claim.",
                    "requires_human_review": True,
                }
            )
    return evidence_items[:max_items]


def parse_youtube_transcript_payload(payload: bytes | str) -> list[dict[str, Any]]:
    text = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else str(payload)
    stripped = text.strip()
    if not stripped:
        return []
    if stripped.startswith("{"):
        try:
            return _parse_youtube_json3(json.loads(stripped))
        except json.JSONDecodeError:
            return []
    return _parse_youtube_xml(stripped)


def parse_bilibili_subtitle_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = payload.get("body") or []
    segments = []
    for index, item in enumerate(body):
        text = _clean_text(item.get("content"))
        if not text:
            continue
        segments.append(
            {
                "index": index,
                "start_seconds": _float_or_none(item.get("from")),
                "end_seconds": _float_or_none(item.get("to")),
                "duration_seconds": _duration(item.get("from"), item.get("to")),
                "text": text,
            }
        )
    return segments


def _parse_youtube_xml(text: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    segments = []
    for index, node in enumerate(root.findall(".//text")):
        segment_text = _clean_text("".join(node.itertext()))
        if not segment_text:
            continue
        start = _float_or_none(node.attrib.get("start"))
        duration = _float_or_none(node.attrib.get("dur"))
        end = start + duration if start is not None and duration is not None else None
        segments.append(
            {
                "index": index,
                "start_seconds": start,
                "end_seconds": end,
                "duration_seconds": duration,
                "text": segment_text,
            }
        )
    return segments


def _parse_youtube_json3(payload: dict[str, Any]) -> list[dict[str, Any]]:
    segments = []
    for index, event in enumerate(payload.get("events") or []):
        parts = event.get("segs") or []
        text = _clean_text("".join(str(part.get("utf8") or "") for part in parts))
        if not text:
            continue
        start_ms = _float_or_none(event.get("tStartMs"))
        duration_ms = _float_or_none(event.get("dDurationMs"))
        start = start_ms / 1000 if start_ms is not None else None
        duration = duration_ms / 1000 if duration_ms is not None else None
        end = start + duration if start is not None and duration is not None else None
        segments.append(
            {
                "index": index,
                "start_seconds": start,
                "end_seconds": end,
                "duration_seconds": duration,
                "text": text,
            }
        )
    return segments


def _select_youtube_caption_track(html_text: str, *, preferred_languages: list[str]) -> dict[str, Any] | None:
    player = _extract_youtube_player_response(html_text)
    tracks = (
        (((player.get("captions") or {}).get("playerCaptionsTracklistRenderer") or {}).get("captionTracks") or [])
        if player
        else []
    )
    if not tracks:
        tracks = _extract_caption_tracks_regex(html_text)
    if not tracks:
        return None
    preferred = [language.lower() for language in preferred_languages if language]

    def score(track: dict[str, Any]) -> tuple[int, int, str]:
        language = str(track.get("languageCode") or track.get("vssId") or "").lower()
        preferred_rank = min((index for index, item in enumerate(preferred) if item and item in language), default=99)
        asr_rank = 1 if track.get("kind") == "asr" else 0
        return (preferred_rank, asr_rank, language)

    return sorted(tracks, key=score)[0]


def _extract_youtube_player_response(html_text: str) -> dict[str, Any]:
    marker_position = html_text.find(YOUTUBE_PLAYER_MARKER)
    if marker_position < 0:
        return {}
    brace_position = html_text.find("{", marker_position)
    if brace_position < 0:
        return {}
    json_text = _balanced_json_object(html_text, brace_position)
    if not json_text:
        return {}
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        return {}


def _balanced_json_object(text: str, start: int) -> str:
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return ""


def _extract_caption_tracks_regex(html_text: str) -> list[dict[str, Any]]:
    marker = '"captionTracks"'
    start = html_text.find(marker)
    if start < 0:
        return []
    array_start = html_text.find("[", start)
    if array_start < 0:
        return []
    array_text = _balanced_json_array(html_text, array_start)
    if not array_text:
        return []
    try:
        return json.loads(array_text)
    except json.JSONDecodeError:
        return []


def _balanced_json_array(text: str, start: int) -> str:
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return ""


def _select_bilibili_subtitle(subtitles: list[dict[str, Any]], *, preferred_languages: list[str]) -> dict[str, Any]:
    preferred = [language.lower() for language in preferred_languages if language]

    def score(subtitle: dict[str, Any]) -> tuple[int, str]:
        language = str(subtitle.get("lan") or subtitle.get("lan_doc") or "").lower()
        preferred_rank = min((index for index, item in enumerate(preferred) if item and item in language), default=99)
        return (preferred_rank, language)

    return sorted(subtitles, key=score)[0]


def _bilibili_first_cid(pagelist: dict[str, Any]) -> str | None:
    data = pagelist.get("data") or []
    if not data:
        return None
    cid = data[0].get("cid")
    return str(cid) if cid is not None else None


def _normalize_bilibili_subtitle_url(subtitle_url: str, page_url: str) -> str:
    if not subtitle_url:
        return ""
    if subtitle_url.startswith("//"):
        return "https:" + subtitle_url
    return urljoin(page_url, subtitle_url)


def _fetch_web_reader_metadata(url: str, *, cache_path: Path, rate_limit_seconds: float) -> dict[str, Any]:
    reader_url = WEB_READER_PREFIX + url
    try:
        markdown = fetch_bytes(
            reader_url,
            headers={"User-Agent": EXECUTIVE_VIDEO_USER_AGENT, "Accept": "text/plain"},
            timeout=35,
            rate_limit_seconds=rate_limit_seconds,
        ).decode("utf-8", errors="replace")
        write_json(cache_path, {"url": url, "reader_url": reader_url, "markdown": markdown})
        return {"status": "reader_page_collected"}
    except FetchError as exc:
        return {"status": "reader_page_failed", "error": str(exc)}


def _youtube_video_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith("youtu.be"):
        return parsed.path.strip("/")
    values = parse_qs(parsed.query).get("v") or []
    return values[0] if values else ""


def _bilibili_bvid(url: str) -> str:
    match = re.search(r"\bBV[A-Za-z0-9]+", url)
    return match.group(0) if match else ""


def _safe_caption_track(track: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in track.items()
        if key in {"name", "languageCode", "kind", "vssId", "isTranslatable"}
    }


def _segments_to_text(segments: list[dict[str, Any]]) -> str:
    return "\n".join(str(segment.get("text") or "") for segment in segments if segment.get("text"))


def _first_matching_segment_window(
    segments: list[dict[str, Any]],
    terms: list[str],
    *,
    window: int = 0,
    excerpt_limit: int = 240,
) -> dict[str, Any] | None:
    for index, segment in enumerate(segments):
        text = str(segment.get("text") or "")
        lower = text.lower()
        matched = [term for term in terms if term and term.lower() in lower]
        if not matched:
            continue
        start = max(0, index - window)
        end = min(len(segments), index + window + 1)
        excerpt = _focused_excerpt(
            " ".join(str(item.get("text") or "") for item in segments[start:end]),
            matched_terms=matched,
            limit=excerpt_limit,
        )
        return {
            "excerpt": excerpt,
            "start_seconds": segment.get("start_seconds"),
            "matched_terms": matched[:8],
        }
    return None


def _manual_transcript_file_to_segments(path: Path, *, max_segments: int) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
        if isinstance(payload, dict) and isinstance(payload.get("body"), list):
            return parse_bilibili_subtitle_payload(payload)[:max_segments]
        if isinstance(payload, dict) and isinstance(payload.get("segments"), list):
            return [_normalize_manual_segment(item, index) for index, item in enumerate(payload["segments"][:max_segments])]
        if isinstance(payload, list):
            return [_normalize_manual_segment(item, index) for index, item in enumerate(payload[:max_segments])]
        if isinstance(payload, dict) and payload.get("transcript"):
            return _markdown_to_segments(str(payload.get("transcript") or ""), max_segments=max_segments)
        return []
    return _markdown_to_segments(text, max_segments=max_segments)


def _normalize_manual_segment(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {
            "index": index,
            "start_seconds": None,
            "end_seconds": None,
            "duration_seconds": None,
            "text": _clean_text(str(item)),
        }
    text = _clean_text(item.get("text") or item.get("content") or item.get("sentence") or "")
    start = _float_or_none(item.get("start_seconds", item.get("start", item.get("from"))))
    end = _float_or_none(item.get("end_seconds", item.get("end", item.get("to"))))
    return {
        "index": int(item.get("index", item.get("segment_index", index)) or index),
        "start_seconds": start,
        "end_seconds": end,
        "duration_seconds": _duration(start, end),
        "speaker": item.get("speaker"),
        "text": text,
    }


def _markdown_to_segments(markdown: str, *, max_segments: int) -> list[dict[str, Any]]:
    segments = []
    for raw_line in markdown.splitlines():
        clean = _clean_markdown_line(raw_line)
        if len(clean) < 18:
            continue
        if clean.lower().startswith(("title:", "url source:", "markdown content:")):
            continue
        if clean.startswith(("![", "[![", "Image:")):
            continue
        if "Sign in to continue" in clean:
            break
        for chunk in _chunk_text(clean, max_chars=260):
            segments.append(
                {
                    "index": len(segments),
                    "start_seconds": None,
                    "end_seconds": None,
                    "duration_seconds": None,
                    "text": chunk,
                }
            )
            if len(segments) >= max_segments:
                break
        if len(segments) >= max_segments:
            break
    return segments


def _segments_need_direct_html_fallback(segments: list[dict[str, Any]]) -> bool:
    useful_segments = [
        str(segment.get("text") or "")
        for segment in segments
        if len(str(segment.get("text") or "")) >= 80
    ]
    return _segments_text_length(segments) < 1200 or len(useful_segments) < 3


def _segments_text_length(segments: list[dict[str, Any]]) -> int:
    return sum(len(str(segment.get("text") or "")) for segment in segments)


def _html_article_to_segments(html_text: str, *, max_segments: int) -> list[dict[str, Any]]:
    parser = _ArticleTextParser()
    parser.feed(html_text)
    candidate_texts = parser.texts or _html_tag_texts(html_text)
    segments: list[dict[str, Any]] = []
    seen: set[str] = set()
    for text in candidate_texts:
        clean = _clean_text(text)
        if len(clean) < 12 or clean in seen:
            continue
        seen.add(clean)
        segments.append({"index": len(segments), "text": clean})
        if len(segments) >= max_segments:
            break
    return segments


def _html_tag_texts(html_text: str) -> list[str]:
    texts: list[str] = []
    for _tag, body in HTML_ARTICLE_TEXT_PATTERN.findall(html_text):
        text = HTML_TAG_PATTERN.sub("", body)
        text = html.unescape(text)
        if text:
            texts.append(text)
    return texts


class _ArticleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._capture_stack: list[str] = []
        self._skip_depth = 0
        self._current: list[str] = []
        self.texts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in {"h1", "h2", "h3", "p"}:
            self._capture_stack.append(tag)
            self._current = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if self._capture_stack and tag == self._capture_stack[-1]:
            text = _clean_text("".join(self._current))
            if text:
                self.texts.append(text)
            self._capture_stack.pop()
            self._current = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not self._capture_stack:
            return
        self._current.append(data)


def _clean_markdown_line(line: str) -> str:
    clean = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", line)
    clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)
    clean = re.sub(r"^#+\s*", "", clean.strip())
    clean = clean.strip(" -*\t")
    return _clean_text(clean)


def _chunk_text(text: str, *, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r"(?<=[。！？.!?])\s*", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(sentence[index : index + max_chars] for index in range(0, len(sentence), max_chars))
            continue
        if current and len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


def _looks_like_blocked_page(markdown: str) -> bool:
    lower = markdown.lower()
    blocked_markers = [
        "target url returned error 403",
        "target url returned error 451",
        "you've been blocked",
        "requiring captcha",
        "verification successful. waiting",
    ]
    return any(marker in lower for marker in blocked_markers)


def _theme_summary(evidence_items: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(item.get("claim_id") or "unknown") for item in evidence_items)
    examples: dict[str, list[dict[str, Any]]] = {}
    for item in evidence_items:
        claim_id = str(item.get("claim_id") or "unknown")
        examples.setdefault(claim_id, [])
        if len(examples[claim_id]) < 3:
            examples[claim_id].append(
                {
                    "source_name": item.get("source_name"),
                    "platform": item.get("platform"),
                    "excerpt": item.get("excerpt"),
                    "source_url": item.get("source_url"),
                }
            )
    return {"counts": dict(sorted(counts.items())), "examples": examples}


def _claim_from_group_id(group_id: str) -> str:
    labels = {
        "business_model": "Executive transcript discusses the business model, platform, ecosystem, users, or merchants.",
        "operating_values": "Executive transcript discusses operating values, long-term orientation, trust, or responsibility.",
        "price_and_quality": "Executive transcript discusses price, quality, cost, or value-for-money.",
        "competition": "Executive transcript discusses competition or replicability.",
        "leadership_and_org": "Executive transcript gives leadership or organization context.",
        "transcript_presence": "Transcript collection state.",
    }
    return labels.get(group_id, group_id.replace("_", " "))


def _clean_text(value: Any) -> str:
    return SPACE_PATTERN.sub(" ", html.unescape(unquote(str(value or ""))).replace("\xa0", " ")).strip()


def _trim_excerpt(text: str, *, limit: int = 620) -> str:
    clean = SPACE_PATTERN.sub(" ", str(text).replace("\xa0", " ")).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def _focused_excerpt(text: str, *, matched_terms: list[str], limit: int) -> str:
    clean = SPACE_PATTERN.sub(" ", str(text).replace("\xa0", " ")).strip()
    if len(clean) <= limit:
        return clean
    lower = clean.lower()
    positions = [
        lower.find(term.lower())
        for term in matched_terms
        if term and lower.find(term.lower()) >= 0
    ]
    if not positions:
        return _trim_excerpt(clean, limit=limit)
    center = min(positions)
    half = limit // 2
    start = max(0, center - half)
    end = min(len(clean), start + limit)
    if end - start < limit:
        start = max(0, end - limit)
    excerpt = clean[start:end].strip()
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(clean):
        excerpt = excerpt.rstrip() + "..."
    return excerpt


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _duration(start_value: Any, end_value: Any) -> float | None:
    start = _float_or_none(start_value)
    end = _float_or_none(end_value)
    if start is None or end is None:
        return None
    return end - start


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _slug(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-")
    return clean or "source"
