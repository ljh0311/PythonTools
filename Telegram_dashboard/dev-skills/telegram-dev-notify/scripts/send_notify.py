#!/usr/bin/env python3
"""Send text or a file to Telegram — delegates to tdash.py when available."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

TELEGRAM_MAX = 4096
SKILL_ROOT = Path(__file__).resolve().parent.parent
SKILL_ENV = SKILL_ROOT / ".env"


def load_env_file(path: Path) -> None:
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


def find_tdash() -> Path | None:
    env_hint = os.environ.get("TELEGRAM_DASHBOARD_ROOT", "").strip()
    candidates = [
        Path(env_hint) / "openclaw" / "skills" / "telegram-dashboard" / "scripts" / "tdash.py" if env_hint else None,
        Path.home()
        / "Documents"
        / "brightnessControl"
        / "PythonTools"
        / "Telegram_dashboard"
        / "openclaw"
        / "skills"
        / "telegram-dashboard"
        / "scripts"
        / "tdash.py",
        SKILL_ROOT.parent.parent / "openclaw" / "skills" / "telegram-dashboard" / "scripts" / "tdash.py",
        Path.home() / ".openclaw" / "workspace" / "skills" / "telegram-dashboard" / "scripts" / "tdash.py",
    ]
    for path in candidates:
        if path is not None and path.is_file():
            return path
    return None


def base_url() -> str:
    return os.environ.get("TELEGRAM_DASHBOARD_URL", "http://localhost:8000").rstrip("/")


def api_key() -> str:
    key = os.environ.get("DASHBOARD_API_KEY", "")
    if not key:
        raise SystemExit(f"DASHBOARD_API_KEY is not set. Add it to {SKILL_ENV}.")
    return key


def default_chat_id() -> str:
    for name in ("NOTIFY_TELEGRAM_CHAT_ID", "EOD_TELEGRAM_CHAT_ID", "TELEGRAM_CHAT_ID"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise SystemExit(f"No default chat ID in {SKILL_ENV}; pass --chat-id.")


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


def send_http(chat: str, text: str) -> dict:
    payload = json.dumps({"chat_id": chat, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url()}/api/send",
        data=payload,
        headers={"Content-Type": "application/json", "X-API-Key": api_key()},
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


def run_tdash(args: argparse.Namespace, tdash: Path) -> int:
    chat = (args.chat_id or default_chat_id()).strip()
    if args.text:
        cmd = [sys.executable, str(tdash), "send", "--chat-id", chat, "--text", args.text]
    else:
        cmd = [sys.executable, str(tdash), "send-file", "--file", args.file]
        if args.chat_id:
            cmd.extend(["--chat-id", args.chat_id])
    if args.dry_run:
        text = truncate_for_telegram(read_payload(args))
        print(json.dumps({"chat_id": chat, "text": text, "via": "tdash"}, indent=2))
        return 0
    return subprocess.call(cmd)


def main() -> None:
    load_env_file(SKILL_ENV)

    parser = argparse.ArgumentParser(description="Send dev notify via Dashboard API (tdash preferred)")
    parser.add_argument("--text")
    parser.add_argument("--file")
    parser.add_argument("--chat-id")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tdash = find_tdash()
    if tdash:
        raise SystemExit(run_tdash(args, tdash))

    chat = (args.chat_id or default_chat_id()).strip()
    text = truncate_for_telegram(read_payload(args))
    if args.dry_run:
        print(json.dumps({"chat_id": chat, "text": text, "url": f"{base_url()}/api/send"}, indent=2))
        return
    print(json.dumps(send_http(chat, text), indent=2))


if __name__ == "__main__":
    main()
