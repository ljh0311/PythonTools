# Docker mode — Telegram Dashboard

Run the dashboard in a container for a consistent local setup. Data persists in a Docker volume.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2
- A `.env` file (copy from `.env.example`)

## First-time setup

```bash
cd Telegram_dashboard
cp .env.example .env
```

Edit `.env` and set at minimum:

| Variable | Notes |
|----------|-------|
| `DASHBOARD_API_KEY` | Secret for API/OpenClaw access — change from default |
| `OPERATOR_PASSWORD` | Dashboard login password (recommended) |
| `OPERATOR_USERNAME` | Login username (default `admin`) |
| `TELEGRAM_BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) if using Telegram |
| `GEMINI_API_KEY` | Optional; for AI summaries |

Build and start:

```bash
docker compose up -d --build
```

Open: [http://localhost:8000](http://localhost:8000)

## Daily commands

| Task | Command |
|------|---------|
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| View logs | `docker compose logs -f telegram-dashboard` |
| Restart after `.env` change | `docker compose up -d --build` |
| Check health | `curl http://localhost:8000/api/health` |

## Data persistence

SQLite database is stored in the `dashboard-data` volume at `/app/data/dashboard.db` inside the container.

Backup:

```bash
docker compose exec telegram-dashboard cat /app/data/dashboard.db > backup-dashboard.db
```

Restore (stop container first):

```bash
docker compose down
docker run --rm -v telegram_dashboard_dashboard-data:/data -v "$PWD":/backup alpine \
  cp /backup/backup-dashboard.db /data/dashboard.db
docker compose up -d
```

## Telegram webhook (local)

Telegram requires HTTPS for webhooks. For local Docker:

1. Use a tunnel (ngrok, Cloudflare Tunnel) pointing to `localhost:8000`
2. Register webhook:

```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://YOUR-TUNNEL/webhook/telegram","secret_token":"YOUR_TELEGRAM_WEBHOOK_SECRET"}'
```

## OpenClaw on the same laptop

| OpenClaw runs… | Guide | Dashboard URL in OpenClaw config |
|----------------|-------|----------------------------------|
| On host (not Docker) | below | `http://localhost:8000` |
| **In Docker (same laptop)** | **[docs/openclaw-docker-laptop.md](docs/openclaw-docker-laptop.md)** | **`http://telegram-dashboard:8000`** |

This compose file joins network **`openclaw-net`**. Connect your OpenClaw container:

```bash
docker network connect openclaw-net YOUR_OPENCLAW_CONTAINER_NAME
```

Host-only OpenClaw config:

```json5
// ~/.openclaw/openclaw.json
{
  skills: {
    entries: {
      "telegram-dashboard": {
        enabled: true,
        env: {
          TELEGRAM_DASHBOARD_URL: "http://localhost:8000",
          DASHBOARD_API_KEY: "same-as-your-env-file",
        },
      },
    },
  },
}
```

## Seed demo data (optional)

```bash
docker compose exec telegram-dashboard python3 scripts/seed_demo_data.py
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 8000 in use | Set `PORT=8001` in `.env` and update compose port mapping |
| 401 on API | Check `DASHBOARD_API_KEY` matches between client and `.env` |
| Login loop | Set `OPERATOR_PASSWORD` in `.env` and restart container |
| AI summaries empty | Add `GEMINI_API_KEY` or run Ollama on host (`OLLAMA_BASE_URL=http://host.docker.internal:11434/v1`) |

## Maintenance checklist

- [ ] Rotate `DASHBOARD_API_KEY` periodically
- [ ] Back up `dashboard-data` volume before upgrades
- [ ] Run `docker compose pull && docker compose up -d --build` after pulling code changes
- [ ] Review logs weekly: `docker compose logs --tail=200`
