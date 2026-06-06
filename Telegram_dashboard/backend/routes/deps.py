from fastapi import Header, HTTPException

from backend.services.auth_service import validate_token


def verify_operator(
    x_api_key: str = Header(default=""),
    authorization: str = Header(default=""),
) -> str:
    token = x_api_key
    if not token and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not validate_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired credentials")
    return token
