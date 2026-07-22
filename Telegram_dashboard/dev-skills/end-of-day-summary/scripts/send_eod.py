#!/usr/bin/env python3
"""Send an EOD markdown file via telegram-dev-notify (no duplicated HTTP code)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SKILL_ENV = SKILL_ROOT / ".env"
NOTIFY_SKILL_NAMES = ("telegram-dev-notify",)


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


def resolve_notify_script() -> Path:
    candidates: list[Path] = []

    sibling = SKILL_ROOT.parent / "telegram-dev-notify" / "scripts" / "send_notify.py"
    candidates.append(sibling)

    home_skills = Path.home() / ".cursor" / "skills"
    for name in NOTIFY_SKILL_NAMES:
        candidates.append(home_skills / name / "scripts" / "send_notify.py")

    for path in candidates:
        if path.is_file():
            return path

    joined = "\n  ".join(str(p) for p in candidates)
    raise SystemExit(
        "telegram-dev-notify not found. Install dev-skills/telegram-dev-notify to "
        f"~/.cursor/skills/telegram-dev-notify/\nTried:\n  {joined}"
    )


def main() -> None:
    load_env_file(SKILL_ENV)

    parser = argparse.ArgumentParser(description="Send EOD summary file to Telegram")
    parser.add_argument("--file", required=True, help="Path to eod-YYYY-MM-DD.md")
    parser.add_argument("--chat-id", default=None, help="Override EOD_TELEGRAM_CHAT_ID")
    parser.add_argument("--dry-run", action="store_true", help="Print payload only")
    args = parser.parse_args()

    notify_script = resolve_notify_script()
    cmd = [sys.executable, str(notify_script), "--file", args.file]
    if args.chat_id:
        cmd.extend(["--chat-id", args.chat_id])
    elif os.environ.get("EOD_TELEGRAM_CHAT_ID", "").strip():
        cmd.extend(["--chat-id", os.environ["EOD_TELEGRAM_CHAT_ID"].strip()])
    if args.dry_run:
        cmd.append("--dry-run")

    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
