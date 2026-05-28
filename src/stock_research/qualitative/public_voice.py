from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from stock_research.sources.http import FetchError, fetch_bytes, fetch_json, write_json
from stock_research.state import utc_now_iso


DEFAULT_PDD_PUBLIC_VOICE_REGISTRY = Path("config/qualitative/pdd_public_voice_sources.v1.json")
PUBLIC_VOICE_USER_AGENT = "stock-research-system/0.1 public-voice-research"
SPACE_PATTERN = re.compile(r"\s+")
WEB_READER_PREFIX = "https://r.jina.ai/"


def collect_public_voice_evidence(
    *,
    company: dict[str, Any],
    cache_root: str | Path = "data/raw/public_voice",
    offline: bool | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    company_id = str(company.get("company_id") or "").lower()
    if company_id != "pdd":
        return {
            "status": "not_configured_for_company_v1",
            "company_id": company_id or "unknown",
            "evidence_items": [],
            "source_results": [],
            "theme_summary": {},
            "audit_notes": ["Public voice collection is currently configured for PDD only."],
        }

    if offline is None:
        offline = os.environ.get("STOCK_RESEARCH_OFFLINE") == "1"

    registry = _load_registry(registry_path or DEFAULT_PDD_PUBLIC_VOICE_REGISTRY)
    cache_dir = Path(cache_root) / company_id
    source_results = []
    evidence_items: list[dict[str, Any]] = []
    for source in registry.get("sources", []):
        if source.get("adapter") == "reddit_public_json":
            result = _collect_reddit_source(source, registry=registry, cache_dir=cache_dir, offline=offline)
        elif source.get("adapter") == "web_reader_public_page":
            result = _collect_web_reader_source(source, registry=registry, cache_dir=cache_dir, offline=offline)
        else:
            result = _manual_source_result(source)
        source_results.append(result)
        evidence_items.extend(result.get("evidence_items", []))

    theme_summary = _theme_summary(evidence_items, registry.get("theme_keywords", {}))
    theme_findings = _theme_findings(theme_summary.get("counts", {}))
    status = "collected_with_partial_adapters" if evidence_items else "source_plan_ready_no_public_comments_collected"
    if offline:
        status = "offline_source_plan_ready"
    errors = [
        error
        for result in source_results
        for error in result.get("errors", [])
    ]
    collection_stats = _collection_stats(source_results, len(evidence_items))
    return {
        "status": status,
        "company_id": company_id,
        "registry_path": str(registry_path or DEFAULT_PDD_PUBLIC_VOICE_REGISTRY),
        "generated_at": utc_now_iso(),
        "offline": offline,
        "source_count": len(registry.get("sources", [])),
        "collectable_source_count": sum(1 for source in registry.get("sources", []) if _is_collectable_adapter(source)),
        "manual_or_blocked_source_count": sum(1 for source in registry.get("sources", []) if not _is_collectable_adapter(source)),
        "evidence_items": evidence_items,
        "evidence_item_count": len(evidence_items),
        "collection_stats": collection_stats,
        "source_results": source_results,
        "theme_summary": theme_summary,
        "theme_findings": theme_findings,
        "audit_policy": registry.get("audit_policy", {}),
        "audit_notes": [
            "Public voice sources are Tier 3/Tier 4 lead or pattern evidence only.",
            "Do not use comments/forums for official financial numbers.",
            "Important claims from comments require human review and stronger-source triangulation.",
            "Deleted/removed Reddit comments are skipped.",
            "Web-reader pages are cached and treated as low-confidence public-review evidence.",
        ],
        "errors": errors,
    }


def _load_registry(path: str | Path) -> dict[str, Any]:
    registry_path = Path(path)
    return json.loads(registry_path.read_text(encoding="utf-8"))


def _is_collectable_adapter(source: dict[str, Any]) -> bool:
    return source.get("adapter") in {"reddit_public_json", "web_reader_public_page"}


def _manual_source_result(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": source.get("source_id"),
        "name": source.get("name"),
        "adapter": source.get("adapter"),
        "status": source.get("status", "planned"),
        "quality_tier": source.get("quality_tier"),
        "voice_type": source.get("voice_type"),
        "language": source.get("language"),
        "search_locator": source.get("search_locator"),
        "evidence_items": [],
        "errors": [],
        "notes": [
            "Source is registered for the same evidence schema, but needs a source-specific collector or manual URL ingestion.",
        ],
    }


def _collection_stats(source_results: list[dict[str, Any]], evidence_item_count: int) -> dict[str, int]:
    return {
        "searches_attempted": sum(int(result.get("searches_attempted", 0)) for result in source_results),
        "posts_collected": sum(int(result.get("posts_collected", 0)) for result in source_results),
        "unique_posts_with_evidence": sum(int(result.get("unique_posts_with_evidence", 0)) for result in source_results),
        "comments_seen_before_filter": sum(int(result.get("comments_seen_before_filter", 0)) for result in source_results),
        "comments_collected": evidence_item_count,
        "duplicate_comments_skipped": sum(int(result.get("duplicate_comments_skipped", 0)) for result in source_results),
        "cache_fallbacks": sum(int(result.get("cache_fallbacks", 0)) for result in source_results),
    }


def _collect_web_reader_source(
    source: dict[str, Any],
    *,
    registry: dict[str, Any],
    cache_dir: Path,
    offline: bool,
) -> dict[str, Any]:
    result = {
        "source_id": source.get("source_id"),
        "name": source.get("name"),
        "adapter": source.get("adapter"),
        "status": "offline_not_collected" if offline else "collection_attempted",
        "quality_tier": source.get("quality_tier"),
        "voice_type": source.get("voice_type"),
        "language": source.get("language"),
        "url": source.get("url"),
        "parser": source.get("parser"),
        "posts_collected": 0,
        "comments_collected": 0,
        "comments_seen_before_filter": 0,
        "unique_posts_with_evidence": 0,
        "duplicate_comments_skipped": 0,
        "cache_fallbacks": 0,
        "aggregate_summary": {},
        "evidence_items": [],
        "errors": [],
        "notes": source.get("bias_risks", []),
    }
    if offline:
        return result

    url = str(source.get("url") or "").strip()
    if not url:
        result["status"] = "missing_url"
        result["errors"].append(f"Missing URL for source {source.get('source_id')}")
        return result

    limits = source.get("limits", {})
    max_evidence_items = int(limits.get("max_evidence_items", 25))
    rate_limit_seconds = float(limits.get("rate_limit_seconds", 1.0))
    cache_path = cache_dir / "web_reader" / f"{_slug(str(source.get('source_id') or url))}.json"
    reader_url = WEB_READER_PREFIX + url
    try:
        markdown = fetch_bytes(
            reader_url,
            headers={"User-Agent": PUBLIC_VOICE_USER_AGENT, "Accept": "text/plain"},
            timeout=35,
            rate_limit_seconds=rate_limit_seconds,
        ).decode("utf-8", errors="replace")
        write_json(cache_path, {"url": url, "reader_url": reader_url, "markdown": markdown})
    except FetchError as exc:
        cached = _read_json_if_exists(cache_path)
        if cached and cached.get("markdown"):
            markdown = str(cached["markdown"])
            result["cache_fallbacks"] += 1
            result["notes"].append(f"Used cached web-reader page for source: {source.get('source_id')}")
        else:
            result["status"] = "collection_failed_or_blocked"
            result["errors"].append(str(exc))
            return result

    if _looks_like_blocked_page(markdown):
        result["status"] = "collection_failed_or_blocked"
        result["errors"].append(f"Reader page appears blocked for {url}")
        return result

    if source.get("parser") == "sitejabber_reviews":
        parsed = _sitejabber_evidence_items(
            source=source,
            markdown=markdown,
            theme_keywords=registry.get("theme_keywords", {}),
            max_items=max_evidence_items,
        )
    else:
        parsed = _generic_web_reader_evidence_items(
            source=source,
            markdown=markdown,
            theme_keywords=registry.get("theme_keywords", {}),
            max_items=max_evidence_items,
        )
    result["aggregate_summary"] = parsed.get("aggregate_summary", {})
    result["evidence_items"] = parsed.get("evidence_items", [])
    result["comments_seen_before_filter"] = int(parsed.get("items_seen_before_filter", 0))
    result["comments_collected"] = len(result["evidence_items"])
    result["posts_collected"] = 1
    result["unique_posts_with_evidence"] = 1 if result["evidence_items"] else 0

    if result["evidence_items"]:
        result["status"] = "review_items_collected"
    else:
        result["status"] = "no_relevant_review_items_found"
    return result


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


def _sitejabber_evidence_items(
    *,
    source: dict[str, Any],
    markdown: str,
    theme_keywords: dict[str, list[str]],
    max_items: int,
) -> dict[str, Any]:
    aggregate_summary = _sitejabber_aggregate_summary(markdown)
    evidence_items: list[dict[str, Any]] = []
    if aggregate_summary:
        evidence_items.append(
            {
                "source_id": source.get("source_id"),
                "source_name": source.get("name"),
                "source_quality_tier": source.get("quality_tier"),
                "voice_type": source.get("voice_type"),
                "language": source.get("language"),
                "source_url": source.get("url"),
                "query": "sitejabber aggregate profile",
                "post_title": "Sitejabber Temu aggregate review profile",
                "comment_id": "sitejabber-aggregate",
                "comment_url": source.get("url"),
                "themes": [
                    "refund_customer_service",
                    "shipping_delivery",
                    "product_quality",
                    "value_for_money",
                ],
                "excerpt": _sitejabber_aggregate_excerpt(aggregate_summary),
                "evidence_type": "review_site_aggregate",
                "evidence_direction": "lead_only",
                "confidence": "low",
                "requires_human_review": True,
                "collected_at": utc_now_iso(),
            }
        )

    review_matches = list(
        re.finditer(
            r"^\[(?P<title>[^\]\n]{5,160})\]\((?P<url>https://www\.sitejabber\.com/reviews/temu\.com#(?P<id>\d+))\)$",
            markdown,
            flags=re.MULTILINE,
        )
    )
    items_seen = len(review_matches)
    for index, match in enumerate(review_matches):
        if len(evidence_items) >= max_items:
            break
        next_start = review_matches[index + 1].start() if index + 1 < len(review_matches) else len(markdown)
        block_end = min(_positive_positions(markdown.find(marker, match.end(), next_start) for marker in ["## From the business", "\nQuestion\n", "\n### Have a question"]))
        if block_end == -1:
            block_end = next_start
        text = _sitejabber_review_text(match.group("title"), markdown[match.end() : block_end])
        themes = _matched_themes(text, theme_keywords)
        if not themes:
            continue
        evidence_items.append(
            {
                "source_id": source.get("source_id"),
                "source_name": source.get("name"),
                "source_quality_tier": source.get("quality_tier"),
                "voice_type": source.get("voice_type"),
                "language": source.get("language"),
                "source_url": source.get("url"),
                "query": "sitejabber individual review",
                "post_title": match.group("title"),
                "comment_id": f"sitejabber-{match.group('id')}",
                "comment_score": None,
                "comment_url": match.group("url"),
                "themes": themes,
                "excerpt": _excerpt(text, limit=220),
                "evidence_type": "review_site_review",
                "evidence_direction": "lead_only",
                "confidence": "low",
                "requires_human_review": True,
                "collected_at": utc_now_iso(),
            }
        )
    return {
        "aggregate_summary": aggregate_summary,
        "items_seen_before_filter": items_seen,
        "evidence_items": evidence_items,
    }


def _positive_positions(positions: Any) -> list[int]:
    return [position for position in positions if isinstance(position, int) and position >= 0] or [-1]


def _sitejabber_aggregate_summary(markdown: str) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    rating_match = re.search(
        r"Temu has a rating of (?P<rating>[0-9.]+) stars from (?P<count>[\d,]+) reviews",
        markdown,
    )
    if rating_match:
        summary["rating"] = float(rating_match.group("rating"))
        summary["review_count"] = int(rating_match.group("count").replace(",", ""))
    recommend_match = re.search(r"(?P<pct>\d+)%\s*\n\nof reviewers recommend", markdown)
    if recommend_match:
        summary["recommend_percent"] = int(recommend_match.group("pct"))
    recent_positive_match = re.search(r"Positive reviews \(last 12 months\):\s*\n\n(?P<pct>[0-9.]+)%", markdown)
    if recent_positive_match:
        summary["positive_reviews_last_12_months_percent"] = float(recent_positive_match.group("pct"))
    category_counts = {}
    for label in ["service", "value", "shipping", "returns", "quality"]:
        count_match = re.search(rf"\n{label}\s*\n\n(?P<count>[\d,]+)\s*\n", markdown)
        if count_match:
            category_counts[label] = int(count_match.group("count").replace(",", ""))
    if category_counts:
        summary["category_mention_counts"] = category_counts
    return summary


def _sitejabber_aggregate_excerpt(summary: dict[str, Any]) -> str:
    parts = []
    if summary.get("rating") is not None and summary.get("review_count") is not None:
        parts.append(f"Sitejabber aggregate rating {summary['rating']}/5 from {summary['review_count']:,} reviews")
    if summary.get("recommend_percent") is not None:
        parts.append(f"{summary['recommend_percent']}% reviewer recommendation rate")
    if summary.get("positive_reviews_last_12_months_percent") is not None:
        parts.append(f"{summary['positive_reviews_last_12_months_percent']}% positive reviews in last 12 months")
    counts = summary.get("category_mention_counts") or {}
    if counts:
        parts.append("category counts: " + ", ".join(f"{label}={count:,}" for label, count in sorted(counts.items())))
    return "; ".join(parts) or "Sitejabber aggregate review profile collected."


def _sitejabber_review_text(title: str, block: str) -> str:
    lines = [_strip_markdown(title)]
    for raw_line in block.splitlines():
        line = _strip_markdown(raw_line)
        if not line:
            continue
        if line == "Comments":
            break
        if _is_sitejabber_noise_line(line):
            continue
        lines.append(line)
    return _clean_text(" ".join(lines))


def _is_sitejabber_noise_line(line: str) -> bool:
    exact_noise = {
        "Verified purchase",
        "Updated review",
        "Previous review",
        "Share Review",
        "Report Review",
        "Show More",
        "Thank You",
    }
    if line in exact_noise:
        return True
    noise_prefixes = [
        "Follow ",
        "Unfollow ",
        "Date of experience:",
        "Helpful (",
        "Image ",
        "![",
        "* * *",
    ]
    if any(line.startswith(prefix) for prefix in noise_prefixes):
        return True
    return "— Temu Rep" in line or "Temu Rep" in line


def _generic_web_reader_evidence_items(
    *,
    source: dict[str, Any],
    markdown: str,
    theme_keywords: dict[str, list[str]],
    max_items: int,
) -> dict[str, Any]:
    paragraphs = [
        _clean_text(_strip_markdown(paragraph))
        for paragraph in re.split(r"\n\s*\n", markdown)
    ]
    evidence_items = []
    seen = 0
    for paragraph in paragraphs:
        if len(evidence_items) >= max_items:
            break
        if len(paragraph) < 80:
            continue
        seen += 1
        themes = _matched_themes(paragraph, theme_keywords)
        if not themes:
            continue
        evidence_items.append(
            {
                "source_id": source.get("source_id"),
                "source_name": source.get("name"),
                "source_quality_tier": source.get("quality_tier"),
                "voice_type": source.get("voice_type"),
                "language": source.get("language"),
                "source_url": source.get("url"),
                "query": "web-reader paragraph",
                "post_title": source.get("name"),
                "comment_id": f"{source.get('source_id')}-{len(evidence_items) + 1}",
                "comment_url": source.get("url"),
                "themes": themes,
                "excerpt": _excerpt(paragraph, limit=220),
                "evidence_type": "web_reader_paragraph",
                "evidence_direction": "lead_only",
                "confidence": "low",
                "requires_human_review": True,
                "collected_at": utc_now_iso(),
            }
        )
    return {
        "aggregate_summary": {},
        "items_seen_before_filter": seen,
        "evidence_items": evidence_items,
    }


def _collect_reddit_source(
    source: dict[str, Any],
    *,
    registry: dict[str, Any],
    cache_dir: Path,
    offline: bool,
) -> dict[str, Any]:
    result = {
        "source_id": source.get("source_id"),
        "name": source.get("name"),
        "adapter": source.get("adapter"),
        "status": "offline_not_collected" if offline else "collection_attempted",
        "quality_tier": source.get("quality_tier"),
        "voice_type": source.get("voice_type"),
        "language": source.get("language"),
        "queries": source.get("queries", []),
        "subreddit_queries": source.get("subreddit_queries", []),
        "searches_attempted": 0,
        "posts_collected": 0,
        "comments_collected": 0,
        "comments_seen_before_filter": 0,
        "unique_posts_with_evidence": 0,
        "duplicate_comments_skipped": 0,
        "cache_fallbacks": 0,
        "evidence_items": [],
        "errors": [],
        "notes": source.get("bias_risks", []),
    }
    if offline:
        return result

    limits = source.get("limits", {})
    posts_per_query = int(limits.get("posts_per_query", 5))
    comments_per_post = int(limits.get("comments_per_post", 25))
    max_evidence_items = int(limits.get("max_evidence_items", 200))
    rate_limit_seconds = float(limits.get("rate_limit_seconds", 1.0))
    seen_posts: set[str] = set()
    seen_comments: set[str] = set()
    posts_with_evidence: set[str] = set()
    theme_keywords = registry.get("theme_keywords", {})

    for search_spec in _reddit_search_specs(source, default_posts_per_query=posts_per_query):
        if len(result["evidence_items"]) >= max_evidence_items:
            result["notes"].append(f"Stopped collection at max_evidence_items={max_evidence_items}.")
            break
        query = search_spec["query"]
        subreddit = search_spec.get("subreddit")
        search_limit = int(search_spec.get("posts_per_query") or posts_per_query)
        result["searches_attempted"] += 1
        search_cache_path = cache_dir / "reddit" / _search_cache_name(query=query, subreddit=subreddit)
        try:
            posts = _reddit_search(
                query,
                limit=search_limit,
                subreddit=subreddit,
                rate_limit_seconds=rate_limit_seconds,
            )
            write_json(search_cache_path, {"query": query, "subreddit": subreddit, "posts": posts})
        except FetchError as exc:
            cached = _read_json_if_exists(search_cache_path)
            if cached and cached.get("posts"):
                posts = cached["posts"]
                result["cache_fallbacks"] += 1
                scope = f"r/{subreddit}" if subreddit else "all Reddit"
                result["notes"].append(f"Used cached Reddit search results for {scope}: {query}")
            else:
                result["errors"].append(str(exc))
                continue
        for post in posts:
            if len(result["evidence_items"]) >= max_evidence_items:
                break
            post_id = post.get("id")
            if not post_id or post_id in seen_posts:
                continue
            seen_posts.add(post_id)
            result["posts_collected"] += 1
            comments_cache_path = cache_dir / "reddit" / f"comments-{post_id}.json"
            try:
                comments_payload = _reddit_comments(
                    post_id,
                    limit=comments_per_post,
                    rate_limit_seconds=rate_limit_seconds,
                )
                write_json(comments_cache_path, comments_payload)
            except FetchError as exc:
                cached = _read_json_if_exists(comments_cache_path)
                if cached:
                    comments_payload = cached
                    result["cache_fallbacks"] += 1
                    result["notes"].append(f"Used cached Reddit comments for post: {post_id}")
                else:
                    result["errors"].append(str(exc))
                    continue
            comments = _flatten_reddit_comments(comments_payload)
            limited_comments = comments[:comments_per_post]
            result["comments_seen_before_filter"] += len(limited_comments)
            for comment in limited_comments:
                if len(result["evidence_items"]) >= max_evidence_items:
                    break
                comment_id = str(comment.get("id") or "")
                if comment_id and comment_id in seen_comments:
                    result["duplicate_comments_skipped"] += 1
                    continue
                item = _reddit_comment_evidence_item(
                    source=source,
                    query=query,
                    subreddit=subreddit,
                    post=post,
                    comment=comment,
                    theme_keywords=theme_keywords,
                )
                if item is None:
                    continue
                if comment_id:
                    seen_comments.add(comment_id)
                posts_with_evidence.add(str(post_id))
                result["evidence_items"].append(item)
                result["comments_collected"] += 1

    result["unique_posts_with_evidence"] = len(posts_with_evidence)
    if result["evidence_items"]:
        result["status"] = "comments_collected"
    elif result["errors"]:
        result["status"] = "collection_failed_or_blocked"
    else:
        result["status"] = "no_relevant_comments_found"
    return result


def _reddit_search_specs(
    source: dict[str, Any],
    *,
    default_posts_per_query: int,
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for query in source.get("queries", []):
        specs.append(
            {
                "query": str(query),
                "subreddit": None,
                "posts_per_query": default_posts_per_query,
            }
        )
    for subreddit_query in source.get("subreddit_queries", []):
        query = str(subreddit_query.get("query") or "").strip()
        subreddit = str(subreddit_query.get("subreddit") or "").strip()
        if not query or not subreddit:
            continue
        specs.append(
            {
                "query": query,
                "subreddit": subreddit,
                "posts_per_query": int(subreddit_query.get("posts_per_query") or default_posts_per_query),
            }
        )
    return specs


def _read_json_if_exists(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _search_cache_name(*, query: str, subreddit: str | None) -> str:
    if subreddit:
        return f"search-{_slug(subreddit)}-{_slug(query)}.json"
    return f"search-{_slug(query)}.json"


def _reddit_search(
    query: str,
    *,
    limit: int,
    subreddit: str | None = None,
    rate_limit_seconds: float = 1.0,
) -> list[dict[str, Any]]:
    if subreddit:
        url = (
            f"https://www.reddit.com/r/{quote_plus(subreddit)}/search.json?"
            f"q={quote_plus(query)}&restrict_sr=1&type=link&sort=relevance&limit={limit}"
        )
    else:
        url = f"https://www.reddit.com/search.json?q={quote_plus(query)}&type=link&sort=relevance&limit={limit}"
    payload = fetch_json(
        url,
        headers={"User-Agent": PUBLIC_VOICE_USER_AGENT, "Accept": "application/json"},
        timeout=20,
        rate_limit_seconds=rate_limit_seconds,
    )
    children = (((payload or {}).get("data") or {}).get("children") or [])
    posts = []
    for child in children:
        data = child.get("data") or {}
        if not data.get("id"):
            continue
        posts.append(
            {
                "id": data.get("id"),
                "title": _clean_text(data.get("title")),
                "subreddit": data.get("subreddit"),
                "score": data.get("score"),
                "num_comments": data.get("num_comments"),
                "created_utc": data.get("created_utc"),
                "permalink": "https://www.reddit.com" + str(data.get("permalink", "")),
                "selftext": _clean_text(data.get("selftext")),
                "search_subreddit": subreddit,
            }
        )
    return posts


def _reddit_comments(post_id: str, *, limit: int, rate_limit_seconds: float = 1.0) -> Any:
    url = f"https://www.reddit.com/comments/{post_id}.json?limit={limit}&sort=top"
    return fetch_json(
        url,
        headers={"User-Agent": PUBLIC_VOICE_USER_AGENT, "Accept": "application/json"},
        timeout=20,
        rate_limit_seconds=rate_limit_seconds,
    )


def _flatten_reddit_comments(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    root = (((payload[1] or {}).get("data") or {}).get("children") or [])
    comments: list[dict[str, Any]] = []

    def visit(children: list[dict[str, Any]]) -> None:
        for child in children:
            if child.get("kind") != "t1":
                continue
            data = child.get("data") or {}
            body = _clean_text(data.get("body"))
            if not body or body in {"[deleted]", "[removed]"}:
                continue
            author = _clean_text(data.get("author"))
            if _is_moderation_or_housekeeping_comment(body, author):
                continue
            comments.append(
                {
                    "id": data.get("id"),
                    "author": author,
                    "body": body,
                    "score": data.get("score"),
                    "created_utc": data.get("created_utc"),
                    "permalink": "https://www.reddit.com" + str(data.get("permalink", "")),
                }
            )
            replies = data.get("replies")
            if isinstance(replies, dict):
                visit(((replies.get("data") or {}).get("children") or []))

    visit(root)
    return comments


def _reddit_comment_evidence_item(
    *,
    source: dict[str, Any],
    query: str,
    subreddit: str | None,
    post: dict[str, Any],
    comment: dict[str, Any],
    theme_keywords: dict[str, list[str]],
) -> dict[str, Any] | None:
    text = comment.get("body") or ""
    if not _is_company_relevant(post, text):
        return None
    themes = _matched_themes(text, theme_keywords)
    if not themes:
        return None
    return {
        "source_id": source.get("source_id"),
        "source_name": source.get("name"),
        "source_quality_tier": source.get("quality_tier"),
        "voice_type": source.get("voice_type"),
        "language": source.get("language"),
        "query": query,
        "search_subreddit": subreddit,
        "post_title": post.get("title"),
        "post_subreddit": post.get("subreddit"),
        "post_score": post.get("score"),
        "post_num_comments": post.get("num_comments"),
        "post_url": post.get("permalink"),
        "comment_id": comment.get("id"),
        "comment_author": comment.get("author"),
        "comment_score": comment.get("score"),
        "comment_url": comment.get("permalink"),
        "themes": themes,
        "excerpt": _excerpt(text),
        "evidence_direction": "lead_only",
        "confidence": "low",
        "requires_human_review": True,
        "collected_at": utc_now_iso(),
    }


def _matched_themes(text: str, theme_keywords: dict[str, list[str]]) -> list[str]:
    lower = text.lower()
    themes = []
    for theme, keywords in theme_keywords.items():
        if any(keyword.lower() in lower for keyword in keywords):
            themes.append(theme)
    return themes


def _is_company_relevant(post: dict[str, Any], comment_text: str) -> bool:
    company_terms = ["temu", "pinduoduo", "pdd", "拼多多"]
    comment_lower = comment_text.lower()
    if any(term in comment_lower for term in company_terms):
        return True
    subreddit = str(post.get("subreddit") or "").lower()
    title = str(post.get("title") or "").lower()
    is_company_subreddit = any(term in subreddit for term in ["temu", "pinduoduo", "pdd"])
    is_company_thread = any(term in title for term in company_terms)
    return is_company_subreddit and is_company_thread


def _theme_summary(
    evidence_items: list[dict[str, Any]],
    theme_keywords: dict[str, list[str]],
) -> dict[str, Any]:
    counts = Counter(theme for item in evidence_items for theme in item.get("themes", []))
    examples: dict[str, list[dict[str, Any]]] = {theme: [] for theme in theme_keywords}
    used_sources_by_theme: dict[str, set[str]] = {theme: set() for theme in theme_keywords}
    for item in evidence_items:
        for theme in item.get("themes", []):
            if len(examples.setdefault(theme, [])) >= 3:
                continue
            source_id = str(item.get("source_id") or "")
            if source_id in used_sources_by_theme.setdefault(theme, set()):
                continue
            used_sources_by_theme[theme].add(source_id)
            examples[theme].append(
                {
                    "excerpt": item.get("excerpt"),
                    "comment_url": item.get("comment_url"),
                    "post_title": item.get("post_title"),
                    "source_id": item.get("source_id"),
                    "source_name": item.get("source_name"),
                    "evidence_type": item.get("evidence_type"),
                }
            )
    for item in evidence_items:
        for theme in item.get("themes", []):
            if len(examples.setdefault(theme, [])) >= 3:
                continue
            examples[theme].append(
                {
                    "excerpt": item.get("excerpt"),
                    "comment_url": item.get("comment_url"),
                    "post_title": item.get("post_title"),
                    "source_id": item.get("source_id"),
                    "source_name": item.get("source_name"),
                    "evidence_type": item.get("evidence_type"),
                }
            )
    return {
        "counts": dict(sorted(counts.items())),
        "examples": {theme: items for theme, items in examples.items() if items},
    }


def _theme_findings(theme_counts: dict[str, int]) -> list[dict[str, Any]]:
    labels = {
        "product_quality": "product quality / item-description gap",
        "shipping_delivery": "shipping and delivery experience",
        "refund_customer_service": "refunds, returns, and customer service",
        "repeat_purchase_loyalty": "repeat purchase / loyalty signals",
        "trust_safety": "trust, safety, privacy, or scam concerns",
        "merchant_seller_economics": "merchant/seller economics or platform-cost hints",
        "value_for_money": "value-for-money perception",
    }
    findings = []
    for theme, count in sorted(theme_counts.items(), key=lambda item: item[1], reverse=True):
        label = labels.get(theme, theme.replace("_", " "))
        findings.append(
            {
                "theme": theme,
                "label": label,
                "comment_count": count,
                "summary": (
                    f"Collected public-voice evidence contains {count} items matching {label}. "
                    "This is a low-confidence public-voice pattern, not a final conclusion."
                ),
                "confidence": "low",
                "requires_human_review": True,
            }
        )
    return findings


CUSTOMER_HAPPINESS_DIMENSIONS = [
    {
        "dimension_id": "value_for_money",
        "label": "Value for money",
        "theme": "value_for_money",
        "read_template": (
            "Public evidence repeatedly discusses price/value. This supports testing PDD/Temu's customer promise, "
            "but V1 cannot tell whether the value perception is durable or promotion-driven."
        ),
    },
    {
        "dimension_id": "product_quality",
        "label": "Product quality",
        "theme": "product_quality",
        "read_template": (
            "Quality-related evidence is a key anti-moat test because low price does not create durable happiness "
            "if customers see item-description or durability problems."
        ),
    },
    {
        "dimension_id": "shipping_delivery",
        "label": "Shipping and delivery",
        "theme": "shipping_delivery",
        "read_template": (
            "Delivery experience matters because Temu's cross-border model can lose customer trust if shipping is slow, "
            "unclear, or unreliable."
        ),
    },
    {
        "dimension_id": "refund_customer_service",
        "label": "Refunds, returns, and service",
        "theme": "refund_customer_service",
        "read_template": (
            "Refund/service evidence is a direct test of trust and repeat purchase. Complaints here should be treated "
            "as risk leads until measured against stronger aggregate sources."
        ),
    },
    {
        "dimension_id": "repeat_purchase_loyalty",
        "label": "Repeat purchase and loyalty",
        "theme": "repeat_purchase_loyalty",
        "read_template": (
            "Repeat-purchase language is the closest public-voice proxy for customer happiness, but V1 still needs "
            "better evidence than forum/review excerpts."
        ),
    },
    {
        "dimension_id": "trust_safety",
        "label": "Trust, safety, and privacy",
        "theme": "trust_safety",
        "read_template": (
            "Trust/safety concerns can cap the moat even when price is attractive. These claims need regulator, "
            "policy, and stronger-source triangulation."
        ),
    },
    {
        "dimension_id": "merchant_seller_economics",
        "label": "Merchant/seller satisfaction",
        "theme": "merchant_seller_economics",
        "read_template": (
            "Merchant satisfaction is not customer happiness, but it directly affects marketplace supply quality "
            "and therefore the customer value proposition."
        ),
    },
]


def synthesize_customer_happiness(
    public_voice_findings: dict[str, Any],
) -> dict[str, Any]:
    evidence_items = public_voice_findings.get("evidence_items") or []
    theme_summary = public_voice_findings.get("theme_summary") or {}
    theme_counts = theme_summary.get("counts") or {}
    examples = theme_summary.get("examples") or {}
    source_results = public_voice_findings.get("source_results") or []
    aggregate_summaries = [
        {
            "source_id": result.get("source_id"),
            "name": result.get("name"),
            "quality_tier": result.get("quality_tier"),
            "voice_type": result.get("voice_type"),
            "aggregate_summary": result.get("aggregate_summary"),
        }
        for result in source_results
        if result.get("aggregate_summary")
    ]
    dimensions = [
        _customer_happiness_dimension(
            definition=definition,
            evidence_items=evidence_items,
            count=int(theme_counts.get(definition["theme"], 0)),
            examples=examples.get(definition["theme"], []),
        )
        for definition in CUSTOMER_HAPPINESS_DIMENSIONS
    ]
    strongest_risks = [
        dimension
        for dimension in dimensions
        if dimension.get("current_read") in {"risk_pattern_lead", "mixed_or_unresolved_lead"}
    ]
    strongest_risks = sorted(strongest_risks, key=lambda item: int(item.get("evidence_count", 0)), reverse=True)
    status = "structured_from_public_voice" if evidence_items else "pending_public_voice_evidence"
    return {
        "status": status,
        "scope": "Customer-happiness synthesis from source-labeled public voice evidence.",
        "evidence_item_count": len(evidence_items),
        "source_quality_counts": dict(
            sorted(Counter(str(item.get("source_quality_tier", "unknown")) for item in evidence_items).items())
        ),
        "voice_type_counts": dict(
            sorted(Counter(str(item.get("voice_type", "unknown")) for item in evidence_items).items())
        ),
        "dimensions": dimensions,
        "aggregate_summaries": aggregate_summaries,
        "strongest_risk_leads": strongest_risks[:4],
        "current_conclusion": _customer_happiness_conclusion(
            evidence_count=len(evidence_items),
            dimensions=dimensions,
            aggregate_summaries=aggregate_summaries,
        ),
        "source_quality_policy": [
            "Tier 3/Tier 4 public voice can identify patterns and questions, not final customer happiness.",
            "Aggregate review data is more useful than isolated comments, but still has selection bias.",
            "Important customer-happiness conclusions require triangulation across app stores, review sites, forums, and official/regulatory sources.",
        ],
        "requires_human_review": bool(evidence_items),
    }


def _customer_happiness_dimension(
    *,
    definition: dict[str, Any],
    evidence_items: list[dict[str, Any]],
    count: int,
    examples: list[dict[str, Any]],
) -> dict[str, Any]:
    theme = definition["theme"]
    matching_items = [item for item in evidence_items if theme in item.get("themes", [])]
    source_tiers = sorted({str(item.get("source_quality_tier", "unknown")) for item in matching_items})
    source_names = sorted({str(item.get("source_name") or item.get("source_id")) for item in matching_items})
    if count == 0:
        current_read = "insufficient_evidence"
        confidence = "none"
    elif theme in {"refund_customer_service", "shipping_delivery", "product_quality", "trust_safety", "merchant_seller_economics"}:
        current_read = "risk_pattern_lead"
        confidence = "low"
    else:
        current_read = "mixed_or_unresolved_lead"
        confidence = "low"
    return {
        "dimension_id": definition["dimension_id"],
        "label": definition["label"],
        "theme": theme,
        "evidence_count": count,
        "current_read": current_read,
        "confidence": confidence,
        "source_quality_tiers": source_tiers,
        "source_names": source_names[:5],
        "summary": definition["read_template"],
        "representative_examples": examples[:3],
        "requires_human_review": count > 0,
    }


def _customer_happiness_conclusion(
    *,
    evidence_count: int,
    dimensions: list[dict[str, Any]],
    aggregate_summaries: list[dict[str, Any]],
) -> str:
    if evidence_count == 0:
        return "No public-voice evidence has been collected yet; customer happiness is not assessed."
    risk_dimensions = [
        dimension["label"]
        for dimension in dimensions
        if dimension.get("current_read") == "risk_pattern_lead" and int(dimension.get("evidence_count", 0)) > 0
    ]
    aggregate_note = ""
    for summary in aggregate_summaries:
        aggregate = summary.get("aggregate_summary") or {}
        if aggregate.get("rating") is not None and aggregate.get("review_count") is not None:
            aggregate_note = (
                f" One review-site aggregate shows {aggregate['rating']}/5 from "
                f"{aggregate['review_count']:,} reviews, which is a risk lead but still selection-biased."
            )
            break
    if risk_dimensions:
        return (
            "Current public-voice evidence does not prove customer happiness. It creates risk leads around "
            + ", ".join(risk_dimensions[:4])
            + ". Value-for-money may be real, but durability depends on repeat purchase, trust, service, and quality."
            + aggregate_note
        )
    return (
        "Current public-voice evidence is too thin for a customer-happiness conclusion. "
        "The next step is stronger aggregate app/review data and source-specific triangulation."
        + aggregate_note
    )


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return SPACE_PATTERN.sub(" ", str(value)).strip()


def _strip_markdown(value: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", value)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`#>]+", " ", text)
    return _clean_text(text)


def _is_moderation_or_housekeeping_comment(body: str, author: str) -> bool:
    author_lower = author.lower()
    body_lower = body.lower()
    if author_lower in {"automoderator", "reddit", "moderator"}:
        return True
    housekeeping_markers = [
        "thank you for posting in /r/",
        "new to the community",
        "[[wiki]]",
        "i am a bot",
        "beep boop",
        "please review our rules",
        "your post has been removed",
    ]
    return any(marker in body_lower for marker in housekeeping_markers)


def _excerpt(text: str, *, limit: int = 260) -> str:
    clean = _clean_text(text)
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "query"
