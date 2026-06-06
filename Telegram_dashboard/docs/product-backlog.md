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
- [ ] `messages` table includes `chat_id`, `message_id`, `chat_type`
- [ ] Optional `reply_to_message_id` column added
- [ ] Indexes on `user_id`, `chat_id`, `created_at`, `text`
- [ ] Bot handler persists new fields on ingest
- [ ] Existing rows remain readable (migration safe)

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
- [ ] `GET /api/messages` accepts: `user_ids`, `q` (content search), `direction`, `from`, `to`, `limit`, `offset`
- [ ] `user_ids` supports multiple comma-separated IDs; omit = everyone
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
- [ ] Date range filter (from / to)
- [ ] "Load more" or pagination controls
- [ ] Filter state reflected in URL query params (shareable/bookmarkable)

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
- [ ] Returns structured JSON: `{ summary, message_count, generated_at, provider }`
- [ ] Handles empty result set gracefully

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
- [ ] Error state shown if both AI providers fail

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

### US-4.1 — Manual topic tagging

**As an** operator, **I want** to tag messages with topics **so that** I can filter by theme.

| Field | Value |
|-------|-------|
| Priority | P1 |
| Points | 5 |
| Sprint | 3 |

**Acceptance criteria:**
- [ ] `topics` and `message_topics` tables
- [ ] `POST /api/messages/{id}/topics` to add/remove tags
- [ ] `GET /api/messages?topics=support,billing` filter works
- [ ] UI: tag chips on message rows; topic filter dropdown

---

### US-4.2 — AI auto-tagging on ingest

**As an** operator, **I want** messages auto-tagged on arrival **so that** topics stay current without manual work.

| Field | Value |
|-------|-------|
| Priority | P2 |
| Points | 5 |
| Sprint | 3 |

**Acceptance criteria:**
- [ ] Configurable topic list in `.env` or settings
- [ ] New incoming messages classified into zero or more topics
- [ ] Auto-tags visible in inbox; operator can override

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

### US-5.1 — Auto-reply toggle

**As an** operator, **I want** to disable bot auto-replies **so that** I review messages before responding.

| Field | Value |
|-------|-------|
| Priority | P0 |
| Points | 3 |
| Sprint | 3 |

**Acceptance criteria:**
- [ ] `AUTO_REPLY_ENABLED` env var (default: `false`)
- [ ] Dashboard toggle to enable/disable at runtime
- [ ] When disabled: messages ingested and stored; no automatic Telegram reply
- [ ] When enabled: current behaviour preserved

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
| E2 — AI Summaries | 3 | 11 |
| E3 — Suggested Actions | 3 | 16 |
| E4 — Topics & Organisation | 3 | 15 |
| E5 — Operator Workflow & Polish | 5 | 16 |
| **Total** | **19** | **75** |
