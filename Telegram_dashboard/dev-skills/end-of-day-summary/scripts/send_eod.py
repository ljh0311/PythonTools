#!/usr/bin/env python3
"""Send EOD file via tdash send-eod (canonical) or telegram-dev-notify fallback."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

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
    candidates = [
        SKILL_ROOT.parent.parent / "openclaw" / "skills" / "telegram-dashboard" / "scripts" / "tdash.py",
        Path.home() / ".openclaw" / "workspace" / "skills" / "telegram-dashboard" / "scripts" / "tdash.py",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def find_notify_script() -> Path | None:
    candidates = [
        SKILL_ROOT.parent / "telegram-dev-notify" / "scripts" / "send_notify.py",
        Path.home() / ".cursor" / "skills" / "telegram-dev-notify" / "scripts" / "send_notify.py",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def main() -> None:
    load_env_file(SKILL_ENV)

    parser = argparse.ArgumentParser(description="Send EOD summary to Telegram")
    parser.add_argument("--file", required=True, help="Path to eod-YYYY-MM-DD.md")
    parser.add_argument("--chat-id", default=None, help="Override EOD_TELEGRAM_CHAT_ID")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tdash = find_tdash()
    if tdash:
        cmd = [sys.executable, str(tdash), "send-eod", "--file", args.file]
        if args.chat_id:
            cmd.extend(["--chat-id", args.chat_id])
        raise SystemExit(subprocess.call(cmd))

    notify = find_notify_script()
    if notify:
        cmd = [sys.executable, str(notify), "--file", args.file]
        if args.chat_id:
            cmd.extend(["--chat-id", args.chat_id])
        elif os.environ.get("EOD_TELEGRAM_CHAT_ID", "").strip():
            cmd.extend(["--chat-id", os.environ["EOD_TELEGRAM_CHAT_ID"].strip()])
        if args.dry_run:
            cmd.append("--dry-run")
        raise SystemExit(subprocess.call(cmd))

    raise SystemExit(
        "Neither tdash.py nor telegram-dev-notify found. Install dev-skills from Telegram_dashboard."
    )


if __name__ == "__main__":
    main()
