---
name: telegram-dashboard
description: Read Telegram operator inbox, summarize messages, suggest replies, send messages and dev reports (EOD, audit notes) via the local dashboard API.
metadata:
  {"openclaw":{"requires":{"env":["TELEGRAM_DASHBOARD_URL","DASHBOARD_API_KEY"],"bins":["python3"]},"primaryEnv":"DASHBOARD_API_KEY"}}
---

# Telegram Dashboard

Use this skill when the user asks about Telegram inbox messages, operator workflow, summaries, suggested replies, sending Telegram messages through the dashboard, or delivering dev reports (EOD summaries, audit notes, team alerts).

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
python3 {baseDir}/scripts/tdash.py send-file --chat-id 1001 --file docs/eod/eod-2026-07-22.md
python3 {baseDir}/scripts/tdash.py reply-mode
```

Always prefer `tdash.py` over crafting raw curl — it handles auth headers, JSON encoding, and Telegram length limits (~4096 chars, truncated with a footer note for file sends).

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
5. **Dev notify / EOD (dashboard UI)** — open the running dashboard → **Tools** → **Dev notify / EOD** card: paste or load markdown, pick recipient, optional EOD header prefix, send via bot. Same `POST /api/send` as `tdash.py send`.
6. **Dev notify / EOD (CLI)** — `tdash.py send-file --file path/to/report.md [--chat-id ID]`

### EOD and dev-notify (Cursor skills)

For Cursor agents, prefer the staged personal skill packs under `Telegram_dashboard/dev-skills/`:

| Skill | Role |
|-------|------|
| `end-of-day-summary` | Collect git/session work, write `docs/eod/eod-YYYY-MM-DD.md` |
| `telegram-dev-notify` | Send any text/file via `send_notify.py` (EOD, audits, alerts) |

Install both to `~/.cursor/skills/`, configure `.env`, then EOD flow is: write file → `send_eod.py` or `send_notify.py`.

OpenClaw can use `send-file` directly when those skills are not loaded.

Brand/icons for UI or docs: `{baseDir}/assets/icon-operator.svg`, `icon-send.svg`, `icon-eod.svg`.

## Safety

- Do not send messages without explicit user approval unless they asked you to send.
- Summaries and suggestions may involve redacted sensitive data — originals stay in the database.
- Relationship context per chat helps tailor replies; read it from `reply-mode` before drafting.
- Long files are truncated for Telegram; keep the full markdown on disk.

