# Telegram Dashboard — Agile Documentation

This folder contains project documentation aligned with **Agile software development** practices: product vision, backlog, sprint plans, acceptance criteria, and definition of done.

## Document index

| Document | Purpose |
|----------|---------|
| [Product Vision](product-vision.md) | Why we are building this, goals, and success metrics |
| [Current Increment](current-increment.md) | What has been delivered so far (Sprint 0 foundation) |
| [Product Backlog](product-backlog.md) | Epics, user stories, priorities, and acceptance criteria |
| [Sprint Plan](sprint-plan.md) | Sprint goals, scope, and deliverables (Sprints 1–4) |
| [Definition of Done](definition-of-done.md) | Shared quality bar for every backlog item |
| [Architecture](architecture.md) | System design: current state and target v2 |
| [Risks & Decisions](risks-and-decisions.md) | Open client decisions, risks, and assumptions |

## Agile framework in use

We follow a lightweight Scrum-inspired process:

| Ceremony | Cadence | Artifact |
|----------|---------|----------|
| **Product Backlog refinement** | Ongoing | [product-backlog.md](product-backlog.md) |
| **Sprint Planning** | Start of each sprint | [sprint-plan.md](sprint-plan.md) |
| **Daily progress** | Daily (async) | Git commits, PR updates |
| **Sprint Review** | End of sprint | Demo against acceptance criteria |
| **Sprint Retrospective** | End of sprint | Notes appended to sprint plan |

## Roles

| Role | Responsibility |
|------|----------------|
| **Product Owner (Client)** | Prioritises backlog, accepts increments, answers open questions |
| **Development Team** | Delivers working software each sprint |
| **Scrum Master / PM** | Facilitates planning, tracks blockers, maintains documentation |

## Current status

- **Active branch:** `cursor/telegram-dashboard-98e1`
- **Completed:** Sprint 0 — Foundation (see [current-increment.md](current-increment.md))
- **Next up:** Sprint 1 — Inbox & Filtering (see [sprint-plan.md](sprint-plan.md))
