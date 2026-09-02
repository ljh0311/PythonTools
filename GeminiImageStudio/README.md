# Gemini Image Studio

Local-only FastAPI + React app: prompt + optional reference images → Gemini Nano Banana → save/preview under `outputs/`.

**Out of scope (v1):** video / Veo — deferred until image generation is stable.

## Prerequisites

- Python 3.11+
- Node.js 20+
- A Gemini API key ([Google AI Studio](https://aistudio.google.com/apikey))

## Setup

```bat
cd GeminiImageStudio

:: API key
copy .env.example .env
:: Edit .env and set GEMINI_API_KEY=...

:: Backend venv
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

:: Frontend
cd frontend
npm install
cd ..
```

## One-click run (Windows)

```bat
launcher.bat
```

Opens two console windows:

| Process | URL |
|---------|-----|
| API (uvicorn) | http://127.0.0.1:8765 |
| UI (Vite) | http://127.0.0.1:5173 |

Both bind to `127.0.0.1` only. Open the UI URL in your browser.

If the API is **already** healthy on port 8765 (or the UI on 5173), the launcher **reuses** it instead of binding again. That avoids Windows `WinError 10048` (address already in use) when you run the launcher twice.

If the port is taken by something that is **not** this app:

```bat
netstat -ano | findstr :8765
taskkill /PID <pid> /F
```

## Manual run

Terminal 1 — API (safe if already running):

```bat
scripts\start_api.bat
```

Or raw uvicorn:

```bat
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

Terminal 2 — UI:

```bat
cd frontend
npm run dev
```

Or from `frontend/` with both in one terminal (requires `npm install` once):

```bat
npm run start:all
```

`npm run api` uses `scripts\start_api.bat` (reuse-or-start).

## Tests (mocked — no paid API)

```bat
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest tests -q
```

## Notes

- Missing `GEMINI_API_KEY` → `GET /api/health` still 200; `POST /api/generate` returns 400.
- Generated images land in `outputs/` (gitignored).
- Video / Veo is **not** implemented in v1.
