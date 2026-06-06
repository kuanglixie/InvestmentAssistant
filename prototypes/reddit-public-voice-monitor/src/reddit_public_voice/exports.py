"""Export helpers for Reddit public-voice evidence."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


THEME_TO_REVIEW_TOPIC = {
    "shipping_delivery": "delivery_delay",
    "refund_customer_service": "refund_return",
    "product_quality": "product_quality",
    "trust_safety": "trust_scam",
    "merchant_seller_economics": "merchant_seller_economics",
    "value_for_money": "pricing_coupon",
    "repeat_purchase_loyalty": "repeat_purchase",
}

RISK_THEMES = {
    "shipping_delivery",
    "refund_customer_service",
    "product_quality",
    "trust_safety",
    "merchant_seller_economics",
}

POSITIVE_TERMS = {
    "good",
    "great",
    "love",
    "worth it",
    "cheap",
    "happy",
    "recommend",
    "works",
}

NEGATIVE_TERMS = {
    "bad",
    "scam",
    "refund",
    "return",
    "late",
    "fake",
    "broken",
    "penalty",
    "suspended",
    "privacy",
    "unsafe",
    "counterfeit",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def findings_from_json_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept either a direct findings JSON file or a full research state.json file."""
    if "public_voice_findings" in payload and isinstance(payload["public_voice_findings"], dict):
        return payload["public_voice_findings"]
    return payload


def reddit_evidence_items(findings: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for result in findings.get("source_results") or []:
        source_id = str(result.get("source_id") or "").lower()
        adapter = str(result.get("adapter") or "").lower()
        if "reddit" not in source_id and "reddit" not in adapter:
            continue
        for item in result.get("evidence_items") or []:
            if isinstance(item, dict):
                items.append(item)
    if items:
        return items
    for item in findings.get("evidence_items") or []:
        if isinstance(item, dict) and "reddit" in str(item.get("source_id") or "").lower():
            items.append(item)
    return items


def export_demand_monitor_reviews(
    items: list[dict[str, Any]],
    *,
    brand_id: str = "temu",
    market: str = "GLOBAL",
    max_items: int | None = None,
) -> list[dict[str, Any]]:
    limited_items = items[:max_items] if max_items is not None else items
    reviews = []
    for index, item in enumerate(limited_items, start=1):
        themes = [str(theme) for theme in item.get("themes") or []]
        topic = _review_topic(themes)
        text = str(item.get("excerpt") or item.get("text") or "").strip()
        if not text:
            continue
        reviews.append(
            {
                "brand_id": brand_id,
                "market": market,
                "platform": "reddit",
                "review_id": _review_id(item, index),
                "collected_at": item.get("collected_at") or utc_now_iso(),
                "rating": None,
                "title": item.get("post_title"),
                "text": text,
                "review_date": item.get("created_at") or item.get("collected_at"),
                "topic": topic,
                "sentiment": _sentiment(text, themes),
                "source_name": "reddit_public_voice",
                "source_url": item.get("comment_url") or item.get("post_url"),
                "source_context": _relevance_bucket(item),
                "post_subreddit": item.get("post_subreddit"),
                "post_url": item.get("post_url"),
                "comment_score": item.get("comment_score"),
                "themes": themes,
                "raw_payload": item,
            }
        )
    return reviews


def build_reddit_summary(findings: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    theme_counts = Counter(theme for item in items for theme in item.get("themes") or [])
    subreddit_counts = Counter(str(item.get("post_subreddit") or item.get("search_subreddit") or "unknown") for item in items)
    query_counts = Counter(str(item.get("query") or "unknown") for item in items)
    post_counts = Counter(str(item.get("post_title") or "unknown") for item in items)
    relevance_counts = Counter(_relevance_bucket(item) for item in items)
    source_results = [
        result
        for result in findings.get("source_results") or []
        if "reddit" in str(result.get("source_id") or "").lower() or "reddit" in str(result.get("adapter") or "").lower()
    ]
    return {
        "generated_at": utc_now_iso(),
        "status": findings.get("status"),
        "reddit_evidence_item_count": len(items),
        "theme_counts": dict(theme_counts.most_common()),
        "subreddit_counts": dict(subreddit_counts.most_common()),
        "relevance_counts": dict(relevance_counts.most_common()),
        "query_counts": dict(query_counts.most_common(10)),
        "top_posts": dict(post_counts.most_common(10)),
        "source_results": [
            {
                "source_id": result.get("source_id"),
                "status": result.get("status"),
                "posts_collected": result.get("posts_collected"),
                "comments_seen_before_filter": result.get("comments_seen_before_filter"),
                "comments_collected": result.get("comments_collected") or len(result.get("evidence_items") or []),
                "errors": result.get("errors") or [],
                "notes": result.get("notes") or [],
            }
            for result in source_results
        ],
    }


def write_reviews_csv(path: str | Path, reviews: list[dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "review_id",
        "brand_id",
        "market",
        "platform",
        "topic",
        "sentiment",
        "title",
        "text",
        "source_url",
        "source_context",
        "post_subreddit",
        "comment_score",
        "collected_at",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for review in reviews:
            writer.writerow({field: review.get(field) for field in fieldnames})


def render_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Reddit Public Voice Snapshot",
        "",
        f"- Status: {summary.get('status') or 'unknown'}",
        f"- Reddit evidence items: {summary.get('reddit_evidence_item_count', 0)}",
        "",
        "## Top Themes",
    ]
    lines.extend(_counter_lines(summary.get("theme_counts") or {}))
    lines.extend(["", "## Relevance Context"])
    lines.extend(_counter_lines(summary.get("relevance_counts") or {}))
    lines.extend(["", "## Top Subreddits"])
    lines.extend(_counter_lines(summary.get("subreddit_counts") or {}))
    lines.extend(["", "## Top Queries"])
    lines.extend(_counter_lines(summary.get("query_counts") or {}))
    lines.extend(["", "## Collector Status"])
    for result in summary.get("source_results") or []:
        lines.append(
            "- "
            + f"{result.get('source_id')}: {result.get('status')} "
            + f"({result.get('comments_collected') or 0} kept, "
            + f"{result.get('comments_seen_before_filter') or 0} scanned)"
        )
        for error in (result.get("errors") or [])[:3]:
            lines.append(f"  - Error: {error}")
    return "\n".join(lines).rstrip() + "\n"


def _counter_lines(counts: dict[str, int]) -> list[str]:
    if not counts:
        return ["- None"]
    return [f"- {key}: {value}" for key, value in counts.items()]


def _review_id(item: dict[str, Any], index: int) -> str:
    for key in ("comment_id", "post_id", "id"):
        value = str(item.get(key) or "").strip()
        if value:
            return f"reddit-{value}"
    return f"reddit-public-voice-{index}"


def _review_topic(themes: list[str]) -> str:
    for theme in themes:
        if theme in THEME_TO_REVIEW_TOPIC:
            return THEME_TO_REVIEW_TOPIC[theme]
    return "other"


def _relevance_bucket(item: dict[str, Any]) -> str:
    terms = ("temu", "pdd", "pinduoduo", "拼多多")
    subreddit = str(item.get("post_subreddit") or item.get("search_subreddit") or "").lower()
    title = str(item.get("post_title") or "").lower()
    excerpt = str(item.get("excerpt") or item.get("text") or "").lower()
    if any(term in subreddit for term in terms):
        return "brand_subreddit"
    if any(term in title for term in terms):
        return "brand_thread"
    if any(term in excerpt for term in terms):
        return "brand_mention"
    return "query_context"


def _sentiment(text: str, themes: list[str]) -> str:
    normalized = text.lower()
    negative = sum(1 for term in NEGATIVE_TERMS if term in normalized)
    positive = sum(1 for term in POSITIVE_TERMS if term in normalized)
    if any(theme in RISK_THEMES for theme in themes) and negative >= positive:
        return "negative"
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "neutral"
