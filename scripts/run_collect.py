#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.collectors.rss_collector import collect_rss
from src.collectors.telegram_public_collector import collect_telegram_public
from src.collectors.telegram_chat_collector import collect_telegram_chats
from src.collectors.forum_collector import collect_buhgalter911
from src.collectors.facebook_collector import collect_facebook
from src.collectors.minfin_collector import collect_minfin
from src.db.client import insert_raw

print("=== RSS (dtkt.ua) ===")
msgs = collect_rss()
print(f"Fetched: {len(msgs)} → Inserted: {insert_raw(msgs)}")

print("\n=== Telegram public channels ===")
msgs = collect_telegram_public()
print(f"Fetched: {len(msgs)} → Inserted: {insert_raw(msgs)}")

print("\n=== Telegram chats (buhgalteri_kiev, klerkforum) ===")
msgs = collect_telegram_chats()
print(f"Fetched: {len(msgs)} → Inserted: {insert_raw(msgs)}")

print("\n=== Forum buhgalter911.com ===")
msgs = collect_buhgalter911(topics_per_forum=10)
print(f"Fetched: {len(msgs)} → Inserted: {insert_raw(msgs)}")

print("\n=== Facebook groups ===")
msgs = collect_facebook(max_posts_per_group=50)
print(f"Fetched: {len(msgs)} → Inserted: {insert_raw(msgs)}")

print("\n=== Minfin.com.ua — відгуки на банки-конкуренти ===")
msgs = collect_minfin(max_pages=10)
print(f"Fetched: {len(msgs)} → Inserted: {insert_raw(msgs)}")

print("\nDone.")
