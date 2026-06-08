# OpenClaw + Dashboard — both in Docker on the same laptop

Use this guide when **both** OpenClaw and the Telegram Dashboard run as Docker containers on one machine.

## The idea (layman terms)

- Your **browser** opens the dashboard at `http://localhost:8000` (port published to your laptop).
- **OpenClaw** talks to the dashboard over Docker’s **private network** using the name `telegram-dashboard` — not `localhost` (inside a container, `localhost` means the container itself).

```
┌─────────────────────────────────────────────────────────┐
│  Your laptop                                            │
│                                                         │
│   Browser ──► localhost:8000 ──► telegram-dashboard     │
│                                         ▲               │
│   openclaw-net (Docker network)         │               │
│         OpenClaw container ─────────────┘               │
│         http://telegram-dashboard:8000                  │
└─────────────────────────────────────────────────────────┘
```

## Step 1 — Start the dashboard

```bash
cd Telegram_dashboard
cp .env.example .env
# Edit .env — set DASHBOARD_API_KEY and OPERATOR_PASSWORD
docker compose up -d --build
```

This creates network **`openclaw-net`** and container **`telegram-dashboard`**.

Check:

```bash
curl http://localhost:8000/api/health
```

## Step 2 — Connect OpenClaw to the same network

Find your OpenClaw container name:

```bash
docker ps --format "table {{.Names}}\t{{.Image}}"
```

Connect it to `openclaw-net` (one-time per container, survives restarts):

```bash
docker network connect openclaw-net YOUR_OPENCLAW_CONTAINER_NAME
```

**Permanent fix:** add this to your OpenClaw `docker-compose.yml`:

```yaml
services:
  openclaw:   # your service name may differ
    networks:
      - openclaw-net

networks:
  openclaw-net:
    external: true
```

Then `docker compose up -d` for OpenClaw again.

## Step 3 — Mount the skill (no full repo mount)

Mount **only** the skill folder into OpenClaw’s workspace skills directory.

Adjust the **left** path to your repo on the laptop. Adjust the **right** path to match your OpenClaw image (common examples below).

```yaml
services:
  openclaw:
    volumes:
      # Example A — typical node user home
      - /absolute/path/to/Telegram_dashboard/openclaw/skills/telegram-dashboard:/home/node/.openclaw/workspace/skills/telegram-dashboard:ro
      # Example B — if your image uses /root
      # - /absolute/path/to/Telegram_dashboard/openclaw/skills/telegram-dashboard:/root/.openclaw/workspace/skills/telegram-dashboard:ro
```

**Or** install once via exec (no bind mount):

```bash
docker exec -it YOUR_OPENCLAW_CONTAINER_NAME sh
# inside container, if openclaw CLI is available:
openclaw skills install /path/inside/container/if/mounted
```

Easiest approach: bind-mount the skill folder as above.

## Step 4 — Configure OpenClaw env (critical URL)

Edit OpenClaw config on the host (usually `~/.openclaw/openclaw.json`, which is often mounted into the container):

```json5
{
  skills: {
    entries: {
      "telegram-dashboard": {
        enabled: true,
        env: {
          TELEGRAM_DASHBOARD_URL: "http://telegram-dashboard:8000",
          DASHBOARD_API_KEY: "exact-same-value-as-dashboard-.env"
        },
      },
    },
  },
}
```

| Wrong (inside OpenClaw container) | Right |
|-----------------------------------|-------|
| `http://localhost:8000` | `http://telegram-dashboard:8000` |
| `http://127.0.0.1:8000` | `http://telegram-dashboard:8000` |

Restart OpenClaw or start a **new agent session** after changing config.

## Step 5 — Verify from inside OpenClaw container

```bash
docker exec YOUR_OPENCLAW_CONTAINER_NAME curl -s \
  -H "X-API-Key: YOUR_DASHBOARD_API_KEY" \
  http://telegram-dashboard:8000/api/health
```

Expected: `{"status":"ok"}`

Test the skill CLI (if `python3` exists in the image):

```bash
docker exec -e TELEGRAM_DASHBOARD_URL=http://telegram-dashboard:8000 \
  -e DASHBOARD_API_KEY=your-key \
  YOUR_OPENCLAW_CONTAINER_NAME \
  python3 /home/node/.openclaw/workspace/skills/telegram-dashboard/scripts/tdash.py metrics
```

## What you do NOT need

| Don't | Why |
|-------|-----|
| Mount the whole `Telegram_dashboard` repo | OpenClaw only needs the skill folder + HTTP API |
| Use `localhost` in OpenClaw config | That points at the OpenClaw container, not the dashboard |
| Expose the dashboard on a special port for OpenClaw | Internal Docker DNS is enough |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Connection refused` from OpenClaw | Run `docker network connect openclaw-net …` on OpenClaw container |
| `Could not resolve host telegram-dashboard` | OpenClaw not on `openclaw-net`; dashboard not running |
| `401 Unauthorized` | `DASHBOARD_API_KEY` mismatch between `.env` and `openclaw.json` |
| Skill not visible | Check volume mount path; restart OpenClaw; new session |
| Browser works, OpenClaw doesn't | You’re probably still using `localhost` in OpenClaw env |

## Quick reference

| Who | URL |
|-----|-----|
| You (browser) | `http://localhost:8000` |
| OpenClaw (container) | `http://telegram-dashboard:8000` |
| Network name | `openclaw-net` |
| Dashboard container name | `telegram-dashboard` |
