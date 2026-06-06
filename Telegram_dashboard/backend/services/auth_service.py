import hashlib
import secrets
from datetime import datetime, timedelta

from backend.config import DASHBOARD_API_KEY, OPERATOR_PASSWORD, OPERATOR_USERNAME, SESSION_TTL_HOURS
from backend.models.store import store


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def password_auth_enabled() -> bool:
    return bool(OPERATOR_PASSWORD.strip())


def verify_password(username: str, password: str) -> bool:
    if not password_auth_enabled():
        return False
    if username != OPERATOR_USERNAME:
        return False
    return secrets.compare_digest(_hash_password(password), _hash_password(OPERATOR_PASSWORD))


def create_session() -> dict:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)).isoformat()
    store.create_session(token, expires_at)
    return {"token": token, "expires_at": expires_at}


def validate_token(token: str) -> bool:
    if not token:
        return False
    if token == DASHBOARD_API_KEY:
        return True
    return store.session_valid(token)


def revoke_session(token: str) -> None:
    if token == DASHBOARD_API_KEY:
        return
    store.delete_session(token)
