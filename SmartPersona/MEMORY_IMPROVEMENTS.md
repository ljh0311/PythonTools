# memory.json – Evaluation & Improvements

## Issues in your current file

### 1. **Invalid schema (first entry)**

- One entry has `content` as an **object** (array of `{author, messages}`) instead of a string.
- The brain expects every memory to have **string** `content` for context injection. Non-string content can break or bloat prompts.
- **Fix:** The brain **auto-cleans on load**: it converts non-string content to a short string (e.g. "Conversation between Bb ❤️, hong (consolidated)."). `add_memory` also normalizes content so new entries are never stored as list/dict.

### 2. **Duplicate reflection memories**

- The same facts were added multiple times from different teaching runs, e.g.:
  - "Hong and Yappie have a playful relationship." (2×)
  - "Marlboro Ice Blast cigarettes are preferred over Semo brand." (3×)
  - "Hong invited Yappie to join him on a beach day with Chris, but Yappie declined due to financial constraints." (3×)
  - "Hong is referred to as \"laoban\" (boss) by Yappie." (3×)
  - "Hong and Yong Qing are both in Johor Bahru (JB)." (2×)
- **Fix:** The brain **skips adding** a reflection memory if the same content (normalized) already exists for that type. On **load**, the brain **deduplicates** existing entries automatically.

### 3. **Noisy one-per-message events**

- Many events are single raw lines, e.g. `"Bb ❤️, [2/3/2026 10:44 PM]\n\nHAHAHA"`, `"hong, [2/3/2026 10:44 PM]\n\nyas"`, plus an **empty** message stored as event.
- They add little value for the model and bloat context.
- **Fix:** On **load**, the brain **removes** these noisy single-message events and keeps only summary-style "Conversation with X, Y: ..." and reflection-derived memories. The brain only stores **one** conversation summary per teach run (and skips empty summaries).

### 4. **Empty or useless content**

- At least one event has content that is effectively empty (`"Bb ❤️, [2/3/2026 10:45 PM]\n\n"`).
- **Fix:** The brain no longer stores a conversation summary when the summary would be too short (< 5 chars). On **load**, the brain **drops** entries with empty or whitespace-only content. `add_memory` rejects empty content.

---

## Recommendations

| Goal | Action |
|------|--------|
| **Automatic cleanup** | The **brain cleans memory automatically** every time it loads: it normalizes non-string content, drops empty entries, deduplicates, and removes noisy single-message events. You do **not** need to run `clean_memory.py` regularly. |
| **Avoid future duplicates** | Done in `brain.py`: reflection memories are not added if the same content (same type) already exists. |
| **Avoid empty or tiny summaries** | Done: conversation summary is not stored when the content would be too short; `add_memory` rejects empty content. |
| **Keep memory lean** | Prefer one summary event per conversation; the brain only stores one summary per teach run and strips noisy events on load. |

---

## Optional: manual cleanup script

`clean_memory.py` is still available if you want to **preview** what would be removed or create a **backup** before opening the app:

```bash
cd SmartPersona
python clean_memory.py        # preview only
python clean_memory.py --write   # apply and overwrite memory.json (backup created)
```

Normally, just opening the app (which loads the brain) is enough—memory is cleaned on load.
