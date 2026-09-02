#!/usr/bin/env python3
"""Dry checks for send error mapping and setup-status shape."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
from fastapi import HTTPException

from backend.services.send_errors import raise_send_http_error, telegram_http_detail


def test_telegram_http_detail() -> None:
    response = MagicMock()
    response.status_code = 400
    response.json.return_value = {"description": "Bad Request: chat not found"}
    exc = httpx.HTTPStatusError("bad", request=MagicMock(), response=response)
    assert "chat not found" in telegram_http_detail(exc)


def test_value_error_is_400() -> None:
    try:
        raise_send_http_error(ValueError("User account is not connected"))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "not connected" in str(exc.detail)
    else:
        raise AssertionError("expected HTTPException")


def test_request_error_is_502() -> None:
    try:
        raise_send_http_error(httpx.ConnectError("connection refused"))
    except HTTPException as exc:
        assert exc.status_code == 502
        assert "Could not reach Telegram" in str(exc.detail)
    else:
        raise AssertionError("expected HTTPException")


async def test_setup_status_shape() -> None:
    from backend.routes import api as api_routes

    mock_ai = AsyncMock(
        return_value={
            "gemini": {"configured": False},
            "ollama": {"configured": False, "available": False},
        }
    )
    mock_mtproto = AsyncMock(
        return_value={
            "configured": False,
            "authorized": False,
            "listening": False,
        }
    )

    with (
        patch.object(
            type(api_routes.telegram_service),
            "configured",
            new_callable=PropertyMock,
            return_value=False,
        ),
        patch.object(api_routes.mtproto_service, "get_status", mock_mtproto),
        patch.object(api_routes.ai_service, "provider_status", mock_ai),
    ):
        payload = await api_routes.setup_status()

    assert "bot" in payload and "user_account" in payload and "ai" in payload
    assert isinstance(payload["warnings"], list)
    assert any("TELEGRAM_BOT_TOKEN" in w for w in payload["warnings"])


def main() -> int:
    test_telegram_http_detail()
    test_value_error_is_400()
    test_request_error_is_502()
    asyncio.run(test_setup_status_shape())
    print("OK: send_errors + setup-status checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
