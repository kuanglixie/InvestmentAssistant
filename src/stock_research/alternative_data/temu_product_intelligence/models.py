"""Pydantic schemas for the Temu product intelligence monitor."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


StockStatus = Literal["in_stock", "out_of_stock", "unknown"]
TrendDirection = Literal["up", "down", "flat", "unknown"]
Confidence = Literal["high", "medium", "low"]


class ProductConfig(BaseModel):
    tracking_id: str
    category: str
    url: str
    notes: str | None = None
    active: bool = True


class BasketConfig(BaseModel):
    brand: str = "Temu"
    company: str = "PDD"
    region: str = "US"
    currency: str = "USD"
    products: list[ProductConfig] = Field(default_factory=list)


class CrawlerSettings(BaseModel):
    headless: bool = True
    timeout_ms: int = 30_000
    wait_until: str = "domcontentloaded"
    post_load_wait_ms: int = 2_000
    scroll_steps: int = 0
    scroll_wait_ms: int = 800
    min_delay_seconds: float = 3.0
    max_retries: int = 2
    chrome_executable_path: str | None = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    node_executable_path: str | None = "/Users/ajing/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
    node_modules_path: str | None = "/Users/ajing/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
    )


class RawFetchResult(BaseModel):
    tracking_id: str
    url: str
    fetched_at: datetime
    status_code: int | None = None
    final_url: str | None = None
    html_path: str | None = None
    html_sha256: str | None = None
    html: str | None = None
    fetch_success: bool = True
    fetch_error: str | None = None


class ProductSnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")

    snapshot_id: str
    product_tracking_id: str
    product_id: str | None = None
    url: str
    category: str
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    title: str | None = None
    price: float | None = None
    list_price: float | None = None
    discount_pct: float | None = None
    coupon_available: bool = False
    coupon_value: float | None = None
    rating: float | None = None
    review_count: int | None = None
    sold_count_text: str | None = None
    sold_count_estimate: int | None = None
    delivery_min_days: int | None = None
    delivery_max_days: int | None = None
    shipping_fee: float | None = None
    stock_status: StockStatus = "unknown"
    seller_name: str | None = None
    raw_payload_json: dict[str, Any] = Field(default_factory=dict)
    parse_success: bool = True
    parse_error: str | None = None

    @field_validator("price", "list_price", "coupon_value", "shipping_fee")
    @classmethod
    def non_negative_money(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("money fields must be non-negative")
        return value

    @field_validator("discount_pct")
    @classmethod
    def discount_range(cls, value: float | None) -> float | None:
        if value is not None:
            return max(0.0, min(100.0, value))
        return value

    @field_validator("rating")
    @classmethod
    def rating_range(cls, value: float | None) -> float | None:
        if value is not None:
            return max(0.0, min(5.0, value))
        return value


class ProductCardSnapshot(BaseModel):
    card_id: str
    page_tracking_id: str
    product_id: str | None = None
    detail_url: str | None = None
    category: str
    title: str | None = None
    price: float | None = None
    list_price: float | None = None
    discount_pct: float | None = None
    coupon_available: bool = False
    coupon_value: float | None = None
    rating: float | None = None
    review_count: int | None = None
    sold_count_text: str | None = None
    sold_count_estimate: int | None = None
    free_shipping: bool = False
    stock_status: StockStatus = "unknown"


class ProductSurfaceSnapshot(BaseModel):
    snapshot_id: str
    page_tracking_id: str
    url: str
    category: str
    region: str
    currency: str
    collected_at: datetime
    card_count: int
    unique_product_count: int
    priced_card_count: int
    median_price: float | None = None
    median_list_price: float | None = None
    median_discount_pct: float | None = None
    discount_card_rate: float | None = None
    coupon_card_rate: float | None = None
    free_shipping_rate: float | None = None
    in_stock_rate: float | None = None
    stockout_card_rate: float | None = None
    median_sold_count_estimate: float | None = None
    top_title_terms: dict[str, int] = Field(default_factory=dict)
    promo_messages: list[str] = Field(default_factory=list)
    sample_products: list[dict[str, Any]] = Field(default_factory=list)
    cards: list[ProductCardSnapshot] = Field(default_factory=list)


class WeeklyMetric(BaseModel):
    company: str
    brand: str
    period: str
    category: str
    metric_name: str
    value: float | None
    change_1w: float | None = None
    change_4w: float | None = None
    trend_direction: TrendDirection = "unknown"
    confidence: Confidence = "medium"


class ProductSignal(BaseModel):
    company: str
    brand: str
    period: str
    category: str = "all"
    signal: str
    metric: str
    current_value: float | None = None
    change_1w: float | None = None
    change_4w: float | None = None
    investment_question: str
    severity: Literal["low", "medium", "high"] = "medium"
    confidence: Confidence = "medium"
    evidence: dict[str, Any] = Field(default_factory=dict)


class SignalPack(BaseModel):
    company: str
    brand: str
    period: str
    product_signals: list[ProductSignal]


class UnitEconomicsPack(BaseModel):
    company: str
    brand: str
    period: str
    unit_economics_proxies: dict[str, float | None]
