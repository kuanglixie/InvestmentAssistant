"""Low-cost connectors and fixture importers for demand monitoring."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import (
    AdSnapshot,
    AppSnapshot,
    ProductMetricSnapshot,
    ReviewSnapshot,
    SearchSnapshot,
    WatchlistConfig,
    WebSnapshot,
    parse_date,
    parse_datetime,
)
from .topic_classifier import classify_sentiment, classify_topic


USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"
APPLE_STOREFRONT_BY_MARKET = {
    "UK": "gb",
}
GOOGLE_PLAY_GL_BY_MARKET = {
    "UK": "GB",
}


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _brand_id_for_term(watchlist: WatchlistConfig, term: str) -> str:
    return watchlist.term_to_brand_id().get(term.strip().lower(), watchlist.primary_brand_id)


def _brand_id_for_domain(watchlist: WatchlistConfig, domain: str) -> str:
    clean = domain.strip().lower().removeprefix("www.")
    mapping = watchlist.domain_to_brand_id()
    if clean in mapping:
        return mapping[clean]
    for known_domain, brand_id in mapping.items():
        if clean.endswith(known_domain):
            return brand_id
    return watchlist.primary_brand_id


def _apple_storefront(market: str) -> str:
    return APPLE_STOREFRONT_BY_MARKET.get(market.upper(), market.lower())


def _google_play_gl(market: str) -> str:
    return GOOGLE_PLAY_GL_BY_MARKET.get(market.upper(), market.upper())


def _compact_page_text(html_text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", html_text))).strip()


def _parse_human_count(value: str | None) -> int | None:
    if not value:
        return None
    text = value.strip().replace(",", "")
    match = re.match(r"^([0-9]+(?:\.[0-9]+)?)([KMB])?\+?$", text, flags=re.IGNORECASE)
    if not match:
        return None
    number = float(match.group(1))
    suffix = (match.group(2) or "").upper()
    multiplier = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[suffix]
    return int(number * multiplier)


def load_app_snapshots_json(path: str | Path, watchlist: WatchlistConfig) -> list[AppSnapshot]:
    rows = _read_json(path)
    output: list[AppSnapshot] = []
    for row in rows:
        output.append(
            AppSnapshot(
                company_id=watchlist.company_id,
                ticker=watchlist.ticker,
                brand_id=row.get("brand_id") or watchlist.primary_brand_id,
                market=row.get("market", "US"),
                platform=row.get("platform", "ios"),
                app_id=row.get("app_id") or row.get("package_name") or "",
                collected_at=parse_datetime(row.get("collected_at")),
                rank=_to_float(row.get("rank")),
                rating=_to_float(row.get("rating")),
                rating_count=_to_int(row.get("rating_count")),
                review_count=_to_int(row.get("review_count")),
                version=row.get("version"),
                updated_at=parse_datetime(row.get("updated_at"), default=None) if row.get("updated_at") else None,
                source_name=row.get("source_name", "fixture_json"),
                raw_payload_json=row,
            )
        )
    return output


def load_reviews_json(path: str | Path, watchlist: WatchlistConfig) -> list[ReviewSnapshot]:
    rows = _read_json(path)
    output: list[ReviewSnapshot] = []
    for row in rows:
        rating = _to_float(row.get("rating"))
        text = str(row.get("text") or "")
        topic = row.get("topic") or classify_topic(" ".join([str(row.get("title") or ""), text]))
        sentiment = row.get("sentiment") or classify_sentiment(text, rating)
        output.append(
            ReviewSnapshot(
                company_id=watchlist.company_id,
                ticker=watchlist.ticker,
                brand_id=row.get("brand_id") or watchlist.primary_brand_id,
                market=row.get("market", "US"),
                platform=row.get("platform", "ios"),
                review_id=str(row.get("review_id") or f"{row.get('brand_id', watchlist.primary_brand_id)}-{len(output) + 1}"),
                collected_at=parse_datetime(row.get("collected_at")),
                rating=rating,
                title=row.get("title"),
                text=text,
                review_date=parse_datetime(row.get("review_date"), default=None) if row.get("review_date") else None,
                version=row.get("version"),
                topic=topic,
                sentiment=sentiment,
                source_name=row.get("source_name", "fixture_json"),
                raw_payload_json=row,
            )
        )
    return output


def load_search_csv(path: str | Path, watchlist: WatchlistConfig) -> list[SearchSnapshot]:
    output: list[SearchSnapshot] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            term = row["term"]
            output.append(
                SearchSnapshot(
                    company_id=watchlist.company_id,
                    ticker=watchlist.ticker,
                    brand_id=row.get("brand_id") or _brand_id_for_term(watchlist, term),
                    market=row.get("market", "US"),
                    term=term,
                    date=parse_date(row.get("date")),
                    value=float(row["value"]),
                    source_name=row.get("source_name", "manual_csv"),
                )
            )
    return output


def load_web_csv(path: str | Path, watchlist: WatchlistConfig) -> list[WebSnapshot]:
    output: list[WebSnapshot] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            domain = row["domain"]
            output.append(
                WebSnapshot(
                    company_id=watchlist.company_id,
                    ticker=watchlist.ticker,
                    brand_id=row.get("brand_id") or _brand_id_for_domain(watchlist, domain),
                    market=row.get("market", "US"),
                    domain=domain,
                    collected_at=parse_datetime(row.get("collected_at")),
                    rank=_to_float(row.get("rank")),
                    source_name=row.get("source_name", "manual_csv"),
                )
            )
    return output


def load_ads_csv(path: str | Path, watchlist: WatchlistConfig) -> list[AdSnapshot]:
    output: list[AdSnapshot] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            domain = row.get("domain") or ""
            output.append(
                AdSnapshot(
                    company_id=watchlist.company_id,
                    ticker=watchlist.ticker,
                    brand_id=row.get("brand_id") or _brand_id_for_domain(watchlist, domain),
                    market=row.get("market", "US"),
                    source_name=row.get("source_name", "manual_ads_csv"),
                    advertiser_name=row.get("advertiser_name") or "",
                    domain=domain,
                    collected_at=parse_datetime(row.get("collected_at")),
                    ad_count_lower_bound=_to_int(row.get("ad_count_lower_bound")),
                    ad_count_label=row.get("ad_count_label") or None,
                    visible_ad_cards=_to_int(row.get("visible_ad_cards")),
                    visible_video_cards=_to_int(row.get("visible_video_cards")),
                    source_url=row.get("source_url") or None,
                    raw_payload_json=row,
                )
            )
    return output


def load_product_metrics_json(path: str | Path, watchlist: WatchlistConfig, market: str = "US") -> list[ProductMetricSnapshot]:
    rows = _read_json(path)
    output: list[ProductMetricSnapshot] = []
    for row in rows:
        output.append(
            ProductMetricSnapshot(
                company_id=watchlist.company_id,
                ticker=watchlist.ticker,
                brand_id=watchlist.primary_brand_id,
                market=row.get("market", market),
                period=row.get("period", "unknown"),
                metric_name=row["metric_name"],
                value=_to_float(row.get("value")),
                change_1w=_to_float(row.get("change_1w")),
                change_4w=_to_float(row.get("change_4w")),
                source_path=str(path),
            )
        )
    return output


def fetch_apple_review_snapshots(
    watchlist: WatchlistConfig,
    brand_id: str,
    market: str,
    app_id: str,
    pages: int = 1,
    timeout: int = 20,
) -> list[ReviewSnapshot]:
    output: list[ReviewSnapshot] = []
    storefront = _apple_storefront(market)
    collected_at = datetime.now(timezone.utc)
    for page in range(1, pages + 1):
        url = f"https://itunes.apple.com/{storefront}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            continue
        entries = (payload.get("feed") or {}).get("entry") or []
        for entry in entries:
            review_id = str((entry.get("id") or {}).get("label") or "")
            text = str((entry.get("content") or {}).get("label") or "")
            if not review_id or not text:
                continue
            title = (entry.get("title") or {}).get("label")
            rating = _to_float((entry.get("im:rating") or {}).get("label"))
            joined = " ".join([str(title or ""), text])
            output.append(
                ReviewSnapshot(
                    company_id=watchlist.company_id,
                    ticker=watchlist.ticker,
                    brand_id=brand_id,
                    market=market,
                    platform="ios",
                    review_id=review_id,
                    collected_at=collected_at,
                    rating=rating,
                    title=title,
                    text=text,
                    review_date=parse_datetime((entry.get("updated") or {}).get("label"), default=None),
                    version=(entry.get("im:version") or {}).get("label"),
                    topic=classify_topic(joined),
                    sentiment=classify_sentiment(joined, rating),
                    source_name="apple_review_rss",
                    raw_payload_json={
                        "page": page,
                        "storefront": storefront,
                        "author": ((entry.get("author") or {}).get("name") or {}).get("label"),
                        "vote_sum": (entry.get("im:voteSum") or {}).get("label"),
                        "vote_count": (entry.get("im:voteCount") or {}).get("label"),
                        "source_url": url,
                    },
                )
            )
    return output


def fetch_google_play_visible_review_snapshots(
    watchlist: WatchlistConfig,
    brand_id: str,
    market: str,
    package_name: str,
    timeout: int = 20,
) -> list[ReviewSnapshot]:
    gl = _google_play_gl(market)
    params = urllib.parse.urlencode({"id": package_name, "hl": "en_US", "gl": gl})
    url = f"https://play.google.com/store/apps/details?{params}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    collected_at = datetime.now(timezone.utc)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            page = response.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    text = _compact_page_text(page)
    start = text.find("Ratings and reviews")
    end = text.find("See all reviews", start)
    if start == -1 or end == -1:
        return []
    review_block = text[start:end]
    pattern = re.compile(
        r"(?:Show review history\s+)?([A-Z][a-z]{2,9}\s+\d{1,2},\s+\d{4})\s+(.+?)(?=\s+(?:\d+\s+people found this review helpful|Did you find this helpful\?|[A-Z][A-Za-z .'-]+\s+more_vert\s+Flag inappropriate|$))"
    )
    output: list[ReviewSnapshot] = []
    for index, match in enumerate(pattern.finditer(review_block), start=1):
        date_text = match.group(1)
        body = match.group(2).strip()
        if len(body) < 20:
            continue
        try:
            review_date = datetime.strptime(date_text, "%B %d, %Y").replace(tzinfo=timezone.utc)
        except ValueError:
            review_date = None
        review_hash = hashlib.sha1(body.encode("utf-8")).hexdigest()[:16]
        review_id = f"{package_name}:{gl}:{date_text}:{index}:{review_hash}"
        output.append(
            ReviewSnapshot(
                company_id=watchlist.company_id,
                ticker=watchlist.ticker,
                brand_id=brand_id,
                market=market,
                platform="android",
                review_id=review_id,
                collected_at=collected_at,
                rating=None,
                title=None,
                text=body,
                review_date=review_date,
                version=None,
                topic=classify_topic(body),
                sentiment=classify_sentiment(body),
                source_name="google_play_visible_reviews",
                raw_payload_json={
                    "gl": gl,
                    "source_url": url,
                    "parser_note": "Visible public page review snippets only; not a complete review feed.",
                },
            )
        )
    return output


def fetch_apple_lookup_snapshot(
    watchlist: WatchlistConfig,
    brand_id: str,
    market: str,
    app_id: str,
    timeout: int = 20,
) -> AppSnapshot:
    params = urllib.parse.urlencode({"id": app_id, "country": _apple_storefront(market)})
    url = f"https://itunes.apple.com/lookup?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    collected_at = datetime.now(timezone.utc)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return AppSnapshot(
            company_id=watchlist.company_id,
            ticker=watchlist.ticker,
            brand_id=brand_id,
            market=market,
            platform="ios",
            app_id=app_id,
            collected_at=collected_at,
            source_name="apple_lookup",
            fetch_success=False,
            fetch_error=str(exc),
        )
    results = payload.get("results") or []
    item = results[0] if results else {}
    return AppSnapshot(
        company_id=watchlist.company_id,
        ticker=watchlist.ticker,
        brand_id=brand_id,
        market=market,
        platform="ios",
        app_id=app_id,
        collected_at=collected_at,
        rank=None,
        rating=_to_float(item.get("averageUserRating")),
        rating_count=_to_int(item.get("userRatingCount")),
        review_count=_to_int(item.get("userRatingCount")),
        download_count_lower_bound=None,
        version=item.get("version"),
        updated_at=parse_datetime(item.get("currentVersionReleaseDate"), default=None) if item.get("currentVersionReleaseDate") else None,
        source_name="apple_lookup",
        raw_payload_json=item,
    )


def fetch_apple_rss_rank_snapshots(
    watchlist: WatchlistConfig,
    markets: list[str],
    limit: int = 100,
    timeout: int = 20,
) -> list[AppSnapshot]:
    output: list[AppSnapshot] = []
    for market in markets:
        country = _apple_storefront(market)
        url = f"https://rss.marketingtools.apple.com/api/v2/{country}/apps/top-free/{limit}/apps.json"
        collected_at = datetime.now(timezone.utc)
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            results = (payload.get("feed") or {}).get("results") or []
            rank_by_id = {str(item.get("id")): index for index, item in enumerate(results, start=1)}
            name_by_id = {str(item.get("id")): item.get("name") for item in results}
            updated = (payload.get("feed") or {}).get("updated")
        except Exception as exc:
            for brand in watchlist.brands:
                for app in brand.ios_apps:
                    if app.app_id and market in (app.country_scope or markets):
                        output.append(
                            AppSnapshot(
                                company_id=watchlist.company_id,
                                ticker=watchlist.ticker,
                                brand_id=brand.brand_id,
                                market=market,
                                platform="ios",
                                app_id=app.app_id,
                                collected_at=collected_at,
                                source_name="apple_rss_top_free",
                                fetch_success=False,
                                fetch_error=str(exc),
                            )
                        )
            continue

        for brand in watchlist.brands:
            for app in brand.ios_apps:
                if not app.app_id or market not in (app.country_scope or markets):
                    continue
                app_id = str(app.app_id)
                rank = rank_by_id.get(app_id)
                output.append(
                    AppSnapshot(
                        company_id=watchlist.company_id,
                        ticker=watchlist.ticker,
                        brand_id=brand.brand_id,
                        market=market,
                        platform="ios",
                        app_id=app_id,
                        collected_at=collected_at,
                        rank=float(rank) if rank is not None else None,
                        source_name="apple_rss_top_free",
                        raw_payload_json={
                            "rank_limit": limit,
                            "feed_updated": updated,
                            "ranked": rank is not None,
                            "ranked_name": name_by_id.get(app_id),
                            "feed_url": url,
                        },
                    )
                )
    return output


def fetch_google_play_details_snapshot(
    watchlist: WatchlistConfig,
    brand_id: str,
    market: str,
    package_name: str,
    timeout: int = 20,
) -> AppSnapshot:
    gl = _google_play_gl(market)
    params = urllib.parse.urlencode({"id": package_name, "hl": "en_US", "gl": gl})
    url = f"https://play.google.com/store/apps/details?{params}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    collected_at = datetime.now(timezone.utc)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            page = response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return AppSnapshot(
            company_id=watchlist.company_id,
            ticker=watchlist.ticker,
            brand_id=brand_id,
            market=market,
            platform="android",
            app_id=package_name,
            collected_at=collected_at,
            source_name="google_play_details",
            fetch_success=False,
            fetch_error=str(exc),
        )

    text = _compact_page_text(page)
    rating_match = re.search(r"Rated\s+([0-9]+(?:\.[0-9]+)?)", text)
    if not rating_match:
        rating_match = re.search(r"\b([0-9]+(?:\.[0-9]+)?)\s+star\s+[0-9]+(?:\.[0-9]+)?[KMB]?\s+reviews", text, flags=re.IGNORECASE)
    reviews_match = re.search(r"([0-9]+(?:\.[0-9]+)?[KMB]?)\s+reviews", text, flags=re.IGNORECASE)
    downloads_match = re.search(r"([0-9]+(?:\.[0-9]+)?[KMB]?\+?)\s+Downloads", text, flags=re.IGNORECASE)
    updated_match = re.search(r"Updated on\s+([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})", text)
    updated_at = None
    if updated_match:
        try:
            updated_at = datetime.strptime(updated_match.group(1), "%b %d, %Y").replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                updated_at = datetime.strptime(updated_match.group(1), "%B %d, %Y").replace(tzinfo=timezone.utc)
            except ValueError:
                updated_at = None

    reviews = _parse_human_count(reviews_match.group(1) if reviews_match else None)
    downloads = _parse_human_count(downloads_match.group(1) if downloads_match else None)
    return AppSnapshot(
        company_id=watchlist.company_id,
        ticker=watchlist.ticker,
        brand_id=brand_id,
        market=market,
        platform="android",
        app_id=package_name,
        collected_at=collected_at,
        rating=_to_float(rating_match.group(1)) if rating_match else None,
        rating_count=reviews,
        review_count=reviews,
        download_count_lower_bound=downloads,
        updated_at=updated_at,
        source_name="google_play_details",
        raw_payload_json={
            "url": url,
            "gl": gl,
            "rating_text": rating_match.group(0) if rating_match else None,
            "reviews_text": reviews_match.group(0) if reviews_match else None,
            "downloads_text": downloads_match.group(0) if downloads_match else None,
            "updated_text": updated_match.group(0) if updated_match else None,
        },
    )


def fetch_tranco_web_ranks(
    watchlist: WatchlistConfig,
    markets: list[str],
    timeout: int = 30,
) -> list[WebSnapshot]:
    domains = sorted({domain.lower().removeprefix("www.") for brand in watchlist.brands for domain in brand.domains})
    ranks: dict[str, float] = {}
    url = "https://tranco-list.eu/top-1m.csv.zip"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    collected_at = datetime.now(timezone.utc)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            with archive.open("top-1m.csv") as handle:
                for raw_line in handle:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    rank_text, domain = line.split(",", 1)
                    domain = domain.lower().removeprefix("www.")
                    if domain in domains:
                        ranks[domain] = float(rank_text)
                        if len(ranks) == len(domains):
                            break
    except Exception:
        ranks = {}

    output: list[WebSnapshot] = []
    for brand in watchlist.brands:
        for domain in brand.domains:
            clean = domain.lower().removeprefix("www.")
            for market in markets:
                output.append(
                    WebSnapshot(
                        company_id=watchlist.company_id,
                        ticker=watchlist.ticker,
                        brand_id=brand.brand_id,
                        market=market,
                        domain=clean,
                        collected_at=collected_at,
                        rank=ranks.get(clean),
                        source_name="tranco_global_top_1m",
                    )
                )
    return output


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(float(value))
