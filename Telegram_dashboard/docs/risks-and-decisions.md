# Risks, Assumptions & Decisions

**Product Owner:** Client  
**Last updated:** 2026-06-06

---

## Client decisions (resolved)

All five open decisions have been confirmed by the Product Owner.

### D-01 — Auto-reply behaviour ✅ DECIDED

| Field | Value |
|-------|-------|
| **Decision** | **Default: B (operator approves)** — bot does not auto-send until the operator reviews |
| **Also required** | Support **all three modes** with a dashboard switcher |

| Mode | Code | Behaviour |
|------|------|-----------|
| **Auto-reply** | A | Bot replies instantly to every message (current Sprint 0 behaviour) |
| **Operator approves** | B | Messages stored only; operator reviews and sends from dashboard *(default)* |
| **Per-chat** | C | Auto-reply on/off per individual chat (private or group) |

**Implementation:** US-5.1 (expanded) · Sprint 3

---

### D-02 — Message scope ✅ DECIDED

| Field | Value |
|-------|-------|
| **Decision** | **Private chats + group chats** |
| **Excluded for now** | Channels — bot will not handle channel messages in this release |

| Chat type | Supported |
|-----------|-----------|
| Private (1-on-1) | ✅ Yes |
| Group | ✅ Yes |
| Channel | ❌ Not now (future) |

**Implementation:** US-1.1 (store `chat_type`), US-1.3 / US-1.4 (filter by chat type) · Sprint 1

---

### D-03 — Topic / content filter model ✅ DECIDED

| Field | Value |
|-------|-------|
| **Decision** | **Hybrid with toggle** — operator chooses between two modes |

| Mode | Behaviour |
|------|-----------|
| **User type** | Operator types free-form filter labels / topic text to filter messages |
| **AI assign** | AI automatically tags or classifies messages; operator can filter by those tags |

**UI:** Toggle switch between "User type" and "AI assign" modes.

**Implementation:** US-4.1 (merged manual + AI) · Sprint 3

---

### D-04 — Summary language ✅ DECIDED

| Field | Value |
|-------|-------|
| **Decision** | **Summaries default to English** |
| **Also required** | Operator can **view original-language messages** alongside the English summary |

| Output | Language |
|--------|----------|
| AI summary | English (default) |
| Source messages in inbox | Original language preserved |
| Summary panel | Toggle or section to view originals while reading summary |

**Implementation:** US-2.1, US-2.2 · Sprint 2

---

### D-05 — Sensitive data & AI ✅ DECIDED

| Field | Value |
|-------|-------|
| **Decision** | **All messages may be sent to AI** (Gemini / Ollama) |
| **Safeguard** | System must **detect and redact highly sensitive data** before AI processing |

Examples of sensitive patterns to handle:

- National ID / identification numbers
- Passport numbers
- Credit card numbers
- Other configurable PII patterns

**Behaviour:**

- Redact before sending text to Gemini/Ollama
- Show operator a notice when redaction occurred
- Original message text remains intact in the database and inbox

**Implementation:** US-2.4 · Sprint 2

---

## Assumptions

| ID | Assumption |
|----|------------|
| A-01 | Client has or will obtain a Telegram bot token from [@BotFather](https://t.me/BotFather) |
| A-02 | Client has a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey) |
| A-03 | Ollama is optional; used only when Gemini fails or is unavailable |
| A-04 | Single operator (client) uses the dashboard; no multi-user roles in v1 |
| A-05 | Production deployment will use HTTPS for Telegram webhook |
| A-06 | Message volume is low-to-moderate (< 10k messages); SQLite is sufficient |
| A-07 | Bot is added to group chats as a member; group messages are ingested via webhook |
| A-08 | Channel support may be added in a future release |

---

## Risk register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| R-01 | Auto-reply conflicts with operator review workflow | Medium | High | Default mode B; three-mode switcher (D-01) |
| R-02 | AI hallucinations in suggested replies | Medium | High | Editable drafts; operator approves before send |
| R-03 | Token limits on long message threads | Medium | Medium | Pagination; summarise in chunks; cache |
| R-04 | Gemini API quota / rate limits | Medium | Medium | Ollama fallback; summary caching (US-2.3) |
| R-05 | Missing `chat_id` breaks reply targeting | High | High | US-1.1, US-1.5 in Sprint 1 |
| R-06 | SQLite not suitable at scale | Low | Medium | Monitor volume; migrate to PostgreSQL if needed |
| R-07 | Dev API key insecure in production | High | High | US-5.4 in Sprint 4 |
| R-09 | Sensitive data sent to cloud AI | Medium | High | US-2.4 redaction layer (D-05) |
| R-10 | Group chat complexity (multiple senders per chat) | Medium | Medium | Store sender per message; thread by `chat_id` |
| R-11 | English summary loses nuance for non-English messages | Medium | Low | Original messages always visible (D-04) |

---

## Dependencies

| Dependency | Owner | Required by |
|------------|-------|-------------|
| Telegram bot token | Client | Sprint 0 (done) |
| Gemini API key | Client | Sprint 2 |
| Ollama installed locally | Client | Optional fallback |
| Public HTTPS URL for webhook | Client / DevOps | Production |
| Client decisions D-01 – D-05 | Client | ✅ Resolved |

---

## Change log

| Date | Change |
|------|--------|
| 2026-06-06 | Initial risk register and open decisions documented |
| 2026-06-06 | All five decisions resolved per Product Owner input |
