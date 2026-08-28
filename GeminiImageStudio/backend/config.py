"""Environment, paths, and CORS settings for Gemini Image Studio."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_MODEL = "gemini-3.1-flash-image"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8765"))

CORS_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

# Empirical unit cost (USD) — calibrated 2026-07-22
UNIT_COST_USD = {
    "gemini-3.1-flash-image": 0.085,
}


def get_api_key() -> str | None:
    """Return Gemini API key from env, or None if missing."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    return key.strip() if key and key.strip() else None


def get_default_model() -> str:
    return os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL


def ensure_outputs_dir() -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUTS_DIR
