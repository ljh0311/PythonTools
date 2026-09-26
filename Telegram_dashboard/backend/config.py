import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "change-me")
TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"

# v0.2 — user account inbox (MTProto / Telethon)
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0") or "0")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
MTProto_ENABLED = os.getenv("MTProto_ENABLED", "false").lower() in ("1", "true", "yes")
MTProto_SESSION_PATH = DATA_DIR / os.getenv("MTProto_SESSION_NAME", "user.session")
MTProto_PHONE = os.getenv("MTProto_PHONE", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

_GEMINI_KEY_PLACEHOLDERS = frozenset(
    {
        "",
        "your-gemini-api-key",
        "your_gemini_api_key",
        "changeme",
        "change-me",
    }
)


def gemini_key_configured(key: str = GEMINI_API_KEY) -> bool:
    normalized = (key or "").strip()
    if not normalized:
        return False
    if normalized.lower() in _GEMINI_KEY_PLACEHOLDERS:
        return False
    if normalized.lower().startswith("your-"):
        return False
    return True

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
# llama3.2 on some installs emits garbled "@@@" output — prefer qwen2.5:3b locally.
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
_OLLAMA_FALLBACK_RAW = os.getenv(
    "OLLAMA_FALLBACK_MODELS",
    "qwen2.5:3b,qwen2.5:latest,llama3.2",
)
OLLAMA_FALLBACK_MODELS = [
    m.strip() for m in _OLLAMA_FALLBACK_RAW.split(",") if m.strip()
]

# Primary AI provider: "gemini" | "ollama".
# On Gemini 429/errors the other provider is tried; failure text redacts API keys.
_AI_PRIMARY_RAW = (os.getenv("AI_PRIMARY_PROVIDER") or "gemini").strip().lower()
AI_PRIMARY_PROVIDER = _AI_PRIMARY_RAW if _AI_PRIMARY_RAW in ("ollama", "gemini") else "gemini"

DASHBOARD_API_KEY = os.getenv("DASHBOARD_API_KEY", "dev-dashboard-key")
OPERATOR_USERNAME = os.getenv("OPERATOR_USERNAME", "admin")
OPERATOR_PASSWORD = os.getenv("OPERATOR_PASSWORD", "")
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "24"))
OPENCLAW_ENABLED = os.getenv("OPENCLAW_ENABLED", "false").lower() in ("1", "true", "yes")
OPENCLAW_GATEWAY_URL = os.getenv("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")
DATABASE_PATH = DATA_DIR / "dashboard.db"
PROFILES_DIR = DATA_DIR / "profiles"
PROFILES_DIR.mkdir(exist_ok=True)
FRONTEND_DIR = BASE_DIR / "frontend"

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

SUMMARY_CACHE_TTL = int(os.getenv("SUMMARY_CACHE_TTL", "3600"))
AI_RATE_LIMIT_PER_MINUTE = int(os.getenv("AI_RATE_LIMIT_PER_MINUTE", "10"))
REDACTION_EXTRA_PATTERNS = os.getenv("REDACTION_EXTRA_PATTERNS", "")

# D-01: default operator approves (manual). Options: manual | auto | per_chat
AUTO_REPLY_MODE = os.getenv("AUTO_REPLY_MODE", "manual")
# D-03: default user-typed topics. Options: user_type | ai_assign
TOPIC_MODE = os.getenv("TOPIC_MODE", "user_type")

# Optional SmartPersona brain for learn-from-chat (requires Ollama when enabled)
SMARTPERSONA_ENABLED = os.getenv("SMARTPERSONA_ENABLED", "false").lower() in (
    "1",
    "true",
    "yes",
)
SMARTPERSONA_PATH = os.getenv(
    "SMARTPERSONA_PATH", str(BASE_DIR.parent / "SmartPersona")
)

# Needs-reply digest (Telegram bot → operator chat). Dev: prefer AI_PRIMARY_PROVIDER=ollama.
NOTIFY_TELEGRAM_CHAT_ID = (os.getenv("NOTIFY_TELEGRAM_CHAT_ID") or "").strip()
UNREAD_DIGEST_ENABLED = os.getenv("UNREAD_DIGEST_ENABLED", "false").lower() in (
    "1",
    "true",
    "yes",
)
_UNREAD_DIGEST_CHAT = (os.getenv("UNREAD_DIGEST_CHAT_ID") or "").strip()
UNREAD_DIGEST_CHAT_ID = _UNREAD_DIGEST_CHAT or NOTIFY_TELEGRAM_CHAT_ID
UNREAD_DIGEST_INTERVAL_MIN = int(os.getenv("UNREAD_DIGEST_INTERVAL_MIN", "180") or "180")
UNREAD_DIGEST_MAX_THREADS = int(os.getenv("UNREAD_DIGEST_MAX_THREADS", "8") or "8")
# Quiet hours as local clock hours 0–23; empty disables quiet-hours skip.
_QUIET_START_RAW = (os.getenv("UNREAD_DIGEST_QUIET_START") or "").strip()
_QUIET_END_RAW = (os.getenv("UNREAD_DIGEST_QUIET_END") or "").strip()
UNREAD_DIGEST_QUIET_START: int | None = (
    int(_QUIET_START_RAW) if _QUIET_START_RAW.isdigit() else None
)
UNREAD_DIGEST_QUIET_END: int | None = (
    int(_QUIET_END_RAW) if _QUIET_END_RAW.isdigit() else None
)
