"""Normalize merchant-policy text and official regulatory payloads."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable

from .models import MerchantRegulatoryEvent, MerchantRegulatorySummary, SourceConfidence


TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "seller_fees": ("fee", "commission", "service charge", "transaction cost", "platform cost"),
    "ads_traffic": ("product ads", "sponsored", "advertising", "traffic", "campaign", "promote"),
    "returns_refunds": ("return", "refund", "buyer protection", "chargeback", "dispute"),
    "logistics_fulfillment": ("shipping", "delivery", "fulfillment", "warehouse", "last mile", "late shipment"),
    "payout_cashflow": ("payout", "settlement", "cash flow", "payment cycle", "withhold", "reserve"),
    "penalties_enforcement": ("penalty", "violation", "suspend", "delist", "non-compliance", "enforcement"),
    "merchant_profitability": ("profit", "margin", "discount", "coupon", "subsidy", "promotion"),
    "product_safety": ("recall", "hazard", "injury", "unsafe", "fire", "choking", "cpsc", "safety gate"),
    "consumer_protection": ("inform act", "consumer", "deceptive", "complaint", "ftc", "dark pattern"),
    "customs_de_minimis": ("section 321", "de minimis", "customs", "cbp", "tariff", "import duty"),
    "dsa_platform_obligations": ("digital services act", "dsa", "vlop", "illegal products", "systemic risk"),
    "counterfeit_illegal_goods": ("counterfeit", "ip infringement", "illegal goods", "prohibited product"),
}

HIGH_SEVERITY_TERMS = (
    "recall",
    "fine",
    "penalty",
    "lawsuit",
    "ban",
    "illegal",
    "unsafe",
    "injury",
    "violation",
    "non-compliance",
    "tariff",
    "customs enforcement",
)

MEDIUM_SEVERITY_TERMS = (
    "fee",
    "refund",
    "return",
    "late shipment",
    "withhold",
    "reserve",
    "payout",
    "promotion",
    "discount",
    "fulfillment",
)

SOURCE_GROUP_CONFIDENCE: dict[str, SourceConfidence] = {
    "merchant_platform_policy": "high",
    "merchant_voice": "low",
    "regulatory_product_safety": "high",
    "regulatory_trade_policy": "high",
    "regulatory_consumer_protection": "high",
}


def classify_topics(text: str) -> list[str]:
    """Return topic labels whose keyword set appears in the text."""

    normalized = text.lower()
    topics = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(_keyword_in_text(keyword, normalized) for keyword in keywords):
            topics.append(topic)
    return topics


def normalize_text_record(record: dict[str, Any]) -> list[MerchantRegulatoryEvent]:
    """Turn a merchant-policy or merchant-voice text record into topic events."""

    text = str(record.get("text") or "")
    if not text.strip():
        return []

    source_group = str(record.get("source_group") or "merchant_platform_policy")
    source_id = str(record.get("source_id") or "unknown_text_source")
    source_type = str(record.get("source_type") or "public_text")
    source_confidence = _source_confidence(source_group)
    title = str(record.get("title") or source_id)
    collected_at = _parse_datetime(record.get("collected_at")) or datetime.now(timezone.utc)
    published_at = _parse_datetime(record.get("published_at"))
    source_url = record.get("url") or record.get("source_url")

    events: list[MerchantRegulatoryEvent] = []
    for sentence in _split_sentences(text):
        topics = classify_topics(sentence)
        if not topics:
            continue
        for topic in topics:
            events.append(
                MerchantRegulatoryEvent(
                    event_id=_stable_id(source_id, topic, sentence),
                    source_group=source_group,
                    source_id=source_id,
                    source_type=source_type,
                    source_url=str(source_url) if source_url else None,
                    title=title,
                    topic=topic,
                    severity=_infer_severity(sentence, topic),
                    country=record.get("country"),
                    market=record.get("market"),
                    published_at=published_at,
                    collected_at=collected_at,
                    evidence_excerpt=_excerpt(sentence),
                    subject_entities=_subject_entities(record, sentence),
                    source_confidence=source_confidence,
                    raw_payload={key: value for key, value in record.items() if key != "text"},
                )
            )
    return _dedupe_events(events)


def normalize_cpsc_recalls(payload: Any, query_terms: Iterable[str] | None = None) -> list[MerchantRegulatoryEvent]:
    """Normalize CPSC recall API-style JSON into product-safety events."""

    terms = tuple(term.lower() for term in (query_terms or ("temu", "pdd", "pinduoduo")))
    recalls = payload.get("recalls") if isinstance(payload, dict) else payload
    if not isinstance(recalls, list):
        return []

    events: list[MerchantRegulatoryEvent] = []
    for recall in recalls:
        if not isinstance(recall, dict):
            continue
        text = " ".join(_flatten_values(recall))
        if terms and not any(term in text.lower() for term in terms):
            continue
        title = str(recall.get("Title") or recall.get("title") or "CPSC recall")
        recall_id = str(recall.get("RecallID") or recall.get("RecallNumber") or _stable_id("cpsc", title, text))
        published_at = _parse_datetime(recall.get("RecallDate") or recall.get("recall_date"))
        url = recall.get("URL") or recall.get("RecallURL") or recall.get("url")
        excerpt = _excerpt(text)
        events.append(
            MerchantRegulatoryEvent(
                event_id=_stable_id("cpsc_recalls", recall_id, title),
                source_group="regulatory_product_safety",
                source_id="cpsc_recalls_api",
                source_type="official_api",
                source_url=str(url) if url else "https://www.cpsc.gov/Recalls",
                title=title,
                topic="product_safety",
                severity="high",
                country="US",
                market="US",
                published_at=published_at,
                evidence_excerpt=excerpt,
                subject_entities=_recall_entities(recall),
                source_confidence="high",
                raw_payload=recall,
            )
        )
    return _dedupe_events(events)


def build_summary(events: list[MerchantRegulatoryEvent]) -> MerchantRegulatorySummary:
    topic_counts = Counter(event.topic for event in events)
    source_group_counts = Counter(event.source_group for event in events)
    top_events = sorted(events, key=lambda event: (_severity_rank(event.severity), event.collected_at), reverse=True)[:10]
    return MerchantRegulatorySummary(
        event_count=len(events),
        high_severity_count=sum(1 for event in events if event.severity == "high"),
        topic_counts=dict(topic_counts),
        source_group_counts=dict(source_group_counts),
        investment_questions=_investment_questions(topic_counts),
        top_events=top_events,
    )


def _investment_questions(topic_counts: Counter[str]) -> list[str]:
    questions = []
    if any(topic_counts.get(topic, 0) for topic in ("seller_fees", "returns_refunds", "payout_cashflow", "penalties_enforcement")):
        questions.append("Are merchant economics tightening through fees, returns, payout timing, or penalties?")
    if any(topic_counts.get(topic, 0) for topic in ("ads_traffic", "merchant_profitability")):
        questions.append("Is Temu asking merchants or paid promotion to carry more of the growth burden?")
    if any(topic_counts.get(topic, 0) for topic in ("product_safety", "consumer_protection", "counterfeit_illegal_goods")):
        questions.append("Is product safety or consumer-protection scrutiny rising in a way that could hurt conversion or take rate?")
    if topic_counts.get("customs_de_minimis", 0):
        questions.append("Could customs, de minimis, or tariff changes impair cross-border delivery economics?")
    if topic_counts.get("dsa_platform_obligations", 0):
        questions.append("Are EU platform obligations increasing compliance cost or limiting high-risk product supply?")
    if not questions:
        questions.append("No merchant or regulatory topic crossed the V1 keyword thresholds.")
    return questions


def _split_sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    parts = re.split(r"(?<=[.!?。！？])\s+", compact)
    return [part.strip() for part in parts if part.strip()]


def _keyword_in_text(keyword: str, normalized_text: str) -> bool:
    if " " in keyword:
        return keyword in normalized_text
    return re.search(rf"\b{re.escape(keyword)}s?\b", normalized_text) is not None


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def _stable_id(*parts: str) -> str:
    digest = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"merchant_reg_{digest}"


def _excerpt(text: str, limit: int = 420) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _infer_severity(text: str, topic: str) -> str:
    normalized = text.lower()
    if topic in {"product_safety", "consumer_protection", "customs_de_minimis", "dsa_platform_obligations"}:
        if any(term in normalized for term in HIGH_SEVERITY_TERMS):
            return "high"
    if any(term in normalized for term in HIGH_SEVERITY_TERMS):
        return "high"
    if any(term in normalized for term in MEDIUM_SEVERITY_TERMS):
        return "medium"
    return "low"


def _source_confidence(source_group: str) -> SourceConfidence:
    return SOURCE_GROUP_CONFIDENCE.get(source_group, "medium")


def _subject_entities(record: dict[str, Any], text: str) -> list[str]:
    entities = list(record.get("subject_entities") or [])
    normalized = text.lower()
    for candidate in ("Temu", "PDD", "Pinduoduo", "seller", "merchant", "CPSC", "CBP", "FTC", "EU DSA"):
        if candidate.lower() in normalized and candidate not in entities:
            entities.append(candidate)
    return entities


def _recall_entities(recall: dict[str, Any]) -> list[str]:
    entities = ["CPSC"]
    for key in ("Manufacturers", "Retailers", "Products"):
        for value in _flatten_values(recall.get(key)):
            if value and len(value) <= 80 and value not in entities:
                entities.append(value)
    return entities[:12]


def _flatten_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float)):
        return [str(value)]
    if isinstance(value, list):
        flattened = []
        for item in value:
            flattened.extend(_flatten_values(item))
        return flattened
    if isinstance(value, dict):
        flattened = []
        for item in value.values():
            flattened.extend(_flatten_values(item))
        return flattened
    return [str(value)]


def _dedupe_events(events: list[MerchantRegulatoryEvent]) -> list[MerchantRegulatoryEvent]:
    seen = set()
    deduped = []
    for event in events:
        if event.event_id in seen:
            continue
        seen.add(event.event_id)
        deduped.append(event)
    return deduped


def _severity_rank(severity: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(severity, 0)
