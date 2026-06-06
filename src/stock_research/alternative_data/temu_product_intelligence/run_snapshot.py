"""CLI entrypoint for a Temu fixed-basket snapshot run."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .aggregator import aggregate_weekly
from .config import load_basket_config, load_crawler_settings
from .exporter import write_json
from .fetcher import TemuPageFetcher
from .commerce_parser import GenericCommerceProductParser
from .models import ProductSnapshot, RawFetchResult
from .parser import TemuProductParser
from .signal_builder import build_signal_pack, build_unit_economics_pack
from .storage import ProductStore
from .surface import build_surface_snapshot, surface_metric_rows, write_surface_cards_csv


def project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists() and (parent / "src").exists():
            return parent
    raise RuntimeError("Could not locate investment-assistant project root")


def config_root() -> Path:
    return project_root() / "config" / "alternative_data" / "temu_product_intelligence"


def runtime_root() -> Path:
    return project_root() / "data" / "alternative_data" / "temu_product_intelligence"


def fixture_root() -> Path:
    return project_root() / "tests" / "alternative_data" / "temu_product_intelligence" / "fixtures"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(config_root() / "tracked_products.yaml"))
    parser.add_argument("--crawler-settings", default=str(config_root() / "crawler_settings.yaml"))
    parser.add_argument("--db", default=str(runtime_root() / "temu_product_intelligence.sqlite"))
    parser.add_argument("--output-dir", default=str(runtime_root() / "latest"))
    parser.add_argument("--artifact-dir", default=str(runtime_root() / "artifacts"))
    parser.add_argument("--fixture-dir", default=str(fixture_root()))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--collected-at", help="ISO timestamp override for repeatable tests.")
    parser.add_argument("--skip-fetch", action="store_true", help="Only aggregate and export existing snapshots.")
    return parser.parse_args()


def _parse_collected_at(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _failed_snapshot(product, fetch: RawFetchResult, collected_at: datetime) -> ProductSnapshot:
    return ProductSnapshot(
        snapshot_id=f"failed-{product.tracking_id}-{int(collected_at.timestamp())}",
        product_tracking_id=product.tracking_id,
        url=product.url,
        category=product.category,
        collected_at=collected_at,
        raw_payload_json={"fetch": fetch.model_dump(mode="json", exclude={"html"})},
        parse_success=False,
        parse_error=fetch.fetch_error or "fetch failed",
    )


def _parser_for_product(basket, product):
    url = product.url.lower()
    if basket.brand.lower() == "temu" or "temu." in url:
        return TemuProductParser()
    return GenericCommerceProductParser()


def main() -> int:
    args = parse_args()
    basket = load_basket_config(args.config)
    settings = load_crawler_settings(args.crawler_settings)
    products = [product for product in basket.products if product.active]
    if args.limit:
        products = products[: args.limit]

    store = ProductStore(args.db)
    store.init_db()
    store.upsert_products(basket)

    collected_at = _parse_collected_at(args.collected_at) or datetime.now(timezone.utc)
    snapshots: list[ProductSnapshot] = []
    surface_snapshots = []

    if not args.skip_fetch:
        with TemuPageFetcher(settings, Path(args.artifact_dir), Path(args.fixture_dir)) as fetcher:
            for index, product in enumerate(products, start=1):
                print(f"[{index}/{len(products)}] fetching {product.tracking_id} ({product.category})")
                fetch = fetcher.fetch(product)
                if fetch.fetch_success:
                    surface_snapshots.append(build_surface_snapshot(basket, product, fetch, collected_at=collected_at))
                    snapshot = _parser_for_product(basket, product).parse(product, fetch, collected_at=collected_at)
                else:
                    snapshot = _failed_snapshot(product, fetch, collected_at)
                store.insert_snapshot(snapshot)
                snapshots.append(snapshot)
                status = "ok" if snapshot.parse_success else f"parse_failed: {snapshot.parse_error}"
                print(f"[{index}/{len(products)}] stored {product.tracking_id}: {status}")

    metrics = aggregate_weekly(store, basket.company, basket.brand)
    store.insert_weekly_metrics(metrics)
    period = max((metric.period for metric in metrics), default="unknown")
    signal_pack = build_signal_pack(metrics, basket.company, basket.brand, period=period)
    unit_economics_pack = build_unit_economics_pack(metrics, basket.company, basket.brand, period=period)

    output_dir = Path(args.output_dir)
    write_json(output_dir / "weekly_metrics.json", [metric.model_dump(mode="json") for metric in metrics if metric.period == period])
    write_json(output_dir / "product_signal_pack.json", signal_pack)
    write_json(output_dir / "unit_economics_pack.json", unit_economics_pack)
    write_json(output_dir / "latest_snapshots.json", [snapshot.model_dump(mode="json") for snapshot in snapshots])
    write_json(output_dir / "surface_snapshots.json", [snapshot.model_dump(mode="json") for snapshot in surface_snapshots])
    write_json(output_dir / "surface_metrics.json", surface_metric_rows(surface_snapshots))
    write_surface_cards_csv(output_dir / "surface_cards.csv", surface_snapshots)

    print(
        json.dumps(
            {
                "status": "complete",
                "products_in_config": len(basket.products),
                "products_processed": len(products) if not args.skip_fetch else 0,
                "snapshots_written_this_run": len(snapshots),
                "snapshots_in_db": store.count_snapshots(),
                "surface_pages_written_this_run": len(surface_snapshots),
                "surface_cards_written_this_run": sum(snapshot.card_count for snapshot in surface_snapshots),
                "period": period,
                "signals": len(signal_pack.product_signals),
                "output_dir": str(output_dir),
                "db": str(args.db),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
