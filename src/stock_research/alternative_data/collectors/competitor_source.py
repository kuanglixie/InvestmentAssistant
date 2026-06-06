"""Competitor source collector V1."""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from typing import Any

from .common import CollectorFinding, CollectorPack, JsonDict, median, pct_gap, utc_now


TEXT_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "pricing_strategy": ("price", "pricing", "discount", "coupon", "promotion", "value", "affordable"),
    "logistics_delivery": ("delivery", "shipping", "fulfillment", "warehouse", "last mile", "logistics"),
    "marketplace_seller_model": ("seller", "merchant", "marketplace", "third-party", "supplier"),
    "regulatory_risk": ("regulation", "regulatory", "customs", "tariff", "de minimis", "compliance", "consumer protection"),
    "marketing_ads": ("advertising", "ad", "marketing", "traffic", "influencer", "creator"),
    "returns_customer_service": ("return", "refund", "customer service", "dispute"),
}

KNOWN_COMPETITORS = ("amazon", "walmart", "aliexpress", "shein", "tiktok_shop", "ebay")


def build_competitor_source_pack(
    *,
    company: str = "PDD",
    brand: str = "Temu",
    target_snapshots: list[JsonDict] | None = None,
    competitor_snapshots: list[JsonDict] | None = None,
    source_text_records: list[JsonDict] | None = None,
    source_inputs: JsonDict | None = None,
) -> CollectorPack:
    target_rows = _parsed_rows(target_snapshots or [], default_brand="temu")
    competitor_rows = _parsed_rows(competitor_snapshots or [], default_brand=None)
    comparison_metrics = _comparison_metrics(target_rows, competitor_rows)
    text_events = _text_events(source_text_records or [])
    findings = _findings(comparison_metrics, text_events)

    return CollectorPack(
        collector_id="competitor_source_v1",
        company=company,
        brand=brand,
        generated_at=utc_now(),
        source_inputs=source_inputs or {},
        metrics=comparison_metrics,
        events=text_events[:80],
        findings=findings,
        limitations=[
            "Competitor product comparison requires fixed comparable baskets; broad search results are not stable enough for clean trend interpretation.",
            "Public product pages can be region-, account-, and time-dependent. Prefer official APIs or saved page snapshots when available.",
            "Filings and policy pages explain competitor strategy and risk framing, but they are not direct operating metrics.",
        ],
    )


def _parsed_rows(rows: list[JsonDict], default_brand: str | None) -> list[JsonDict]:
    parsed = []
    for row in rows:
        if not row.get("parse_success", True):
            continue
        brand_id = _brand_id(row, default_brand)
        if not brand_id:
            continue
        parsed.append({**row, "competitor_id": brand_id})
    return parsed


def _brand_id(row: JsonDict, default_brand: str | None) -> str | None:
    raw_brand = row.get("brand_id") or row.get("brand") or row.get("source_platform")
    if raw_brand:
        text = _normalize_id(str(raw_brand))
        if text and text != "competitorbasket":
            return text
    tracking_id = _normalize_id(str(row.get("product_tracking_id") or row.get("tracking_id") or ""))
    for competitor in KNOWN_COMPETITORS:
        if tracking_id.startswith(competitor):
            return competitor
    url = str(row.get("url") or row.get("detail_url") or "").lower()
    for competitor in KNOWN_COMPETITORS:
        if competitor.replace("_", "") in url.replace("-", "").replace(".", ""):
            return competitor
    return default_brand


def _normalize_id(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.strip().lower())).strip("_")


def _comparison_metrics(target_rows: list[JsonDict], competitor_rows: list[JsonDict]) -> list[JsonDict]:
    target_by_category: dict[str, list[JsonDict]] = defaultdict(list)
    competitor_by_category_brand: dict[tuple[str, str], list[JsonDict]] = defaultdict(list)
    for row in target_rows:
        target_by_category[str(row.get("category") or "all")].append(row)
    for row in competitor_rows:
        competitor_by_category_brand[(str(row.get("category") or "all"), str(row["competitor_id"]))].append(row)

    output: list[JsonDict] = []
    for (category, competitor_id), rows in sorted(competitor_by_category_brand.items()):
        target = target_by_category.get(category) or target_by_category.get("all") or []
        if not target:
            continue
        target_price = median([row.get("price") for row in target])
        competitor_price = median([row.get("price") for row in rows])
        target_delivery = median([row.get("delivery_max_days") for row in target])
        competitor_delivery = median([row.get("delivery_max_days") for row in rows])
        target_discount = median([row.get("discount_pct") for row in target])
        competitor_discount = median([row.get("discount_pct") for row in rows])
        output.append(
            {
                "comparison_id": f"{category}:{competitor_id}",
                "metric_name": "relative_product_basket_position",
                "category": category,
                "competitor_id": competitor_id,
                "target_snapshot_count": len(target),
                "competitor_snapshot_count": len(rows),
                "target_median_price": target_price,
                "competitor_median_price": competitor_price,
                "relative_price_gap_pct": pct_gap(target_price, competitor_price),
                "target_median_delivery_max_days": target_delivery,
                "competitor_median_delivery_max_days": competitor_delivery,
                "delivery_gap_days": (
                    target_delivery - competitor_delivery
                    if target_delivery is not None and competitor_delivery is not None
                    else None
                ),
                "target_median_discount_pct": target_discount,
                "competitor_median_discount_pct": competitor_discount,
                "discount_gap_pct_points": (
                    target_discount - competitor_discount
                    if target_discount is not None and competitor_discount is not None
                    else None
                ),
                "confidence": "medium" if len(target) >= 3 and len(rows) >= 3 else "low",
            }
        )
    return output


def _text_events(records: list[JsonDict]) -> list[JsonDict]:
    events = []
    for record in records:
        text = str(record.get("text") or "")
        if not text.strip():
            continue
        for sentence in _split_sentences(text):
            topics = _topics(sentence)
            for topic in topics:
                events.append(
                    {
                        "event_id": _stable_id(str(record.get("source_id") or ""), topic, sentence),
                        "source_id": record.get("source_id") or "unknown_competitor_source",
                        "source_type": record.get("source_type") or "public_text",
                        "competitor_id": record.get("competitor_id") or _normalize_id(str(record.get("brand") or "")),
                        "title": record.get("title") or record.get("source_id") or "Competitor source",
                        "url": record.get("url") or record.get("source_url"),
                        "event_topic": topic,
                        "excerpt": sentence[:420],
                        "confidence": _source_confidence(str(record.get("source_type") or "")),
                    }
                )
    return _dedupe_events(events)


def _topics(text: str) -> list[str]:
    normalized = text.lower()
    topics = []
    for topic, keywords in TEXT_TOPIC_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            topics.append(topic)
    return topics


def _findings(comparison_metrics: list[JsonDict], text_events: list[JsonDict]) -> list[CollectorFinding]:
    findings: list[CollectorFinding] = []
    cheaper = [metric for metric in comparison_metrics if (metric.get("relative_price_gap_pct") or 0) <= -10]
    more_expensive = [metric for metric in comparison_metrics if (metric.get("relative_price_gap_pct") or 0) >= 10]
    if cheaper or more_expensive:
        findings.append(
            CollectorFinding(
                finding_id="relative_price_position",
                question="Is Temu cheaper than comparable competitor baskets?",
                summary=_price_summary(cheaper, more_expensive),
                severity="medium" if cheaper else "high",
                confidence=_comparison_confidence(comparison_metrics),
                evidence={
                    "cheaper_comparisons": [_comparison_label(metric) for metric in cheaper],
                    "more_expensive_comparisons": [_comparison_label(metric) for metric in more_expensive],
                },
                next_steps=["Use a stable fixed basket and avoid mixing broad search results with comparable SKU tracking."],
            )
        )

    slower = [metric for metric in comparison_metrics if (metric.get("delivery_gap_days") or 0) >= 2]
    faster = [metric for metric in comparison_metrics if metric.get("delivery_gap_days") is not None and metric["delivery_gap_days"] <= -2]
    if slower or faster:
        findings.append(
            CollectorFinding(
                finding_id="relative_delivery_position",
                question="Does Temu have a delivery-promise advantage or disadvantage?",
                summary=_delivery_summary(faster, slower),
                severity="medium" if slower else "low",
                confidence=_comparison_confidence(comparison_metrics),
                evidence={
                    "faster_comparisons": [_comparison_label(metric) for metric in faster],
                    "slower_comparisons": [_comparison_label(metric) for metric in slower],
                },
                next_steps=["Cross-check stated delivery promises with actual review delivery-delay complaint topics."],
            )
        )

    topic_counts = Counter(str(event.get("event_topic") or "unknown") for event in text_events)
    if any(topic_counts.get(topic, 0) for topic in ("pricing_strategy", "logistics_delivery", "marketplace_seller_model", "marketing_ads")):
        findings.append(
            CollectorFinding(
                finding_id="competitor_strategy_overlap",
                question="Are competitors describing similar pricing, logistics, ads, or seller-model levers?",
                summary="Competitor filings/policies/product pages contain strategy topics that overlap with Temu's model.",
                severity="medium",
                confidence="medium",
                evidence={"topic_counts": dict(topic_counts)},
                next_steps=["Compare topic excerpts against target-company product/pricing/policy findings."],
            )
        )

    if topic_counts.get("regulatory_risk", 0):
        findings.append(
            CollectorFinding(
                finding_id="competitor_regulatory_context",
                question="Is the risk Temu faces company-specific or industry-wide?",
                summary="Competitor official/public sources also discuss regulatory, customs, tariff, or compliance risk.",
                severity="medium",
                confidence="medium",
                evidence={"regulatory_risk_event_count": topic_counts["regulatory_risk"]},
                next_steps=["Separate marketplace-wide regulatory pressure from Temu-specific enforcement evidence."],
            )
        )

    if not findings:
        findings.append(
            CollectorFinding(
                finding_id="competitor_source_no_v1_threshold",
                question="Did any competitor-source threshold fire?",
                summary="No V1 competitor-source threshold finding was triggered.",
                severity="low",
                confidence="low" if not comparison_metrics and not text_events else "medium",
                evidence={"comparison_count": len(comparison_metrics), "text_event_count": len(text_events)},
            )
        )
    return findings


def _split_sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", compact) if part.strip()]


def _stable_id(*parts: str) -> str:
    digest = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"competitor_source_{digest}"


def _dedupe_events(events: list[JsonDict]) -> list[JsonDict]:
    seen = set()
    output = []
    for event in events:
        if event["event_id"] in seen:
            continue
        seen.add(event["event_id"])
        output.append(event)
    return output


def _source_confidence(source_type: str) -> str:
    if source_type in {"official_filing", "annual_report", "10k", "20f"}:
        return "high"
    if "policy" in source_type or "official" in source_type:
        return "medium"
    return "low"


def _comparison_confidence(metrics: list[JsonDict]) -> str:
    if any(metric.get("confidence") == "medium" for metric in metrics):
        return "medium"
    return "low"


def _comparison_label(metric: JsonDict) -> str:
    price_gap = metric.get("relative_price_gap_pct")
    delivery_gap = metric.get("delivery_gap_days")
    return (
        f"{metric.get('category')} vs {metric.get('competitor_id')}: "
        f"price_gap={price_gap:.1f}% " if price_gap is not None else f"{metric.get('category')} vs {metric.get('competitor_id')}: price_gap=na "
    ) + (f"delivery_gap={delivery_gap:.1f}d" if delivery_gap is not None else "delivery_gap=na")


def _price_summary(cheaper: list[JsonDict], more_expensive: list[JsonDict]) -> str:
    if cheaper and more_expensive:
        return "Temu is cheaper in some comparable baskets but more expensive in others."
    if cheaper:
        return "Temu appears cheaper than competitor baskets in the V1 comparable set."
    return "Temu appears more expensive than competitor baskets in the V1 comparable set."


def _delivery_summary(faster: list[JsonDict], slower: list[JsonDict]) -> str:
    if faster and slower:
        return "Temu delivery promise is mixed across comparable baskets."
    if faster:
        return "Temu delivery promise appears faster than competitors in the V1 comparable set."
    return "Temu delivery promise appears slower than competitors in the V1 comparable set."
