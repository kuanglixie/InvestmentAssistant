"""Schemas for merchant and regulatory alternative-data events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Severity = Literal["low", "medium", "high"]
SourceConfidence = Literal["low", "medium", "high"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MerchantRegulatoryEvent(BaseModel):
    """A normalized event from seller policy, merchant voice, or official regulation."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    company: str = "PDD"
    brand: str = "Temu"
    source_group: str
    source_id: str
    source_type: str
    source_url: str | None = None
    title: str
    topic: str
    severity: Severity = "medium"
    country: str | None = None
    market: str | None = None
    published_at: datetime | None = None
    collected_at: datetime = Field(default_factory=utc_now)
    evidence_excerpt: str
    subject_entities: list[str] = Field(default_factory=list)
    source_confidence: SourceConfidence = "medium"
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class MerchantRegulatorySummary(BaseModel):
    generated_at: datetime = Field(default_factory=utc_now)
    company: str = "PDD"
    brand: str = "Temu"
    event_count: int
    high_severity_count: int
    topic_counts: dict[str, int]
    source_group_counts: dict[str, int]
    investment_questions: list[str]
    top_events: list[MerchantRegulatoryEvent]
