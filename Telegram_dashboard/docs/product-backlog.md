# Product Backlog

Backlog items are ordered by priority (highest first). Each item is a **user story** with **acceptance criteria** and a **story point estimate** (Fibonacci: 1, 2, 3, 5, 8).

**Priority key:** P0 = must have · P1 = should have · P2 = could have · P3 = won't have (this release)

---

## Epic E1 — Inbox & Message Filtering

*Enable the operator to browse and filter all recent messages.*

### US-1.1 — Rich message storage

**As an** operator, **I want** messages stored with full Telegram metadata **so that** filtering and replies work reliably.

| Field | Value |
|-------|-------|
| Priority | P0 |
| Points | 3 |
| Sprint | 1 |

**Acceptance criteria:**
- [ ] `messages` table includes `chat_id`, `message_id`, `chat_type` (`private` | `group`)
- [ ] Channels excluded for now; channel updates ignored or logged as unsupported
- [ ] Group messages store the individual sender (`user_id`) alongside `chat_id`
- [ ] Optional `reply_to_message_id` column added
- [ ] Indexes on `user_id`, `chat_id`, `chat_type`, `created_at`, `text`
- [ ] Bot handler persists new fields on ingest
- [ ] Existing rows remain readable (migration safe)

**Client decision:** D-02 — private + group chats; no channels yet

---

### US-1.2 — User directory

**As an** operator, **I want** a list of all known message senders **so that** I can select who to filter by.

| Field | Value |
|-------|-------|
| Priority | P0 |
| Points | 2 |
| Sprint | 1 |

**Acceptance criteria:**
- [ ] `GET /api/users` returns user_id, username, display name, message count, last_seen
- [ ] Results sorted by most recent activity
- [ ] Endpoint protected by API key

---

### US-1.3 — Filtered messages API

**As an** operator, **I want** to query messages with filters **so that** I only see relevant conversations.

| Field | Value |
|-------|-------|
| Priority | P0 |
| Points | 5 |
| Sprint | 1 |

**Acceptance criteria:**
- [ ] `GET /api/messages` accepts: `user_ids`, `chat_type`, `q` (content search), `direction`, `from`, `to`, `limit`, `offset`
- [ ] `user_ids` supports multiple comma-separated IDs; omit = everyone
- [ ] `chat_type` filter: `private`, `group`, or omit for both
- [ ] `q` performs case-insensitive substring match on message text
- [ ] Response includes `total` count for pagination
- [ ] Empty filter returns all messages (paginated)

---

### US-1.4 — Inbox UI with filters

**As an** operator, **I want** a filterable inbox on the dashboard **so that** I can find messages without using the API directly.

| Field | Value |
|-------|-------|
| Priority | P0 |
| Points | 5 |
| Sprint | 1 |

**Acceptance criteria:**
- [ ] Recent Messages panel renamed/refactored to **Inbox**
- [ ] Search input filters by content (debounced)
- [ ] User multi-select: "Everyone" default + individual senders
- [ ] Direction filter: All / Incoming / Outgoing
- [ ] Chat type filter: All / Private / Group
- [ ] Date range filter (from / to)
- [ ] "Load more" or pagination controls
- [ ] Filter state reflected in URL query params (shareable/bookmarkable)
- [ ] Group messages show sender name within the group context

---

### US-1.5 — Correct reply targeting

**As an** operator, **I want** sent replies to reach the correct Telegram chat **so that** responses are delivered to the right person.

| Field | Value |
|-------|-------|
| Priority | P0 |
| Points | 2 |
| Sprint | 1 |

**Acceptance criteria:**
- [ ] Send form can pre-fill `chat_id` when replying from a message row
- [ ] Quick Actions use stored `chat_id` when available
- [ ] Outgoing messages record correct `chat_id` in database

---

## Epic E2 — AI Summaries

*Enable the operator to summarise filtered message sets.*

### US-2.1 — Summarisation service

**As an** operator, **I want** the system to summarise a set of messages **so that** I can grasp the situation quickly.

| Field | Value |
|-------|-------|
| Priority | P0 |
| Points | 5 |
| Sprint | 2 |

**Acceptance criteria:**
- [ ] `SummarizationService` uses Gemini with Ollama fallback
- [ ] `POST /api/ai/summarize` accepts same filter params as messages API
- [ ] Supports summary types: `brief`, `detailed`, `bullets`, `unanswered`
- [ ] **Summaries generated in English by default** (D-04)
- [ ] Response includes original messages: `{ summary, message_count, originals[], generated_at, provider }`
- [ ] Sensitive data redacted from text sent to AI (see US-2.4)
- [ ] Handles empty result set gracefully

**Client decision:** D-04 — English summaries; originals preserved

---

### US-2.2 — Summary UI panel

**As an** operator, **I want** a Summarize button on the inbox **so that** I can generate summaries from my current filter view.

| Field | Value |
|-------|-------|
| Priority | P0 |
| Points | 3 |
| Sprint | 2 |

**Acceptance criteria:**
- [ ] "Summarize" button uses active inbox filters
- [ ] Summary type selector (brief / detailed / bullets / unanswered)
- [ ] Loading state shown during AI call
- [ ] Result displayed in dedicated panel with copy-to-clipboard
- [ ] **"View originals" toggle** shows source messages in their original language alongside English summary (D-04)
- [ ] Redaction notice shown when sensitive data was masked before AI processing
- [ ] Error state shown if both AI providers fail

---

### US-2.4 — Sensitive data redaction

**As an** operator, **I want** sensitive information redacted before AI processing **so that** ID numbers and similar data are not sent to cloud AI.

| Field | Value |
|-------|-------|
| Priority | P0 |
| Points | 5 |
| Sprint | 2 |

**Acceptance criteria:**
- [ ] `RedactionService` masks patterns: ID numbers, passport-like strings, credit card numbers
- [ ] Redaction applied to all text sent to Gemini/Ollama (summaries, suggestions, auto-tags)
- [ ] Original message text in database and inbox is **not** modified
- [ ] API response includes `redaction_applied: true/false` and count of redacted fields
- [ ] Dashboard shows a warning badge when redaction occurred
- [ ] Pattern list configurable via `.env` or settings file

**Client decision:** D-05 — all messages to AI, with sensitive-data safeguards

---

### US-2.3 — Summary caching

**As an** operator, **I want** repeated summaries of the same filter to be fast **so that** I don't wait or waste API quota.

| Field | Value |
|-------|-------|
| Priority | P2 |
| Points | 3 |
| Sprint | 2 |

**Acceptance criteria:**
- [ ] Summaries cached by hash of (filters + summary_type)
- [ ] Cache invalidated when new messages match the filter
- [ ] Cache TTL configurable (default 1 hour)

---

## Epic E3 — Suggested Replies & Next Actions

*Enable the operator to act on AI recommendations.*

### US-3.1 — Action suggestion service

**As an** operator, **I want** AI to suggest replies and next actions **so that** I know what to do next.

| Field | Value |
|-------|-------|
| Priority | P0 |
| Points | 8 |
| Sprint | 2 |

**Acceptance criteria:**
- [ ] `POST /api/ai/suggest-actions` accepts filter params
- [ ] Returns: `summary`, `suggestions[]` with types `reply` | `next_action`
- [ ] Reply suggestions include: `chat_id`, `user`, `draft`, `priority`, `confidence`
- [ ] Next-action suggestions include: `action`, `priority`, `due_hint`
- [ ] Output validated against JSON schema; retry on malformed AI response

---

### US-3.2 — Suggestions UI panel

**As an** operator, **I want** to see and act on suggestions in the dashboard **so that** I can respond without drafting from scratch.

| Field | Value |
|-------|-------|
| Priority | P0 |
| Points | 5 |
| Sprint | 2 |

**Acceptance criteria:**
- [ ] "Suggest Actions" button on inbox (uses active filters)
- [ ] Suggestions rendered as cards grouped by type
- [ ] Reply drafts are editable before send
- [ ] "Send" dispatches via `POST /api/send`
- [ ] "Dismiss" removes suggestion from view
- [ ] Priority indicated visually (high / medium / low)

---

### US-3.3 — Action status tracking

**As an** operator, **I want** to mark suggestions as sent or done **so that** I can track what I've handled.

| Field | Value |
|-------|-------|
| Priority | P1 |
| Points | 3 |
| Sprint | 3 |

**Acceptance criteria:**
- [ ] `suggestions` table: id, filter_hash, type, payload, status, created_at
- [ ] Status values: `pending`, `sent`, `dismissed`, `done`
- [ ] UI reflects status; dismissed items hidden by default

---

## Epic E4 — Topics & Organisation

*Enable filtering by topic and conversation structure.*

### US-4.1 — Topic filtering (manual + AI modes)

**As an** operator, **I want** to filter messages by topic using either my own labels or AI-assigned tags **so that** I can organise conversations my way.

| Field | Value |
|-------|-------|
| Priority | P1 |
| Points | 8 |
| Sprint | 3 |

**Acceptance criteria:**
- [ ] `topics` and `message_topics` tables
- [ ] **Toggle switch in UI:** "User type" mode vs "AI assign" mode (D-03)
- [ ] **User type mode:** operator types free-form filter text; `GET /api/messages?topics=` matches tags or content
- [ ] **AI assign mode:** AI classifies incoming messages; tags stored automatically
- [ ] `POST /api/messages/{id}/topics` to add/remove manual tags
- [ ] Operator can override or remove AI-assigned tags
- [ ] UI: tag chips on message rows; topic filter input/dropdown
- [ ] AI tagging uses redaction layer (US-2.4) before sending to Gemini/Ollama

**Client decision:** D-03 — hybrid with toggle between user-typed and AI-assigned

---

### US-4.2 — ~~AI auto-tagging on ingest~~

> **Merged into US-4.1** per client decision D-03.

---

### US-4.3 — Conversation threading

**As an** operator, **I want** messages grouped by chat/thread **so that** I can follow a conversation holistically.

| Field | Value |
|-------|-------|
| Priority | P1 |
| Points | 5 |
| Sprint | 3 |

**Acceptance criteria:**
- [ ] Inbox toggle: flat list vs grouped by `chat_id`
- [ ] Thread view shows messages in chronological order per chat
- [ ] Thread header shows participant name and message count

---

## Epic E5 — Operator Workflow & Polish

*Production-ready operator experience.*

### US-5.1 — Reply mode switcher (three modes)

**As an** operator, **I want** to choose how the bot responds — auto, manual, or per-chat **so that** I control when messages are sent automatically.

| Field | Value |
|-------|-------|
| Priority | P0 |
| Points | 8 |
| Sprint | 3 |

**Acceptance criteria:**
- [ ] **Default mode: B — Operator approves** (`AUTO_REPLY_MODE=manual`) (D-01)
- [ ] Dashboard mode switcher with three options:
  - **A — Auto-reply:** bot sends AI reply immediately (Sprint 0 behaviour)
  - **B — Operator approves:** ingest only; operator sends from dashboard
  - **C — Per-chat:** auto-reply on/off per `chat_id` (private or group)
- [ ] `GET/PUT /api/settings/reply-mode` persists current mode
- [ ] Per-chat overrides stored in `chat_settings` table (`chat_id`, `auto_reply_enabled`)
- [ ] Per-chat mode UI: list of chats with individual toggles
- [ ] Mode change takes effect on next incoming message without restart

**Client decision:** D-01 — default B; all three modes selectable

---

### US-5.2 — Saved filter presets

**As an** operator, **I want** to save common filter combinations **so that** I can switch views quickly.

| Field | Value |
|-------|-------|
| Priority | P2 |
| Points | 3 |
| Sprint | 4 |

**Acceptance criteria:**
- [ ] Save / load / delete named presets (e.g. "VIP today", "Unanswered support")
- [ ] Presets stored in SQLite; persist across sessions

---

### US-5.3 — Export filtered view

**As an** operator, **I want** to export filtered messages and summaries **so that** I can share or archive them.

| Field | Value |
|-------|-------|
| Priority | P2 |
| Points | 3 |
| Sprint | 4 |

**Acceptance criteria:**
- [ ] Export as CSV and plain-text summary
- [ ] Export respects active inbox filters

---

### US-5.4 — Authentication hardening

**As an** operator, **I want** secure dashboard access **so that** only authorised users can view messages.

| Field | Value |
|-------|-------|
| Priority | P1 |
| Points | 5 |
| Sprint | 4 |

**Acceptance criteria:**
- [ ] Replace dev API key with session-based login or token auth
- [ ] WebSocket requires valid session
- [ ] `.env` secrets not exposed to frontend

---

### US-5.5 — Deployment guide

**As a** deployer, **I want** documented production setup **so that** the dashboard runs reliably with HTTPS webhook.

| Field | Value |
|-------|-------|
| Priority | P1 |
| Points | 2 |
| Sprint | 4 |

**Acceptance criteria:**
- [ ] README or `docs/deployment.md` covers HTTPS, webhook registration, backups
- [ ] Environment variable reference complete

---

## Backlog summary

| Epic | Stories | Total points |
|------|---------|--------------|
| E1 — Inbox & Filtering | 5 | 17 |
| E2 — AI Summaries | 4 | 16 |
| E3 — Suggested Actions | 3 | 16 |
| E4 — Topics & Organisation | 2 active | 13 |
| E5 — Operator Workflow & Polish | 5 | 21 |
| **Total** | **19** | **83** |

> Point totals updated after client decisions (2026-06-06). See [risks-and-decisions.md](risks-and-decisions.md).
