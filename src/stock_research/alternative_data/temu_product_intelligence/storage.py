"""SQLite storage for product masters, snapshots, and weekly signals."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .models import BasketConfig, ProductConfig, ProductSnapshot, WeeklyMetric


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS product_master (
    product_tracking_id TEXT PRIMARY KEY,
    company TEXT,
    brand TEXT,
    category TEXT,
    url TEXT,
    first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
    active INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS product_snapshot (
    snapshot_id TEXT PRIMARY KEY,
    product_tracking_id TEXT,
    collected_at TEXT,
    title TEXT,
    price REAL,
    list_price REAL,
    discount_pct REAL,
    coupon_available INTEGER,
    coupon_value REAL,
    rating REAL,
    review_count INTEGER,
    sold_count_text TEXT,
    sold_count_estimate INTEGER,
    delivery_min_days INTEGER,
    delivery_max_days INTEGER,
    shipping_fee REAL,
    stock_status TEXT,
    seller_name TEXT,
    raw_payload_json TEXT,
    parse_success INTEGER,
    parse_error TEXT,
    FOREIGN KEY(product_tracking_id) REFERENCES product_master(product_tracking_id)
);

CREATE TABLE IF NOT EXISTS weekly_product_signal (
    company TEXT,
    brand TEXT,
    period TEXT,
    category TEXT,
    metric_name TEXT,
    value REAL,
    change_1w REAL,
    change_4w REAL,
    trend_direction TEXT,
    confidence TEXT,
    PRIMARY KEY(company, brand, period, category, metric_name)
);
"""


class ProductStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def upsert_products(self, basket: BasketConfig) -> None:
        with self.connect() as conn:
            for product in basket.products:
                self.upsert_product(conn, basket, product)

    def upsert_product(self, conn: sqlite3.Connection, basket: BasketConfig, product: ProductConfig) -> None:
        conn.execute(
            """
            INSERT INTO product_master(product_tracking_id, company, brand, category, url, active, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_tracking_id) DO UPDATE SET
                company=excluded.company,
                brand=excluded.brand,
                category=excluded.category,
                url=excluded.url,
                active=excluded.active,
                notes=excluded.notes
            """,
            (
                product.tracking_id,
                basket.company,
                basket.brand,
                product.category,
                product.url,
                1 if product.active else 0,
                product.notes,
            ),
        )

    def insert_snapshot(self, snapshot: ProductSnapshot) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO product_snapshot(
                    snapshot_id, product_tracking_id, collected_at, title, price, list_price, discount_pct,
                    coupon_available, coupon_value, rating, review_count, sold_count_text, sold_count_estimate,
                    delivery_min_days, delivery_max_days, shipping_fee, stock_status, seller_name,
                    raw_payload_json, parse_success, parse_error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.snapshot_id,
                    snapshot.product_tracking_id,
                    snapshot.collected_at.isoformat(),
                    snapshot.title,
                    snapshot.price,
                    snapshot.list_price,
                    snapshot.discount_pct,
                    1 if snapshot.coupon_available else 0,
                    snapshot.coupon_value,
                    snapshot.rating,
                    snapshot.review_count,
                    snapshot.sold_count_text,
                    snapshot.sold_count_estimate,
                    snapshot.delivery_min_days,
                    snapshot.delivery_max_days,
                    snapshot.shipping_fee,
                    snapshot.stock_status,
                    snapshot.seller_name,
                    json.dumps(snapshot.raw_payload_json, ensure_ascii=False),
                    1 if snapshot.parse_success else 0,
                    snapshot.parse_error,
                ),
            )

    def insert_weekly_metrics(self, metrics: Iterable[WeeklyMetric]) -> None:
        with self.connect() as conn:
            for metric in metrics:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO weekly_product_signal(
                        company, brand, period, category, metric_name, value,
                        change_1w, change_4w, trend_direction, confidence
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        metric.company,
                        metric.brand,
                        metric.period,
                        metric.category,
                        metric.metric_name,
                        metric.value,
                        metric.change_1w,
                        metric.change_4w,
                        metric.trend_direction,
                        metric.confidence,
                    ),
                )

    def snapshot_rows(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT m.company, m.brand, m.category, s.*
                    FROM product_snapshot s
                    JOIN product_master m ON m.product_tracking_id = s.product_tracking_id
                    ORDER BY s.collected_at
                    """
                )
            )

    def count_snapshots(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM product_snapshot").fetchone()[0])
