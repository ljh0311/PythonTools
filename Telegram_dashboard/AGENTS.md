# AGENTS.md — Telegram Dashboard (Cloud Agent)

Runbook for Cursor Cloud Agents (and any fresh Linux VM clone). Keep secrets out of this file; use `.env.example` names only.

## Stack

| Item | Value |
|------|--------|
| Runtime | Python 3.11+ (3.12 OK) |
| Package manager | `pip` + `venv` |
| App dir | `Telegram_dashboard/` (this folder) |
| Entry | `python -m backend.main` |
| Default bind | `HOST`/`PORT` → `0.0.0.0:8000` |
| DB | SQLite at `data/dashboard.db` (created on start) |
| Profiles | Markdown files under `data/profiles/` |

Monorepo note: git root may be parent `PythonTools`. Always `cd` into `Telegram_dashboard` before install/run.

## Install

```bash
cd Telegram_dashboard
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill secrets / Cloud secrets injection
```

Optional: project may already ship `.venv` locally — prefer it when present.

## Environment (names only)

Copy from `.env.example`. Common keys:

| Key | Purpose |
|-----|---------|
| `TELEGRAM_BOT_TOKEN` | Bot API (v1 / webhook / polling) |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook secret header |
| `TELEGRAM_POLLING` | Local poll without public URL (`true`/`false`) |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Primary AI (optional) |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | Fallback AI (optional) |
| `DASHBOARD_API_KEY` | Operator API key (default in example is for local only) |
| `OPERATOR_USERNAME` / `OPERATOR_PASSWORD` | Browser login; empty password → API-key-only |
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` | MTProto user inbox (v0.2 / Talk data) |
| `MTProto_ENABLED` / `MTProto_PHONE` | Enable user-account ingest |
| `HOST` / `PORT` | Bind address (default `8000`) |

Do **not** commit `.env`, session files under `data/`, or real API keys.

### MTProto notes (Cloud)

- Talk / Act heuristics expect **user_account** messages. Without MTProto, `/v2` Talk may show empty threads; bot-only data still powers classic `/`.
- First MTProto login is interactive (phone code). On Cloud, either inject an existing session file via secrets/volume, or leave `MTProto_ENABLED=false` and smoke UI shells + API with seeded SQLite.
- Session path defaults to `data/user.session` (`MTProto_SESSION_NAME`).

## Start

```bash
cd Telegram_dashboard
source .venv/bin/activate
python -m backend.main
# equivalent: uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Long-lived process: leave running in a Cloud terminal / tmux session.

## Health / URLs

| URL | What |
|-----|------|
| `http://localhost:8000/` | **v1 Operator** dashboard (unchanged) |
| `http://localhost:8000/login` | Operator login |
| `http://localhost:8000/v2` | **v2 Awareness** — Talk / Act / Profiles |
| `http://localhost:8000/v2/static/…` | v2 static assets |
| `http://localhost:8000/api/v2/talk/threads` | Talk API (auth required) |
| `http://localhost:8000/api/v2/act` | Act queue API |
| `http://localhost:8000/api/v2/profiles` | Profiles list API |
| `http://localhost:8000/docs` | FastAPI OpenAPI UI |

Auth: `X-API-Key: <DASHBOARD_API_KEY>` or Bearer session after `/login`.

Terminal smoke:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:8000/
curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:8000/v2
curl -sS -o /dev/null -w "%{http_code}\n" -H "X-API-Key: $DASHBOARD_API_KEY" \
  http://localhost:8000/api/v2/profiles
```

Focused tests (no server required):

```bash
python -m pytest backend/tests/test_profile_md.py backend/tests/test_v2_act.py -q
```

## `/` vs `/v2`

| | `/` (v1 Operator) | `/v2` (Awareness) |
|--|-------------------|-------------------|
| Audience | Bot ops, inbox, analytics, tools | Personal awareness |
| Surfaces | Full classic dashboard | Talk · Act · Profiles only |
| Data bias | Bot + user inbox filters | Talk defaults to `user_account` |
| Status | Production fallback | Early slice — see [docs/v2.md](docs/v2.md) |

Do not redesign or replace v1 when working on v2.

## Cloud Desktop checklist

- [ ] Open `http://localhost:8000/` — classic Operator loads
- [ ] Open `http://localhost:8000/v2` — Awareness shell with Talk / Act / Profiles nav
- [ ] Sign in if redirected to `/login`
- [ ] **Talk**: refresh threads; open one thread (or confirm empty-state copy if no MTProto data)
- [ ] **Act**: Reload queue; optional Refresh AI (needs Gemini/Ollama)
- [ ] **Profiles**: list/edit markdown; Save; optional Refresh from chat
- [ ] Use **Open classic dashboard** link back to `/`
- [ ] Capture screenshot of `/v2` happy or empty state for PR artifacts when UI-facing

Skip full Desktop for pure backend/doc PRs if pytest + curl smoke already cover the change; note what was not UI-verified.

## Docs map

- [README.md](README.md) — setup + **Dashboard v2** section
- [docs/v2.md](docs/v2.md) — v2 behavior, gaps, verification
- [docs/dev-log.md](docs/dev-log.md) — session progress
- [docs/user-inbox.md](docs/user-inbox.md) — MTProto user inbox
- [.env.example](.env.example) — env template
