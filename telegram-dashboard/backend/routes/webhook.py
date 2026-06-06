from fastapi import APIRouter, Header, HTTPException, Request

from backend.config import TELEGRAM_WEBHOOK_SECRET
from backend.routes.api import ws_manager
from backend.services.bot_handler import handle_telegram_update


router = APIRouter(prefix="/webhook", tags=["telegram"])


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=""),
):
    if x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    update = await request.json()
    result = await handle_telegram_update(update)

    if result:
        await ws_manager.broadcast("telegram_update", result)

    return {"ok": True}
