#!/usr/bin/env python3
"""Запускається при старті app-контейнера. Якщо raw_messages порожня — підвантажує
дамп Supabase (raw_messages.csv.gz / classified_pains.csv.gz у корені проєкту).
Ідемпотентно: пропускає, якщо дані вже є (том постійний і переживає перезапуски,
тож це спрацює по-справжньому лише один раз)."""
import gzip
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.db.client import get_conn

SEED_FILES = [
    ("raw_messages", "raw_messages.csv.gz"),
    ("classified_pains", "classified_pains.csv.gz"),
]


def main():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM raw_messages")
        if cur.fetchone()[0] > 0:
            print("Seed: raw_messages вже не порожня — пропускаємо")
            return
        for table, path in SEED_FILES:
            if not os.path.exists(path):
                print(f"Seed: {path} не знайдено — пропускаємо")
                continue
            with gzip.open(path, "rt") as f:
                cur.copy_expert(f"COPY {table} FROM STDIN WITH (FORMAT csv, HEADER true)", f)
            print(f"Seed: {table} завантажено з {path}")
        conn.commit()


if __name__ == "__main__":
    main()
