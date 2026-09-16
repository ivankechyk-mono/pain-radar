import asyncio
import hashlib
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import Message

load_dotenv()

CHATS = [
    "buhgalteri_kiev",
    "klerkforum",
    "bu911",
    "golovbukh",
    "Zrobleno_buhgalter",
    "UAtaxesYou",
    "buhi1c",
]


def _hash(source: str, text: str) -> str:
    return hashlib.sha256(f"{source}:{text[:500]}".encode()).hexdigest()


async def _collect_chat(client: TelegramClient, username: str, since_days: int = 30) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    messages = []
    async for msg in client.iter_messages(username, limit=500):
        if not isinstance(msg, Message) or not msg.text:
            continue
        if msg.date < since or len(msg.text) < 50:
            continue
        messages.append({
            "source": f"tg_{username}",
            "source_url": f"https://t.me/{username}/{msg.id}",
            "content_hash": _hash(f"tg_{username}", msg.text),
            "title": None,
            "body": msg.text[:8000],
            "author": str(msg.sender_id),
            "published_at": msg.date.isoformat(),
        })
    return messages


async def collect_telegram(since_days: int = 30) -> list[dict]:
    client = TelegramClient(
        os.environ["TG_SESSION"],
        int(os.environ["TG_API_ID"]),
        os.environ["TG_API_HASH"],
    )
    all_messages = []
    async with client:
        for username in CHATS:
            try:
                msgs = await _collect_chat(client, username, since_days)
                all_messages.extend(msgs)
                print(f"  {username}: {len(msgs)} messages")
            except Exception as e:
                print(f"  {username}: ERROR — {e}")
    return all_messages


def collect() -> list[dict]:
    return asyncio.run(collect_telegram())
