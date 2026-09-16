#!/usr/bin/env python3
import os
import glob
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.environ.get("DB_HOST", "localhost"),
    port=int(os.environ.get("DB_PORT", 5434)),
    dbname=os.environ.get("DB_NAME", "pain_radar"),
    user=os.environ.get("DB_USER", "redbull1122"),
    password=os.environ.get("DB_PASSWORD", ""),
)
conn.autocommit = True
cur = conn.cursor()

base = os.path.dirname(os.path.dirname(__file__))
migration_files = sorted(glob.glob(os.path.join(base, "migrations", "*.sql")))
for path in migration_files:
    print(f"Running {path}...")
    with open(path) as f:
        cur.execute(f.read())
    print("  OK")

cur.close()
conn.close()
print("Migrations done.")
