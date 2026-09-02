"""Map Telegram/httpx send failures to operator-visible HTTP errors."""

from __future__ import annotations

import httpx
from fastapi import HTTPException
from telethon.errors import RPCError


def telegram_http_detail(exc: httpx.HTTPStatusError) -> str:
    try:
        data = exc.response.json()
        desc = data.get("description")
        if desc:
            return f"Telegram bot API: {desc}"
    except Exception:
        pass
    return f"Telegram bot API HTTP {exc.response.status_code}"


def raise_send_http_error(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, httpx.HTTPStatusError):
        raise HTTPException(status_code=502, detail=telegram_http_detail(exc)) from exc
    if isinstance(exc, httpx.RequestError):
        raise HTTPException(
            status_code=502, detail=f"Could not reach Telegram: {exc}"
        ) from exc
    if isinstance(exc, RPCError):
        raise HTTPException(status_code=502, detail=f"Telegram error: {exc}") from exc
    raise HTTPException(status_code=502, detail=str(exc)) from exc
