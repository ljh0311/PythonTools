from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.routes.deps import verify_operator
from backend.services.auth_service import (
    create_session,
    password_auth_enabled,
    revoke_session,
    verify_password,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


@router.get("/status")
async def auth_status() -> dict[str, bool | str]:
    return {
        "password_login_enabled": password_auth_enabled(),
        "api_key_login_enabled": True,
    }


@router.post("/login")
async def login(body: LoginRequest) -> dict[str, str]:
    if not password_auth_enabled():
        raise HTTPException(
            status_code=400,
            detail="Password login not configured. Set OPERATOR_PASSWORD in .env",
        )
    if not verify_password(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return create_session()


@router.post("/logout")
async def logout(token: str = Depends(verify_operator)) -> dict[str, str]:
    revoke_session(token)
    return {"status": "logged_out"}


@router.get("/me")
async def me(token: str = Depends(verify_operator)) -> dict[str, str]:
    return {"status": "authenticated", "auth_type": "session" if len(token) > 40 else "api_key"}
