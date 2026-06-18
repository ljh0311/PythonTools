---
name: smart-persona-profile
description: Load the user's learned SmartPersona profile (markdown) as context for personalized assistance and personal-growth coaching.
metadata:
  {"openclaw":{"requires":{"env":["SMARTPERSONA_WORKDIR"],"bins":["python3"]},"primaryEnv":"SMARTPERSONA_WORKDIR"}}
---

# SmartPersona User Profile

Use this skill when the user wants personalized help that reflects who they are — preferences, relationships, habits, communication style, and growth themes learned from their chats.

## Configuration

| Variable | Example | Purpose |
|----------|---------|---------|
| `SMARTPERSONA_WORKDIR` | `/path/to/SmartPersona` | Folder containing `user_profile.md` |
| `SMARTPERSONA_PROFILE_PATH` | `/data/me/profile.md` | Optional explicit profile file path |

SmartPersona auto-writes `user_profile.md` when you teach from chats or add memories (unless `SMARTPERSONA_AUTO_EXPORT_PROFILE=0`).

## Helper script

```bash
python3 {baseDir}/scripts/sp.py path
python3 {baseDir}/scripts/sp.py context
python3 {baseDir}/scripts/sp.py context --json
python3 {baseDir}/scripts/sp.py profile
```

- **`context`** — concise bullets for system prompts (OpenClaw, chatbots)
- **`profile`** — full markdown including growth sections and reflection prompts

## How to use the output

1. **Chatbots / agents:** inject `context` (or the `## Agent context` section) as system or developer context.
2. **Personal growth:** read `profile` with the user; use **Growth & reflection** prompts for journaling or coaching.

## Generating / updating the profile

Run the SmartPersona GUI (`python main.py`), paste chat exports in **Teach**, or add memories manually. The profile updates automatically.
