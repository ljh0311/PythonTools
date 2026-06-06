# Deployment guide

Quick reference for running the Telegram Dashboard locally. For step-by-step instructions see:

- [local_mode.md](../local_mode.md) — Python venv, no containers
- [docker_mode.md](../docker_mode.md) — Docker Compose, volumes, maintenance

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | For live bot | Telegram BotFather token |
| `TELEGRAM_WEBHOOK_SECRET` | Recommended | Webhook header validation |
| `DASHBOARD_API_KEY` | Yes | API/OpenClaw authentication |
| `OPERATOR_USERNAME` | If using login | Browser login username |
| `OPERATOR_PASSWORD` | Recommended | Browser login password |
| `GEMINI_API_KEY` | For AI | Primary summarization provider |
| `OLLAMA_BASE_URL` | Optional | Local AI fallback |
| `AUTO_REPLY_MODE` | Optional | `manual` (default), `auto`, `per_chat` |
| `TOPIC_MODE` | Optional | `user_type` (default), `ai_assign` |
| `HOST` / `PORT` | Optional | Bind address (default `0.0.0.0:8000`) |

## HTTPS webhook checklist

1. Dashboard reachable on HTTPS (reverse proxy or tunnel)
2. `POST /webhook/telegram` with `X-Telegram-Bot-Api-Secret-Token`
3. Register webhook via Telegram Bot API `setWebhook`
4. Confirm with `getWebhookInfo`

## Backups

- SQLite file: `data/dashboard.db`
- Docker: volume `dashboard-data` (see docker_mode.md)

## OpenClaw

See [openclaw-integration.md](openclaw-integration.md). Mount the **skills folder only**, not the full repo.

## Production hardening (future)

- Put nginx/Caddy in front with TLS
- Restrict CORS origins in `backend/main.py`
- Use strong `DASHBOARD_API_KEY` and `OPERATOR_PASSWORD`
- Do not expose Ollama to the public internet
