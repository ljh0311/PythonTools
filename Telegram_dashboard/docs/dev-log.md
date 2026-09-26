# Dev log — Telegram Dashboard

## 2026-09-26 — Act triage hardening, needs-reply digest, AI provider order

**Progress**
- Completed: Act reply-state / open-items merge, quality logging, scheduled needs-reply digest, Gemini→Ollama primary switch with key redaction, v1↔v2 UI toggle + login polish, Awareness loading-state fixes.
- Shipped on `feat/telegram-dashboard-v2` (PR #7) for merge to `main`.
- Left out of this ship: `3d_reconstruction` Gaussian splat WIP, `CarRS/ml_model_meta.json`, local `.cursor` / `.mcp.json` / `_fix_ai_raise.py`.

**Implementation**
- Act: `act_reply_state.py`, `act_open_items.py`, `act_quality.py`; richer `/api/v2/act` queue (needs-reply first, suppress drafts when already replied).
- Digest: `unread_digest_service.py` + lifespan loop; env `UNREAD_DIGEST_*` / `NOTIFY_TELEGRAM_CHAT_ID`; optional quiet hours.
- AI: `AI_PRIMARY_PROVIDER` (default `gemini`), Ollama fallback models, honesty tests for 429 + garbled output.
- UI: `frontend/js/ui-version.js`, login brand icons, Act/Talk UX polish.

**Verification**
- `python -m pytest backend/tests/test_profile_md.py backend/tests/test_v2_act.py backend/tests/test_unread_digest.py backend/tests/test_ai_honesty.py backend/tests/test_providers.py -q` → 30 passed

## 2026-09-07 — Dashboard v2 Awareness slice + Cloud readiness

**Progress**
- Completed: `/v2` shell (Talk / Act / Profiles), `/api/v2` routes, Markdown profiles service, focused tests, README + AGENTS.md + this log.
- Remaining: Talk send/reply, Act `open_items` UI, deeper MTProto demo seeding, more route/UI tests (see [v2.md](v2.md)).

**Implementation**
- Behavior: Classic Operator stays at `/`. Awareness UI at `/v2` with static under `/v2/static`. APIs under `/api/v2` (operator auth).
- Key paths: `backend/routes/v2_api.py`, `backend/services/profile_md.py`, `frontend/v2/`, `backend/main.py`, `backend/config.py` (`PROFILES_DIR`)
- Config/env: no new required keys; reuses `.env.example` operator/AI/MTProto vars. Profiles on disk under `data/profiles/`.

**Verification**
- `python -m pytest backend/tests/test_profile_md.py backend/tests/test_v2_act.py -q` → 4 passed
- TestClient smoke: `/`, `/v2`, `/api/v2/talk/threads`, `/api/v2/act`, `/api/v2/profiles` → 200 with configured API key
