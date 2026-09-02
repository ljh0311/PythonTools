# User inbox (v0.2) — see all messages on your Telegram account

**v0.1** = bot only (PMs to the bot + groups the bot is in).  
**v0.2** = your personal Telegram account (all chats you are in).

Both can run at the same time. Messages are tagged `bot` or `user_account` in the database and UI.

## What you need

1. **API credentials** from [my.telegram.org](https://my.telegram.org) → API development tools  
   - `api_id` (number)  
   - `api_hash` (string)

2. Your **phone number** (same one as your Telegram app)

## Setup

### 1. Add to `.env`

```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your-api-hash-here
MTProto_ENABLED=true
MTProto_PHONE=+6512345678
```

Optional: `MTProto_SESSION_NAME=user.session` (default saves to `data/user.session`)

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Log in once (creates session file)

```bash
cd Telegram_dashboard
source .venv/bin/activate
export PYTHONPATH="$(pwd)"
python3 scripts/mtproto_login.py
```

Telegram will send a login code to your app. Enter it in the terminal.  
If you use 2FA, enter your Telegram password too.

The session file is like staying logged in — **keep it secret** (already in `.gitignore` via `data/`).

### 4. Start the dashboard

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Top bar should show: `My account v0.2: @yourusername` when listening.

## What gets captured

| Chat type | Captured? |
|-----------|-----------|
| Private chats you are in | Yes |
| Groups / supergroups you are in | Yes |
| Channels you follow | Yes (posts appear as messages) |
| Secret chats | No (Telegram does not allow this) |
| Chats you are not in | No |

- **Incoming** = someone else sent to you  
- **Outgoing** = you sent (from any device)

Auto-reply from the bot **does not** run on user-account messages.

## Sending replies

**Tools** view → **Send as me** — sends from your personal account (v0.2).  
**Send via bot** — still uses the bot (v0.1).

## Filtering in Inbox

Advanced filters → **Message source**:

- **Bot (v0.1)** — only bot webhook messages  
- **My account (v0.2)** — only your account inbox  
- **All sources** — both combined

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/user-account/status` | Login / listening status |
| POST | `/api/user-account/login/send-code` | Send SMS code (alternative to CLI) |
| POST | `/api/user-account/login/confirm` | Confirm code |
| POST | `/api/user-account/send` | Send as your account |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `not logged in` | Run `scripts/mtproto_login.py` |
| `listening off` | Set `MTProto_ENABLED=true` and restart |
| Duplicate messages in groups | Bot and your account both see group messages — filter by source or ignore duplicates (same `chat_id` + `message_id` is deduped) |
| Session invalid | Delete `data/user.session` and log in again |

## Security notes

- The session file is **full access** to your Telegram account.  
- Do not commit `data/` or share the session.  
- Use a dedicated Telegram account if you prefer isolation.
