# Dev log — Telegram Dashboard

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
