"""Collection / pickup location fields for rental records."""

import pandas as pd

COLLECTION_LOCATION_COL = "Collection location"
DISTANCE_RATING_COL = "Distance rating"
DISTANCE_RATING_MIN = 0
DISTANCE_RATING_MAX = 5


def parse_distance_rating(value):
    """Parse optional 0-5 convenience rating. Returns int or None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        rating = int(float(text))
    except (TypeError, ValueError):
        return None
    if DISTANCE_RATING_MIN <= rating <= DISTANCE_RATING_MAX:
        return rating
    return None


def format_distance_rating(value):
    """Format rating for display; empty string when unset."""
    parsed = parse_distance_rating(value)
    return "" if parsed is None else str(parsed)


def format_collection_location(value):
    """Normalize collection location text for storage."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def ensure_collection_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure collection location columns exist on the dataframe."""
    df = df.copy()
    if COLLECTION_LOCATION_COL not in df.columns:
        df[COLLECTION_LOCATION_COL] = ""
    else:
        df[COLLECTION_LOCATION_COL] = df[COLLECTION_LOCATION_COL].apply(
            format_collection_location
        )
    if DISTANCE_RATING_COL not in df.columns:
        df[DISTANCE_RATING_COL] = pd.NA
    else:
        df[DISTANCE_RATING_COL] = df[DISTANCE_RATING_COL].apply(parse_distance_rating)
    return df
