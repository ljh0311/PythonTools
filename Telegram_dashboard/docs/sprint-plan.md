# Sprint Plan

Sprint length recommendation: **2 weeks** per sprint (adjust based on capacity).

**Velocity baseline:** Unknown — estimate after Sprint 1 retrospective.

---

## Sprint 0 — Foundation ✅ COMPLETE

| Field | Value |
|-------|-------|
| Status | Done |
| Goal | Working dashboard, Telegram webhook, AI providers |
| Delivered | See [current-increment.md](current-increment.md) |

---

## Sprint 1 — Inbox & Filtering

| Field | Value |
|-------|-------|
| Status | **Planned — next** |
| Goal | Operator can browse and filter all recent messages |
| Epic | E1 |
| Stories | US-1.1, US-1.2, US-1.3, US-1.4, US-1.5 |
| Points | 17 |

### Sprint 1 backlog (ordered)

1. US-1.1 — Rich message storage (schema migration)
2. US-1.2 — User directory API
3. US-1.3 — Filtered messages API
4. US-1.5 — Correct reply targeting (depends on US-1.1)
5. US-1.4 — Inbox UI with filters (depends on US-1.2, US-1.3)

### Sprint 1 definition of ready

- [ ] Client confirms message scope: DMs only vs groups/channels (see [risks-and-decisions.md](risks-and-decisions.md))
- [ ] Sprint 0 code merged and runnable locally

### Sprint 1 review demo script

1. Ingest test messages from 3 different users via webhook
2. Open dashboard → Inbox shows all messages
3. Filter to one user → only their messages shown
4. Search keyword → matching messages only
5. Click "Reply" on a row → chat_id pre-filled → send works

### Sprint 1 retrospective (template)

| Question | Notes |
|----------|-------|
| What went well? | |
| What didn't go well? | |
| What will we change in Sprint 2? | |

---

## Sprint 2 — AI Summaries & Suggested Actions

| Field | Value |
|-------|-------|
| Status | Planned |
| Goal | Operator can summarise filtered messages and get reply/action suggestions |
| Epics | E2, E3 |
| Stories | US-2.1, US-2.2, US-3.1, US-3.2 (+ US-2.3 if capacity) |
| Points | 21 (or 24 with caching) |

### Sprint 2 backlog (ordered)

1. US-2.1 — Summarisation service
2. US-2.2 — Summary UI panel
3. US-3.1 — Action suggestion service
4. US-3.2 — Suggestions UI panel
5. US-2.3 — Summary caching (stretch)

### Sprint 2 dependencies

- Requires Sprint 1 filtered messages API (US-1.3)
- Requires `GEMINI_API_KEY` configured for best results

### Sprint 2 review demo script

1. Filter inbox to 10+ messages from 2 users
2. Click "Summarize" → brief summary appears
3. Click "Suggest Actions" → reply drafts and next actions shown
4. Edit a draft → Send → message delivered via Telegram

---

## Sprint 3 — Topics & Operator Workflow

| Field | Value |
|-------|-------|
| Status | Planned |
| Goal | Organise messages by topic; operator controls auto-reply |
| Epics | E4, E5 (partial) |
| Stories | US-4.1, US-4.3, US-5.1, US-3.3 (+ US-4.2 if capacity) |
| Points | 16 (or 21 with auto-tagging) |

### Sprint 3 backlog (ordered)

1. US-5.1 — Auto-reply toggle (high product impact — do early in sprint)
2. US-4.1 — Manual topic tagging
3. US-4.3 — Conversation threading
4. US-3.3 — Action status tracking
5. US-4.2 — AI auto-tagging (stretch)

### Sprint 3 review demo script

1. Disable auto-reply → new message appears in inbox, no bot reply sent
2. Tag messages with "support" → filter by topic works
3. Switch to thread view → conversation grouped by chat
4. Mark a suggestion as "sent" → status persists

---

## Sprint 4 — Polish & Deployment

| Field | Value |
|-------|-------|
| Status | Planned |
| Goal | Production-ready dashboard with auth and export |
| Epic | E5 |
| Stories | US-5.2, US-5.3, US-5.4, US-5.5 |
| Points | 13 |

### Sprint 4 backlog (ordered)

1. US-5.4 — Authentication hardening
2. US-5.5 — Deployment guide
3. US-5.3 — Export filtered view
4. US-5.2 — Saved filter presets

### Sprint 4 review demo script

1. Log in with credentials (not dev API key)
2. Export filtered inbox as CSV
3. Load saved preset "VIP today"
4. Walk through deployment checklist

---

## Release plan

| Release | Sprints | Client value |
|---------|---------|--------------|
| **v0.1** | Sprint 0 | Foundation dashboard + bot |
| **v0.2** | Sprint 1 | Filterable inbox |
| **v0.3** | Sprint 2 | AI summaries + suggested actions |
| **v0.4** | Sprint 3 | Topics + operator workflow |
| **v1.0** | Sprint 4 | Production-ready |
