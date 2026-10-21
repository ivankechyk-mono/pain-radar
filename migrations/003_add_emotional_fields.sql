-- emotional_layer, quote, competitor_name були додані вручну в Supabase prod і
-- локальну БД (поза міграціями) — код у src/db/client.py, dashboard.py та
-- pain_classifier.py їх уже використовує. Ця міграція наздоганяє файл до
-- реального стану БД, щоб `make migrate` на чистій БД не падав на insert.

ALTER TABLE classified_pains ADD COLUMN IF NOT EXISTS emotional_layer TEXT;
ALTER TABLE classified_pains ADD COLUMN IF NOT EXISTS quote TEXT;
ALTER TABLE classified_pains ADD COLUMN IF NOT EXISTS competitor_name TEXT;
