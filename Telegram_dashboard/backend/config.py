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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

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
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

DASHBOARD_API_KEY = os.getenv("DASHBOARD_API_KEY", "dev-dashboard-key")
OPERATOR_USERNAME = os.getenv("OPERATOR_USERNAME", "admin")
OPERATOR_PASSWORD = os.getenv("OPERATOR_PASSWORD", "")
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "24"))
OPENCLAW_ENABLED = os.getenv("OPENCLAW_ENABLED", "false").lower() in ("1", "true", "yes")
OPENCLAW_GATEWAY_URL = os.getenv("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")
DATABASE_PATH = DATA_DIR / "dashboard.db"
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
