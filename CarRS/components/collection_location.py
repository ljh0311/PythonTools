"""Collection location and convenience Distance rating (0–5)."""

from __future__ import annotations

from typing import Optional, Tuple

import pandas as pd

COLLECTION_LOCATION_COL = "Collection location"
DISTANCE_RATING_COL = "Distance rating"

RATING_MIN = 0
RATING_MAX = 5

# 0 = beside house; 3 = OK by bus/MRT; 5 = avoid unless urgent
RATING_LABELS = {
    0: "Beside house / next door",
    1: "Very short walk",
    2: "Nearby (short trip)",
    3: "Acceptable by bus/MRT",
    4: "Long commute — prefer avoid",
    5: "Last resort / urgent only",
}


def rating_choice_labels() -> list[str]:
    """Combobox display values including blank."""
    return [""] + [f"{score} — {RATING_LABELS[score]}" for score in range(RATING_MIN, RATING_MAX + 1)]


def parse_rating_choice(choice: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """Parse combobox/text into 0–5. Empty is allowed (None)."""
    text = (choice or "").strip()
    if not text:
        return True, None, None
    try:
        score = int(text.split("—", 1)[0].split("-", 1)[0].strip())
    except (TypeError, ValueError):
        return False, None, "Distance rating must be a whole number from 0 to 5."
    if score < RATING_MIN or score > RATING_MAX:
        return False, None, f"Distance rating must be between {RATING_MIN} and {RATING_MAX}."
    return True, score, None


def format_rating_choice(score) -> str:
    """Turn stored score into combobox label."""
    if score is None or (isinstance(score, float) and pd.isna(score)):
        return ""
    try:
        value = int(score)
    except (TypeError, ValueError):
        return ""
    if value not in RATING_LABELS:
        return str(value)
    return f"{value} — {RATING_LABELS[value]}"


def ensure_collection_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure location/rating columns exist; coerce rating to nullable int 0–5."""
    df = df.copy()
    if COLLECTION_LOCATION_COL not in df.columns:
        df[COLLECTION_LOCATION_COL] = ""
    if DISTANCE_RATING_COL not in df.columns:
        df[DISTANCE_RATING_COL] = pd.NA
    df[COLLECTION_LOCATION_COL] = (
        df[COLLECTION_LOCATION_COL].fillna("").astype(str).replace({"nan": "", "None": ""})
    )
    ratings = pd.to_numeric(df[DISTANCE_RATING_COL], errors="coerce")
    ratings = ratings.where(ratings.between(RATING_MIN, RATING_MAX))
    df[DISTANCE_RATING_COL] = ratings.astype("Int64")
    return df
