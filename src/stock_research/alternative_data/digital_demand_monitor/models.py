"""Dataclass models for the digital demand monitor."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any


JsonDict = dict[str, Any]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | datetime | None, default: datetime | None = None) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        return default or utc_now()
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_date(value: str | date | None) -> date:
    if isinstance(value, date):
        return value
    if not value:
        return utc_now().date()
    return date.fromisoformat(str(value)[:10])


def to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value


@dataclass
class AppConfig:
    app_id: str | None = None
    package_name: str | None = None
    name: str | None = None
    category: str | None = None
    country_scope: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "AppConfig":
        return cls(
            app_id=data.get("app_id"),
            package_name=data.get("package_name"),
            name=data.get("name"),
            category=data.get("category"),
            country_scope=list(data.get("country_scope") or []),
        )


@dataclass
class BrandConfig:
    brand_id: str
    display_name: str
    role: str = "primary"
    domains: list[str] = field(default_factory=list)
    ios_apps: list[AppConfig] = field(default_factory=list)
    android_apps: list[AppConfig] = field(default_factory=list)
    search_terms: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "BrandConfig":
        return cls(
            brand_id=data["brand_id"],
            display_name=data.get("display_name") or data["brand_id"],
            role=data.get("role", "primary"),
            domains=list(data.get("domains") or []),
            ios_apps=[AppConfig.from_dict(item) for item in data.get("ios_apps") or []],
            android_apps=[AppConfig.from_dict(item) for item in data.get("android_apps") or []],
            search_terms=list(data.get("search_terms") or []),
        )


@dataclass
class WatchlistConfig:
    company_id: str
    ticker: str
    company_name: str
    primary_brand_id: str
    markets: list[str]
    brands: list[BrandConfig]
    competitor_groups: dict[str, list[str]] = field(default_factory=dict)
    review_taxonomy: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "WatchlistConfig":
        return cls(
            company_id=data["company_id"],
            ticker=data["ticker"],
            company_name=data.get("company_name") or data["ticker"],
            primary_brand_id=data.get("primary_brand_id") or data["brands"][0]["brand_id"],
            markets=list(data.get("markets") or []),
            brands=[BrandConfig.from_dict(item) for item in data.get("brands") or []],
            competitor_groups={key: list(value) for key, value in (data.get("competitor_groups") or {}).items()},
            review_taxonomy=list(data.get("review_taxonomy") or []),
        )

    def brand_by_id(self) -> dict[str, BrandConfig]:
        return {brand.brand_id: brand for brand in self.brands}

    def term_to_brand_id(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for brand in self.brands:
            for term in brand.search_terms:
                mapping[term.strip().lower()] = brand.brand_id
        return mapping

    def domain_to_brand_id(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for brand in self.brands:
            for domain in brand.domains:
                mapping[domain.strip().lower()] = brand.brand_id
        return mapping


@dataclass
class AppSnapshot:
    company_id: str
    ticker: str
    brand_id: str
    market: str
    platform: str
    app_id: str
    collected_at: datetime
    rank: float | None = None
    rating: float | None = None
    rating_count: int | None = None
    review_count: int | None = None
    download_count_lower_bound: int | None = None
    version: str | None = None
    updated_at: datetime | None = None
    source_name: str = "manual_or_fixture"
    raw_payload_json: JsonDict = field(default_factory=dict)
    fetch_success: bool = True
    fetch_error: str | None = None


@dataclass
class ReviewSnapshot:
    company_id: str
    ticker: str
    brand_id: str
    market: str
    platform: str
    review_id: str
    collected_at: datetime
    rating: float | None
    title: str | None
    text: str
    review_date: datetime | None = None
    version: str | None = None
    topic: str | None = None
    sentiment: str | None = None
    source_name: str = "manual_or_fixture"
    raw_payload_json: JsonDict = field(default_factory=dict)


@dataclass
class SearchSnapshot:
    company_id: str
    ticker: str
    brand_id: str
    market: str
    term: str
    date: date
    value: float
    source_name: str = "manual_csv"


@dataclass
class WebSnapshot:
    company_id: str
    ticker: str
    brand_id: str
    market: str
    domain: str
    collected_at: datetime
    rank: float | None
    source_name: str = "manual_csv"


@dataclass
class AdSnapshot:
    company_id: str
    ticker: str
    brand_id: str
    market: str
    source_name: str
    advertiser_name: str
    domain: str
    collected_at: datetime
    ad_count_lower_bound: int | None = None
    ad_count_label: str | None = None
    visible_ad_cards: int | None = None
    visible_video_cards: int | None = None
    source_url: str | None = None
    raw_payload_json: JsonDict = field(default_factory=dict)


@dataclass
class ProductMetricSnapshot:
    company_id: str
    ticker: str
    brand_id: str
    market: str
    period: str
    metric_name: str
    value: float | None
    change_1w: float | None = None
    change_4w: float | None = None
    source_path: str | None = None


@dataclass
class DemandMetric:
    company_id: str
    ticker: str
    brand_id: str
    market: str
    metric_name: str
    current_value: float | None
    previous_value: float | None = None
    change: float | None = None
    change_pct: float | None = None
    direction: str = "unknown"
    source_type: str = "unknown"
    confidence: str = "medium"
    evidence: JsonDict = field(default_factory=dict)


@dataclass
class DemandSignal:
    company_id: str
    ticker: str
    brand_id: str
    market: str
    signal: str
    status: str
    severity: str
    confidence: str
    summary: str
    drivers: list[str] = field(default_factory=list)
    contradicting_signals: list[str] = field(default_factory=list)
    evidence: JsonDict = field(default_factory=dict)


@dataclass
class DemandSignalPack:
    company_id: str
    ticker: str
    company_name: str
    primary_brand_id: str
    generated_at: datetime
    markets: list[str]
    metrics: list[DemandMetric]
    signals: list[DemandSignal]
