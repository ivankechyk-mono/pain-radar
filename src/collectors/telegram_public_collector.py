import asyncio
import hashlib
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

load_dotenv()

API_ID   = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]

SESSION  = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "pain_radar")

PUBLIC_CHANNELS = [
    # бухгалтерські канали
    "bu911",
    "golovbukh",
    "Zrobleno_buhgalter",
    "UAtaxesYou",
    "buhi1c",
    # канали де клієнти скаржаться на банки-конкуренти
    "pumbbank",          # ПУМБ офіційний
    "privatbankua",      # ПриватБанк
    "ABankUkraine",      # А-Банк
    "SenseBankUA",       # Sense Bank
]

SINCE_DATE        = datetime(2026, 1, 1, tzinfo=timezone.utc)
SLEEP_BETWEEN     = 3   # seconds between channels — stay well within rate limits


def _hash(source: str, text: str) -> str:
    return hashlib.sha256(f"{source}:{text[:500]}".encode()).hexdigest()


async def _fetch_channel(client: TelegramClient, username: str) -> list[dict]:
    messages = []
    try:
        async for msg in client.iter_messages(username, offset_date=None, reverse=False):
            if msg.date and msg.date.astimezone(timezone.utc) < SINCE_DATE:
                break
            text = msg.text or msg.message or ""
            text = text.strip()
            if len(text) < 30:
                continue

            pub_dt = None
            if msg.date:
                pub_dt = msg.date.astimezone(timezone.utc).isoformat()

            source = f"tg_{username}"
            url    = f"https://t.me/{username}/{msg.id}"

            messages.append({
                "source":       source,
                "source_url":   url,
                "content_hash": _hash(source, text),
                "title":        None,
                "body":         text[:8000],
                "author":       None,
                "published_at": pub_dt,
            })

    except FloodWaitError as e:
        wait = e.seconds + 10
        print(f"  [tg_{username}] FloodWait — sleeping {wait}s", flush=True)
        await asyncio.sleep(wait)
    except Exception as e:
        print(f"  [tg_{username}] ERROR — {e}", flush=True)

    return messages


async def _collect_all() -> list[dict]:
    all_messages = []
    async with TelegramClient(SESSION, API_ID, API_HASH) as client:
        for username in PUBLIC_CHANNELS:
            msgs = await _fetch_channel(client, username)
            print(f"  tg_{username}: {len(msgs)} messages", flush=True)
            all_messages.extend(msgs)
            await asyncio.sleep(SLEEP_BETWEEN)
    return all_messages


def collect_telegram_public() -> list[dict]:
    return asyncio.run(_collect_all())
