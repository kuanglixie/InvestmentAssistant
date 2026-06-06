"""Landing-page product-card extraction for Temu demand signals."""

from __future__ import annotations

import csv
import hashlib
import html
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

from .models import BasketConfig, ProductCardSnapshot, ProductConfig, ProductSurfaceSnapshot, RawFetchResult
from .normalizer import compute_discount_pct, iso_week_period, median_or_none, parse_count, parse_money, parse_percent, rate


_COMMON_TITLE_TERMS = {
    "and",
    "for",
    "with",
    "the",
    "this",
    "that",
    "from",
    "your",
    "women",
    "mens",
    "men",
    "set",
    "piece",
    "pieces",
    "pc",
    "pcs",
    "new",
    "temu",
    "suitable",
    "daily",
    "casual",
    "home",
    "gift",
    "use",
}


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


def _anchor_cards(source: str) -> Iterable[str]:
    pattern = re.compile(
        r"<a\b(?=[^>]*href=[\"'][^\"']*g-[0-9]+\.html[^\"']*[\"'])[\s\S]*?</a>",
        flags=re.IGNORECASE,
    )
    return (match.group(0) for match in pattern.finditer(source))


def _first_regex_text(source: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, source, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return _clean_text(match.group(1))
    return None


def _href(card_html: str) -> str | None:
    return _first_regex_text(card_html, [r"<a\b[^>]*href=[\"']([^\"']+)[\"']"])


def _goods_id(card_html: str, href: str | None) -> str | None:
    for value in (href or "", card_html):
        match = re.search(r"g-([0-9]+)\.html", value)
        if match:
            return match.group(1)
    match = re.search(r"data-unique-id=[\"']([A-Za-z0-9_-]{6,})[\"']", card_html)
    return match.group(1) if match else None


def _title_from_url(href: str | None) -> str | None:
    if not href:
        return None
    match = re.search(r"/([^/?#]+)-g-[0-9]+\.html", href)
    if not match:
        return None
    slug = re.sub(r"[-_]+", " ", match.group(1))
    return _clean_text(slug.title())


def _card_title(card_html: str, href: str | None) -> str | None:
    title = _first_regex_text(
        card_html,
        [
            r'data-tooltip-title="([^"]+)"',
            r"data-tooltip-title='([^']+)'",
            r"<h3[\s\S]*?<span\b[^>]*>(.*?)</span>",
            r"<img\b[^>]*alt=[\"']([^\"']+)[\"']",
        ],
    )
    if title and title.lower() not in {"image", "product image"}:
        return title
    return _title_from_url(href)


def _money_from_labels(source: str, skip_original: bool = True) -> float | None:
    labels = re.findall(r"aria-label=[\"']([^\"']+)[\"']", source, flags=re.IGNORECASE)
    for label in labels:
        if skip_original and re.search(r"\b(original|list|was)\b", label, flags=re.IGNORECASE):
            continue
        if re.search(r"[$€£]|[A-Z]{1,3}\$", label):
            parsed = parse_money(label)
            if parsed is not None:
                return parsed
    return None


def _card_price(card_html: str) -> float | None:
    price_region = re.search(r"data-type=[\"']price[\"'][\s\S]{0,650}", card_html, flags=re.IGNORECASE)
    source = price_region.group(0) if price_region else card_html
    value = _money_from_labels(source)
    if value is not None:
        return value
    match = re.search(r">([^<]*(?:[$€£]|[A-Z]{1,3}\$)\s*[0-9][^<]*)<", source)
    return parse_money(match.group(1)) if match else None


def _card_list_price(card_html: str) -> float | None:
    text = _visible_text(card_html)
    value = _first_regex_text(
        text,
        [
            r"(?:Original price|List price|Was)\s*(?:[A-Z]{1,3}\$|[$€£])?\s*([0-9][0-9,.]*(?:\.[0-9]+)?)",
        ],
    )
    return parse_money(value)


def _card_coupon(card_html: str) -> tuple[bool, float | None]:
    text = _visible_text(card_html)
    if not re.search(r"\b(coupon|voucher|promo)\b", text, flags=re.IGNORECASE):
        return False, None
    value = _first_regex_text(
        text,
        [
            r"((?:[A-Z]{1,3}\$|[$€£])\s*[0-9][0-9,.]*(?:\.[0-9]+)?)[^.!?]{0,40}(?:coupon|voucher|promo)",
            r"(?:coupon|voucher|promo)[^.!?]{0,40}((?:[A-Z]{1,3}\$|[$€£])\s*[0-9][0-9,.]*(?:\.[0-9]+)?)",
        ],
    )
    return True, parse_money(value)


def _card_stock_status(text: str) -> str:
    lower = text.lower()
    if any(token in lower for token in ("out of stock", "sold out", "currently unavailable")):
        return "out_of_stock"
    if any(token in lower for token in ("add to cart", "buy now", "in stock")):
        return "in_stock"
    return "unknown"


def extract_product_cards(product: ProductConfig, fetch: RawFetchResult) -> list[ProductCardSnapshot]:
    """Extract all visible product cards from a Temu landing/feed/search page."""

    page_url = fetch.final_url or product.url
    output: list[ProductCardSnapshot] = []
    seen: set[str] = set()

    for index, card_html in enumerate(_anchor_cards(fetch.html or ""), start=1):
        href = _href(card_html)
        product_id = _goods_id(card_html, href)
        detail_url = urljoin(page_url, html.unescape(href)) if href else None
        dedupe_key = product_id or detail_url or hashlib.sha256(card_html.encode("utf-8")).hexdigest()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        text = _visible_text(card_html)
        price = _card_price(card_html)
        list_price = _card_list_price(card_html)
        discount_pct = parse_percent(_first_regex_text(text, [r"([0-9]+(?:\.[0-9]+)?\s*%\s*off)"]))
        if discount_pct is None:
            discount_pct = compute_discount_pct(price, list_price)
        coupon_available, coupon_value = _card_coupon(card_html)
        rating_text = _first_regex_text(text, [r"([0-9](?:\.[0-9])?)\s*out of five stars"])
        review_text = _first_regex_text(text, [r"\(([0-9][0-9,]*)\)\s*reviews?"])
        sold_count_text = _first_regex_text(text, [r"([0-9][0-9,.]*(?:\.[0-9]+)?\s*[KMBkmb]?\+?\s*sold)"])

        output.append(
            ProductCardSnapshot(
                card_id=f"{product.tracking_id}-{index:04d}",
                page_tracking_id=product.tracking_id,
                product_id=product_id,
                detail_url=detail_url,
                category=product.category,
                title=_card_title(card_html, href),
                price=price,
                list_price=list_price,
                discount_pct=discount_pct,
                coupon_available=coupon_available,
                coupon_value=coupon_value,
                rating=float(rating_text) if rating_text else None,
                review_count=parse_count(review_text),
                sold_count_text=sold_count_text,
                sold_count_estimate=parse_count(sold_count_text),
                free_shipping=bool(re.search(r"\bfree shipping\b", text, flags=re.IGNORECASE)),
                stock_status=_card_stock_status(text),
            )
        )

    return output


def _top_title_terms(cards: list[ProductCardSnapshot], limit: int = 12) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for card in cards:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9]+", card.title or ""):
            normalized = token.lower()
            if len(normalized) >= 4 and normalized not in _COMMON_TITLE_TERMS:
                counter[normalized] += 1
    return dict(counter.most_common(limit))


def _promo_messages(source: str, limit: int = 10) -> list[str]:
    text = _visible_text(source)
    patterns = [
        r"Get\s+(?:[A-Z]{1,3}\$|[$€£])\s*[0-9][0-9,.]*(?:\.[0-9]+)?\s+coupon bundle!?",
        r"(?:[A-Z]{1,3}\$|[$€£])\s*[0-9][0-9,.]*(?:\.[0-9]+)?\s+coupon",
        r"[0-9]+(?:\.[0-9]+)?\s*%\s*off",
        r"free shipping",
        r"free gift",
        r"limited time",
        r"flash sale",
        r"\bspin\b",
    ]
    messages: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = _clean_text(match.group(0))
            if value and value.lower() not in {item.lower() for item in messages}:
                messages.append(value)
            if len(messages) >= limit:
                return messages
    return messages


def build_surface_snapshot(
    basket: BasketConfig,
    product: ProductConfig,
    fetch: RawFetchResult,
    collected_at: datetime,
) -> ProductSurfaceSnapshot:
    cards = extract_product_cards(product, fetch)
    snapshot_id = hashlib.sha256(f"{product.tracking_id}:surface:{collected_at.isoformat()}".encode("utf-8")).hexdigest()[:24]
    priced_cards = [card for card in cards if card.price is not None]
    stock_known = [card.stock_status for card in cards if card.stock_status != "unknown"]
    sample_cards = sorted(cards, key=lambda card: (card.price is None, card.price or 0))[:10]

    return ProductSurfaceSnapshot(
        snapshot_id=snapshot_id,
        page_tracking_id=product.tracking_id,
        url=fetch.final_url or product.url,
        category=product.category,
        region=basket.region,
        currency=basket.currency,
        collected_at=collected_at,
        card_count=len(cards),
        unique_product_count=len({card.product_id or card.detail_url or card.card_id for card in cards}),
        priced_card_count=len(priced_cards),
        median_price=median_or_none(card.price for card in priced_cards),
        median_list_price=median_or_none(card.list_price for card in cards),
        median_discount_pct=median_or_none(card.discount_pct for card in cards),
        discount_card_rate=rate(card.discount_pct is not None and card.discount_pct > 0 for card in cards),
        coupon_card_rate=rate(card.coupon_available for card in cards),
        free_shipping_rate=rate(card.free_shipping for card in cards),
        in_stock_rate=rate(status == "in_stock" for status in stock_known),
        stockout_card_rate=rate(status == "out_of_stock" for status in stock_known),
        median_sold_count_estimate=median_or_none(card.sold_count_estimate for card in cards),
        top_title_terms=_top_title_terms(cards),
        promo_messages=_promo_messages(fetch.html or ""),
        sample_products=[card.model_dump(mode="json") for card in sample_cards],
        cards=cards,
    )


def surface_metric_rows(surfaces: list[ProductSurfaceSnapshot]) -> list[dict[str, object]]:
    if not surfaces:
        return []

    latest_period = iso_week_period(max(surface.collected_at for surface in surfaces))
    region = surfaces[0].region
    cards = [card for surface in surfaces for card in surface.cards]
    priced_cards = [card for card in cards if card.price is not None]
    metrics = {
        "surface_page_count": float(len(surfaces)),
        "surface_card_count": float(len(cards)),
        "surface_priced_card_count": float(len(priced_cards)),
        "surface_unique_product_count": float(len({card.product_id or card.detail_url or card.card_id for card in cards})),
        "surface_median_price": median_or_none(card.price for card in priced_cards),
        "surface_median_list_price": median_or_none(card.list_price for card in cards),
        "surface_median_discount_pct": median_or_none(card.discount_pct for card in cards),
        "surface_discount_card_rate": rate(card.discount_pct is not None and card.discount_pct > 0 for card in cards),
        "surface_coupon_card_rate": rate(card.coupon_available for card in cards),
        "surface_free_shipping_rate": rate(card.free_shipping for card in cards),
        "surface_stockout_card_rate": rate(card.stock_status == "out_of_stock" for card in cards if card.stock_status != "unknown"),
    }
    return [
        {
            "market": region,
            "period": latest_period,
            "metric_name": metric_name,
            "value": value,
            "source_name": "temu_website_surface",
        }
        for metric_name, value in metrics.items()
    ]


def write_surface_cards_csv(path: str | Path, surfaces: list[ProductSurfaceSnapshot]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "collected_at",
        "region",
        "currency",
        "page_tracking_id",
        "category",
        "card_id",
        "product_id",
        "title",
        "price",
        "list_price",
        "discount_pct",
        "coupon_available",
        "coupon_value",
        "free_shipping",
        "stock_status",
        "sold_count_estimate",
        "rating",
        "review_count",
        "detail_url",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for surface in surfaces:
            for card in surface.cards:
                row = {
                    "collected_at": surface.collected_at.isoformat(),
                    "region": surface.region,
                    "currency": surface.currency,
                    "page_tracking_id": surface.page_tracking_id,
                    "category": surface.category,
                    **card.model_dump(mode="json"),
                }
                writer.writerow({field: row.get(field) for field in fieldnames})
