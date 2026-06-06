from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.config import DASHBOARD_API_KEY
from backend.models.store import store
from backend.services.ai_service import ai_service
from backend.services.telegram_service import telegram_service


router = APIRouter(prefix="/api", tags=["dashboard"])


def verify_api_key(x_api_key: str = Header(default="")) -> None:
    if x_api_key != DASHBOARD_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


class SendMessageRequest(BaseModel):
    chat_id: int | str
    text: str = Field(min_length=1, max_length=4096)


class QuickAction(BaseModel):
    label: str
    command: str
    enabled: bool = True


class QuickActionsRequest(BaseModel):
    actions: list[QuickAction]


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1, max_length=1000)
    user_id: int | None = None
    username: str | None = None


class SummarizeThreadRequest(BaseModel):
    chat_id: int
    message_ids: list[int] | None = None


class WebSocketManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast(self, event: str, data: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for connection in self.connections:
            try:
                await connection.send_json({"event": event, "data": data})
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


ws_manager = WebSocketManager()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metrics", dependencies=[Depends(verify_api_key)])
async def metrics() -> dict[str, Any]:
    return store.metrics()


@router.get("/users", dependencies=[Depends(verify_api_key)])
async def users() -> list[dict[str, Any]]:
    return store.list_users()


def _parse_message_filters(
    user_ids: str,
    chat_type: str | None,
    direction: str | None,
    date_from: str | None,
    date_to: str | None,
) -> tuple[list[int] | None, str | None, str | None, str | None, str | None]:
    parsed_user_ids: list[int] | None = None
    if user_ids.strip():
        parsed_user_ids = [int(uid) for uid in user_ids.split(",") if uid.strip()]

    if chat_type and chat_type not in ("private", "group"):
        raise HTTPException(status_code=400, detail="chat_type must be private or group")

    if direction and direction not in ("incoming", "outgoing"):
        raise HTTPException(status_code=400, detail="direction must be incoming or outgoing")

    if date_from and len(date_from) == 10:
        date_from = f"{date_from}T00:00:00"
    if date_to and len(date_to) == 10:
        date_to = f"{date_to}T23:59:59"

    return parsed_user_ids, chat_type, direction, date_from, date_to


@router.get("/messages", dependencies=[Depends(verify_api_key)])
async def messages(
    user_ids: str = "",
    chat_type: str | None = None,
    direction: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    parsed_user_ids, chat_type, direction, date_from, date_to = _parse_message_filters(
        user_ids, chat_type, direction, date_from, date_to
    )
    return store.query_messages(
        user_ids=parsed_user_ids,
        chat_type=chat_type,
        direction=direction,
        q=q,
        date_from=date_from,
        date_to=date_to,
        limit=min(limit, 200),
        offset=offset,
    )


@router.get("/inbox/threads", dependencies=[Depends(verify_api_key)])
async def inbox_threads(
    user_ids: str = "",
    chat_type: str | None = None,
    direction: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    parsed_user_ids, chat_type, direction, date_from, date_to = _parse_message_filters(
        user_ids, chat_type, direction, date_from, date_to
    )
    return store.query_threads(
        user_ids=parsed_user_ids,
        chat_type=chat_type,
        direction=direction,
        q=q,
        date_from=date_from,
        date_to=date_to,
        thread_limit=min(limit, 50),
        thread_offset=offset,
    )


@router.post("/ai/summarize-thread", dependencies=[Depends(verify_api_key)])
async def summarize_thread(body: SummarizeThreadRequest) -> dict[str, Any]:
    if body.message_ids:
        messages = store.get_messages_by_ids(body.message_ids)
    else:
        messages = store.get_messages_by_chat_id(body.chat_id)
    if not messages:
        raise HTTPException(status_code=404, detail="No messages for this chat")
    result = await ai_service.summarize_thread(messages)
    return {"chat_id": body.chat_id, **result}


@router.get("/events", dependencies=[Depends(verify_api_key)])
async def events(limit: int = 50) -> list[dict[str, Any]]:
    return store.recent_events(limit)


@router.get("/analytics/commands", dependencies=[Depends(verify_api_key)])
async def command_analytics(days: int = 7) -> dict[str, Any]:
    return store.command_usage_over_time(days)


@router.get("/quick-actions", dependencies=[Depends(verify_api_key)])
async def get_quick_actions() -> list[dict[str, Any]]:
    return store.list_quick_actions()


@router.put("/quick-actions", dependencies=[Depends(verify_api_key)])
async def update_quick_actions(body: QuickActionsRequest) -> list[dict[str, Any]]:
    actions = [action.model_dump() for action in body.actions]
    saved = store.save_quick_actions(actions)
    await ws_manager.broadcast("quick_actions_updated", {"actions": saved})
    return saved


@router.get("/feedback", dependencies=[Depends(verify_api_key)])
async def feedback(limit: int = 20) -> list[dict[str, Any]]:
    return store.recent_feedback(limit)


@router.post("/feedback", dependencies=[Depends(verify_api_key)])
async def submit_feedback(body: FeedbackRequest) -> dict[str, Any]:
    item = store.add_feedback(body.user_id, body.username, body.rating, body.comment)
    await ws_manager.broadcast("feedback_received", item)
    return item


@router.post("/send", dependencies=[Depends(verify_api_key)])
async def send_message(body: SendMessageRequest) -> dict[str, Any]:
    if not telegram_service.configured:
        raise HTTPException(status_code=400, detail="Telegram bot token not configured")

    result = await telegram_service.send_message(body.chat_id, body.text)
    chat_id_int = int(body.chat_id)
    store.add_message(
        0,
        "operator",
        "outgoing",
        body.text,
        chat_id=chat_id_int,
        chat_type="private",
    )
    await ws_manager.broadcast(
        "message_sent", {"chat_id": body.chat_id, "text": body.text}
    )
    return result


@router.get("/ai/status", dependencies=[Depends(verify_api_key)])
async def ai_status() -> dict[str, Any]:
    return await ai_service.provider_status()


@router.get("/bot/status", dependencies=[Depends(verify_api_key)])
async def bot_status() -> dict[str, Any]:
    if not telegram_service.configured:
        return {"configured": False, "bot": None}
    try:
        me = await telegram_service.get_me()
        return {"configured": True, "bot": me.get("result")}
    except Exception as exc:
        return {"configured": True, "bot": None, "error": str(exc)}


@router.websocket("/ws")
async def dashboard_ws(websocket: WebSocket, api_key: str = ""):
    if api_key != DASHBOARD_API_KEY:
        await websocket.close(code=1008)
        return

    await ws_manager.connect(websocket)
    try:
        await websocket.send_json(
            {
                "event": "snapshot",
                "data": {
                    "metrics": store.metrics(),
                    "messages": store.recent_messages(20),
                    "events": store.recent_events(20),
                    "quick_actions": store.list_quick_actions(),
                    "analytics": store.command_usage_over_time(),
                    "feedback": store.recent_feedback(10),
                },
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
