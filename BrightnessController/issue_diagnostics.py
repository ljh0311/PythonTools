"""Format and validate runtime issue summaries for the BrightnessController GUI."""

from __future__ import annotations

from typing import Dict, List


def format_issue_log(events: List[Dict[str, str]]) -> str:
    if not events:
        return "No runtime issues recorded yet."
    lines = []
    for event in events[-12:]:
        lines.append(f"[{event['level']}] {event['source']}: {event['message']}")
    return "\n".join(lines)


def build_fallback_summary(events: List[Dict[str, str]]) -> str:
    recent = events[-6:]
    unique: List[Dict[str, str]] = []
    seen = set()
    for item in recent:
        key = (item["level"], item["source"], item["message"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    lines = [
        "Setup tips:",
        "- Close other apps using the camera before starting control.",
    ]
    for item in unique[:4]:
        level = item["level"]
        source = item["source"]
        message = item["message"]
        if level == "ERROR":
            lines.append(f"- Error in {source}: {message}. Retry after closing other camera apps.")
        elif level == "WARN":
            lines.append(f"- Warning in {source}: {message}. Check camera selection in Settings.")
        else:
            lines.append(f"- {source}: {message}")
    return "\n".join(lines)


def sanitize_summary(text: str, fallback: str) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) < 12:
        return fallback

    lowered = cleaned.lower()
    junk_markers = ("**none**", "* **none**", "none,", "no issues", "no errors")
    if any(marker in lowered for marker in junk_markers):
        return fallback

    return cleaned
