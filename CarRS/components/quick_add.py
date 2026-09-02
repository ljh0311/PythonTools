"""Parse quick-add shortcut text for rental records."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

DEFAULT_SHORTCUTS = [
    "1 hour rental(40km), mazda 3",
    "2 hours (60km), honda vezel",
    "3h 80km getgo",
]

_DURATION_RE = re.compile(
    r"(?P<hours>\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hour|hours)\b",
    re.IGNORECASE,
)
_DISTANCE_RE = re.compile(
    r"(?P<km>\d+(?:\.\d+)?)\s*(?:km|kilometers?)\b",
    re.IGNORECASE,
)
_DISTANCE_PAREN_RE = re.compile(
    r"\(\s*(?P<km>\d+(?:\.\d+)?)\s*(?:km)?\s*\)",
    re.IGNORECASE,
)
_RATING_RE = re.compile(
    r"(?:rating|r)\s*[:=\-]?\s*(?P<rating>[0-5])\b",
    re.IGNORECASE,
)
_FROM_RE = re.compile(
    r"(?:from|@|collected(?:\s+from)?)\s+(?P<loc>.+?)(?=\s+(?:rating|r)\s*[:=\-]?\s*[0-5]\b|[,;|]|$)",
    re.IGNORECASE,
)
_PROVIDER_PATTERNS = [
    (re.compile(r"\bgetgo\s*\(?\s*ev\s*\)?\b", re.I), "Getgo(EV)"),
    (re.compile(r"\bgetgo\b", re.I), "Getgo"),
    (re.compile(r"\bcar\s*club\b", re.I), "Car Club"),
    (re.compile(r"\becon\b", re.I), "Econ"),
    (re.compile(r"\bstand\b", re.I), "Stand"),
    (re.compile(r"\btribecar\b", re.I), "Tribecar"),
    (re.compile(r"\bsocar\b", re.I), "SoCar"),
    (re.compile(r"\bnormal\s*rental\b", re.I), "NormalRental"),
]


def _default_shortcuts_path() -> Path:
    return Path(__file__).resolve().parent.parent / "quick_add_shortcuts.json"


def load_shortcuts(path: Optional[Path] = None) -> list[str]:
    file_path = path or _default_shortcuts_path()
    if not file_path.exists():
        return list(DEFAULT_SHORTCUTS)
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        items = data.get("shortcuts", data) if isinstance(data, dict) else data
        cleaned = [str(item).strip() for item in items if str(item).strip()]
        return cleaned or list(DEFAULT_SHORTCUTS)
    except (OSError, json.JSONDecodeError, TypeError):
        return list(DEFAULT_SHORTCUTS)


def save_shortcuts(shortcuts: list[str], path: Optional[Path] = None) -> None:
    file_path = path or _default_shortcuts_path()
    cleaned = []
    seen = set()
    for item in shortcuts:
        text = str(item).strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    file_path.write_text(
        json.dumps({"shortcuts": cleaned}, indent=2),
        encoding="utf-8",
    )


def _match_known_model(text: str, known_models: Optional[list[str]]) -> Optional[str]:
    if not known_models or not text:
        return None
    lowered = text.casefold()
    # Prefer longest model name match
    ranked = sorted((m for m in known_models if m), key=lambda m: len(m), reverse=True)
    for model in ranked:
        if model.casefold() in lowered:
            return model
    return None


def _extract_model_from_remainder(text: str) -> str:
    cleaned = text
    for pattern, _ in _PROVIDER_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    cleaned = _DURATION_RE.sub(" ", cleaned)
    cleaned = _DISTANCE_RE.sub(" ", cleaned)
    cleaned = _DISTANCE_PAREN_RE.sub(" ", cleaned)
    cleaned = _RATING_RE.sub(" ", cleaned)
    cleaned = _FROM_RE.sub(" ", cleaned)
    cleaned = re.sub(r"\brental\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"[,;|/]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_")
    return cleaned


def parse_quick_add(
    text: str,
    known_models: Optional[list[str]] = None,
    default_provider: str = "Getgo",
    default_region: str = "Singapore",
) -> dict[str, Any]:
    """
    Parse shortcut text into rental fields.

    Example: \"1 hour rental(40km), mazda 3\"
    → hours=1, distance=40, car_model=\"mazda 3\"
    """
    raw = (text or "").strip()
    result: dict[str, Any] = {
        "ok": False,
        "error": None,
        "hours": None,
        "distance": None,
        "car_model": None,
        "provider": default_provider,
        "region": default_region,
        "collection_location": "",
        "distance_rating": None,
        "date": datetime.now(),
        "is_weekend": datetime.now().weekday() >= 5,
        "raw": raw,
    }
    if not raw:
        result["error"] = "Type a shortcut, e.g. 1 hour rental(40km), mazda 3"
        return result

    hours_match = _DURATION_RE.search(raw)
    distance_match = _DISTANCE_RE.search(raw) or _DISTANCE_PAREN_RE.search(raw)
    rating_match = _RATING_RE.search(raw)
    from_match = _FROM_RE.search(raw)

    if hours_match:
        result["hours"] = float(hours_match.group("hours"))
    if distance_match:
        result["distance"] = float(distance_match.group("km"))
    if rating_match:
        result["distance_rating"] = int(rating_match.group("rating"))
    if from_match:
        result["collection_location"] = from_match.group("loc").strip(" .,;")

    for pattern, provider in _PROVIDER_PATTERNS:
        if pattern.search(raw):
            result["provider"] = provider
            if provider in ("SoCar", "NormalRental"):
                result["region"] = "Malaysia"
            break

    known = _match_known_model(raw, known_models)
    if known:
        result["car_model"] = known
    else:
        # Prefer text after the last comma as model
        if "," in raw:
            after = raw.split(",")[-1].strip()
            model = _extract_model_from_remainder(after) or _extract_model_from_remainder(raw)
        else:
            model = _extract_model_from_remainder(raw)
        result["car_model"] = model or None

    missing = []
    if result["hours"] is None:
        missing.append("hours")
    if result["distance"] is None:
        missing.append("distance (km)")
    if not result["car_model"]:
        missing.append("car model")
    if missing:
        result["error"] = "Need " + ", ".join(missing) + "."
        return result

    result["ok"] = True
    return result
