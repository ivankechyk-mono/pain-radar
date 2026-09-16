import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

_conn = None


def get_conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", 5434)),
            dbname=os.environ.get("DB_NAME", "pain_radar"),
            user=os.environ.get("DB_USER", "redbull1122"),
            password=os.environ.get("DB_PASSWORD", ""),
        )
    return _conn


def insert_raw(messages: list[dict]) -> int:
    if not messages:
        return 0
    conn = get_conn()
    with conn.cursor() as cur:
        inserted = 0
        for m in messages:
            cur.execute("""
                INSERT INTO raw_messages (source, source_url, content_hash, title, body, author, published_at)
                VALUES (%(source)s, %(source_url)s, %(content_hash)s, %(title)s, %(body)s, %(author)s, %(published_at)s)
                ON CONFLICT (content_hash) DO NOTHING
            """, m)
            inserted += cur.rowcount
        conn.commit()
    return inserted


def get_unclassified_by_source(source: str, limit: int = 200) -> list[dict]:
    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, source, title, body, published_at
            FROM raw_messages
            WHERE is_classified = FALSE
              AND source = %s
              AND length(body) >= 80
            ORDER BY published_at DESC NULLS LAST
            LIMIT %s
        """, (source, limit))
        return [dict(r) for r in cur.fetchall()]


def get_unclassified(limit: int = 100) -> list[dict]:
    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, source, title, body, published_at
            FROM raw_messages
            WHERE is_classified = FALSE
              AND published_at >= '2026-01-01'
              AND length(body) >= 80
            ORDER BY published_at DESC
            LIMIT %s
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]


def insert_classified(pains: list[dict]) -> None:
    if not pains:
        return
    conn = get_conn()
    with conn.cursor() as cur:
        for p in pains:
            cur.execute("""
                INSERT INTO classified_pains
                  (raw_message_id, is_pain, pain_category, pain_description, target, intensity, emotional_layer, quote, competitor_name, model_used)
                VALUES
                  (%(raw_message_id)s, %(is_pain)s, %(pain_category)s, %(pain_description)s,
                   %(target)s, %(intensity)s, %(emotional_layer)s, %(quote)s, %(competitor_name)s, %(model_used)s)
            """, p)
        conn.commit()


def mark_classified(ids: list[str]) -> None:
    if not ids:
        return
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE raw_messages SET is_classified = TRUE WHERE id = ANY(%s::uuid[])",
            (ids,)
        )
        conn.commit()
