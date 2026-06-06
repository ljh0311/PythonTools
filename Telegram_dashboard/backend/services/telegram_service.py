from typing import Any

import httpx

from backend.config import TELEGRAM_API_BASE, TELEGRAM_BOT_TOKEN


class TelegramService:
    def __init__(self, token: str = TELEGRAM_BOT_TOKEN):
        self.token = token

    @property
    def configured(self) -> bool:
        return bool(self.token)

    def _url(self, method: str) -> str:
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured")
        return TELEGRAM_API_BASE.format(token=self.token) + f"/{method}"

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str | None = None,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = reply_markup

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self._url("sendMessage"), json=payload)
            response.raise_for_status()
            return response.json()

    async def set_webhook(self, url: str, secret_token: str) -> dict[str, Any]:
        payload = {"url": url, "secret_token": secret_token}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self._url("setWebhook"), json=payload)
            response.raise_for_status()
            return response.json()

    async def delete_webhook(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self._url("deleteWebhook"))
            response.raise_for_status()
            return response.json()

    async def get_me(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self._url("getMe"))
            response.raise_for_status()
            return response.json()


telegram_service = TelegramService()
