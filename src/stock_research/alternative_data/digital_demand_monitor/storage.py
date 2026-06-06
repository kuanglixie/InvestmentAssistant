"""SQLite storage for demand monitor snapshots."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .models import AdSnapshot, AppSnapshot, ProductMetricSnapshot, ReviewSnapshot, SearchSnapshot, WebSnapshot, to_jsonable


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_snapshot (
    company_id TEXT,
    ticker TEXT,
    brand_id TEXT,
    market TEXT,
    platform TEXT,
    app_id TEXT,
    collected_at TEXT,
    rank REAL,
    rating REAL,
    rating_count INTEGER,
    review_count INTEGER,
    download_count_lower_bound INTEGER,
    version TEXT,
    updated_at TEXT,
    source_name TEXT,
    raw_payload_json TEXT,
    fetch_success INTEGER,
    fetch_error TEXT
);

CREATE TABLE IF NOT EXISTS review_snapshot (
    company_id TEXT,
    ticker TEXT,
    brand_id TEXT,
    market TEXT,
    platform TEXT,
    review_id TEXT,
    collected_at TEXT,
    rating REAL,
    title TEXT,
    text TEXT,
    review_date TEXT,
    version TEXT,
    topic TEXT,
    sentiment TEXT,
    source_name TEXT,
    raw_payload_json TEXT,
    PRIMARY KEY(company_id, brand_id, platform, review_id)
);

CREATE TABLE IF NOT EXISTS search_snapshot (
    company_id TEXT,
    ticker TEXT,
    brand_id TEXT,
    market TEXT,
    term TEXT,
    date TEXT,
    value REAL,
    source_name TEXT
);

CREATE TABLE IF NOT EXISTS web_snapshot (
    company_id TEXT,
    ticker TEXT,
    brand_id TEXT,
    market TEXT,
    domain TEXT,
    collected_at TEXT,
    rank REAL,
    source_name TEXT
);

CREATE TABLE IF NOT EXISTS ad_snapshot (
    company_id TEXT,
    ticker TEXT,
    brand_id TEXT,
    market TEXT,
    source_name TEXT,
    advertiser_name TEXT,
    domain TEXT,
    collected_at TEXT,
    ad_count_lower_bound INTEGER,
    ad_count_label TEXT,
    visible_ad_cards INTEGER,
    visible_video_cards INTEGER,
    source_url TEXT,
    raw_payload_json TEXT
);

CREATE TABLE IF NOT EXISTS product_metric_snapshot (
    company_id TEXT,
    ticker TEXT,
    brand_id TEXT,
    market TEXT,
    period TEXT,
    metric_name TEXT,
    value REAL,
    change_1w REAL,
    change_4w REAL,
    source_path TEXT
);
"""


class DemandStore:
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
            columns = {row[1] for row in conn.execute("PRAGMA table_info(app_snapshot)")}
            if "download_count_lower_bound" not in columns:
                conn.execute("ALTER TABLE app_snapshot ADD COLUMN download_count_lower_bound INTEGER")

    def reset_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                DROP TABLE IF EXISTS app_snapshot;
                DROP TABLE IF EXISTS review_snapshot;
                DROP TABLE IF EXISTS search_snapshot;
                DROP TABLE IF EXISTS web_snapshot;
                DROP TABLE IF EXISTS ad_snapshot;
                DROP TABLE IF EXISTS product_metric_snapshot;
                """
            )
        self.init_db()

    def insert_app_snapshots(self, snapshots: Iterable[AppSnapshot]) -> None:
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO app_snapshot (
                    company_id, ticker, brand_id, market, platform, app_id, collected_at,
                    rank, rating, rating_count, review_count, download_count_lower_bound,
                    version, updated_at, source_name, raw_payload_json, fetch_success, fetch_error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row.company_id,
                        row.ticker,
                        row.brand_id,
                        row.market,
                        row.platform,
                        row.app_id,
                        row.collected_at.isoformat(),
                        row.rank,
                        row.rating,
                        row.rating_count,
                        row.review_count,
                        row.download_count_lower_bound,
                        row.version,
                        row.updated_at.isoformat() if row.updated_at else None,
                        row.source_name,
                        json.dumps(to_jsonable(row.raw_payload_json), ensure_ascii=False),
                        1 if row.fetch_success else 0,
                        row.fetch_error,
                    )
                    for row in snapshots
                ],
            )

    def insert_ad_snapshots(self, snapshots: Iterable[AdSnapshot]) -> None:
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO ad_snapshot VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row.company_id,
                        row.ticker,
                        row.brand_id,
                        row.market,
                        row.source_name,
                        row.advertiser_name,
                        row.domain,
                        row.collected_at.isoformat(),
                        row.ad_count_lower_bound,
                        row.ad_count_label,
                        row.visible_ad_cards,
                        row.visible_video_cards,
                        row.source_url,
                        json.dumps(to_jsonable(row.raw_payload_json), ensure_ascii=False),
                    )
                    for row in snapshots
                ],
            )

    def insert_reviews(self, reviews: Iterable[ReviewSnapshot]) -> None:
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO review_snapshot VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row.company_id,
                        row.ticker,
                        row.brand_id,
                        row.market,
                        row.platform,
                        row.review_id,
                        row.collected_at.isoformat(),
                        row.rating,
                        row.title,
                        row.text,
                        row.review_date.isoformat() if row.review_date else None,
                        row.version,
                        row.topic,
                        row.sentiment,
                        row.source_name,
                        json.dumps(to_jsonable(row.raw_payload_json), ensure_ascii=False),
                    )
                    for row in reviews
                ],
            )

    def insert_search_snapshots(self, snapshots: Iterable[SearchSnapshot]) -> None:
        with self.connect() as conn:
            conn.executemany(
                "INSERT INTO search_snapshot VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row.company_id,
                        row.ticker,
                        row.brand_id,
                        row.market,
                        row.term,
                        row.date.isoformat(),
                        row.value,
                        row.source_name,
                    )
                    for row in snapshots
                ],
            )

    def insert_web_snapshots(self, snapshots: Iterable[WebSnapshot]) -> None:
        with self.connect() as conn:
            conn.executemany(
                "INSERT INTO web_snapshot VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row.company_id,
                        row.ticker,
                        row.brand_id,
                        row.market,
                        row.domain,
                        row.collected_at.isoformat(),
                        row.rank,
                        row.source_name,
                    )
                    for row in snapshots
                ],
            )

    def insert_product_metrics(self, snapshots: Iterable[ProductMetricSnapshot]) -> None:
        with self.connect() as conn:
            conn.executemany(
                "INSERT INTO product_metric_snapshot VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        row.company_id,
                        row.ticker,
                        row.brand_id,
                        row.market,
                        row.period,
                        row.metric_name,
                        row.value,
                        row.change_1w,
                        row.change_4w,
                        row.source_path,
                    )
                    for row in snapshots
                ],
            )

    def rows(self, table: str) -> list[sqlite3.Row]:
        if table not in {"app_snapshot", "review_snapshot", "search_snapshot", "web_snapshot", "ad_snapshot", "product_metric_snapshot"}:
            raise ValueError(f"Unsupported table: {table}")
        with self.connect() as conn:
            return list(conn.execute(f"SELECT * FROM {table}"))
