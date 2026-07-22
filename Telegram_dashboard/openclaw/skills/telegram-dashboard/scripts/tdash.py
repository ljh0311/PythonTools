#!/usr/bin/env python3
"""OpenClaw helper CLI for Telegram Dashboard API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
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
        print("Error: DASHBOARD_API_KEY is not set", file=sys.stderr)
        sys.exit(1)
    return key


def request(method: str, path: str, *, params: dict | None = None, body: dict | None = None) -> dict | list | str:
    url = f"{base_url()}{path}"
    if params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None and v != ""})
        if query:
            url = f"{url}?{query}"
    data = None
    headers = {"X-API-Key": api_key(), "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = resp.read().decode()
            if "text/csv" in resp.headers.get("Content-Type", ""):
                return payload
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        print(f"HTTP {exc.code}: {detail}", file=sys.stderr)
        sys.exit(1)


def truncate_for_telegram(text: str) -> str:
    if len(text) <= TELEGRAM_MAX:
        return text
    note = "\n\n…truncated for Telegram (full file on disk)."
    return text[: TELEGRAM_MAX - len(note)].rstrip() + note


def read_file_text(path: str) -> str:
    file_path = Path(path)
    if not file_path.is_file():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    return truncate_for_telegram(file_path.read_text(encoding="utf-8").strip())


def resolve_chat_id(explicit: str | None, *, env_names: tuple[str, ...]) -> str:
    chat_id = (explicit or "").strip()
    if chat_id:
        return chat_id
    for name in env_names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    env_hint = " or ".join(env_names)
    print(f"Error: pass --chat-id or set {env_hint}", file=sys.stderr)
    sys.exit(1)


def cmd_manifest(_: argparse.Namespace) -> None:
    print(json.dumps(request("GET", "/api/agent/manifest"), indent=2))


def cmd_metrics(_: argparse.Namespace) -> None:
    print(json.dumps(request("GET", "/api/metrics"), indent=2))


def cmd_messages(args: argparse.Namespace) -> None:
    print(
        json.dumps(
            request(
                "GET",
                "/api/messages",
                params={
                    "user_ids": args.user_ids,
                    "chat_type": args.chat_type,
                    "direction": args.direction,
                    "q": args.q,
                    "topics": args.topics,
                    "limit": args.limit,
                },
            ),
            indent=2,
        )
    )


def cmd_threads(args: argparse.Namespace) -> None:
    print(
        json.dumps(
            request(
                "GET",
                "/api/inbox/threads",
                params={
                    "user_ids": args.user_ids,
                    "chat_type": args.chat_type,
                    "direction": args.direction,
                    "q": args.q,
                    "topics": args.topics,
                    "limit": args.limit,
                },
            ),
            indent=2,
        )
    )


def cmd_summarize(args: argparse.Namespace) -> None:
    print(
        json.dumps(
            request(
                "POST",
                "/api/ai/summarize",
                body={
                    "summary_type": args.summary_type,
                    "user_ids": args.user_ids or "",
                    "chat_type": args.chat_type,
                    "direction": args.direction,
                    "q": args.q,
                    "topics": args.topics,
                },
            ),
            indent=2,
        )
    )


def cmd_suggest(args: argparse.Namespace) -> None:
    print(
        json.dumps(
            request(
                "POST",
                "/api/ai/suggest-actions",
                body={
                    "user_ids": args.user_ids or "",
                    "chat_type": args.chat_type,
                    "direction": args.direction,
                    "q": args.q,
                    "topics": args.topics,
                },
            ),
            indent=2,
        )
    )


def cmd_send(args: argparse.Namespace) -> None:
    print(json.dumps(request("POST", "/api/send", body={"chat_id": args.chat_id, "text": args.text}), indent=2))


def cmd_send_file(args: argparse.Namespace) -> None:
    chat_id = resolve_chat_id(
        args.chat_id,
        env_names=("NOTIFY_TELEGRAM_CHAT_ID", "EOD_TELEGRAM_CHAT_ID", "TELEGRAM_CHAT_ID"),
    )
    text = read_file_text(args.file)
    print(json.dumps(request("POST", "/api/send", body={"chat_id": chat_id, "text": text}), indent=2))


def cmd_send_eod(args: argparse.Namespace) -> None:
    chat_id = resolve_chat_id(args.chat_id, env_names=("EOD_TELEGRAM_CHAT_ID",))
    text = read_file_text(args.file)
    print(json.dumps(request("POST", "/api/send", body={"chat_id": chat_id, "text": text}), indent=2))


def cmd_reply_mode(_: argparse.Namespace) -> None:
    print(json.dumps(request("GET", "/api/settings/reply-mode"), indent=2))


def main() -> None:
    load_env_file(SKILL_ENV)

    parser = argparse.ArgumentParser(description="Telegram Dashboard CLI for OpenClaw")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("manifest", help="Agent tool manifest").set_defaults(func=cmd_manifest)
    sub.add_parser("metrics", help="Dashboard metrics").set_defaults(func=cmd_metrics)
    sub.add_parser("reply-mode", help="Reply mode and per-chat settings").set_defaults(func=cmd_reply_mode)

    p_messages = sub.add_parser("messages", help="List messages")
    p_messages.add_argument("--user-ids", default="")
    p_messages.add_argument("--chat-type", default=None)
    p_messages.add_argument("--direction", default=None)
    p_messages.add_argument("--q", default=None)
    p_messages.add_argument("--topics", default=None)
    p_messages.add_argument("--limit", default=50)
    p_messages.set_defaults(func=cmd_messages)

    p_threads = sub.add_parser("threads", help="List conversation threads")
    p_threads.add_argument("--user-ids", default="")
    p_threads.add_argument("--chat-type", default=None)
    p_threads.add_argument("--direction", default=None)
    p_threads.add_argument("--q", default=None)
    p_threads.add_argument("--topics", default=None)
    p_threads.add_argument("--limit", default=20)
    p_threads.set_defaults(func=cmd_threads)

    p_sum = sub.add_parser("summarize", help="AI summarize filtered messages")
    p_sum.add_argument("--summary-type", default="brief")
    p_sum.add_argument("--user-ids", default="")
    p_sum.add_argument("--chat-type", default=None)
    p_sum.add_argument("--direction", default=None)
    p_sum.add_argument("--q", default=None)
    p_sum.add_argument("--topics", default=None)
    p_sum.set_defaults(func=cmd_summarize)

    p_sug = sub.add_parser("suggest", help="AI suggest replies/actions")
    p_sug.add_argument("--user-ids", default="")
    p_sug.add_argument("--chat-type", default=None)
    p_sug.add_argument("--direction", default=None)
    p_sug.add_argument("--q", default=None)
    p_sug.add_argument("--topics", default=None)
    p_sug.set_defaults(func=cmd_suggest)

    p_send = sub.add_parser("send", help="Send Telegram message")
    p_send.add_argument("--chat-id", required=True)
    p_send.add_argument("--text", required=True)
    p_send.set_defaults(func=cmd_send)

    p_send_file = sub.add_parser("send-file", help="Send file contents as Telegram message")
    p_send_file.add_argument("--file", required=True, help="Path to text/markdown file")
    p_send_file.add_argument("--chat-id", default=None, help="Chat ID or @username (default from env)")
    p_send_file.set_defaults(func=cmd_send_file)

    p_send_eod = sub.add_parser("send-eod", help="Send EOD markdown file (uses EOD_TELEGRAM_CHAT_ID)")
    p_send_eod.add_argument("--file", required=True, help="Path to eod-YYYY-MM-DD.md")
    p_send_eod.add_argument("--chat-id", default=None, help="Override EOD_TELEGRAM_CHAT_ID")
    p_send_eod.set_defaults(func=cmd_send_eod)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
