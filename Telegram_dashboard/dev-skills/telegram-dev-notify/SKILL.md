---
name: telegram-dev-notify
description: >-
  Sends arbitrary text, markdown files, or reports to Telegram through the local
  Telegram Dashboard API. Use when delivering EOD summaries, audit notes, feature
  tracking updates, team alerts, or any dev workflow notification to Telegram.
---

# Telegram Dev Notify

**Scope:** personal/general skill (`~/.cursor/skills/telegram-dev-notify/`). Works in any workspace.

Send text or file content to Telegram via Dashboard `POST /api/send`. **Canonical client:** `tdash.py` from the OpenClaw telegram-dashboard skill; this pack provides a thin wrapper for Cursor agents.

## Install

```bash
# macOS / Linux
cp -r Telegram_dashboard/dev-skills/telegram-dev-notify ~/.cursor/skills/

# Windows (PowerShell)
Copy-Item -Recurse Telegram_dashboard\dev-skills\telegram-dev-notify $env:USERPROFILE\.cursor\skills\
```

Configure env (copy [.env.example](.env.example) → `.env`):

| Variable | Purpose |
|----------|---------|
| `TELEGRAM_DASHBOARD_URL` | Dashboard base URL (default `http://localhost:8000`) |
| `DASHBOARD_API_KEY` | Client key; must match dashboard server `.env` |
| `NOTIFY_TELEGRAM_CHAT_ID` | Default numeric chat ID or resolvable `@username` |

Process environment wins over the skill `.env` file.

## Send (preferred order)

**1. tdash.py** (canonical, when Telegram_dashboard is available):

```bash
python3 Telegram_dashboard/openclaw/skills/telegram-dashboard/scripts/tdash.py send --chat-id ID --text "Deploy finished."
python3 Telegram_dashboard/openclaw/skills/telegram-dashboard/scripts/tdash.py send-file --file reports/audit.md
```

**2. Skill wrapper** (delegates to tdash when found, else stdlib HTTP):

```bash
python {baseDir}/scripts/send_notify.py --text "CI green on main."
python {baseDir}/scripts/send_notify.py --file docs/eod/eod-2026-07-22.md
python {baseDir}/scripts/send_notify.py --file note.md --chat-id 123456789 --dry-run
```

**Rules:** dashboard must be running; ~4096 char limit with truncation; do not send without user approval unless they asked.

## Common workflows

### EOD summaries

Pair with **end-of-day-summary** skill. After saving `docs/eod/eod-YYYY-MM-DD.md`:

```bash
python3 Telegram_dashboard/openclaw/skills/telegram-dashboard/scripts/tdash.py send-eod --file docs/eod/eod-YYYY-MM-DD.md
```

### Audit / feature notes

```bash
python {baseDir}/scripts/send_notify.py --file path/to/report.md
```

Template: [templates/eod.md](templates/eod.md)

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `DASHBOARD_API_KEY is not set` | Copy `.env.example` → `.env` |
| `HTTP 401` | Client key mismatch |
| Connection refused | Start dashboard (`python -m backend.main`) |

## Additional resources

- Env template: [.env.example](.env.example)
- Wrapper: [scripts/send_notify.py](scripts/send_notify.py)
