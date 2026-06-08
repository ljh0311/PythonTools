# Current Increment — Sprint 0 (Foundation)

**Status:** ✅ Delivered  
**Branch:** `cursor/telegram-dashboard-98e1`  
**Location:** `Telegram_dashboard/`

This document records the working software delivered in Sprint 0. It forms the baseline for all future sprints.

---

## Sprint 0 goal

Establish a working Telegram bot backend and operator dashboard with message ingestion, basic metrics, and AI provider integration.

## Delivered features

### Backend

| Component | Path | Status |
|-----------|------|--------|
| FastAPI application | `backend/main.py` | ✅ |
| Environment configuration | `backend/config.py` | ✅ |
| SQLite data store | `backend/models/store.py` | ✅ |
| REST + WebSocket API | `backend/routes/api.py` | ✅ |
| Telegram webhook | `backend/routes/webhook.py` | ✅ |
| Bot message handler | `backend/services/bot_handler.py` | ✅ |
| Telegram API client | `backend/services/telegram_service.py` | ✅ |
| AI provider chain (Gemini → Ollama) | `backend/services/ai_service.py` | ✅ |
| Shared AI tools | `backend/services/ai_tools.py` | ✅ |
| Gemini provider | `backend/services/providers/gemini.py` | ✅ |
| Ollama provider | `backend/services/providers/ollama.py` | ✅ |

### Frontend

| Component | Path | Status |
|-----------|------|--------|
| Dashboard shell | `frontend/index.html` | ✅ |
| Responsive styles + theme toggle | `frontend/css/styles.css`, `js/theme.js` | ✅ |
| API client | `frontend/js/api.js` | ✅ |
| Dashboard logic | `frontend/js/app.js` | ✅ |
| Command usage chart | `frontend/js/chart.js` | ✅ |

### Data model (SQLite)

| Table | Fields | Purpose |
|-------|--------|---------|
| `users` | user_id, username, first_name, last_name, last_seen | Known Telegram users |
| `messages` | id, user_id, username, direction, text, created_at | Chat log |
| `events` | id, event_type, payload, created_at | Raw event log |
| `command_usage` | id, command, created_at | Analytics |
| `feedback` | id, user_id, username, rating, comment, created_at | User feedback |
| `quick_actions` | id, label, command, enabled | Customisable commands |

### API endpoints (live)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/health` | Health check |
| GET | `/api/metrics` | Connected users, message totals |
| GET | `/api/messages` | Recent messages (limit only, no filters) |
| GET | `/api/events` | Recent events |
| GET | `/api/analytics/commands` | Command usage chart data |
| GET/PUT | `/api/quick-actions` | Manage quick actions |
| POST | `/api/send` | Send Telegram message |
| POST | `/api/feedback` | Submit feedback |
| GET | `/api/ai/status` | Gemini / Ollama provider status |
| GET | `/api/bot/status` | Bot connection status |
| WS | `/api/ws` | Real-time dashboard updates |
| POST | `/webhook/telegram` | Telegram update ingestion |

### Dashboard widgets (live)

- Connected Users counter (24h active)
- Total Messages counter
- Commands Run counter
- Command Usage Over Time chart (Chart.js)
- Recent Messages feed (flat list, max 50)
- Incoming Events log
- Quick Actions panel (add / edit / save / run)
- Send Message form
- User Feedback section
- Dark / light mode toggle

---

## Sprint 1 increment — Inbox & Filtering ✅

**Status:** Delivered

### New capabilities

| Story | Delivered |
|-------|-----------|
| US-1.1 Rich message storage | `chat_id`, `message_id`, `chat_type`, `chat_title`, `reply_to_message_id`; channels ignored |
| US-1.2 User directory | `GET /api/users` |
| US-1.3 Filtered messages API | `GET /api/messages` with filters + pagination |
| US-1.4 Inbox UI | Search, user multi-select, chat type, direction, dates, load more, URL params |
| US-1.5 Reply targeting | Reply button pre-fills chat ID |

### Demo

```bash
cd Telegram_dashboard
PYTHONPATH=$(pwd) python3 scripts/seed_demo_data.py
PYTHONPATH=$(pwd) python3 -m backend.main
# Open http://localhost:8000
```

---

## Known limitations (drives backlog)

| Gap | Impact | Addressed in |
|-----|--------|--------------|
| AI responds to users, not operator | No summaries or suggestions | Sprint 2 |
| No topic tagging | Cannot filter by theme | Sprint 3 |
| Bot auto-replies to every message | Conflicts with review workflow | Sprint 3 |
| Dev API key only | Not production-ready auth | Sprint 4 |

---

## Sprint 0 retrospective notes

| Went well | To improve |
|-----------|------------|
| Modular backend and frontend structure | Message schema too minimal for operator use case |
| Gemini + Ollama fallback working | AI oriented toward bot replies, not dashboard insights |
| Real-time WebSocket updates | Recent Messages panel needs inbox-grade UX |
