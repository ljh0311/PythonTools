#!/usr/bin/env python3
"""
One-time cleanup for memory.json:
- Ensures every entry has string content (fixes invalid/object content)
- Removes entries with empty or whitespace-only content
- Deduplicates by (type, normalized content), keeping the first occurrence
- Optionally removes noisy one-line conversation events (e.g. "User, [date]\\n\\nmsg")
  and keeps only summary-style events and reflection-derived memories.

Usage:
  python clean_memory.py              # dry run (print what would change)
  python clean_memory.py --write      # apply changes and overwrite memory.json (backup created)
"""

import json
import os
import re
import sys

MEMORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")


def normalize_content(content):
    """Return content as string; empty if not usable."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, (list, dict)):
        # Replace object-style "conversation" with a short summary
        if isinstance(content, list) and len(content) > 0:
            authors = []
            for part in content:
                if isinstance(part, dict) and part.get("author"):
                    authors.append(part["author"])
            if authors:
                return f"Conversation between {', '.join(authors[:5])} (consolidated)."
        return "Conversation (consolidated)."
    return str(content).strip()


def is_noisy_single_message_event(content):
    """True if content looks like a single raw message line (e.g. 'User, [date]\\n\\nmsg') or just sender+timestamp."""
    if not content or len(content) < 10:
        return False
    # Keep summary-style events: "Conversation with X, Y: ..." (valuable)
    if content.strip().startswith("Conversation with ") and len(content) > 50:
        return False
    # Noisy: content is only "Name, [timestamp]" or "Name - [timestamp]" (no message body)
    stripped = content.strip()
    if re.search(r"^[^[]+[,\-]\s*\[\d", stripped) and len(stripped) < 80 and "\n" not in stripped:
        return True
    if re.search(r"^[^[]+[,\-]\s*\[\d", stripped) and stripped.count("\n") <= 1:
        after_first_line = stripped.split("\n", 1)[-1].strip() if "\n" in stripped else ""
        if len(after_first_line) < 4:  # no real message after sender line
            return True
    # Pattern: "Name, [timestamp]\n\nmessage" with message on one line
    if "\n\n" in content:
        parts = content.split("\n\n", 1)
        if len(parts) == 2 and parts[0].strip() and re.search(r"\[\d", parts[0]):
            msg = parts[1].strip()
            # Very short or empty message = noisy
            if len(msg) < 4 or msg in ("", "Okie", "yas", "Hehe", "Lol", "Mew", "mewww", "okiee", "yesh"):
                return True
            # Single short line only
            if "\n" not in parts[1] and len(msg) < 60:
                return True
    return False


def run_cleanup(dry_run=True):
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("memory.json is not a list; skipping.")
        return

    seen = {}  # (type, normalized_content_lower) -> index
    kept = []
    removed_empty = 0
    removed_duplicate = 0
    removed_noisy = 0
    fixed_content = 0

    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            continue
        raw = entry.get("content")
        content = normalize_content(raw)
        typ = entry.get("type", "fact")
        source = entry.get("source", "")

        # Fix non-string content
        if raw is not None and not isinstance(raw, str):
            fixed_content += 1
        if not content:
            removed_empty += 1
            continue

        # Deduplicate: same type + same content (case-insensitive)
        key = (typ, content.lower())
        if key in seen:
            removed_duplicate += 1
            continue
        seen[key] = len(kept)

        # Optional: drop noisy one-message events (keeps reflection and summary-style events)
        if typ == "event" and source == "message_history" and is_noisy_single_message_event(content):
            removed_noisy += 1
            continue

        kept.append({
            "type": typ,
            "content": content,
            "timestamp": entry.get("timestamp"),
            "source": entry.get("source"),
        })
        # Preserve extra keys (optional memory fields and legacy fields)
        for k in ("timestamp_start", "timestamp_end", "summary", "person", "topic", "situation", "role"):
            if k in entry and k not in kept[-1]:
                kept[-1][k] = entry[k]

    print(f"Original entries: {len(data)}")
    print(f"Removed (empty): {removed_empty}")
    print(f"Removed (duplicate): {removed_duplicate}")
    print(f"Removed (noisy single-message events): {removed_noisy}")
    print(f"Fixed (non-string content): {fixed_content}")
    print(f"Kept: {len(kept)}")

    if dry_run:
        print("\n[DRY RUN] Use --write to apply changes.")
        return

    backup = MEMORY_PATH + ".backup"
    with open(backup, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nBackup written to {backup}")

    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(kept, f, indent=2, ensure_ascii=False)
    print(f"Written {len(kept)} entries to {MEMORY_PATH}")


if __name__ == "__main__":
    run_cleanup(dry_run="--write" not in sys.argv)
