---
name: end-of-day-summary
description: >-
  Summarizes today's code changes across any project into an End of Day (EOD)
  markdown file and sends it to Telegram via tdash send-eod (unless user says skip).
  Use when the user asks for end of day, EOD, daily wrap-up, or today's changes summary.
---

# End of Day Summary

**Scope:** personal/general skill (`~/.cursor/skills/end-of-day-summary/`). Works in any workspace.

Produce a dated EOD summary, save markdown, then **always send to Telegram** via `tdash.py send-eod` or `telegram-dev-notify` — skip only when the user explicitly says so.

## Install

```bash
cp -r Telegram_dashboard/dev-skills/telegram-dev-notify ~/.cursor/skills/
cp -r Telegram_dashboard/dev-skills/end-of-day-summary ~/.cursor/skills/
```

| File | Variables |
|------|-----------|
| `~/.cursor/skills/telegram-dev-notify/.env` | `TELEGRAM_DASHBOARD_URL`, `DASHBOARD_API_KEY`, `NOTIFY_TELEGRAM_CHAT_ID` |
| `~/.cursor/skills/end-of-day-summary/.env` | `EOD_TELEGRAM_CHAT_ID` (optional override for EOD recipient) |
| `Telegram_dashboard/openclaw/skills/telegram-dashboard/.env` | Same keys for OpenClaw `tdash.py` |

## Output format (verbatim)

```markdown
1. <What was done, for which project>

2. <What was done well>

3. <What can be improved>
```

## Workflow

```
EOD Progress:
- [ ] 1. Collect today's changes
- [ ] 2. Draft summary in the required format
- [ ] 3. Save markdown file
- [ ] 4. Send to Telegram via send-eod (unless user says skip)
- [ ] 5. Confirm paths + Telegram result to user
```

### 1. Collect today's changes

```bash
git log --since=midnight --until=now --author="$(git config user.name)" --pretty=format:"%h %s" --name-only
git status -sb
git diff --stat
```

Group by project/repo. If nothing changed, still write the file and ask before sending.

### 2–3. Draft and save

Default path: `docs/eod/eod-YYYY-MM-DD.md`

Template: [templates/eod-template.md](templates/eod-template.md)

### 4. Send to Telegram (default: yes)

**Preferred — tdash send-eod:**

```bash
python3 Telegram_dashboard/openclaw/skills/telegram-dashboard/scripts/tdash.py send-eod --file docs/eod/eod-YYYY-MM-DD.md
```

**Skill wrapper** (finds tdash, else notify):

```bash
python {baseDir}/scripts/send_eod.py --file docs/eod/eod-YYYY-MM-DD.md
```

Skip Telegram **only** when the user says skip / no telegram / don't send.

### 5. Confirm

Report saved path, Telegram result, and one-line preview of section 1.

## Additional resources

- [.env.example](.env.example)
- [scripts/send_eod.py](scripts/send_eod.py)
