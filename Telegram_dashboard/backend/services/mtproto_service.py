from __future__ import annotations

from typing import Any

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import Channel, Chat, User

from backend.config import (
    MTProto_ENABLED,
    MTProto_PHONE,
    MTProto_SESSION_PATH,
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
)
from backend.services.user_account_handler import handle_mtproto_message
from backend.services.ws_manager import ws_manager
from backend.models.store import store


import logging

logger = logging.getLogger(__name__)

class MtprotoService:
    def __init__(self) -> None:
        self._client: TelegramClient | None = None
        self._me_id: int | None = None
        self._me_user: dict[str, Any] | None = None
        self._phone_code_hash: str | None = None
        self._handler_registered = False

    @property
    def configured(self) -> bool:
        return bool(TELEGRAM_API_ID and TELEGRAM_API_HASH)

    @property
    def enabled(self) -> bool:
        return MTProto_ENABLED and self.configured

    @property
    def client(self) -> TelegramClient | None:
        return self._client

    def _build_client(self) -> TelegramClient:
        MTProto_SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
        return TelegramClient(
            str(MTProto_SESSION_PATH),
            TELEGRAM_API_ID,
            TELEGRAM_API_HASH,
        )

    async def connect(self) -> None:
        if not self.configured:
            return
        if self._client is None:
            self._client = self._build_client()
        if not self._client.is_connected():
            import sqlite3
            import asyncio
            for attempt in range(3):
                try:
                    await self._client.connect()
                    break
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < 2:
                        await asyncio.sleep(1)
                        continue
                    raise

    async def disconnect(self) -> None:
        if self._client and self._client.is_connected():
            await self._client.disconnect()

    async def is_authorized(self) -> bool:
        if not self._client:
            return False
        return await self._client.is_user_authorized()

    async def get_status(self) -> dict[str, Any]:
        if not self.configured:
            return {
                "configured": False,
                "enabled": self.enabled,
                "authorized": False,
                "connected": False,
                "user": None,
                "session_path": str(MTProto_SESSION_PATH),
            }

        await self.connect()
        authorized = await self.is_authorized()
        user = None
        if authorized and self._client:
            me = await self._client.get_me()
            self._me_id = me.id
            user = {
                "id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "phone": me.phone,
            }
            self._me_user = user
            self._register_account_user(user)
        return {
            "configured": True,
            "enabled": self.enabled,
            "authorized": authorized,
            "connected": bool(self._client and self._client.is_connected()),
            "listening": self._handler_registered and authorized and self.enabled,
            "user": user,
            "session_path": str(MTProto_SESSION_PATH),
        }

    def _register_account_user(self, user: dict[str, Any] | None) -> None:
        if not user or not user.get("id"):
            return
        store.upsert_user(user)
        updated = store.backfill_message_usernames(user["id"], user.get("username"))
        if updated:
            logger.info(
                "MTProto: Backfilled username on %s outgoing message(s) for user %s",
                updated,
                user["id"],
            )

    def _register_handlers(self) -> None:
        if not self._client or self._handler_registered:
            return

        @self._client.on(events.NewMessage(incoming=True, outgoing=True))
        async def on_new_message(event: events.NewMessage.Event) -> None:
            if not self.enabled or self._me_id is None:
                return
            result = await handle_mtproto_message(event, self._me_id, self._me_user)
            if result:
                await ws_manager.broadcast("telegram_update", result)

        self._handler_registered = True

    async def start_listening(self) -> None:
        if not self.enabled:
            return
        try:
            await self.connect()
            if not await self.is_authorized():
                logger.info("MTProto: Not authorized. Run scripts/mtproto_login.py")
                return
            me = await self._client.get_me()
            self._me_id = me.id
            self._me_user = {
                "id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
            }
            self._register_account_user(self._me_user)
            self._register_handlers()
            logger.info(f"MTProto: Listening as @{me.username or me.first_name}")
        except Exception as e:
            logger.error(f"MTProto: Failed to start listener: {e}")
            if self._client:
                try:
                    await self._client.disconnect()
                except Exception as disconnect_exc:
                    logger.warning(
                        "MTProto: disconnect after failed start raised: %s",
                        disconnect_exc,
                    )
                self._client = None

    async def send_code(self, phone: str | None = None) -> dict[str, Any]:
        if not self.configured:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required")
        await self.connect()
        target = (phone or MTProto_PHONE or "").strip()
        if not target:
            raise ValueError("Phone number is required")
        sent = await self._client.send_code_request(target)
        self._phone_code_hash = sent.phone_code_hash
        return {"phone": target, "sent": True}

    async def confirm_code(
        self,
        phone: str,
        code: str,
        password: str | None = None,
    ) -> dict[str, Any]:
        if not self._client or not self._phone_code_hash:
            raise ValueError("Call send-code first")
        try:
            await self._client.sign_in(
                phone=phone.strip(),
                code=code.strip(),
                phone_code_hash=self._phone_code_hash,
            )
        except SessionPasswordNeededError:
            if not password:
                return {"needs_password": True}
            await self._client.sign_in(password=password)
        self._phone_code_hash = None
        me = await self._client.get_me()
        self._me_id = me.id
        self._me_user = {
            "id": me.id,
            "username": me.username,
            "first_name": me.first_name,
        }
        self._register_account_user(self._me_user)
        if self.enabled:
            self._register_handlers()
        return {
            "authorized": True,
            "user": {
                "id": me.id,
                "username": me.username,
                "first_name": me.first_name,
            },
        }

    async def send_message(self, chat_id: int | str, text: str) -> dict[str, Any]:
        if not self._client or not await self.is_authorized():
            raise ValueError("User account is not connected")
        message = await self._client.send_message(int(chat_id), text)
        return {"chat_id": int(chat_id), "message_id": message.id, "text": text}


mtproto_service = MtprotoService()
