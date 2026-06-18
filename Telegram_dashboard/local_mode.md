# Local mode — Telegram Dashboard (no Docker)

Run directly on your machine with Python. Best for development and quick iteration.

## Prerequisites

- **Python 3.12** (required — use `py -3.12` on Windows; do **not** use Python 3.14; pinned deps lack 3.14 wheels and `pip install` will fail building `pydantic-core`)
- `pip` and `venv`
- Optional: [Ollama](https://ollama.ai) for local AI fallback
- Optional: Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## First-time setup

**Windows (PowerShell):**

```powershell
cd Telegram_dashboard
py -3.12 -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

**macOS / Linux:**

```bash
cd Telegram_dashboard
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` — see `.env.example` for all options. Minimum recommended:

```env
DASHBOARD_API_KEY=choose-a-long-random-secret
OPERATOR_USERNAME=admin
OPERATOR_PASSWORD=choose-a-strong-password
```

## Start the app

**Windows (PowerShell):**

```powershell
cd Telegram_dashboard
.\venv\Scripts\activate
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**macOS / Linux:**

```bash
source venv/bin/activate
export PYTHONPATH="$(pwd)"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Or use the helper script (macOS / Linux):

```bash
./run.sh
```

Open: [http://localhost:8000](http://localhost:8000)

- If `OPERATOR_PASSWORD` is set → you’ll be asked to log in at `/login`
- If not set → dev mode uses API key only (default key `dev-dashboard-key`)

> **Tip:** If login fails with “invalid username or password”, stop any stale server on port 8000 and restart without `--reload`. Ensure `.env` credentials have no stray spaces.

## Real Telegram messages (not demo data)

The inbox only shows messages **received by your bot after setup**. It does **not** import your full Telegram chat history.

| What you see | Why |
|--------------|-----|
| `@alice`, `@bob_dev`, `@carol`, “Project Alpha” | Demo data from `scripts/seed_demo_data.py` |
| Your real chats | Bot received updates via polling or webhook |

**Local setup (no ngrok):**

1. In `.env`, set your bot token and enable polling:

```env
TELEGRAM_BOT_TOKEN=your-token-from-BotFather
TELEGRAM_POLLING=true
```

2. Remove demo data (optional but recommended):

```powershell
# stop the server first
Remove-Item data\dashboard.db
```

3. Restart the dashboard (see **Start the app** above).

4. In Telegram, open your bot (`@tel_dashbot` or whatever BotFather gave you) and send a message (e.g. `/start` or “hello”).

5. Refresh the dashboard — your message should appear.

> **Note:** Bots only see messages sent **to the bot** (private chat), in **groups where the bot is a member**, or **channel posts** after the bot is added as a **channel admin**. They cannot read your other Telegram conversations or old posts from before the bot was added.

### Channels

1. In Telegram → channel → **Manage** → **Administrators** → add your bot as an admin (posting rights optional; admin is required to receive updates).
2. Post a **new** message in the channel (older posts are not backfilled).
3. Channel updates arrive as `channel_post` (not regular chat `message` events).

**Production / HTTPS:** set `TELEGRAM_POLLING=false` and register a webhook — see [Telegram webhook](#telegram-webhook) below.

## Seed demo data (optional)

Only for UI testing without a real bot:

```bash
python scripts/seed_demo_data.py
```

## OpenClaw integration

Install the skill into your OpenClaw workspace:

```bash
openclaw skills install /absolute/path/to/Telegram_dashboard/openclaw/skills/telegram-dashboard
```

Or add to `~/.openclaw/openclaw.json`:

```json5
{
  skills: {
    load: {
      extraDirs: ["/absolute/path/to/Telegram_dashboard/openclaw/skills"],
    },
    entries: {
      "telegram-dashboard": {
        enabled: true,
        env: {
          TELEGRAM_DASHBOARD_URL: "http://localhost:8000",
          DASHBOARD_API_KEY: "same-value-as-in-your-.env",
        },
      },
    },
  },
}
```

Test from terminal:

```bash
export TELEGRAM_DASHBOARD_URL=http://localhost:8000
export DASHBOARD_API_KEY=your-key
python openclaw/skills/telegram-dashboard/scripts/tdash.py metrics
```

See [docs/openclaw-integration.md](docs/openclaw-integration.md) for full details.

## Telegram webhook

For local testing without HTTPS you can use long-polling separately, but this dashboard expects webhook mode. Use a tunnel:

1. `ngrok http 8000`
2. Point Telegram webhook to `https://xxxx.ngrok.io/webhook/telegram`

## Daily commands

| Task | Windows (PowerShell) | macOS / Linux |
|------|----------------------|---------------|
| Start | `.\venv\Scripts\activate`; `$env:PYTHONPATH = (Get-Location).Path`; `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000` | `PYTHONPATH=. uvicorn backend.main:app --reload --port 8000` |
| Stop | `Ctrl+C` in terminal | `Ctrl+C` in terminal |
| Reset demo DB | `Remove-Item data\dashboard.db`; `python scripts\seed_demo_data.py` | `rm data/dashboard.db && python scripts/seed_demo_data.py` |
| Export inbox | Use **Export CSV** in the Inbox UI | Use **Export CSV** in the Inbox UI |

## Environment reference

| Variable | Purpose |
|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot API token |
| `TELEGRAM_WEBHOOK_SECRET` | Validates incoming webhooks |
| `GEMINI_API_KEY` | Primary AI provider |
| `OLLAMA_BASE_URL` | Local AI fallback |
| `DASHBOARD_API_KEY` | Machine/API access (OpenClaw, scripts) |
| `OPERATOR_USERNAME` / `OPERATOR_PASSWORD` | Human login |
| `AUTO_REPLY_MODE` | `manual` \| `auto` \| `per_chat` |
| `TOPIC_MODE` | `user_type` \| `ai_assign` |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `pip install` fails on `pydantic-core` | Recreate the venv with Python 3.12: `py -3.12 -m venv venv` (Windows) or `python3.12 -m venv venv` (Unix). Do not use the default `python` if it is 3.14. |
| `ModuleNotFoundError: backend` | Set `PYTHONPATH` to project root |
| Port in use | Change `PORT` in `.env` or use `--port 8001`; kill stale `uvicorn` on 8000 |
| Login always fails | Restart server without `--reload`; check `.env` for trailing spaces in credentials |
| Only fake users (`@carol`, `@bob_dev`) | Demo seed data — delete `data/dashboard.db`, set `TELEGRAM_POLLING=true`, message your bot |
| No new messages appear | Send a message to the bot in Telegram; confirm `TELEGRAM_POLLING=true` or webhook is registered |
| Auto-reply loops in groups | Restart server after update; bot no longer replies to its own messages |
| WebSocket disconnects | Ensure same auth token/API key as REST calls |
| OpenClaw can’t reach API | Confirm dashboard is running; check URL and API key |

## When to switch to Docker

Use [docker_mode.md](docker_mode.md) when you want:

- Isolated dependencies
- Persistent volume without managing `data/` manually
- Same setup on multiple machines
- Running alongside other containerized services (including OpenClaw)
