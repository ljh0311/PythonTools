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


@router.get("/messages", dependencies=[Depends(verify_api_key)])
async def messages(limit: int = 50) -> list[dict[str, Any]]:
    return store.recent_messages(limit)


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
    store.add_message(int(body.chat_id), None, "outgoing", body.text)
    await ws_manager.broadcast("message_sent", {"chat_id": body.chat_id, "text": body.text})
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
