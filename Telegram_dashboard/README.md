# Telegram Dashboard & Chatbot

A responsive Telegram bot dashboard with real-time metrics, chat logs, quick actions, analytics, and AI-powered message handling.

## Project documentation (Agile)

Planning and backlog documentation lives in [`docs/`](docs/README.md):

- [Product Vision](docs/product-vision.md)
- [Current Increment (Sprint 0)](docs/current-increment.md)
- [Product Backlog](docs/product-backlog.md)
- [Sprint Plan](docs/sprint-plan.md)
- [Definition of Done](docs/definition-of-done.md)
- [Architecture](docs/architecture.md)
- [Risks & Decisions](docs/risks-and-decisions.md)

## Features

- **Dashboard UI**: Dark/light theme, live metrics, message feed, events log, feedback panel
- **Telegram integration**: Webhook receiver and secure send-message API
- **AI routing**: Gemini primary with Ollama fallback, plus tool calls for metrics, analytics, and webhooks
- **Real-time updates**: WebSocket push to the dashboard

## Project Structure

```
Telegram_dashboard/
├── docs/                    # Agile project documentation
├── backend/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py              # Environment configuration
│   ├── models/store.py        # SQLite persistence layer
│   ├── routes/api.py          # Dashboard REST + WebSocket endpoints
│   ├── routes/webhook.py      # Telegram webhook endpoint
│   └── services/              # Telegram, AI, and bot handler modules
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   └── js/                    # Modular dashboard scripts
├── requirements.txt
└── .env.example
```

## Versions

| Version | What it does | Setup |
|---------|--------------|-------|
| **v0.1** | Bot inbox — PMs to bot + groups the bot is in | `TELEGRAM_BOT_TOKEN` + webhook |
| **v0.2** | Your personal account — all chats you are in | [docs/user-inbox.md](docs/user-inbox.md) |

Both can run together. Filter by source in the Inbox UI.

## Quick start on your laptop

See **[SETUP_LAPTOP.md](SETUP_LAPTOP.md)** for copy-paste steps (clone → install → run → open browser).

## Run modes

| Mode | Guide |
|------|-------|
| **Local (no Docker)** | [local_mode.md](local_mode.md) |
| **Docker** | [docker_mode.md](docker_mode.md) |
| **OpenClaw agent** | [docs/openclaw-integration.md](docs/openclaw-integration.md) |
| **OpenClaw + Docker (same laptop)** | [docs/openclaw-docker-laptop.md](docs/openclaw-docker-laptop.md) |
| **User inbox (v0.2)** | [docs/user-inbox.md](docs/user-inbox.md) |

## Setup

1. Create a virtual environment and install dependencies:

```bash
cd Telegram_dashboard
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Copy environment variables:

```bash
cp .env.example .env
```

3. Set your Telegram bot token from [@BotFather](https://t.me/BotFather).

4. Configure AI providers in `.env`:

**Gemini (primary)** — get a free API key from [Google AI Studio](https://aistudio.google.com/apikey):

```env
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.6-flash
AI_PRIMARY_PROVIDER=gemini
```

**Ollama (fallback)** — install from [ollama.ai](https://ollama.ai), pull a model, and start the service:

```bash
ollama pull llama3.2
ollama serve
```

```env
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:3b
```

The app tries Gemini first (`AI_PRIMARY_PROVIDER=gemini`). On 429 or other Gemini errors it falls back to Ollama; failure text redacts API keys. If both are unavailable, built-in `/help`, `/status`, `/analytics`, and `/feedback` commands still work.

5. Start the server:

```bash
python -m backend.main
```

Open `http://localhost:8000` for the dashboard.

## Dashboard v2 (Awareness)

Personal awareness UI **alongside** the classic Operator dashboard (v1 is not replaced).

| URL | UI |
|-----|-----|
| `http://localhost:8000/` | **v1 Operator** — inbox, analytics, tools, bot ops |
| `http://localhost:8000/v2` | **v2 Awareness** — Talk / Act / Profiles |

### How to open

1. Start the server as usual (`python -m backend.main`).
2. Sign in if prompted (`/login`, same operator auth as v1).
3. Open **`/v2`**, or use **Open classic dashboard** from v2 to return to `/`.

Cloud Agents: see **[AGENTS.md](AGENTS.md)** (install → env → start → health → Desktop checklist).

### Current state

Early usable slice:

- **Talk** — browse personal (`user_account`) threads and messages
- **Act** — AI suggestion queue with done/dismiss; heuristic “open” threads from API
- **Profiles** — Markdown contact cards in `data/profiles/`, editable + refresh-from-chat

Focused tests: `pytest backend/tests/test_profile_md.py backend/tests/test_v2_act.py`.

### What needs improvement

1. Talk send/reply and richer filters (v1 inbox is still deeper for ops)
2. Surface Act `open_items` in the UI; tighter AI empty/degraded feedback
3. Create/open Profiles from Talk without leaving the view
4. Demo path when MTProto is off (Talk often empty without user-account ingest)
5. Broader automated coverage (Talk routes, UI smoke)

### Known gaps vs v1 Operator

No metrics/analytics/tools panels on `/v2`; no message send from Talk; UI biased to user-account data. Full detail: **[docs/v2.md](docs/v2.md)**. Session notes: **[docs/dev-log.md](docs/dev-log.md)**.

## Telegram Webhook

Point Telegram to your public HTTPS endpoint:

```
POST https://your-domain.com/webhook/telegram
Header: X-Telegram-Bot-Api-Secret-Token: <TELEGRAM_WEBHOOK_SECRET>
```

You can register the webhook with:

```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://your-domain.com/webhook/telegram","secret_token":"change-me"}'
```

## API Authentication

Dashboard API requests require:

```
X-API-Key: <DASHBOARD_API_KEY>
```

The default development key is `dev-dashboard-key`.

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/metrics` | Connected users and totals |
| GET | `/api/messages` | Recent chat log |
| GET | `/api/events` | Incoming Telegram events |
| GET | `/api/analytics/commands` | Command usage chart data |
| GET/PUT | `/api/quick-actions` | Manage quick command buttons |
| POST | `/api/send` | Send a Telegram message |
| POST | `/api/feedback` | Submit user feedback |
| WS | `/api/ws?api_key=...` | Real-time dashboard updates |
| GET | `/api/ai/status` | Gemini/Ollama provider status |
| POST | `/webhook/telegram` | Telegram update webhook |

## AI Tools

When Gemini or Ollama is available, the bot can call:

- `get_metrics` — dashboard counters
- `analyze_command_usage` — 7-day command trends
- `webhook_notify` — POST to an external webhook URL

Without AI providers, built-in `/help`, `/status`, `/analytics`, and `/feedback` commands still work.
