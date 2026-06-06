"""Generic commerce product parser for competitor baskets."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from .models import ProductConfig, ProductSnapshot, RawFetchResult
from .normalizer import compute_discount_pct, parse_count, parse_delivery_days, parse_money
from .parser import (
    _clean_text,
    _find_product_json,
    _first_json_number,
    _first_regex_text,
    _json_ld_blocks,
    _meta_content,
    _title_tag,
    _visible_text,
)


class GenericCommerceProductParser:
    """Best-effort parser for non-Temu competitor product pages.

    The first competitor-basket version should prefer stable product URLs and
    structured page data over broad search scraping. This parser intentionally
    uses JSON-LD, Open Graph metadata, and conservative visible-text patterns
    that work across many retail pages.
    """

    parser_name = "generic_commerce_product_v1"

    def parse(self, product: ProductConfig, fetch: RawFetchResult, collected_at: datetime | None = None) -> ProductSnapshot:
        collected_at = collected_at or fetch.fetched_at or datetime.now(timezone.utc)
        html_source = fetch.html or ""
        snapshot_id = hashlib.sha256(f"{product.tracking_id}:{collected_at.isoformat()}".encode("utf-8")).hexdigest()[:24]

        try:
            json_ld = _json_ld_blocks(html_source)
            product_json = _find_product_json(json_ld) or {}
            text = _visible_text(html_source)
            offers = _first_offer(product_json.get("offers"))
            aggregate = product_json.get("aggregateRating") or {}

            title = (
                _clean_text(product_json.get("name"))
                or _meta_content(html_source, "og:title")
                or _title_tag(html_source)
                or _first_regex_text(html_source, [r'"name"\s*:\s*"([^"]{4,220})"'])
            )
            price = (
                parse_money(offers.get("price"))
                or parse_money(_meta_content(html_source, "product:price:amount"))
                or _first_json_number(html_source, ["salePrice", "price", "priceAmount", "currentPrice"])
                or parse_money(
                    _first_regex_text(
                        text,
                        [
                            r"(?:current price|sale price|price|now)\s*(?:is)?\s*(?:USD\s*)?([$€£]?\s*[0-9][0-9,.]*(?:\.[0-9]+)?)",
                            r"([$€£]\s*[0-9][0-9,.]*(?:\.[0-9]+)?)",
                        ],
                    )
                )
            )
            list_price = (
                parse_money(offers.get("highPrice"))
                or _first_json_number(html_source, ["listPrice", "wasPrice", "originalPrice", "regularPrice", "strikethroughPrice"])
                or parse_money(
                    _first_regex_text(
                        text,
                        [
                            r"(?:list price|was|original price|regular price)\s*(?:USD\s*)?([$€£]?\s*[0-9][0-9,.]*(?:\.[0-9]+)?)",
                        ],
                    )
                )
            )
            rating = parse_money(aggregate.get("ratingValue")) or _first_json_number(html_source, ["ratingValue", "averageRating"])
            review_count = (
                parse_count(aggregate.get("reviewCount"))
                or parse_count(_first_regex_text(text, [r"([0-9][0-9,.]*\+?\s*(?:reviews?|ratings?))"]))
            )
            sold_count_text = _first_regex_text(text, [r"([0-9][0-9,.]*(?:\.[0-9]+)?\s*[KMBkmb]?\+?\s*(?:sold|bought))"])
            delivery_min_days, delivery_max_days = parse_delivery_days(text, collected_at)
            shipping_fee = 0.0 if re.search(r"\bfree\s+(?:shipping|delivery)\b", text, flags=re.IGNORECASE) else None
            stock_status = _stock_status(offers, text)

            parse_success, parse_error = _parse_success(title, price)
            return ProductSnapshot(
                snapshot_id=snapshot_id,
                product_tracking_id=product.tracking_id,
                product_id=_extract_competitor_product_id(fetch.final_url or product.url),
                url=fetch.final_url or product.url,
                category=product.category,
                collected_at=collected_at,
                title=title,
                price=price,
                list_price=list_price,
                discount_pct=compute_discount_pct(price, list_price),
                rating=rating,
                review_count=review_count,
                sold_count_text=sold_count_text,
                sold_count_estimate=parse_count(sold_count_text),
                delivery_min_days=delivery_min_days,
                delivery_max_days=delivery_max_days,
                shipping_fee=shipping_fee,
                stock_status=stock_status,
                seller_name=_clean_text(offers.get("seller") or offers.get("sellerName")),
                raw_payload_json={
                    "parser_name": self.parser_name,
                    "source_platform": _source_platform(fetch.final_url or product.url),
                    "json_ld_product_present": bool(product_json),
                    "final_url": fetch.final_url,
                    "html_path": fetch.html_path,
                    "notes": product.notes,
                },
                parse_success=parse_success,
                parse_error=parse_error,
            )
        except Exception as exc:
            return ProductSnapshot(
                snapshot_id=snapshot_id,
                product_tracking_id=product.tracking_id,
                product_id=_extract_competitor_product_id(fetch.final_url or product.url),
                url=fetch.final_url or product.url,
                category=product.category,
                collected_at=collected_at,
                raw_payload_json={
                    "parser_name": self.parser_name,
                    "source_platform": _source_platform(fetch.final_url or product.url),
                    "html_path": fetch.html_path,
                    "notes": product.notes,
                },
                parse_success=False,
                parse_error=str(exc),
            )


def _first_offer(offers: Any) -> dict[str, Any]:
    if isinstance(offers, list):
        return offers[0] if offers and isinstance(offers[0], dict) else {}
    return offers if isinstance(offers, dict) else {}


def _parse_success(title: str | None, price: float | None) -> tuple[bool, str | None]:
    if not title:
        return False, "missing title"
    if price is None:
        return False, "missing price"
    return True, None


def _stock_status(offers: dict[str, Any], text: str) -> str:
    availability = str(offers.get("availability") or "").lower()
    lower_text = text.lower()
    if "outofstock" in availability or any(token in lower_text for token in ("out of stock", "sold out", "currently unavailable")):
        return "out_of_stock"
    if "instock" in availability or any(token in lower_text for token in ("in stock", "add to cart", "buy now")):
        return "in_stock"
    return "unknown"


def _extract_competitor_product_id(url: str) -> str | None:
    parsed = urlparse(url)
    patterns = [
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/ip/(?:[^/]+/)?([0-9]{5,})",
        r"/item/([0-9]{5,})",
        r"-p-([0-9]{5,})",
        r"[?&](?:sku|skuId|productId|goods_id|item_id)=([A-Za-z0-9_-]{5,})",
    ]
    target = parsed.path + ("?" + parsed.query if parsed.query else "")
    for pattern in patterns:
        match = re.search(pattern, target, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _source_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "amazon." in host:
        return "amazon"
    if "walmart." in host:
        return "walmart"
    if "aliexpress." in host:
        return "aliexpress"
    if "shein." in host:
        return "shein"
    return host.removeprefix("www.") or "unknown"
