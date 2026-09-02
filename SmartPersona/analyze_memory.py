#!/usr/bin/env python3
"""Quick memory.json health report."""
import json
import os
from collections import Counter

from brain import _content_similarity, _is_noisy_event_content, _normalize_memory_content

MEMORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")


def main():
    with open(MEMORY_PATH, encoding="utf-8") as f:
        data = json.load(f)

    print(f"Total entries: {len(data)}")
    print("By type:", dict(Counter(e.get("type", "?") for e in data)))
    print("By source:", dict(Counter(e.get("source", "?") for e in data)))

    empty = noisy = bad_type = non_str = 0
    for e in data:
        if not isinstance(e.get("content"), str):
            non_str += 1
        if not _normalize_memory_content(e.get("content")):
            empty += 1
        if e.get("type") == "event" and e.get("source") == "message_history":
            if _is_noisy_event_content(e.get("content")):
                noisy += 1
        if e.get("type") not in (
            "fact", "event", "preference", "habit", "belief",
            "relationship", "voice", "topic_style", "reaction",
        ):
            bad_type += 1

    print(f"Empty content: {empty}")
    print(f"Non-string content: {non_str}")
    print(f"Noisy events: {noisy}")
    print(f"Invalid types: {bad_type}")

    seen = {}
    dups = 0
    for e in data:
        c = _normalize_memory_content(e.get("content")).lower()
        person = (e.get("person") or "").strip().lower() if e.get("type") == "relationship" else ""
        key = (e.get("type"), c, person)
        if key in seen:
            dups += 1
        else:
            seen[key] = True
    print(f"Exact duplicates (type+content+person): {dups}")

    sim_pairs = 0
    str_items = [e for e in data if isinstance(e.get("content"), str)]
    for a in range(len(str_items)):
        for b in range(a + 1, len(str_items)):
            ea, eb = str_items[a], str_items[b]
            if ea.get("type") != eb.get("type"):
                continue
            if _content_similarity(ea.get("content", ""), eb.get("content", "")) >= 0.65:
                sim_pairs += 1
    print(f"Near-duplicate pairs (same type, similarity>=0.65): {sim_pairs}")

    rel_no_person = sum(
        1 for e in data
        if e.get("type") == "relationship" and not (e.get("person") or "").strip()
    )
    print(f"Relationship entries missing person field: {rel_no_person}")


if __name__ == "__main__":
    main()
