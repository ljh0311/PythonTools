# Local mode — Telegram Dashboard (no Docker)

Run directly on your machine with Python. Best for development and quick iteration.

## Prerequisites

- Python 3.11+ (3.12 recommended)
- `pip` and `venv`
- Optional: [Ollama](https://ollama.ai) for local AI fallback
- Optional: Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## First-time setup

```bash
cd Telegram_dashboard
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
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

```bash
source .venv/bin/activate
export PYTHONPATH="$(pwd)"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Or use the helper script:

```bash
./run.sh
```

Open: [http://localhost:8000](http://localhost:8000)

- If `OPERATOR_PASSWORD` is set → you’ll be asked to log in at `/login`
- If not set → dev mode uses API key only (default key `dev-dashboard-key`)

## Seed demo data (optional)

```bash
python3 scripts/seed_demo_data.py
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
python3 openclaw/skills/telegram-dashboard/scripts/tdash.py metrics
```

See [docs/openclaw-integration.md](docs/openclaw-integration.md) for full details.

## Telegram webhook

For local testing without HTTPS you can use long-polling separately, but this dashboard expects webhook mode. Use a tunnel:

1. `ngrok http 8000`
2. Point Telegram webhook to `https://xxxx.ngrok.io/webhook/telegram`

## Daily commands

| Task | Command |
|------|---------|
| Start (dev) | `PYTHONPATH=. uvicorn backend.main:app --reload --port 8000` |
| Stop | `Ctrl+C` in terminal |
| Reset demo DB | `rm data/dashboard.db && python3 scripts/seed_demo_data.py` |
| Export inbox | Use **Export CSV** in the Inbox UI |

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
| `ModuleNotFoundError: backend` | Set `PYTHONPATH` to project root |
| Port in use | Change `PORT` in `.env` or use `--port 8001` |
| WebSocket disconnects | Ensure same auth token/API key as REST calls |
| OpenClaw can’t reach API | Confirm dashboard is running; check URL and API key |

## When to switch to Docker

Use [docker_mode.md](docker_mode.md) when you want:

- Isolated dependencies
- Persistent volume without managing `data/` manually
- Same setup on multiple machines
- Running alongside other containerized services (including OpenClaw)
