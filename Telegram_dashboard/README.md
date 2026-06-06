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

## Run modes

| Mode | Guide |
|------|-------|
| **Local (no Docker)** | [local_mode.md](local_mode.md) |
| **Docker** | [docker_mode.md](docker_mode.md) |
| **OpenClaw agent** | [docs/openclaw-integration.md](docs/openclaw-integration.md) |
| **OpenClaw + Docker (same laptop)** | [docs/openclaw-docker-laptop.md](docs/openclaw-docker-laptop.md) |

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
GEMINI_MODEL=gemini-2.0-flash
```

**Ollama (fallback)** — install from [ollama.ai](https://ollama.ai), pull a model, and start the service:

```bash
ollama pull llama3.2
ollama serve
```

```env
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.2
```

The bot tries Gemini first. If Gemini fails or is not configured, it falls back to Ollama. If both are unavailable, built-in `/help`, `/status`, `/analytics`, and `/feedback` commands still work.

5. Start the server:

```bash
python -m backend.main
```

Open `http://localhost:8000` for the dashboard.

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
