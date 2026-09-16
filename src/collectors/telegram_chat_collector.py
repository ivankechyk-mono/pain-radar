import asyncio
import hashlib
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import Message

load_dotenv()

API_ID   = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION  = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "pain_radar")

# Тільки публічні чати де бухгалтери спілкуються між собою
CHATS = [
    "buhgalteri_kiev",
]

SINCE_DAYS    = 7
LIMIT_PER_CHAT = 200   # не більше — чати активні, цього достатньо
SLEEP_BETWEEN  = 5     # секунди між чатами


def _hash(source: str, text: str) -> str:
    return hashlib.sha256(f"{source}:{text[:500]}".encode()).hexdigest()


async def _fetch_chat(client: TelegramClient, username: str) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=SINCE_DAYS)
    messages = []
    try:
        async for msg in client.iter_messages(username, limit=LIMIT_PER_CHAT):
            if not isinstance(msg, Message) or not msg.text:
                continue
            if msg.date.astimezone(timezone.utc) < since:
                break
            if len(msg.text) < 40:
                continue
            messages.append({
                "source":       f"tg_{username}",
                "source_url":   f"https://t.me/{username}/{msg.id}",
                "content_hash": _hash(f"tg_{username}", msg.text),
                "title":        None,
                "body":         msg.text[:8000],
                "author":       None,  # не зберігаємо sender_id
                "published_at": msg.date.astimezone(timezone.utc).isoformat(),
            })
    except FloodWaitError as e:
        wait = e.seconds + 15
        print(f"  [tg_{username}] FloodWait — sleeping {wait}s", flush=True)
        await asyncio.sleep(wait)
    except Exception as e:
        print(f"  [tg_{username}] ERROR — {e}", flush=True)
    return messages


async def _collect_all() -> list[dict]:
    all_messages = []
    async with TelegramClient(SESSION, API_ID, API_HASH) as client:
        for username in CHATS:
            msgs = await _fetch_chat(client, username)
            print(f"  tg_{username}: {len(msgs)} messages", flush=True)
            all_messages.extend(msgs)
            await asyncio.sleep(SLEEP_BETWEEN)
    return all_messages


def collect_telegram_chats() -> list[dict]:
    return asyncio.run(_collect_all())
