"""CLI for running the PDD-first digital demand monitor."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .config import load_watchlist
from .connectors import (
    fetch_apple_rss_rank_snapshots,
    fetch_apple_lookup_snapshot,
    fetch_apple_review_snapshots,
    fetch_google_play_details_snapshot,
    fetch_google_play_visible_review_snapshots,
    fetch_tranco_web_ranks,
    load_ads_csv,
    load_app_snapshots_json,
    load_product_metrics_json,
    load_reviews_json,
    load_search_csv,
    load_web_csv,
)
from .metrics import build_metrics
from .models import DemandSignalPack
from .report import write_outputs
from .signal_builder import build_signals
from .storage import DemandStore


def project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists() and (parent / "src").exists():
            return parent
    raise RuntimeError("Could not locate investment-assistant project root")


def config_root() -> Path:
    return project_root() / "config" / "alternative_data" / "digital_demand_monitor"


def runtime_root() -> Path:
    return project_root() / "data" / "alternative_data" / "digital_demand_monitor"


def fixture_root() -> Path:
    return project_root() / "tests" / "alternative_data" / "digital_demand_monitor" / "fixtures"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watchlist", default=str(config_root() / "watchlists" / "pdd_temu.yaml"))
    parser.add_argument("--db", default=str(runtime_root() / "digital_demand_monitor.sqlite"))
    parser.add_argument("--output-dir", default=str(runtime_root() / "latest"))
    parser.add_argument("--app-snapshots-json")
    parser.add_argument("--reviews-json")
    parser.add_argument("--search-csv")
    parser.add_argument("--web-csv")
    parser.add_argument("--ads-csv")
    parser.add_argument("--product-metrics-json")
    parser.add_argument("--use-fixtures", action="store_true", help="Use bundled fixture data for a deterministic smoke run.")
    parser.add_argument("--live-apple-lookup", action="store_true", help="Fetch Apple lookup metadata for configured iOS apps.")
    parser.add_argument("--live-apple-rss-rank", action="store_true", help="Fetch Apple top-free RSS rank for configured iOS apps.")
    parser.add_argument("--live-apple-reviews", action="store_true", help="Fetch recent Apple App Store review RSS for configured iOS apps.")
    parser.add_argument("--apple-review-pages", type=int, default=1, help="Apple review RSS pages to fetch per app/market.")
    parser.add_argument("--live-google-play-details", action="store_true", help="Fetch Google Play public app details for configured Android apps.")
    parser.add_argument("--live-google-play-visible-reviews", action="store_true", help="Fetch visible Google Play public page review snippets for configured Android apps.")
    parser.add_argument("--live-tranco-web-rank", action="store_true", help="Fetch Tranco global domain ranks for configured domains.")
    parser.add_argument("--reset-db", action="store_true", help="Drop existing snapshot tables before ingesting this run.")
    parser.add_argument("--markets", help="Comma-separated market override, e.g. US,UK.")
    return parser.parse_args()


def run_pipeline(args: argparse.Namespace) -> dict[str, object]:
    watchlist = load_watchlist(args.watchlist)
    markets = args.markets.split(",") if args.markets else watchlist.markets

    if args.use_fixtures:
        fixture_dir = fixture_root()
        args.app_snapshots_json = args.app_snapshots_json or str(fixture_dir / "app_snapshots.json")
        args.reviews_json = args.reviews_json or str(fixture_dir / "reviews.json")
        args.search_csv = args.search_csv or str(fixture_dir / "search_trends.csv")
        args.web_csv = args.web_csv or str(fixture_dir / "web_ranks.csv")
        args.product_metrics_json = args.product_metrics_json or str(fixture_dir / "product_weekly_metrics.json")

    store = DemandStore(args.db)
    if args.reset_db or args.use_fixtures:
        store.reset_db()
    else:
        store.init_db()

    counts = {
        "app_snapshots": 0,
        "reviews": 0,
        "search_snapshots": 0,
        "web_snapshots": 0,
        "ad_snapshots": 0,
        "product_metrics": 0,
    }

    if args.app_snapshots_json:
        rows = load_app_snapshots_json(args.app_snapshots_json, watchlist)
        store.insert_app_snapshots(rows)
        counts["app_snapshots"] += len(rows)

    if args.live_apple_lookup:
        rows = []
        for brand in watchlist.brands:
            for app in brand.ios_apps:
                for market in (app.country_scope or markets):
                    if market in markets and app.app_id:
                        rows.append(fetch_apple_lookup_snapshot(watchlist, brand.brand_id, market, app.app_id))
        store.insert_app_snapshots(rows)
        counts["app_snapshots"] += len(rows)

    if args.live_apple_rss_rank:
        rows = fetch_apple_rss_rank_snapshots(watchlist, markets)
        store.insert_app_snapshots(rows)
        counts["app_snapshots"] += len(rows)

    if getattr(args, "live_apple_reviews", False):
        rows = []
        for brand in watchlist.brands:
            for app in brand.ios_apps:
                for market in (app.country_scope or markets):
                    if market in markets and app.app_id:
                        rows.extend(
                            fetch_apple_review_snapshots(
                                watchlist,
                                brand.brand_id,
                                market,
                                app.app_id,
                                pages=getattr(args, "apple_review_pages", 1),
                            )
                        )
        store.insert_reviews(rows)
        counts["reviews"] += len(rows)

    if getattr(args, "live_google_play_details", False):
        rows = []
        for brand in watchlist.brands:
            for app in brand.android_apps:
                for market in (app.country_scope or markets):
                    if market in markets and app.package_name:
                        rows.append(fetch_google_play_details_snapshot(watchlist, brand.brand_id, market, app.package_name))
        store.insert_app_snapshots(rows)
        counts["app_snapshots"] += len(rows)

    if getattr(args, "live_google_play_visible_reviews", False):
        rows = []
        for brand in watchlist.brands:
            for app in brand.android_apps:
                for market in (app.country_scope or markets):
                    if market in markets and app.package_name:
                        rows.extend(fetch_google_play_visible_review_snapshots(watchlist, brand.brand_id, market, app.package_name))
        store.insert_reviews(rows)
        counts["reviews"] += len(rows)

    if args.reviews_json:
        rows = load_reviews_json(args.reviews_json, watchlist)
        store.insert_reviews(rows)
        counts["reviews"] += len(rows)

    if args.search_csv:
        rows = load_search_csv(args.search_csv, watchlist)
        store.insert_search_snapshots(rows)
        counts["search_snapshots"] += len(rows)

    if args.web_csv:
        rows = load_web_csv(args.web_csv, watchlist)
        store.insert_web_snapshots(rows)
        counts["web_snapshots"] += len(rows)

    if getattr(args, "ads_csv", None):
        rows = load_ads_csv(args.ads_csv, watchlist)
        store.insert_ad_snapshots(rows)
        counts["ad_snapshots"] += len(rows)

    if args.live_tranco_web_rank:
        rows = fetch_tranco_web_ranks(watchlist, markets)
        store.insert_web_snapshots(rows)
        counts["web_snapshots"] += len(rows)

    if args.product_metrics_json:
        rows = load_product_metrics_json(args.product_metrics_json, watchlist)
        store.insert_product_metrics(rows)
        counts["product_metrics"] += len(rows)

    metrics = build_metrics(store, watchlist)
    signals = build_signals(metrics, watchlist)
    pack = DemandSignalPack(
        company_id=watchlist.company_id,
        ticker=watchlist.ticker,
        company_name=watchlist.company_name,
        primary_brand_id=watchlist.primary_brand_id,
        generated_at=datetime.now(timezone.utc),
        markets=markets,
        metrics=metrics,
        signals=signals,
    )
    write_outputs(args.output_dir, pack, watchlist)

    return {
        "status": "complete",
        "counts": counts,
        "metrics": len(metrics),
        "signals": len(signals),
        "output_dir": args.output_dir,
        "db": args.db,
    }


def main() -> int:
    result = run_pipeline(parse_args())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
