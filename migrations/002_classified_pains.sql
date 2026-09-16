CREATE TABLE IF NOT EXISTS classified_pains (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_message_id   UUID NOT NULL REFERENCES raw_messages(id),
    is_pain          BOOLEAN NOT NULL,
    pain_category    TEXT,
    pain_description TEXT,
    target           TEXT,
    intensity        SMALLINT CHECK (intensity BETWEEN 1 AND 5),
    classified_at    TIMESTAMPTZ DEFAULT NOW(),
    model_used       TEXT DEFAULT 'claude-haiku-4-5-20251001'
);

CREATE INDEX IF NOT EXISTS idx_classified_pains_category  ON classified_pains(pain_category);
CREATE INDEX IF NOT EXISTS idx_classified_pains_is_pain   ON classified_pains(is_pain);
CREATE INDEX IF NOT EXISTS idx_classified_pains_intensity ON classified_pains(intensity DESC);
