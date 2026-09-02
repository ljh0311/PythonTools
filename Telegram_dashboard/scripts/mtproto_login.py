#!/usr/bin/env python3
"""One-time login for v0.2 user inbox (Telethon session file)."""
import asyncio
import getpass
import os
import sys

from dotenv import load_dotenv

load_dotenv()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.config import MTProto_PHONE, MTProto_SESSION_PATH, TELEGRAM_API_HASH, TELEGRAM_API_ID  # noqa: E402
from telethon import TelegramClient  # noqa: E402
from telethon.errors import SessionPasswordNeededError  # noqa: E402


async def main() -> None:
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env (from https://my.telegram.org)")
        sys.exit(1)

    phone = (MTProto_PHONE or input("Phone number (with country code): ")).strip()
    MTProto_SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)

    client = TelegramClient(str(MTProto_SESSION_PATH), TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Already logged in as @{me.username or me.first_name} (id {me.id})")
        await client.disconnect()
        return

    sent = await client.send_code_request(phone)
    code = input("Login code from Telegram: ").strip()
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=sent.phone_code_hash)
    except SessionPasswordNeededError:
        password = getpass.getpass("Two-factor password: ")
        await client.sign_in(password=password)

    me = await client.get_me()
    print(f"Logged in as @{me.username or me.first_name}. Session saved to {MTProto_SESSION_PATH}")
    print("Set MTProto_ENABLED=true in .env and restart the dashboard.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
