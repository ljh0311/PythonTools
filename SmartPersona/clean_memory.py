#!/usr/bin/env python3
"""
Clean memory.json using SmartPersonaBrain tidy pipeline (recommended).

Usage:
  python clean_memory.py              # dry run (report only)
  python clean_memory.py --write      # apply (backup created first)
"""

import json
import os
import shutil
import sys

MEMORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")


def main():
    if not os.path.isfile(MEMORY_PATH):
        print(f"No memory file at {MEMORY_PATH}")
        return 1

    with open(MEMORY_PATH, encoding="utf-8") as f:
        before_data = json.load(f)
    before = len(before_data) if isinstance(before_data, list) else 0

    dry_run = "--write" not in sys.argv
    if dry_run:
        from brain import SmartPersonaBrain

        brain = SmartPersonaBrain(persist=False)
        brain._memory = json.loads(json.dumps(before_data, ensure_ascii=False))
        brain.tidy_memory()
        after = len(brain._memory)
        print(f"Original entries: {before}")
        print(f"Would keep: {after}")
        print(f"Would remove: {max(0, before - after)}")
        print("\n[DRY RUN] Use --write to apply changes.")
        return 0

    backup = MEMORY_PATH + ".backup"
    shutil.copy2(MEMORY_PATH, backup)
    print(f"Backup written to {backup}")

    from brain import SmartPersonaBrain

    brain = SmartPersonaBrain(persist=True)
    brain.tidy_memory()
    if hasattr(brain, "export_user_profile"):
        try:
            brain.export_user_profile()
        except OSError:
            pass
    after = len(brain.get_memory())
    print(f"Tidied: {before} → {after} entries ({max(0, before - after)} removed)")
    print(f"Written to {MEMORY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
