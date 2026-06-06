"""Parse Temu product page HTML into normalized product snapshots."""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from .models import ProductConfig, ProductSnapshot, RawFetchResult
from .normalizer import compute_discount_pct, parse_count, parse_delivery_days, parse_money, parse_percent


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = html.unescape(re.sub(r"\s+", " ", value)).strip()
    return cleaned or None


def _visible_text(source: str) -> str:
    source = re.sub(r"<script\b[^>]*>.*?</script>", " ", source, flags=re.IGNORECASE | re.DOTALL)
    source = re.sub(r"<style\b[^>]*>.*?</style>", " ", source, flags=re.IGNORECASE | re.DOTALL)
    source = re.sub(r"<[^>]+>", " ", source)
    return _clean_text(source) or ""


def _meta_content(source: str, name: str) -> str | None:
    pattern = (
        r"<meta\b(?=[^>]*(?:property|name)=[\"']"
        + re.escape(name)
        + r"[\"'])(?=[^>]*content=[\"']([^\"']+)[\"'])[^>]*>"
    )
    match = re.search(pattern, source, flags=re.IGNORECASE)
    return _clean_text(match.group(1)) if match else None


def _title_tag(source: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", source, flags=re.IGNORECASE | re.DOTALL)
    return _clean_text(match.group(1)) if match else None


def _json_ld_blocks(source: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for match in re.finditer(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        raw = html.unescape(match.group(1)).strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            blocks.extend(item for item in parsed if isinstance(item, dict))
        elif isinstance(parsed, dict):
            blocks.append(parsed)
    return blocks


def _find_product_json(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            node_type = node.get("@type")
            if node_type == "Product" or (isinstance(node_type, list) and "Product" in node_type):
                candidates.append(node)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    for block in blocks:
        visit(block)
    return candidates[0] if candidates else None


def _first_json_number(source: str, keys: list[str]) -> float | None:
    for key in keys:
        pattern = r"[\"']" + re.escape(key) + r"[\"']\s*:\s*[\"']?([0-9][0-9,]*(?:\.[0-9]+)?)"
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if match:
            return parse_money(match.group(1))
    return None


def _first_regex_text(source: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if match:
            return _clean_text(match.group(1))
    return None


def extract_product_id(url: str, source: str) -> str | None:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key in ("goods_id", "product_id", "item_id", "sku_id"):
        if query.get(key):
            return query[key][0]
    path_match = re.search(r"(?:goods|product|item)[_-]?([0-9]{6,})", parsed.path, flags=re.IGNORECASE)
    if path_match:
        return path_match.group(1)
    json_match = re.search(r"[\"'](?:goodsId|productId|itemId)[\"']\s*:\s*[\"']?([A-Za-z0-9_-]{6,})", source)
    return json_match.group(1) if json_match else None


def _extract_goods_card(source: str, url: str) -> dict[str, Any] | None:
    goods_id = extract_product_id(url, source)
    if not goods_id:
        return None
    card_match = re.search(r"<a\b(?=[^>]*g-" + re.escape(goods_id) + r"\.html)[\s\S]*?</a>", source)
    if not card_match:
        card_match = re.search(r"<a\b(?=[\s\S]{0,900}?data-unique-id=[\"']" + re.escape(goods_id) + r"[\"'])[\s\S]*?</a>", source)
    if not card_match:
        return None

    card = card_match.group(0)
    href_match = re.search(r"<a\b[^>]*href=[\"']([^\"']+)[\"']", card, flags=re.IGNORECASE)
    title_match = (
        re.search(r'data-tooltip-title="([^"]+)"', card, flags=re.IGNORECASE)
        or re.search(r"data-tooltip-title='([^']+)'", card, flags=re.IGNORECASE)
        or re.search(r"<h3[\s\S]*?<span\b[^>]*>(.*?)</span>", card, flags=re.IGNORECASE)
        or re.search(r"<img\b[^>]*alt=[\"']([^\"']+)[\"']", card, flags=re.IGNORECASE)
    )
    price_region = re.search(r"data-type=[\"']price[\"'][\s\S]{0,450}", card, flags=re.IGNORECASE)
    price_match = re.search(r">([^<]*[$€£][^<]+)<", price_region.group(0), flags=re.IGNORECASE) if price_region else None
    if not price_match:
        price_match = re.search(r"aria-label=[\"']([^\"']*[$€£][^\"']+)[\"']", card, flags=re.IGNORECASE)
    list_match = re.search(r"Original price\s*([0-9][0-9,.]*)", card, flags=re.IGNORECASE)
    discount_match = re.search(r"discount-[^>]*>[\s\S]{0,120}?(-?[0-9]+(?:\.[0-9]+)?\s*%)", card, flags=re.IGNORECASE)
    rating_match = re.search(r"([0-9](?:\.[0-9])?)\s*out of five stars", card, flags=re.IGNORECASE)
    review_match = re.search(r"\(([0-9][0-9,]*)\)\s*reviews?", card, flags=re.IGNORECASE)
    sold_match = re.search(r"([0-9][0-9,.]*(?:\.[0-9]+)?\s*[KMBkmb]?\+?\s*sold)", card, flags=re.IGNORECASE)

    return {
        "goods_id": goods_id,
        "card_html_present": True,
        "url": urljoin("https://www.temu.com", html.unescape(href_match.group(1))) if href_match else None,
        "title": _clean_text(title_match.group(1)) if title_match else None,
        "price": parse_money(price_match.group(1)) if price_match else None,
        "list_price": parse_money(list_match.group(1)) if list_match else None,
        "discount_pct": parse_percent(discount_match.group(1)) if discount_match else None,
        "rating": float(rating_match.group(1)) if rating_match else None,
        "review_count": parse_count(review_match.group(1)) if review_match else None,
        "sold_count_text": _clean_text(sold_match.group(1)) if sold_match else None,
        "sold_count_estimate": parse_count(sold_match.group(1)) if sold_match else None,
        "stock_status": "in_stock" if "Add to cart" in card else "unknown",
    }


def _parse_success(page_url: str, title: str | None, price: float | None, rating: float | None, review_count: int | None, delivery_max_days: int | None, sold_count_text: str | None) -> tuple[bool, str | None]:
    if "/login.html" in page_url or (title and title.strip().lower() == "temu | login"):
        return False, "login required or redirected to login"
    if not title:
        return False, "missing title"
    generic_titles = (
        "temu | explore the latest clothing, beauty, home, jewelry & more",
        "temu | shop for electronic",
    )
    if title.strip().lower().startswith(generic_titles):
        return False, "generic Temu shell title; likely not a product detail page"
    if price is None:
        return False, "missing price"
    if rating is None and review_count is None and delivery_max_days is None and not sold_count_text:
        return False, "partial product card only; missing rating/review/delivery/sold evidence"
    return True, None


class TemuProductParser:
    """Best-effort parser for Temu product HTML.

    Temu is JavaScript-heavy, so this parser favors structured data, meta tags,
    and resilient text patterns instead of brittle CSS selectors.
    """

    def parse(self, product: ProductConfig, fetch: RawFetchResult, collected_at: datetime | None = None) -> ProductSnapshot:
        collected_at = collected_at or fetch.fetched_at or datetime.now(timezone.utc)
        html_source = fetch.html or ""
        snapshot_id = hashlib.sha256(f"{product.tracking_id}:{collected_at.isoformat()}".encode("utf-8")).hexdigest()[:24]

        try:
            json_ld = _json_ld_blocks(html_source)
            product_json = _find_product_json(json_ld) or {}
            goods_card = _extract_goods_card(html_source, product.url) or {}
            text = _visible_text(html_source)

            offers = product_json.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers and isinstance(offers[0], dict) else {}
            aggregate = product_json.get("aggregateRating") or {}

            title = (
                goods_card.get("title")
                or _clean_text(product_json.get("name"))
                or _meta_content(html_source, "og:title")
                or _title_tag(html_source)
                or _first_regex_text(html_source, [r'"title"\s*:\s*"([^"]{4,200})"'])
            )

            price = (
                goods_card.get("price")
                or parse_money(offers.get("price"))
                or parse_money(_meta_content(html_source, "product:price:amount"))
                or _first_json_number(html_source, ["salePrice", "price", "priceAmount"])
                or parse_money(_first_regex_text(text, [r"(?:Now|Price|Sale price)\s*\$?\s*([0-9][0-9,.]*)"]))
            )
            list_price = (
                goods_card.get("list_price")
                or parse_money(offers.get("highPrice"))
                or _first_json_number(html_source, ["listPrice", "marketPrice", "originalPrice", "retailPrice"])
                or parse_money(_first_regex_text(text, [r"(?:List price|Was|Original price)\s*\$?\s*([0-9][0-9,.]*)"]))
            )
            discount_pct = (
                goods_card.get("discount_pct")
                or parse_percent(_first_regex_text(text, [r"([0-9]+(?:\.[0-9]+)?\s*%\s*off)"]))
                or compute_discount_pct(price, list_price)
            )

            coupon_text = _first_regex_text(
                text,
                [
                    r"(\$?\s*[0-9][0-9,.]*\s*(?:coupon|promo)[^.]{0,80})",
                    r"((?:coupon|promo)[^.]{0,80}\$[0-9][0-9,.]*)",
                    r"((?:no\s+)?(?:coupon|promo)[^.]{0,80})",
                ],
            )
            no_coupon_nearby = re.search(r"\bno\s+(?:coupon|promo)\b", text, flags=re.IGNORECASE)
            coupon_available = bool(coupon_text) and not no_coupon_nearby and not re.search(
                r"(?:no|without|not|unavailable|none)\s+(?:coupon|promo)|(?:coupon|promo)\s+(?:currently\s+)?(?:unavailable|not\s+available)",
                coupon_text,
                flags=re.IGNORECASE,
            )
            coupon_value = parse_money(coupon_text)
            if not coupon_available:
                coupon_value = None

            rating = parse_money(aggregate.get("ratingValue")) or _first_json_number(html_source, ["ratingValue", "rating"])
            rating = goods_card.get("rating") or rating
            review_count = (
                goods_card.get("review_count")
                or parse_count(aggregate.get("reviewCount"))
                or parse_count(_first_regex_text(text, [r"([0-9][0-9,.]*\+?\s*(?:reviews?|ratings?))"]))
            )
            sold_count_text = goods_card.get("sold_count_text") or _first_regex_text(text, [r"([0-9][0-9,.]*(?:\.[0-9]+)?\s*[KMBkmb]?\+?\s*sold)"])
            sold_count_estimate = goods_card.get("sold_count_estimate") or parse_count(sold_count_text)

            delivery_min_days, delivery_max_days = parse_delivery_days(text, collected_at)
            shipping_fee = 0.0 if re.search(r"free\s+shipping", text, flags=re.IGNORECASE) else parse_money(
                _first_regex_text(text, [r"(?:shipping|delivery)\s*(?:fee|cost)?\s*\$?\s*([0-9][0-9,.]*)"])
            )

            lower_text = text.lower()
            if any(token in lower_text for token in ("out of stock", "sold out", "currently unavailable")):
                stock_status = "out_of_stock"
            elif any(token in lower_text for token in ("in stock", "add to cart", "buy now")):
                stock_status = "in_stock"
            else:
                stock_status = "unknown"
            if goods_card.get("stock_status") == "in_stock":
                stock_status = "in_stock"

            seller_name = _first_regex_text(text, [r"(?:sold by|seller)\s*:?\s*([A-Za-z0-9 &.'_-]{2,80})"])
            raw_payload = {
                "fetch": fetch.model_dump(mode="json", exclude={"html"}),
                "json_ld": json_ld[:5],
                "meta": {
                    "og:title": _meta_content(html_source, "og:title"),
                    "product:price:amount": _meta_content(html_source, "product:price:amount"),
                },
                "goods_card": goods_card,
            }
            output_url = goods_card.get("url") or fetch.final_url or product.url
            parse_success, parse_error = _parse_success(output_url, title, price, rating, review_count, delivery_max_days, sold_count_text)

            return ProductSnapshot(
                snapshot_id=snapshot_id,
                product_tracking_id=product.tracking_id,
                product_id=goods_card.get("goods_id") or extract_product_id(product.url, html_source),
                url=output_url,
                category=product.category,
                collected_at=collected_at,
                title=title,
                price=price,
                list_price=list_price,
                discount_pct=discount_pct,
                coupon_available=coupon_available,
                coupon_value=coupon_value,
                rating=rating,
                review_count=review_count,
                sold_count_text=sold_count_text,
                sold_count_estimate=sold_count_estimate,
                delivery_min_days=delivery_min_days,
                delivery_max_days=delivery_max_days,
                shipping_fee=shipping_fee,
                stock_status=stock_status,
                seller_name=seller_name,
                raw_payload_json=raw_payload,
                parse_success=parse_success,
                parse_error=parse_error,
            )
        except Exception as exc:
            return ProductSnapshot(
                snapshot_id=snapshot_id,
                product_tracking_id=product.tracking_id,
                url=fetch.final_url or product.url,
                category=product.category,
                collected_at=collected_at,
                raw_payload_json={"fetch": fetch.model_dump(mode="json", exclude={"html"})},
                parse_success=False,
                parse_error=str(exc),
            )
