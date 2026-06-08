# Get this on your laptop (simple steps)

## 1. Download the code

```bash
git clone https://github.com/ljh0311/PythonTools.git
cd PythonTools
git checkout cursor/telegram-dashboard-98e1
cd Telegram_dashboard
```

## 2. Install Python stuff (one time)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows, use `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

## 3. Edit `.env` file

Open `.env` in any text editor. At minimum set:

- `OPERATOR_PASSWORD` — your login password for the website
- `DASHBOARD_API_KEY` — any long random secret you make up
- `TELEGRAM_BOT_TOKEN` — from Telegram BotFather (optional for testing UI)

For AI summaries, also add `GEMINI_API_KEY` or run Ollama locally.

## 4. Start the app

```bash
source .venv/bin/activate
export PYTHONPATH="$(pwd)"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Or run: `./run.sh`

## 5. Open in browser

Go to: **http://localhost:8000**

- Login page appears if you set `OPERATOR_PASSWORD`
- Default username: `admin` (from `.env`)

## 6. Try demo data (optional)

In another terminal:

```bash
cd Telegram_dashboard
source .venv/bin/activate
python3 scripts/seed_demo_data.py
```

Refresh the browser — you will see sample chats.

## More help

| What you want | Read this file |
|---------------|----------------|
| Full local setup | [local_mode.md](local_mode.md) |
| Docker | [docker_mode.md](docker_mode.md) |
| OpenClaw on same laptop | [docs/openclaw-docker-laptop.md](docs/openclaw-docker-laptop.md) |
| All docs | [docs/README.md](docs/README.md) |
