# OpenClaw integration

Connect your [OpenClaw](https://docs.openclaw.ai/) agent to the Telegram Operator Dashboard so it can read the inbox, summarize messages, suggest replies, and send Telegram messages on your behalf.

## Do you need to mount the whole project?

**No.** OpenClaw only needs:

1. The **skill folder** (`openclaw/skills/telegram-dashboard/`)
2. **Network access** to the dashboard URL (e.g. `http://localhost:8000`)
3. The **`DASHBOARD_API_KEY`** from your `.env`

You do **not** need to mount the entire `Telegram_dashboard` repo unless you want OpenClaw to edit the source code.

## Quick setup (recommended)

### Step 1 — Run the dashboard

Local or Docker — see [local_mode.md](../local_mode.md) or [docker_mode.md](../docker_mode.md).

### Step 2 — Install the skill

```bash
openclaw skills install /absolute/path/to/Telegram_dashboard/openclaw/skills/telegram-dashboard
```

### Step 3 — Configure secrets in OpenClaw

Edit `~/.openclaw/openclaw.json`:

```json5
{
  skills: {
    entries: {
      "telegram-dashboard": {
        enabled: true,
        env: {
          TELEGRAM_DASHBOARD_URL: "http://localhost:8000",
          DASHBOARD_API_KEY: "your-dashboard-api-key-from-env",
        },
      },
    },
  },
}
```

Restart OpenClaw or start a **new agent session** so the skill snapshot refreshes.

### Step 4 — Verify

```bash
export TELEGRAM_DASHBOARD_URL=http://localhost:8000
export DASHBOARD_API_KEY=your-key
python3 /path/to/Telegram_dashboard/openclaw/skills/telegram-dashboard/scripts/tdash.py manifest
```

## Alternative: extraDirs (no install copy)

Keep the skill in the repo and reference it:

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
          DASHBOARD_API_KEY: "your-key",
        },
      },
    },
  },
}
```

Use `allowSymlinkTargets` if you symlink the skills folder.

## Docker: OpenClaw + Dashboard together

| Setup | `TELEGRAM_DASHBOARD_URL` |
|-------|--------------------------|
| Dashboard in Docker, OpenClaw on host | `http://localhost:8000` |
| **Both in Docker on same laptop** | **`http://telegram-dashboard:8000`** — see [openclaw-docker-laptop.md](openclaw-docker-laptop.md) |
| Dashboard on host, OpenClaw in Docker | `http://host.docker.internal:8000` (Mac/Win); Linux: host gateway IP |

### Both Docker on same laptop (most common)

1. Start dashboard: `docker compose up -d` (creates network `openclaw-net`)
2. Connect OpenClaw: `docker network connect openclaw-net YOUR_OPENCLAW_CONTAINER`
3. Set URL to `http://telegram-dashboard:8000` in `skills.entries.telegram-dashboard.env`
4. Mount only the skill folder into OpenClaw (see [openclaw-docker-laptop.md](openclaw-docker-laptop.md))

Example snippet: [openclaw/openclaw.docker.example.json5](../openclaw/openclaw.docker.example.json5)

Mount **only** the skills directory if OpenClaw runs in Docker:

```yaml
volumes:
  - /path/to/Telegram_dashboard/openclaw/skills/telegram-dashboard:/home/node/.openclaw/workspace/skills/telegram-dashboard:ro
```

## What the agent can do

| Tool (via `tdash.py`) | Purpose |
|-----------------------|---------|
| `metrics` | User/message counts |
| `messages` / `threads` | Read filtered inbox |
| `summarize` | AI summary of filtered messages |
| `suggest` | Reply drafts + next actions |
| `send` | Send Telegram message (use with care) |
| `reply-mode` | Auto-reply settings + relationship context per chat |

Agent discovery API: `GET /api/agent/manifest`  
Full OpenAPI: `GET /openapi.json`

## Authentication model

| Client | Auth method |
|--------|-------------|
| **OpenClaw / scripts** | `X-API-Key: DASHBOARD_API_KEY` |
| **Browser (human)** | Login at `/login` with `OPERATOR_PASSWORD` → session token |

Keep the API key secret in OpenClaw `skills.entries.*.env` — it is injected per agent run, not shown in prompts.

## Security notes

- Approve sends explicitly — the skill instructs the agent not to auto-send without user consent.
- Sensitive data is redacted before cloud AI calls; OpenClaw reading via API gets full message text from your local database.
- Rotate `DASHBOARD_API_KEY` if compromised; update OpenClaw config to match.

## Troubleshooting

| Issue | Check |
|-------|-------|
| Skill not listed | `openclaw skills list` — ensure `enabled: true` |
| Connection refused | Dashboard running? Correct URL? |
| 401 Unauthorized | API key matches `.env` `DASHBOARD_API_KEY` |
| Skill gated / missing | `python3` on PATH; env vars set in `skills.entries` |
