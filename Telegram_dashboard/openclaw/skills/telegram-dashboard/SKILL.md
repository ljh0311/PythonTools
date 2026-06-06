---
name: telegram-dashboard
description: Read Telegram operator inbox, summarize messages, suggest replies, and send messages via the local dashboard API.
metadata:
  {"openclaw":{"requires":{"env":["TELEGRAM_DASHBOARD_URL","DASHBOARD_API_KEY"],"bins":["python3"]},"primaryEnv":"DASHBOARD_API_KEY"}}
---

# Telegram Dashboard

Use this skill when the user asks about Telegram inbox messages, operator workflow, summaries, suggested replies, or sending Telegram messages through the dashboard.

## Configuration

Set these environment variables (via `skills.entries.telegram-dashboard` in `openclaw.json` or your shell):

| Variable | Example | Purpose |
|----------|---------|---------|
| `TELEGRAM_DASHBOARD_URL` | `http://localhost:8000` | Dashboard base URL |
| `DASHBOARD_API_KEY` | `your-secret-key` | API authentication |

Docker note: from another container on the same compose network, use `http://telegram-dashboard:8000`.

## Helper script

Run commands with the bundled CLI (no extra dependencies):

```bash
python3 {baseDir}/scripts/tdash.py manifest
python3 {baseDir}/scripts/tdash.py metrics
python3 {baseDir}/scripts/tdash.py messages --q billing --limit 20
python3 {baseDir}/scripts/tdash.py threads --chat-type group
python3 {baseDir}/scripts/tdash.py summarize --summary-type brief --topics billing
python3 {baseDir}/scripts/tdash.py suggest --user-ids 101
python3 {baseDir}/scripts/tdash.py send --chat-id 1001 --text "Thanks, we will follow up."
python3 {baseDir}/scripts/tdash.py reply-mode
```

Always prefer `tdash.py` over crafting raw curl — it handles auth headers and JSON encoding.

## Direct API (when scripting)

All requests need:

```
X-API-Key: $DASHBOARD_API_KEY
```

Agent discovery endpoint:

```
GET $TELEGRAM_DASHBOARD_URL/api/agent/manifest
```

OpenAPI spec:

```
GET $TELEGRAM_DASHBOARD_URL/openapi.json
```

## Common workflows

1. **Check inbox** — `tdash.py messages` or `tdash.py threads`
2. **Summarize a situation** — `tdash.py summarize` with the same filters the operator would use
3. **Draft replies** — `tdash.py suggest` then review before `tdash.py send`
4. **Workflow check** — `tdash.py reply-mode` shows auto-reply mode and per-chat relationship context

## Safety

- Do not send messages without explicit user approval unless they asked you to send.
- Summaries and suggestions may involve redacted sensitive data — originals stay in the database.
- Relationship context per chat helps tailor replies; read it from `reply-mode` before drafting.
