import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "change-me")
TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

DASHBOARD_API_KEY = os.getenv("DASHBOARD_API_KEY", "dev-dashboard-key")
DATABASE_PATH = DATA_DIR / "dashboard.db"
FRONTEND_DIR = BASE_DIR / "frontend"

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

SUMMARY_CACHE_TTL = int(os.getenv("SUMMARY_CACHE_TTL", "3600"))
REDACTION_EXTRA_PATTERNS = os.getenv("REDACTION_EXTRA_PATTERNS", "")
