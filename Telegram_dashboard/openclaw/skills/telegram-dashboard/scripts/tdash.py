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


def cmd_reply_mode(_: argparse.Namespace) -> None:
    print(json.dumps(request("GET", "/api/settings/reply-mode"), indent=2))


def main() -> None:
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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
