#!/usr/bin/env python3
"""Send text or a file to Telegram via Dashboard POST /api/send."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

TELEGRAM_MAX = 4096
SKILL_ROOT = Path(__file__).resolve().parent.parent
SKILL_ENV = SKILL_ROOT / ".env"


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE lines into os.environ if the key is not already set."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def base_url() -> str:
    return os.environ.get("TELEGRAM_DASHBOARD_URL", "http://localhost:8000").rstrip("/")


def api_key() -> str:
    key = os.environ.get("DASHBOARD_API_KEY", "")
    if not key:
        raise SystemExit(
            f"DASHBOARD_API_KEY is not set. Add it to {SKILL_ENV} (see .env.example)."
        )
    return key


def default_chat_id() -> str:
    for name in ("NOTIFY_TELEGRAM_CHAT_ID", "EOD_TELEGRAM_CHAT_ID", "TELEGRAM_CHAT_ID"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise SystemExit(
        "No default chat ID. Set NOTIFY_TELEGRAM_CHAT_ID in "
        f"{SKILL_ENV} or pass --chat-id."
    )


def read_payload(args: argparse.Namespace) -> str:
    if args.text and args.file:
        raise SystemExit("Use --text or --file, not both.")
    if args.text:
        return args.text.strip()
    if args.file:
        path = Path(args.file)
        if not path.is_file():
            raise SystemExit(f"File not found: {path}")
        return path.read_text(encoding="utf-8").strip()
    raise SystemExit("Provide --text or --file.")


def truncate_for_telegram(text: str) -> str:
    if len(text) <= TELEGRAM_MAX:
        return text
    note = "\n\n…truncated for Telegram (full content on disk)."
    return text[: TELEGRAM_MAX - len(note)].rstrip() + note


def send(chat: str, text: str) -> dict:
    payload = json.dumps({"chat_id": chat, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url()}/api/send",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key(),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {"ok": True}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Request failed: {exc}") from exc


def main() -> None:
    load_env_file(SKILL_ENV)

    parser = argparse.ArgumentParser(
        description="Send text or a markdown/report file to Telegram via Dashboard API"
    )
    parser.add_argument("--text", help="Message body (plain text or markdown)")
    parser.add_argument("--file", help="Path to a text/markdown file to send")
    parser.add_argument("--chat-id", default=None, help="Override default Telegram chat ID")
    parser.add_argument("--dry-run", action="store_true", help="Print payload only")
    args = parser.parse_args()

    text = truncate_for_telegram(read_payload(args))
    target = (args.chat_id or default_chat_id()).strip()

    if args.dry_run:
        print(
            json.dumps(
                {"chat_id": target, "text": text, "url": f"{base_url()}/api/send"},
                indent=2,
            )
        )
        return

    result = send(target, text)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
