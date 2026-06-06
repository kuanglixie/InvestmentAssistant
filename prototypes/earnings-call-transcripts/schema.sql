CREATE TABLE IF NOT EXISTS earnings_transcripts (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    company_name TEXT,
    fiscal_year INTEGER,
    fiscal_quarter TEXT,
    quarter TEXT NOT NULL,
    call_date DATE,

    provider TEXT NOT NULL,
    source_url TEXT,
    source_type TEXT NOT NULL,

    transcript_text TEXT NOT NULL,
    raw_json TEXT,

    is_official INTEGER DEFAULT 0,
    is_machine_generated INTEGER DEFAULT 0,
    confidence TEXT,

    can_store INTEGER,
    can_redistribute INTEGER,
    license_notes TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_earnings_transcripts_ticker_quarter
ON earnings_transcripts (ticker, quarter);

CREATE TABLE IF NOT EXISTS transcript_source_candidates (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    quarter TEXT NOT NULL,
    provider TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_type TEXT NOT NULL,
    access_type TEXT,
    can_store INTEGER,
    can_redistribute INTEGER,
    license_notes TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transcript_source_candidates_ticker_quarter
ON transcript_source_candidates (ticker, quarter);
