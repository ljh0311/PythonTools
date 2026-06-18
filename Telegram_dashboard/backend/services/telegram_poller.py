import asyncio
import logging

from backend.services.bot_handler import handle_telegram_update
from backend.services.telegram_service import telegram_service

logger = logging.getLogger(__name__)


async def run_telegram_poller(broadcast) -> None:
    if not telegram_service.configured:
        logger.warning("Telegram polling disabled: TELEGRAM_BOT_TOKEN not set")
        return

    try:
        info = await telegram_service.get_webhook_info()
        webhook_url = (info.get("result") or {}).get("url") or ""
        if webhook_url:
            logger.info("Removing Telegram webhook %s (required for polling)", webhook_url)
            await telegram_service.delete_webhook()
    except Exception:
        logger.exception("Failed to prepare Telegram polling")

    offset = 0
    logger.info("Telegram polling started — send a message to your bot in Telegram")

    while True:
        try:
            payload = await telegram_service.get_updates(offset=offset, timeout=50)
            for update in payload.get("result", []):
                offset = update["update_id"] + 1
                result = await handle_telegram_update(update)
                if result:
                    await broadcast("telegram_update", result)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Telegram polling error; retrying in 5s")
            await asyncio.sleep(5)
