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
