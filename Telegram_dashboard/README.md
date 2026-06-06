# Telegram Dashboard & Chatbot

A responsive Telegram bot dashboard with real-time metrics, chat logs, quick actions, analytics, and AI-powered message handling.

## Features

- **Dashboard UI**: Dark/light theme, live metrics, message feed, events log, feedback panel
- **Telegram integration**: Webhook receiver and secure send-message API
- **AI routing**: OpenAI-compatible chat with tool calls for metrics, analytics, and webhooks
- **Real-time updates**: WebSocket push to the dashboard

## Project Structure

```
Telegram_dashboard/
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

4. Start the server:

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
| POST | `/webhook/telegram` | Telegram update webhook |

## AI Tools

When `OPENAI_API_KEY` is set, the bot can call:

- `get_metrics` — dashboard counters
- `analyze_command_usage` — 7-day command trends
- `webhook_notify` — POST to an external webhook URL

Without an API key, built-in `/help`, `/status`, `/analytics`, and `/feedback` commands still work.
