"""Rental start/end date helpers and rental-hour computation."""

import pandas as pd

RENTAL_END_DATE_COL = "Rental end date"
RENTAL_START_DATE_COL = "Date"


def compute_rental_hours_from_dates(start_date, end_date, fallback_hours=None):
    """
    Compute rental duration in hours from start and end dates.

    Convention (date-only fields, no pickup/return clock times):
    - Same calendar day: use fallback_hours (manual entry), default 0.1 if unset.
    - Multi-day (end after start): inclusive calendar days × 24 hours.
      Example: start 01/01, end 03/01 → 3 days → 72 hours.
    - End before start: invalid; returns fallback_hours.
    """
    if start_date is None or pd.isna(start_date):
        return fallback_hours
    start = pd.Timestamp(start_date).normalize()
    if end_date is None or pd.isna(end_date):
        return fallback_hours
    end = pd.Timestamp(end_date).normalize()
    if end < start:
        return fallback_hours
    if start == end:
        if fallback_hours is not None and fallback_hours > 0:
            return float(fallback_hours)
        return 0.1
    inclusive_days = (end - start).days + 1
    return float(inclusive_days * 24)


def infer_end_date_from_hours(start_date, rental_hours):
    """Infer rental end timestamp from start date and duration in hours."""
    if start_date is None or pd.isna(start_date):
        return pd.NaT
    start = pd.Timestamp(start_date)
    hours = float(rental_hours) if rental_hours is not None and not pd.isna(rental_hours) else 0
    if hours <= 0:
        return start.normalize()
    return start + pd.Timedelta(hours=hours)


def ensure_rental_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure rental end date column exists. Backfill from Date + Rental hour for legacy rows.
    Date remains the rental start date.
    """
    df = df.copy()
    if RENTAL_END_DATE_COL not in df.columns:
        df[RENTAL_END_DATE_COL] = pd.NaT

    if RENTAL_START_DATE_COL not in df.columns:
        return df

    mask = df[RENTAL_END_DATE_COL].isna() & df[RENTAL_START_DATE_COL].notna()
    for idx in df.index[mask]:
        start = df.at[idx, RENTAL_START_DATE_COL]
        hours = df.at[idx, "Rental hour"] if "Rental hour" in df.columns else None
        df.at[idx, RENTAL_END_DATE_COL] = infer_end_date_from_hours(start, hours)

    return df


def sync_rental_hours_from_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute Rental hour when both start and end dates are present."""
    df = df.copy()
    if "Rental hour" not in df.columns:
        df["Rental hour"] = pd.NA
    for idx, row in df.iterrows():
        start = row.get(RENTAL_START_DATE_COL)
        end = row.get(RENTAL_END_DATE_COL)
        if pd.isna(start) or pd.isna(end):
            continue
        start_ts = pd.Timestamp(start).normalize()
        end_ts = pd.Timestamp(end).normalize()
        if end_ts > start_ts:
            df.at[idx, "Rental hour"] = compute_rental_hours_from_dates(
                start_ts, end_ts, fallback_hours=row.get("Rental hour")
            )
    return df
