import re
from typing import Any

from backend.models.store import store
from backend.services.ai_service import ai_service
from backend.services.telegram_service import telegram_service


COMMAND_PATTERN = re.compile(r"^/(\w+)")


async def handle_telegram_update(update: dict[str, Any]) -> dict[str, Any] | None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        store.add_event("unsupported_update", update)
        return None

    user = message.get("from", {})
    chat = message.get("chat", {})
    text = (message.get("text") or "").strip()
    user_id = user.get("id")
    chat_id = chat.get("id")
    username = user.get("username")

    store.upsert_user(user)
    store.add_message(user_id, username, "incoming", text)
    store.add_event("message_received", {"user_id": user_id, "text": text})

    match = COMMAND_PATTERN.match(text)
    if match:
        store.track_command(f"/{match.group(1)}")

    reply = await ai_service.process_message(text, store)
    store.add_message(user_id, username, "outgoing", reply)

    if telegram_service.configured and chat_id:
        await telegram_service.send_message(chat_id, reply)

    return {"user_id": user_id, "chat_id": chat_id, "reply": reply}
