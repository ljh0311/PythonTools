# Risks, Assumptions & Open Decisions

Items requiring **Product Owner (client)** input are marked **DECISION REQUIRED**.

---

## Open decisions

| ID | Question | Options | Impact | Status |
|----|----------|---------|--------|--------|
| D-01 | **Auto-reply behaviour** | A) Bot auto-replies (current) · B) Operator approves all replies · C) Per-chat toggle | Sprint 3 scope; affects bot_handler | **DECISION REQUIRED** |
| D-02 | **Message scope** | A) Direct messages only · B) Groups · C) Channels · D) All | Schema (`chat_type`), UI complexity | **DECISION REQUIRED** |
| D-03 | **Topic model** | A) Free-form tags · B) Fixed categories · C) AI-only auto-tags | Sprint 3 design | **DECISION REQUIRED** |
| D-04 | **Summary language** | A) Same as source messages · B) Always English | AI prompt design | **DECISION REQUIRED** |
| D-05 | **PII / exclusion rules** | A) All messages sent to AI · B) Exclude specific users · C) Redact before AI | Privacy, compliance | **DECISION REQUIRED** |

### Recommended defaults (if client defers)

| ID | Recommendation | Rationale |
|----|----------------|-----------|
| D-01 | B — Operator approves (auto-reply off by default) | Aligns with review-then-act vision |
| D-02 | A — Direct messages only for v0.2 | Simplest; extend later |
| D-03 | A — Free-form tags + optional AI auto-tag | Flexible, low friction |
| D-04 | A — Same as source | Respects multilingual users |
| D-05 | A — All messages to AI (local Ollama fallback) | Simplest; revisit for production |

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

---

## Risk register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| R-01 | Auto-reply conflicts with operator review workflow | High | High | US-5.1; decide D-01 in Sprint 1 |
| R-02 | AI hallucinations in suggested replies | Medium | High | Editable drafts; operator must approve before send |
| R-03 | Token limits on long message threads | Medium | Medium | Pagination; summarise in chunks; cache |
| R-04 | Gemini API quota / rate limits | Medium | Medium | Ollama fallback; summary caching (US-2.3) |
| R-05 | Missing `chat_id` breaks reply targeting | High | High | US-1.1, US-1.5 in Sprint 1 |
| R-06 | SQLite not suitable at scale | Low | Medium | Monitor volume; migrate to PostgreSQL if needed |
| R-07 | Dev API key insecure in production | High | High | US-5.4 in Sprint 4 |
| R-08 | Client decisions delayed | Medium | Medium | Use recommended defaults; proceed with Sprint 1 |

---

## Dependencies

| Dependency | Owner | Required by |
|------------|-------|-------------|
| Telegram bot token | Client | Sprint 0 (done) |
| Gemini API key | Client | Sprint 2 |
| Ollama installed locally | Client | Optional fallback |
| Public HTTPS URL for webhook | Client / DevOps | Production |
| Sprint 1 decisions (D-01, D-02) | Client | Sprint 1 start |

---

## Change log

| Date | Change |
|------|--------|
| 2026-06-06 | Initial risk register and open decisions documented |
