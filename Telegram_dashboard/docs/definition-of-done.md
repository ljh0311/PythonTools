# Definition of Done

A backlog item is **Done** only when all criteria below are met. This applies to every user story across all sprints.

---

## Story-level checklist

### Functionality
- [ ] All acceptance criteria in [product-backlog.md](product-backlog.md) are met
- [ ] Feature works in the latest Chrome and Firefox
- [ ] Feature is responsive (mobile and desktop layouts)
- [ ] Error states handled with user-visible feedback (toast or inline message)
- [ ] Empty states handled (no messages, no users, AI unavailable)

### Code quality
- [ ] Code follows existing project conventions (`Telegram_dashboard/backend/`, `frontend/`)
- [ ] No unrelated changes or scope creep in the PR
- [ ] New environment variables documented in `.env.example`
- [ ] Database migrations are backward-compatible (existing data preserved)

### API & security
- [ ] New endpoints protected by API key (or session auth from Sprint 4 onward)
- [ ] Input validated (Pydantic models for request bodies)
- [ ] No secrets logged or returned in API responses

### Testing
- [ ] Manually tested against acceptance criteria (demo script in sprint plan)
- [ ] Webhook ingest tested with sample Telegram update payload
- [ ] AI features tested with Gemini; fallback to Ollama verified when Gemini unavailable

### Documentation
- [ ] [current-increment.md](current-increment.md) updated if new endpoints or widgets shipped
- [ ] README updated if setup steps change
- [ ] Sprint retrospective notes added to [sprint-plan.md](sprint-plan.md)

### Delivery
- [ ] Code committed on feature branch
- [ ] Branch pushed to remote
- [ ] PR created or updated with summary and test notes
- [ ] Product Owner (client) has reviewed demo or approved criteria

---

## Sprint-level checklist

A sprint is **Done** when:

- [ ] All committed stories meet the story-level Definition of Done
- [ ] Sprint review demo completed against sprint plan script
- [ ] Retrospective completed; notes recorded in [sprint-plan.md](sprint-plan.md)
- [ ] Product backlog re-prioritised for next sprint
- [ ] No P0 bugs left open from the sprint

---

## Release-level checklist (v1.0)

- [ ] All P0 and P1 stories complete
- [ ] Authentication hardened (US-5.4)
- [ ] Deployment guide written (US-5.5)
- [ ] Client sign-off on operator workflow end-to-end
