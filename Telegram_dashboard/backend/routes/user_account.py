from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.routes.deps import verify_operator
from backend.services.mtproto_service import mtproto_service


router = APIRouter(prefix="/api/user-account", tags=["user-account"])


class SendCodeRequest(BaseModel):
    phone: str | None = None


class ConfirmCodeRequest(BaseModel):
    phone: str = Field(min_length=5)
    code: str = Field(min_length=3, max_length=12)
    password: str | None = None


class UserSendRequest(BaseModel):
    chat_id: int | str
    text: str = Field(min_length=1, max_length=4096)


@router.get("/status", dependencies=[Depends(verify_operator)])
async def user_account_status() -> dict[str, Any]:
    return await mtproto_service.get_status()


@router.post("/login/send-code", dependencies=[Depends(verify_operator)])
async def send_login_code(body: SendCodeRequest) -> dict[str, Any]:
    try:
        return await mtproto_service.send_code(body.phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/login/confirm", dependencies=[Depends(verify_operator)])
async def confirm_login_code(body: ConfirmCodeRequest) -> dict[str, Any]:
    try:
        result = await mtproto_service.confirm_code(
            body.phone, body.code, body.password
        )
        if result.get("needs_password"):
            raise HTTPException(status_code=401, detail="Two-factor password required")
        return result
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/send", dependencies=[Depends(verify_operator)])
async def send_as_user(body: UserSendRequest) -> dict[str, Any]:
    from backend.models.store import store
    from backend.services.ws_manager import ws_manager

    try:
        result = await mtproto_service.send_message(body.chat_id, body.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    status = await mtproto_service.get_status()
    user = status.get("user") or {}
    chat_id_int = int(body.chat_id)
    store.add_message(
        user.get("id", 0),
        user.get("username"),
        "outgoing",
        body.text,
        chat_id=chat_id_int,
        message_id=result.get("message_id"),
        chat_type="private",
        ingestion_source="user_account",
    )
    await ws_manager.broadcast(
        "message_sent",
        {"chat_id": body.chat_id, "text": body.text, "via": "user_account"},
    )
    return result
