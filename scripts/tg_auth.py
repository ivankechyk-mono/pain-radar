#!/usr/bin/env python3
"""
Step 1: python tg_auth.py send   — sends code to phone
Step 2: python tg_auth.py login CODE — completes auth
"""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

API_ID   = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
PHONE    = os.environ["TG_PHONE"]
SESSION  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pain_radar")
HASH_FILE = "/tmp/tg_code_hash.txt"

async def send():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    result = await client.send_code_request(PHONE)
    with open(HASH_FILE, "w") as f:
        f.write(result.phone_code_hash)
    print(f"Code sent to {PHONE}")
    print(f"Now run:  .venv/bin/python3.12 scripts/tg_auth.py login XXXXX")
    await client.disconnect()

async def login(code, pwd=None):
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.connect()
    with open(HASH_FILE) as f:
        phone_code_hash = f.read().strip()
    try:
        await client.sign_in(PHONE, code, phone_code_hash=phone_code_hash)
    except SessionPasswordNeededError:
        await client.sign_in(password=pwd)
    me = await client.get_me()
    print(f"Logged in as: {me.first_name} ({me.phone})")
    await client.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "send":
        asyncio.run(send())
    elif sys.argv[1] == "login":
        code = sys.argv[2]
        pwd  = sys.argv[3] if len(sys.argv) > 3 else None
        asyncio.run(login(code, pwd))
