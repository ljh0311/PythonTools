---
name: end-of-day-summary
description: >-
  Summarizes today's code changes across any project into an End of Day (EOD)
  markdown file and sends it to Telegram via the telegram-dev-notify skill.
  Use when the user asks for end of day, EOD, daily wrap-up, today's changes
  summary, or to send the day's work summary to Telegram.
---

# End of Day Summary

**Scope:** personal/general skill (`~/.cursor/skills/end-of-day-summary/`). Works in any workspace. Not tied to one repo.

Produce a dated EOD summary from today's git/session work, save it as markdown, then deliver it with **telegram-dev-notify** (no duplicated HTTP code in this skill).

## Prerequisites

Install both skill packs (order does not matter):

```bash
# From Telegram_dashboard repo root
cp -r Telegram_dashboard/dev-skills/telegram-dev-notify ~/.cursor/skills/
cp -r Telegram_dashboard/dev-skills/end-of-day-summary ~/.cursor/skills/
```

Configure credentials:

| File | Variables |
|------|-----------|
| `~/.cursor/skills/telegram-dev-notify/.env` | `TELEGRAM_DASHBOARD_URL`, `DASHBOARD_API_KEY`, `NOTIFY_TELEGRAM_CHAT_ID` |
| `~/.cursor/skills/end-of-day-summary/.env` | Optional `EOD_TELEGRAM_CHAT_ID` if EOD goes to a different chat |

If `EOD_TELEGRAM_CHAT_ID` is unset, the send wrapper uses `NOTIFY_TELEGRAM_CHAT_ID` from telegram-dev-notify.

## Output format (verbatim)

Write the summary body exactly in this structure:

```markdown
1. <What was done, for which project>

2. <What was done well>

3. <What can be improved>
```

Fill each numbered line with concrete content (not the angle-bracket placeholders). Use short bullets under a number only when one line is not enough.

## Workflow

```
EOD Progress:
- [ ] 1. Collect today's changes
- [ ] 2. Draft summary in the required format
- [ ] 3. Save markdown file
- [ ] 4. Send to Telegram via telegram-dev-notify (unless user says skip)
- [ ] 5. Confirm paths + Telegram result to user
```

### 1. Collect today's changes

From the active workspace (and other repos the user names), gather evidence for **today's local date**:

```bash
git log --since=midnight --until=now --author="$(git config user.name)" --pretty=format:"%h %s" --name-only
git status -sb
git diff --stat
```

Also use this chat/session for uncommitted or multi-project work. Group findings **by project/repo name**.

If nothing changed today, still write the file noting that, and ask before sending Telegram.

### 2. Draft the summary

- **1.** What shipped or progressed, named by project (features, fixes, refactors, docs).
- **2.** What went well (clean diffs, tests, modularity, fast feedback).
- **3.** What to improve next (gaps, debt, flaky checks, unclear scope).

Keep it factual and grounded in the collected evidence. Do not invent commits.

### 3. Save markdown

Default path **in the active project** (create dirs if needed):

```
docs/eod/eod-YYYY-MM-DD.md
```

Use today's date (`YYYY-MM-DD`). If `docs/eod/` is wrong for the repo, prefer an existing `docs/` or `notes/` pattern; otherwise create `docs/eod/`.

File contents:

1. Title line: `# End of Day — YYYY-MM-DD`
2. Blank line
3. The three numbered sections in the required format
4. Optional footer: `Generated: <ISO timestamp>`

Template: [templates/eod-template.md](templates/eod-template.md)

### 4. Send to Telegram

**Do not reimplement HTTP here.** Use one of:

**Preferred — thin EOD wrapper** (loads this skill's `.env`, delegates to telegram-dev-notify):

```bash
python {baseDir}/scripts/send_eod.py --file docs/eod/eod-YYYY-MM-DD.md
```

**Direct — telegram-dev-notify** (same API, general-purpose):

```bash
python ~/.cursor/skills/telegram-dev-notify/scripts/send_notify.py --file docs/eod/eod-YYYY-MM-DD.md
```

**OpenClaw** (when available):

```bash
python3 Telegram_dashboard/openclaw/skills/telegram-dashboard/scripts/tdash.py send-file \
  --chat-id "$NOTIFY_TELEGRAM_CHAT_ID" --file docs/eod/eod-YYYY-MM-DD.md
```

**Rules:**

- Dashboard server must be running.
- Messages truncate at ~4096 chars; full file stays on disk.
- If env/send fails, keep the `.md` and report the error.
- Skip Telegram only when the user says so.

### 5. Confirm to user

Report:

- Path of the saved `.md`
- Whether Telegram send succeeded
- One-line preview of section 1

## Additional resources

- Env template: [.env.example](.env.example)
- Message template: [templates/eod-template.md](templates/eod-template.md)
- Send wrapper: [scripts/send_eod.py](scripts/send_eod.py)
- Delivery skill: `~/.cursor/skills/telegram-dev-notify/SKILL.md`
