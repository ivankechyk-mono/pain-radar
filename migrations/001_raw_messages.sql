CREATE TABLE IF NOT EXISTS raw_messages (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source        TEXT NOT NULL,
    source_url    TEXT,
    content_hash  TEXT NOT NULL UNIQUE,
    title         TEXT,
    body          TEXT NOT NULL,
    author        TEXT,
    published_at  TIMESTAMPTZ,
    collected_at  TIMESTAMPTZ DEFAULT NOW(),
    is_classified BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_raw_messages_source        ON raw_messages(source);
CREATE INDEX IF NOT EXISTS idx_raw_messages_is_classified ON raw_messages(is_classified);
CREATE INDEX IF NOT EXISTS idx_raw_messages_published_at  ON raw_messages(published_at DESC);
