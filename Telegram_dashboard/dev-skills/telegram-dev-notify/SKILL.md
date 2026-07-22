---
name: telegram-dev-notify
description: >-
  Sends arbitrary text, markdown files, or reports to Telegram through the local
  Telegram Dashboard API. Use when delivering EOD summaries, audit notes, feature
  tracking updates, team alerts, or any dev workflow notification to Telegram.
---

# Telegram Dev Notify

**Scope:** personal/general skill (`~/.cursor/skills/telegram-dev-notify/`). Works in any workspace. Not tied to one repo.

Send text or file content to a Telegram chat via the running Telegram Dashboard `POST /api/send` endpoint.

## Dashboard UI (Dev notify / EOD)

When the dashboard is running locally, operators can send without CLI:

1. Open **Tools** in the sidebar.
2. Use the **Dev notify / EOD** card (full-width below Quick actions).
3. Paste markdown or **Load markdown file**, pick recipient from the compose list, optionally **Prefix with EOD header**, then **Send via bot**.

Character count shows live vs the 4096 Telegram limit. Icons: `openclaw/skills/telegram-dashboard/assets/icon-dev-notify.svg`.

## Install

Copy this folder to your personal skills directory:

```bash
# macOS / Linux
cp -r Telegram_dashboard/dev-skills/telegram-dev-notify ~/.cursor/skills/

# Windows (PowerShell)
Copy-Item -Recurse Telegram_dashboard\dev-skills\telegram-dev-notify $env:USERPROFILE\.cursor\skills\
```

Create the skill-local env file from the template:

```bash
cp ~/.cursor/skills/telegram-dev-notify/.env.example ~/.cursor/skills/telegram-dev-notify/.env
```

| Variable | Purpose |
|----------|---------|
| `TELEGRAM_DASHBOARD_URL` | Dashboard base URL (default `http://localhost:8000`) |
| `DASHBOARD_API_KEY` | Client key; must match the dashboard server `.env` |
| `NOTIFY_TELEGRAM_CHAT_ID` | Default numeric chat ID or resolvable `@username` |

Process environment wins over the skill `.env` file.

## Send helper

Prefer the bundled script (stdlib only, no pip deps):

```bash
python {baseDir}/scripts/send_notify.py --text "Deploy finished on staging."
python {baseDir}/scripts/send_notify.py --file reports/audit-2026-07-22.md
python {baseDir}/scripts/send_notify.py --file docs/eod/eod-2026-07-22.md --chat-id 123456789
python {baseDir}/scripts/send_notify.py --file note.md --dry-run
```

**Rules:**

- Dashboard server must be running.
- Telegram message limit is ~4096 characters — the script truncates with a footer note; keep full content on disk.
- Use `--chat-id` to override the default recipient for one-off sends.
- Do not send without user approval unless they explicitly asked.

## Common workflows

### EOD summaries

The **end-of-day-summary** skill generates the markdown file. **This skill delivers it.** After saving `docs/eod/eod-YYYY-MM-DD.md`, send with:

```bash
python {baseDir}/scripts/send_notify.py --file docs/eod/eod-YYYY-MM-DD.md
```

Optional EOD body template: [templates/eod.md](templates/eod.md)

### Audit / feature notes

Write any markdown or plain-text report in the repo, then:

```bash
python {baseDir}/scripts/send_notify.py --file path/to/report.md
```

### Quick alerts

```bash
python {baseDir}/scripts/send_notify.py --text "CI green on main — ready to tag v1.2."
```

## OpenClaw alternative

When OpenClaw is available, the bundled dashboard skill also supports file sends:

```bash
python3 Telegram_dashboard/openclaw/skills/telegram-dashboard/scripts/tdash.py send-file --chat-id ID --file report.md
```

Use whichever CLI matches the agent runtime; both hit the same API.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `DASHBOARD_API_KEY is not set` | Copy `.env.example` → `.env` and set the key |
| `HTTP 401` | Client key does not match dashboard server |
| `Request failed: Connection refused` | Start the dashboard (`uvicorn` / docker compose) |
| Message truncated | Expected for long files; full file remains on disk |

## Additional resources

- Env template: [.env.example](.env.example)
- Send script: [scripts/send_notify.py](scripts/send_notify.py)
- EOD template: [templates/eod.md](templates/eod.md)
