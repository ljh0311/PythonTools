import os
import time
import pandas as pd
import numpy as np
import requests
import json
from typing import List, Dict, Optional
import re
from datetime import datetime, timedelta

# Region and provider constants: Singapore vs Malaysia categories kept separate
VALID_REGIONS = ("Singapore", "Malaysia")
SINGAPORE_PROVIDERS = ["Getgo", "Car Club", "Econ", "Stand", "Getgo(EV)"]
MALAYSIA_PROVIDERS = ["SoCar", "NormalRental"]

# Data cleaning pipeline: schema and deduplication
REQUIRED_COLUMNS = ["Date"]  # Minimum required for pipeline to run
RECOMMENDED_COLUMNS = ["Car model", "Car Cat", "Distance (KM)", "Rental hour", "Total"]
DEDUP_KEY_COLUMNS = ["Date", "Car model", "Car Cat", "Distance (KM)", "Rental hour"]


def validate_schema(df: pd.DataFrame) -> tuple:
    """
    Validate that the dataframe has required columns for the cleaning pipeline.
    Returns (is_valid, errors) where errors is a list of message strings.
    """
    errors = []
    if df is None or not isinstance(df, pd.DataFrame):
        return False, ["Input is not a valid DataFrame"]
    if df.empty:
        return False, ["DataFrame is empty"]
    missing_required = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_required:
        errors.append(f"Missing required columns: {missing_required}")
    missing_recommended = [c for c in RECOMMENDED_COLUMNS if c not in df.columns]
    if missing_recommended:
        errors.append(f"Missing recommended columns (some features may be limited): {missing_recommended}")
    is_valid = len(missing_required) == 0
    return is_valid, errors


def get_providers_for_region(region: Optional[str]) -> List[str]:
    """Return provider list for the given region. If None or invalid, returns Singapore list."""
    if region == "Malaysia":
        return MALAYSIA_PROVIDERS
    return SINGAPORE_PROVIDERS


def validate_numeric_input(
    value_str,
    field_name,
    min_value=None,
    max_value=None,
    allow_zero=True,
    allow_negative=False,
    required=False,
):
    """
    Validate numeric input. Returns (is_valid, value, error_message).
    Used by GUI for form validation; no UI dependencies.
    """
    if not value_str or not str(value_str).strip():
        if required:
            return False, None, f"{field_name} is required."
        return True, None, None
    try:
        value = float(str(value_str).strip())
    except ValueError:
        return False, None, f"{field_name} must be a valid number."
    if not allow_negative and value < 0:
        return False, None, f"{field_name} cannot be negative."
    if not allow_zero and value == 0:
        return False, None, f"{field_name} cannot be zero."
    if min_value is not None and value < min_value:
        return False, None, f"{field_name} must be at least {min_value}."
    if max_value is not None and value > max_value:
        return False, None, f"{field_name} must be at most {max_value}."
    return True, value, None


def validate_date_input(
    date_str,
    field_name="Date",
    allow_future=True,
    min_year=2000,
    max_year=None,
    required=True,
):
    """
    Validate date input (DD/MM/YYYY or parseable). Returns (is_valid, date_object, error_message).
    Used by GUI for form validation; no UI dependencies.
    """
    if not date_str or not str(date_str).strip():
        if required:
            return False, None, f"{field_name} is required."
        return True, None, None
    try:
        date_obj = pd.to_datetime(str(date_str).strip(), format="%d/%m/%Y")
    except (ValueError, TypeError):
        try:
            date_obj = pd.to_datetime(str(date_str).strip())
        except (ValueError, TypeError):
            return False, None, f"{field_name} must be in DD/MM/YYYY format (e.g., 15/01/2024)."
    if date_obj.year < min_year:
        return False, None, f"{field_name} year must be {min_year} or later."
    if max_year is None:
        max_year = datetime.now().year + 1
    if date_obj.year > max_year:
        return False, None, f"{field_name} year must be {max_year} or earlier."
    if not allow_future and date_obj > pd.Timestamp.now():
        return False, None, f"{field_name} cannot be in the future for historical records."
    return True, date_obj, None


def validate_date_range(
    start_date_str,
    end_date_str,
    start_field="Start Date",
    end_field="End Date",
):
    """
    Validate that start date is before end date.
    Returns (is_valid, start_date, end_date, error_message).
    """
    start_valid, start_date, start_error = validate_date_input(
        start_date_str, start_field, allow_future=True, required=True
    )
    if not start_valid:
        return False, None, None, start_error
    end_valid, end_date, end_error = validate_date_input(
        end_date_str, end_field, allow_future=True, required=True
    )
    if not end_valid:
        return False, None, None, end_error
    if start_date >= end_date:
        return False, None, None, f"{start_field} must be before {end_field}."
    return True, start_date, end_date, None


def ensure_region_column(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure Region column exists; backfill with Singapore and normalize values."""
    df = df.copy()
    if "Region" not in df.columns:
        df["Region"] = "Singapore"
        print("Added Region column and set all rows to Singapore")
    else:
        # Normalize: strip and coerce to Singapore or Malaysia
        def norm(r):
            if pd.isna(r):
                return "Singapore"
            s = str(r).strip()
            if s.lower() in ("malaysia", "my"):
                return "Malaysia"
            return "Singapore"

        df["Region"] = df["Region"].apply(norm)
    return df


def load_data(file_path):
    """Load and validate data from CSV file. Ensures Region column exists and is normalized.
    Used by run_cleaning_pipeline(); for full cleaning use run_cleaning_pipeline() instead."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")

    df = pd.read_csv(file_path)
    df = ensure_region_column(df)
    print(f"Loaded {len(df)} records from {file_path}")
    return df


def enhance_dataframe(df):
    """Fix and enhance dataframe with proper formatting for all analyses to work.
    Part of the data cleaning pipeline (run_cleaning_pipeline)."""
    # Make a copy to avoid SettingWithCopyWarning
    df = df.copy()

    # Convert Date column to datetime
    if "Date" in df.columns:
        try:
            df["Date"] = pd.to_datetime(df["Date"])
            print("Date column converted to datetime")
            # Add Month and Year columns needed for analysis
            df["Month"] = df["Date"].dt.month
            df["Year"] = df["Date"].dt.year
            print("Added Month and Year columns")
        except Exception as e:
            print(f"Warning: Could not convert Date column: {str(e)}")

    # Ensure numeric columns are properly formatted (including Malaysia NormalRental optional columns)
    # Excel_Calculated_* columns are preserved on import for CSVs exported from Excel; not shown in UI
    numeric_cols = [
        "Distance (KM)",
        "Fuel pumped",
        "Estimated fuel usage",
        "Consumption (KM/L)",
        "Fuel cost",
        "Pumped fuel cost",
        "Mileage cost ($0.39)",
        "Cost per KM",
        "Duration cost",
        "Total",
        "Est original fuel savings",
        "Rental hour",
        "Cost/HR",
        "Deposit (RM)",
        "Rental fee (RM)",
        "Additional fee (RM)",
        "Excel_Calculated_total",
        "Excel_Calculated_cost_per_km",
        "Excel_Calculated_consumption",
        "Excel_Calculated_fuel_cost",
        "Excel_Calculated_pumped_fuel_cost",
        "Excel_Calculated_mileage_cost",
        "Excel_Calculated_original_fuel_savings",
        "Excel_Calculated_cost_hr",
        "Excel_Calculated_cost_hr_adjusted",
    ]

    for col in numeric_cols:
        if col in df.columns:
            try:
                # Convert column to string, remove $ and L symbols, then convert to numeric
                df[col] = pd.to_numeric(
                    df[col]
                    .astype(str)
                    .str.replace("$", "")
                    .str.replace("L", "")
                    .str.strip(),
                    errors="coerce",
                )
                print(f"Converted {col} to numeric")
            except Exception as e:
                print(f"Warning: Could not convert {col} to numeric: {str(e)}")

    # Fill NaN values with reasonable defaults to prevent analysis errors
    fillna_dict = {
        "Cost per KM": (
            df["Cost per KM"].mean()
            if "Cost per KM" in df.columns and not df["Cost per KM"].isna().all()
            else 0.75
        ),
        "Cost/HR": (
            df["Cost/HR"].mean()
            if "Cost/HR" in df.columns and not df["Cost/HR"].isna().all()
            else 15.0
        ),
        "Consumption (KM/L)": (
            df["Consumption (KM/L)"].mean()
            if "Consumption (KM/L)" in df.columns
            and not df["Consumption (KM/L)"].isna().all()
            else 12.0
        ),
        "Weekday/weekend": "weekday",
    }
    if "Region" in df.columns:
        fillna_dict["Region"] = "Singapore"
    df = df.fillna(fillna_dict)

    print(f"Enhanced dataframe: {len(df)} rows ready for analysis")
    return df


def _apply_deduplication(df: pd.DataFrame, key_columns: List[str]) -> tuple:
    """Remove duplicate rows by key columns. Returns (df_deduped, n_removed)."""
    existing = [c for c in key_columns if c in df.columns]
    if not existing:
        return df, 0
    n_before = len(df)
    df_out = df.drop_duplicates(subset=existing, keep="first")
    return df_out, n_before - len(df_out)


def _apply_outlier_caps(df: pd.DataFrame, columns: List[str], iqr_factor: float = 1.5) -> tuple:
    """
    Cap numeric columns at IQR-based bounds (non-destructive: values are capped, not dropped).
    Returns (df_with_caps_applied, count_of_values_capped).
    """
    df_out = df.copy()
    total_capped = 0
    for col in columns:
        if col not in df_out.columns or not np.issubdtype(df_out[col].dtype, np.number):
            continue
        q1 = df_out[col].quantile(0.25)
        q3 = df_out[col].quantile(0.75)
        iqr = q3 - q1
        if iqr <= 0:
            continue
        low = q1 - iqr_factor * iqr
        high = q3 + iqr_factor * iqr
        before = df_out[col].copy()
        df_out[col] = df_out[col].clip(lower=low, upper=high)
        total_capped += (before != df_out[col]).sum()
    return df_out, int(total_capped)


def run_cleaning_pipeline(
    input_path: str,
    output_path: Optional[str] = None,
    handle_outliers: bool = False,
    outlier_columns: Optional[List[str]] = None,
) -> tuple:
    """
    Automated data cleaning pipeline for car rental data: schema validation, normalization,
    enrichment, deduplication, optional outlier capping, and optional quality report.

    Steps: validate schema -> load CSV -> ensure region -> enhance dataframe -> deduplicate
    -> optional outlier capping -> optional write to output_path.

    Returns:
        (df, quality_report): cleaned DataFrame and a dict with keys such as
        rows_in, rows_out, duplicates_removed, schema_valid, schema_errors, outliers_capped.
    """
    quality_report = {
        "rows_in": 0,
        "rows_out": 0,
        "duplicates_removed": 0,
        "schema_valid": True,
        "schema_errors": [],
        "outliers_capped": 0,
    }
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Data file not found: {input_path}")

    df = pd.read_csv(input_path)
    quality_report["rows_in"] = len(df)

    # Schema validation
    schema_valid, schema_errors = validate_schema(df)
    quality_report["schema_valid"] = schema_valid
    quality_report["schema_errors"] = schema_errors
    if not schema_valid:
        missing_required = [e for e in schema_errors if "Missing required" in e]
        if missing_required:
            raise ValueError(f"Schema validation failed: {schema_errors}")

    df = ensure_region_column(df)
    df = enhance_dataframe(df)

    # Deduplicate on initial load
    df, n_dup = _apply_deduplication(df, DEDUP_KEY_COLUMNS)
    quality_report["duplicates_removed"] = n_dup

    if handle_outliers:
        cols = outlier_columns or ["Distance (KM)", "Total", "Rental hour"]
        cols = [c for c in cols if c in df.columns]
        if cols:
            df, n_capped = _apply_outlier_caps(df, cols)
            quality_report["outliers_capped"] = n_capped

    quality_report["rows_out"] = len(df)

    if output_path:
        df.to_csv(output_path, index=False)
        print(f"Wrote cleaned data to {output_path}")

    return df, quality_report


def create_complete_cost_analysis(df, region=None):
    """Create a comprehensive cost analysis for providers. If region is set and df has Region column, only that region's data and providers are used."""
    if df is None or df.empty:
        providers = get_providers_for_region(region or "Singapore")
        results = {}
        for provider in providers:
            results[provider] = {
                "avg_cost_per_km": 0.75,
                "avg_cost_per_hour": 15.00,
                "car_models": {"Generic": {"avg_cost_per_km": 0.75, "avg_cost_per_hour": 15.00, "avg_consumption": 12.0, "count": 1}},
            }
        return results

    if "Region" in df.columns and region is not None:
        df = df[df["Region"] == region].copy()
    providers = get_providers_for_region(region or "Singapore")
    results = {}

    for provider in providers:
        provider_data = (
            df[df["Car Cat"] == provider] if "Car Cat" in df.columns else pd.DataFrame()
        )
        if not provider_data.empty:
            # Calculate basic stats
            avg_cost_per_km = (
                provider_data["Cost per KM"].mean()
                if "Cost per KM" in provider_data.columns
                else 0.75
            )
            avg_cost_per_hour = (
                provider_data["Cost/HR"].mean()
                if "Cost/HR" in provider_data.columns
                else 15.00
            )

            # Get unique car models
            car_models = (
                provider_data["Car model"].unique()
                if "Car model" in provider_data.columns
                else []
            )
            car_model_stats = {}

            # Add stats for each car model
            for model in car_models:
                if pd.isna(model):  # Skip NaN model names
                    continue

                model_data = provider_data[provider_data["Car model"] == model]
                car_model_stats[model] = {
                    "avg_cost_per_km": (
                        model_data["Cost per KM"].mean()
                        if "Cost per KM" in model_data.columns
                        else avg_cost_per_km
                    ),
                    "avg_cost_per_hour": (
                        model_data["Cost/HR"].mean()
                        if "Cost/HR" in model_data.columns
                        else avg_cost_per_hour
                    ),
                    "avg_consumption": (
                        model_data["Consumption (KM/L)"].mean()
                        if "Consumption (KM/L)" in model_data.columns
                        else 12.0
                    ),
                    "count": len(model_data),
                }

            results[provider] = {
                "avg_cost_per_km": avg_cost_per_km,
                "avg_cost_per_hour": avg_cost_per_hour,
                "car_models": car_model_stats,
            }

    # If we don't have any providers from the data, add some defaults
    if len(results) == 0:
        for provider in providers:
            results[provider] = {
                "avg_cost_per_km": 0.75,  # Default cost per km
                "avg_cost_per_hour": 15.00,  # Default cost per hour
                "car_models": {
                    "Generic": {
                        "avg_cost_per_km": 0.75,
                        "avg_cost_per_hour": 15.00,
                        "avg_consumption": 12.0,
                        "count": 1,
                    }
                },
            }

    print(f"Created cost analysis for {len(results)} providers")
    return results


def calculate_estimated_cost(
    distance, duration, provider, car_model=None, cost_analysis=None, is_weekend=False, pricing_config=None
):
    """Calculate estimated cost for a rental using pricing_config.json rates"""
    # Load pricing config if not provided
    if pricing_config is None:
        try:
            with open("pricing_config.json", "r") as f:
                pricing_config = json.load(f)
        except:
            pricing_config = {}
    
    # Try to use pricing_config first
    if provider in pricing_config:
        config = pricing_config[provider]
        pricing_type = config.get("pricing_type", "mileage")

        # NormalRental (Malaysia): traditional daily rental, no formula-based estimate
        if pricing_type == "traditional":
            return None

        # SoCar (Malaysia): hour rate + mileage package (10/50/100 km add-ons) + excess RM/km
        if pricing_type == "socar":
            hour_rate = config.get("hour_rate", 8.0)
            packages = config.get("mileage_packages", [{"km": 10, "price": 2.5}, {"km": 50, "price": 11}, {"km": 100, "price": 15}])
            excess_km_rate = config.get("excess_km_rate", 0.25)
            duration_cost = (duration or 0) * hour_rate
            # Best package: smallest package that covers distance, or largest if distance exceeds all
            packages_sorted = sorted(packages, key=lambda p: p["km"])
            chosen = packages_sorted[0]
            for p in packages_sorted:
                if (distance or 0) <= p["km"]:
                    chosen = p
                    break
                chosen = p
            package_km = chosen["km"]
            package_price = chosen["price"]
            excess_km = max(0, (distance or 0) - package_km)
            mileage_cost = package_price + excess_km * excess_km_rate
            total_cost = duration_cost + mileage_cost
            return {
                "total_cost": total_cost,
                "duration_cost": duration_cost,
                "mileage_cost": mileage_cost,
                "fuel_cost": 0,
            }

        day_type = "weekend" if is_weekend else "weekday"
        hour_rate_key = f"hour_rate_{day_type}" if f"hour_rate_{day_type}" in config else "hour_rate"
        km_rate_key = f"km_rate_{day_type}" if f"km_rate_{day_type}" in config else "mileage_rate"
        base_key = f"base_{day_type}" if f"base_{day_type}" in config else "base_weekday"

        hour_rate = config.get(hour_rate_key, config.get("hour_rate", 10.0))
        base_cost = config.get(base_key, config.get("base_weekday", 0.0))

        if pricing_type == "mileage":
            km_rate = config.get(km_rate_key, config.get("mileage_rate", 0.39))
            mileage_cost = distance * km_rate
            duration_cost = duration * hour_rate
            fuel_cost = 0
            total_cost = base_cost + mileage_cost + duration_cost
        else:  # fuel-based
            fuel_rate = config.get("fuel_rate", config.get("usual_fuel_amount", 20.0))
            duration_cost = duration * hour_rate
            fuel_cost = fuel_rate
            mileage_cost = 0
            total_cost = base_cost + duration_cost + fuel_cost

        return {
            "total_cost": total_cost,
            "duration_cost": duration_cost,
            "mileage_cost": mileage_cost,
            "fuel_cost": fuel_cost,
        }
    
    # Fallback to cost_analysis if pricing_config not available
    if not cost_analysis or provider not in cost_analysis:
        return None

    provider_data = cost_analysis[provider]

    # Get car model specific data if available
    if car_model and car_model in provider_data["car_models"]:
        model_data = provider_data["car_models"][car_model]
        cost_per_km = model_data["avg_cost_per_km"]
        cost_per_hour = model_data["avg_cost_per_hour"]
    else:
        cost_per_km = provider_data["avg_cost_per_km"]
        cost_per_hour = provider_data["avg_cost_per_hour"]

    # Calculate base costs
    if provider in ["Getgo", "Car Club"]:
        # These providers charge per km and per hour
        mileage_rate = 0.39 if provider == "Getgo" else 0.33
        mileage_cost = distance * mileage_rate
        duration_cost = duration * cost_per_hour
        total_cost = mileage_cost + duration_cost
    else:
        # Econ and Stand charge per hour and include fuel
        duration_cost = duration * cost_per_hour
        fuel_cost = (
            (distance / 110) * 20 if distance > 0 else 0
        )  # Assuming 110km per tank
        total_cost = duration_cost + fuel_cost

    # Weekend surcharge if applicable
    if is_weekend:
        total_cost *= 1.2  # 20% surcharge for weekends

    return {
        "total_cost": total_cost,
        "duration_cost": duration_cost,
        "mileage_cost": mileage_cost if provider in ["Getgo", "Car Club"] else 0,
        "fuel_cost": fuel_cost if provider in ["Econ", "Stand"] else 0,
    }


def get_recommendations(distance, duration, cost_analysis, is_weekend=False, top_n=5):
    """Get top N rental recommendations based on cost"""
    recommendations = []

    for provider in cost_analysis:
        provider_data = cost_analysis[provider]

        # Get recommendations for each car model
        for model, model_data in provider_data["car_models"].items():
            cost = calculate_estimated_cost(
                distance, duration, provider, model, cost_analysis, is_weekend
            )

            if cost:
                recommendations.append(
                    {
                        "provider": provider,
                        "model": model,
                        "total_cost": cost["total_cost"],
                        "duration_cost": cost["duration_cost"],
                        "mileage_cost": cost["mileage_cost"],
                        "fuel_cost": cost["fuel_cost"],
                    }
                )

    # Sort by total cost and return top N
    recommendations.sort(key=lambda x: x["total_cost"])
    return recommendations[:top_n]


def analyze_rental_costs(df):
    """Analyze rental costs and return statistics"""
    if df.empty:
        return {}

    stats = {
        "total_rentals": len(df),
        "total_distance": df["Distance (KM)"].sum(),
        "total_cost": df["Total"].sum(),
        "avg_cost_per_km": df["Cost per KM"].mean(),
        "avg_cost_per_hour": df["Cost/HR"].mean(),
        "avg_consumption": df["Consumption (KM/L)"].mean(),
        "providers": {},
    }

    # Provider-specific stats
    for provider in df["Car Cat"].unique():
        provider_data = df[df["Car Cat"] == provider]
        stats["providers"][provider] = {
            "count": len(provider_data),
            "avg_cost": provider_data["Total"].mean(),
            "avg_distance": provider_data["Distance (KM)"].mean(),
            "avg_duration": provider_data["Rental hour"].mean(),
        }

    return stats


# Cost Planning Functions (from zzGG.py)
def calculate_required_mileage(target_cost, duration, provider="Getgo"):
    """Calculate required mileage to reach target cost given duration"""
    if provider == "Getgo":
        # Getgo: cost = mileage * 0.39 + duration * 8
        # mileage = (target_cost - duration * 8) / 0.39
        mileage_rate = 0.39
        hourly_rate = 8.0
    elif provider == "Car Club":
        # Car Club: cost = mileage * 0.33 + duration * hourly_rate
        mileage_rate = 0.33
        hourly_rate = 8.0  # Adjust based on actual rates
    else:
        # For other providers, use different calculation
        return None

    # Calculate the duration cost first
    duration_cost = duration * hourly_rate

    # If duration cost already exceeds target, it's impossible
    if duration_cost >= target_cost:
        return None  # Will be handled by the calling function

    required_mileage = (target_cost - duration_cost) / mileage_rate
    return max(0, required_mileage)


def calculate_required_duration(target_cost, mileage, provider="Getgo"):
    """Calculate required duration to reach target cost given mileage"""
    if provider == "Getgo":
        # Getgo: cost = mileage * 0.39 + duration * 8
        # duration = (target_cost - mileage * 0.39) / 8
        mileage_rate = 0.39
        hourly_rate = 8.0
    elif provider == "Car Club":
        # Car Club: cost = mileage * 0.33 + duration * hourly_rate
        mileage_rate = 0.33
        hourly_rate = 8.0  # Adjust based on actual rates
    else:
        # For other providers, use different calculation
        return None

    # Calculate the mileage cost first
    mileage_cost = mileage * mileage_rate

    # If mileage cost already exceeds target, it's impossible
    if mileage_cost >= target_cost:
        return {
            "days": 0,
            "hours": 0,
            "minutes": 0,
            "total_hours": 0,
            "impossible": True,
            "reason": f"Mileage cost (${mileage_cost:.2f}) exceeds target cost (${target_cost:.2f})",
        }

    required_hours = (target_cost - mileage_cost) / hourly_rate
    required_hours = max(0, required_hours)

    # Convert to days, hours, minutes
    total_minutes = int(round(required_hours * 60))
    days = total_minutes // (24 * 60)
    hours = (total_minutes % (24 * 60)) // 60
    minutes = total_minutes % 60

    # Round minutes to nearest 0, 15, 30, or 45
    minute_options = [0, 15, 30, 45]
    minutes = min(minute_options, key=lambda x: abs(x - minutes))

    # If rounding up to 60, increment hour
    if minutes == 60:
        minutes = 0
        hours += 1
        if hours == 24:
            hours = 0
            days += 1

    return {
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "total_hours": required_hours,
        "impossible": False,
    }


def generate_booking_scenarios(
    target_cost, duration=None, mileage=None, provider="Getgo"
):
    """Generate booking scenarios to reach target monthly cost"""
    scenarios = []

    if duration is not None:
        # Calculate required mileage based on duration
        required_mileage = calculate_required_mileage(target_cost, duration, provider)
        if required_mileage is None or required_mileage <= 0:
            return scenarios

        # Generate scenarios based on bookings per week
        for bookings_per_week in range(1, 21):  # Limit to 20 bookings per week
            total_bookings_per_month = bookings_per_week * 4
            km_per_booking = required_mileage / total_bookings_per_month

            # On average, 1 hour covers 30km
            hours_per_booking_by_km = km_per_booking / 30

            # Only show if minimum 1 hour per booking
            if hours_per_booking_by_km < 1:
                continue

            # Round hours to nearest 0.25 (15 minutes)
            minute_options = [0, 0.25, 0.5, 0.75]
            fractional = hours_per_booking_by_km % 1
            rounded_fractional = min(minute_options, key=lambda x: abs(x - fractional))
            rounded_hours = int(hours_per_booking_by_km) + rounded_fractional

            if abs(rounded_hours - hours_per_booking_by_km) < 0.13:
                # Calculate actual total hours per month based on the rounded hours
                total_hours_per_month = rounded_hours * total_bookings_per_month

                # Only include if total hours don't exceed the target duration
                if total_hours_per_month <= duration:
                    scenarios.append(
                        {
                            "bookings_per_week": bookings_per_week,
                            "total_hours_per_month": total_hours_per_month,
                            "km_per_booking": km_per_booking,
                            "hours_per_booking": rounded_hours,
                            "type": "duration_based",
                        }
                    )

    if mileage is not None:
        # Calculate required duration based on mileage
        required_duration = calculate_required_duration(target_cost, mileage, provider)
        if required_duration is None:
            return scenarios

        total_hours = required_duration["total_hours"]

        # Generate scenarios based on bookings per week
        for bookings_per_week in range(1, 21):  # Limit to 20 bookings per week
            total_bookings_per_month = bookings_per_week * 4

            hours_per_booking = total_hours / total_bookings_per_month

            # Only show results with .0, .25, .50, .75 decimal
            decimal_part = round(hours_per_booking % 1, 2)
            if decimal_part in {0.0, 0.25, 0.5, 0.75}:
                # On average, 1 hour covers 30km
                km_per_booking_by_hours = hours_per_booking * 30

                scenarios.append(
                    {
                        "bookings_per_week": bookings_per_week,
                        "total_hours_per_month": total_hours,
                        "km_per_booking": km_per_booking_by_hours,
                        "hours_per_booking": hours_per_booking,
                        "type": "mileage_based",
                    }
                )

    return scenarios


def calculate_cost_breakdown(mileage, duration, provider="Getgo"):
    """Calculate detailed cost breakdown for a rental"""
    if provider == "Getgo":
        mileage_rate = 0.39
        hourly_rate = 8.0
    elif provider == "Car Club":
        mileage_rate = 0.33
        hourly_rate = 8.0  # Adjust based on actual rates
    else:
        return None

    mileage_cost = mileage * mileage_rate
    duration_cost = duration * hourly_rate
    total_cost = mileage_cost + duration_cost

    return {
        "mileage_cost": mileage_cost,
        "duration_cost": duration_cost,
        "total_cost": total_cost,
        "mileage_rate": mileage_rate,
        "hourly_rate": hourly_rate,
    }


def test_cost_planning_functions():
    """Test function to validate cost planning calculations"""
    print("Testing Cost Planning Functions...")

    # Test 1: Calculate required mileage for $2000 target with 100 hours
    target_cost = 2000
    duration = 100
    required_mileage = calculate_required_mileage(target_cost, duration, "Getgo")
    print(
        f"Target: ${target_cost}, Duration: {duration}h, Required Mileage: {required_mileage:.2f} km"
    )

    # Test 2: Calculate required duration for $2000 target with 1000 km
    mileage = 1000
    required_duration = calculate_required_duration(target_cost, mileage, "Getgo")
    print(
        f"Target: ${target_cost}, Mileage: {mileage}km, Required Duration: {required_duration['total_hours']:.2f}h"
    )

    # Test 3: Generate booking scenarios
    scenarios = generate_booking_scenarios(
        target_cost, duration=duration, provider="Getgo"
    )
    print(f"Generated {len(scenarios)} booking scenarios")

    # Test 4: Cost breakdown
    breakdown = calculate_cost_breakdown(required_mileage, duration, "Getgo")
    print(
        f"Cost Breakdown: Mileage=${breakdown['mileage_cost']:.2f}, Duration=${breakdown['duration_cost']:.2f}, Total=${breakdown['total_cost']:.2f}"
    )

    print("Cost planning functions test completed successfully!")


def create_ml_recommendations(distance, duration, df, is_weekend=False, top_n=5):
    """Create machine learning based recommendations using historical data patterns"""
    if df.empty:
        return []

    # Prepare features for ML
    features = []
    targets = []

    # Extract features from historical data
    for _, row in df.iterrows():
        if (
            pd.notna(row["Distance (KM)"])
            and pd.notna(row["Rental hour"])
            and pd.notna(row["Total"])
        ):
            # Features: distance, duration, provider (encoded), car model (encoded), weekend
            provider_encoded = {"Getgo": 0, "Car Club": 1, "Econ": 2, "Stand": 3}.get(
                row["Car Cat"], 0
            )
            weekend_encoded = 1 if row.get("Weekday/weekend") == "weekend" else 0

            features.append(
                [
                    row["Distance (KM)"],
                    row["Rental hour"],
                    provider_encoded,
                    weekend_encoded,
                ]
            )
            targets.append(row["Total"])

    if len(features) < 5:  # Need minimum data for ML
        return []

    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.preprocessing import StandardScaler
        import numpy as np

        # Convert to numpy arrays
        X = np.array(features)
        y = np.array(targets)

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Train a simple ML model
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(X_scaled, y)

        # Prepare input for prediction
        provider_encoded = {"Getgo": 0, "Car Club": 1, "Econ": 2, "Stand": 3}.get(
            "Getgo", 0
        )
        weekend_encoded = 1 if is_weekend else 0

        input_features = np.array(
            [[distance, duration, provider_encoded, weekend_encoded]]
        )

        input_scaled = scaler.transform(input_features)

        # Get predictions for different providers
        recommendations = []
        providers = ["Getgo", "Car Club", "Econ", "Stand"]

        for provider in providers:
            provider_encoded = {"Getgo": 0, "Car Club": 1, "Econ": 2, "Stand": 3}[
                provider
            ]

            # Get historical data for this provider
            provider_data = df[df["Car Cat"] == provider]
            if not provider_data.empty:
                # Get most common car model for this provider
                car_models = provider_data["Car model"].dropna().value_counts()
                most_common_model = (
                    car_models.index[0] if len(car_models) > 0 else "Generic"
                )

                # Predict cost
                input_features = np.array(
                    [[distance, duration, provider_encoded, weekend_encoded]]
                )
                input_scaled = scaler.transform(input_features)
                predicted_cost = model.predict(input_scaled)[0]

                # Calculate confidence based on data availability
                confidence = min(
                    1.0, len(provider_data) / 10
                )  # More data = higher confidence

                recommendations.append(
                    {
                        "provider": provider,
                        "model": most_common_model,
                        "total_cost": max(0, predicted_cost),
                        "confidence": confidence,
                        "data_points": len(provider_data),
                        "method": "ML Prediction",
                    }
                )

        # Sort by predicted cost
        recommendations.sort(key=lambda x: x["total_cost"])
        return recommendations[:top_n]

    except ImportError:
        # Fallback if sklearn is not available
        return []
    except Exception as e:
        print(f"ML recommendation error: {e}")
        return []


def get_enhanced_recommendations(
    distance, duration, df, cost_analysis=None, is_weekend=False, top_n=5, use_ml=True
):
    """Get enhanced recommendations combining traditional and ML approaches"""
    recommendations = []

    # Get traditional recommendations
    if cost_analysis:
        traditional_recs = get_recommendations(
            distance, duration, cost_analysis, is_weekend, top_n
        )
        for rec in traditional_recs:
            rec["method"] = "Historical Analysis"
            rec["confidence"] = 0.8
            recommendations.append(rec)

    # Get ML recommendations if requested and data is available
    if use_ml and len(df) >= 10:  # Need minimum data for ML
        ml_recs = create_ml_recommendations(distance, duration, df, is_weekend, top_n)
        recommendations.extend(ml_recs)

    # If no recommendations from either method, create fallback recommendations
    if not recommendations:
        recommendations = create_fallback_recommendations(
            distance, duration, is_weekend
        )

    # Sort by total cost and return top N
    recommendations.sort(key=lambda x: x["total_cost"])
    return recommendations[:top_n]


def create_fallback_recommendations(distance, duration, is_weekend=False):
    """Create fallback recommendations when no data is available"""
    providers = ["Getgo", "Car Club", "Econ", "Stand"]
    recommendations = []

    for provider in providers:
        if provider in ["Getgo", "Car Club"]:
            # Per km + per hour pricing
            mileage_rate = 0.39 if provider == "Getgo" else 0.33
            hourly_rate = 8.0
            mileage_cost = distance * mileage_rate
            duration_cost = duration * hourly_rate
            total_cost = mileage_cost + duration_cost
        else:
            # Per hour + fuel cost
            hourly_rate = 15.0
            duration_cost = duration * hourly_rate
            fuel_cost = (distance / 110) * 20 if distance > 0 else 0
            total_cost = duration_cost + fuel_cost

        # Weekend surcharge
        if is_weekend:
            total_cost *= 1.2

        recommendations.append(
            {
                "provider": provider,
                "model": "Standard",
                "total_cost": total_cost,
                "duration_cost": duration_cost,
                "mileage_cost": (
                    mileage_cost if provider in ["Getgo", "Car Club"] else 0
                ),
                "fuel_cost": fuel_cost if provider in ["Econ", "Stand"] else 0,
                "confidence": 0.5,
                "method": "Default Pricing",
            }
        )

    return recommendations


def create_ollama_recommendations(
    distance, duration, df, is_weekend=False, top_n=5, model_name="llama2",
    passenger_count=None, space_requirements=None, rental_timing=None
):
    """
    Create recommendations using Ollama LLM based on historical data patterns

    Args:
        distance: Travel distance in km
        duration: Rental duration in hours
        df: Historical rental data
        is_weekend: Whether this is a weekend trip
        top_n: Number of recommendations to return
        model_name: Ollama model to use (default: llama2)
        passenger_count: Number of passengers
        space_requirements: Space/luggage requirements
        rental_timing: Rental timing information dict

    Returns:
        List of recommendation dictionaries
    """
    try:
        # Prepare context data for the LLM
        context_data = prepare_context_for_ollama(
            distance, duration, df, is_weekend,
            passenger_count=passenger_count,
            space_requirements=space_requirements,
            rental_timing=rental_timing
        )

        # Create the prompt for Ollama
        prompt = create_ollama_prompt(context_data)

        # Call Ollama API
        response = call_ollama_api(prompt, model_name)

        # Parse the response
        recommendations = parse_ollama_response(response, context_data)

        return recommendations[:top_n]

    except Exception as e:
        print(f"Ollama recommendation error: {e}")
        return []


def prepare_context_for_ollama(distance, duration, df, is_weekend,
                                passenger_count=None, space_requirements=None, rental_timing=None):
    """Prepare historical data context for Ollama analysis with range information"""
    # Determine ranges for this trip
    distance_range = get_distance_range(distance)
    duration_range = get_duration_range(duration)
    
    context = {
        "user_request": {
            "distance_km": distance,
            "duration_hours": duration,
            "is_weekend": is_weekend,
            "passenger_count": passenger_count,
            "space_requirements": space_requirements,
            "rental_timing": rental_timing,
            "distance_range": distance_range,
            "duration_range": duration_range,
        },
        "historical_data": {},
        "range_analysis": {},
    }
    
    # Add size requirements if passenger info provided
    if passenger_count is not None:
        size_req = get_car_size_recommendation(passenger_count, space_requirements or "")
        context["user_request"]["size_requirements"] = size_req
    
    # Add range-specific statistics
    if df is not None and not df.empty:
        range_stats = get_range_specific_statistics(df, distance_range, duration_range)
        if range_stats:
            context["range_analysis"] = {
                "distance_range": distance_range,
                "duration_range": duration_range,
                "total_rentals_in_range": range_stats.get("total_rentals", 0),
                "avg_cost_in_range": range_stats.get("avg_cost", 0),
                "providers_in_range": {}
            }
            # Add provider-specific range statistics
            for provider, provider_stats in range_stats.get("providers", {}).items():
                context["range_analysis"]["providers_in_range"][provider] = {
                    "avg_cost": provider_stats.get("avg_cost", 0),
                    "rental_count": provider_stats.get("rental_count", 0),
                    "popular_models": provider_stats.get("popular_models", {})
                }

    if df is not None and not df.empty:
        # Group by provider and calculate statistics
        for provider in df["Car Cat"].unique() if "Car Cat" in df.columns else []:
            if pd.isna(provider):
                continue

            provider_data = df[df["Car Cat"] == provider]

            # Calculate key metrics
            avg_cost_per_km = (
                provider_data["Cost per KM"].mean()
                if "Cost per KM" in provider_data.columns
                else None
            )
            avg_cost_per_hour = (
                provider_data["Cost/HR"].mean()
                if "Cost/HR" in provider_data.columns
                else None
            )
            avg_consumption = (
                provider_data["Consumption (KM/L)"].mean()
                if "Consumption (KM/L)" in provider_data.columns
                else None
            )

            # Get popular car models
            car_models = provider_data["Car model"].dropna().value_counts().head(3)

            context["historical_data"][provider] = {
                "avg_cost_per_km": (
                    round(avg_cost_per_km, 2) if avg_cost_per_km else None
                ),
                "avg_cost_per_hour": (
                    round(avg_cost_per_hour, 2) if avg_cost_per_hour else None
                ),
                "avg_consumption_km_l": (
                    round(avg_consumption, 1) if avg_consumption else None
                ),
                "total_rentals": len(provider_data),
                "popular_models": car_models.to_dict() if not car_models.empty else {},
                "weekend_rentals": (
                    len(provider_data[provider_data["Weekday/weekend"] == "weekend"])
                    if "Weekday/weekend" in provider_data.columns
                    else 0
                ),
            }

    return context


def create_ollama_prompt(context_data):
    """Create a structured prompt for Ollama to analyze car rental recommendations"""

    # Format historical data
    historical_summary = ""
    if context_data["historical_data"]:
        for provider, data in context_data["historical_data"].items():
            historical_summary += f"\n{provider}:\n"
            historical_summary += (
                f"  - Average cost per km: ${data['avg_cost_per_km']}\n"
                if data["avg_cost_per_km"]
                else ""
            )
            historical_summary += (
                f"  - Average cost per hour: ${data['avg_cost_per_hour']}\n"
                if data["avg_cost_per_hour"]
                else ""
            )
            historical_summary += (
                f"  - Average fuel consumption: {data['avg_consumption_km_l']} km/L\n"
                if data["avg_consumption_km_l"]
                else ""
            )
            historical_summary += f"  - Total rentals: {data['total_rentals']}\n"
            historical_summary += f"  - Weekend rentals: {data['weekend_rentals']}\n"
            if data["popular_models"]:
                models_str = ", ".join(
                    [
                        f"{model} ({count})"
                        for model, count in list(data["popular_models"].items())[:3]
                    ]
                )
                historical_summary += f"  - Popular models: {models_str}\n"

    # Build customer request summary
    customer_request = f"""Customer Request:
- Distance: {context_data['user_request']['distance_km']} km
- Duration: {context_data['user_request']['duration_hours']} hours
- Weekend: {'Yes' if context_data['user_request']['is_weekend'] else 'No'}"""
    
    if context_data['user_request'].get('passenger_count'):
        customer_request += f"\n- Passengers: {context_data['user_request']['passenger_count']}"
    if context_data['user_request'].get('space_requirements'):
        customer_request += f"\n- Space needs: {context_data['user_request']['space_requirements']}"
    if context_data['user_request'].get('size_requirements'):
        size_req = context_data['user_request']['size_requirements']
        customer_request += f"\n- Recommended car size: {size_req.get('size_category', 'mid-size')} ({size_req.get('description', '')})"
    if context_data['user_request'].get('rental_timing'):
        timing = context_data['user_request']['rental_timing']
        if timing.get('rental_date'):
            customer_request += f"\n- Rental date: {timing.get('day_name', 'N/A')}"
    
    prompt = f"""You are an expert in car rental recommendations. Your task is to suggest the best value options for a 24-year-old driver with 3 years of experience, prioritizing cost-effectiveness and reliability.

{customer_request}

Historical Data:{historical_summary}

Instructions:
- Recommend exactly 3 car rental options based only on providers and models present in the historical data.
- Focus on: 
  • Lowest total cost for the requested trip
  • Provider reliability and popularity
  • Value for money (cost per km/hour)
  • Suitability for errands, leisure, or sightseeing
  • Frequency of rentals (popularity)
  • Car size suitability for passenger count and space needs (if provided)
  • Pricing model (mileage-included vs pay-per-km) based on trip distance
- Exclude any cars not found in the historical data.
- Consider that for short trips (<50km), mileage-included pricing (Econ, Stand, Tribecar) is usually better.
- Consider that for long trips (>100km), pay-per-km pricing (Getgo, Car Club) may be more economical.

Respond with a JSON array in this format:
[
  {{
    "provider": "Provider Name",
    "model": "Car Model",
    "total_cost": estimated_cost,
    "reasoning": "Brief explanation of why this is a good value for the customer",
    "confidence": 0.8,
    "method": "Ollama Analysis"
  }}
]
Return only the JSON array, no extra commentary.
"""

    return prompt


def call_ollama_api(prompt, model_name="llama2"):
    """Call Ollama API to get LLM response"""
    try:
        url = "http://localhost:11434/api/generate"

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Lower temperature for more consistent responses
                "top_p": 0.9,
                "max_tokens": 1000,
            },
        }

        # Timeout: longer for larger models (they can take 60–120s on CPU)
        timeout = 45 if "3b" in model_name.lower() else 120
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()

        result = response.json()
        return result.get("response", "")

    except requests.exceptions.ConnectionError:
        raise Exception(
            "Cannot connect to Ollama. Please ensure Ollama is running on localhost:11434"
        )
    except requests.exceptions.Timeout:
        raise Exception("Ollama request timed out. Please try again.")


def call_ollama_chat_api(messages, model_name="llama2"):
    """
    Call Ollama Chat API for better structured outputs with system messages.
    
    Args:
        messages: List of message dicts with 'role' ('system', 'user', 'assistant') and 'content'
        model_name: Ollama model to use
    
    Returns:
        Response text from the assistant
    """
    try:
        url = "http://localhost:11434/api/chat"

        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.2,  # Lower temperature for more consistent JSON responses
                "top_p": 0.9,
                "max_tokens": 1000,
            },
        }

        # Timeout: longer for larger models (they can take 60–120s on CPU)
        timeout = 45 if "3b" in model_name.lower() else 120
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()

        result = response.json()
        # Chat API returns message object with content
        message = result.get("message", {})
        return message.get("content", "")

    except requests.exceptions.ConnectionError:
        raise Exception(
            "Cannot connect to Ollama. Please ensure Ollama is running on localhost:11434"
        )
    except requests.exceptions.Timeout:
        raise Exception("Ollama request timed out. Please try again.")
    except Exception as e:
        # Fallback to generate API if chat API fails
        print(f"Chat API failed, falling back to generate API: {e}")
        # Extract user message for fallback
        user_msg = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
        if user_msg:
            return call_ollama_api(user_msg, model_name)
        raise
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 500:
            raise Exception(
                "Ollama server error. Try restarting Ollama or using a different model."
            )
        else:
            raise Exception(f"Ollama HTTP error: {e.response.status_code}")
    except Exception as e:
        raise Exception(f"Ollama API error: {str(e)}")


def parse_ollama_response(response, context_data):
    """Parse Ollama response and extract recommendations"""
    try:
        # Try to extract JSON from the response
        import re

        # Look for JSON array in the response
        json_match = re.search(r"\[.*\]", response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            recommendations = json.loads(json_str)
        else:
            # If no JSON found, create fallback recommendations
            recommendations = create_fallback_from_response(response, context_data)

        # Validate and clean recommendations
        cleaned_recommendations = []
        for rec in recommendations:
            if isinstance(rec, dict) and "provider" in rec and "total_cost" in rec:
                cleaned_rec = {
                    "provider": str(rec.get("provider", "Unknown")),
                    "model": str(rec.get("model", "Standard")),
                    "total_cost": float(rec.get("total_cost", 0)),
                    "reasoning": str(rec.get("reasoning", "LLM recommendation")),
                    "confidence": float(rec.get("confidence", 0.7)),
                    "method": "Ollama Analysis",
                }
                cleaned_recommendations.append(cleaned_rec)

        return cleaned_recommendations

    except json.JSONDecodeError:
        # If JSON parsing fails, create fallback recommendations
        return create_fallback_from_response(response, context_data)
    except Exception as e:
        print(f"Error parsing Ollama response: {e}")
        return []


def create_fallback_from_response(response, context_data):
    """Create fallback recommendations when JSON parsing fails"""
    recommendations = []

    # Extract provider names from the response
    providers = (
        list(context_data["historical_data"].keys())
        if context_data["historical_data"]
        else ["Getgo", "Car Club", "Econ", "Stand"]
    )

    # Create basic recommendations based on available providers
    for i, provider in enumerate(providers[:3]):  # Top 3 providers
        base_cost = (
            20
            + (context_data["user_request"]["distance_km"] * 0.3)
            + (context_data["user_request"]["duration_hours"] * 8)
        )
        if context_data["user_request"]["is_weekend"]:
            base_cost *= 1.2

        recommendations.append(
            {
                "provider": provider,
                "model": "Standard",
                "total_cost": round(base_cost, 2),
                "reasoning": f"Based on historical data analysis for {provider}",
                "confidence": 0.6,
                "method": "Ollama Analysis (Fallback)",
            }
        )

    return recommendations


def extract_dataset_examples_for_llm(df):
    """
    Extract actual examples from the dataset to help LLM understand the correct format.
    
    Args:
        df: DataFrame with rental records
    
    Returns:
        Dictionary with:
        - car_models: list of unique car model examples (top 30)
        - providers: list of unique provider names from "Car Cat" column
        - example_rows: list of example rows showing car model + provider combinations
    """
    examples = {
        "car_models": [],
        "providers": [],
        "example_rows": []
    }
    
    if df is None or df.empty:
        return examples
    
    # Extract unique car models (top 30)
    if "Car model" in df.columns:
        car_models = df["Car model"].dropna().unique()
        # Filter out any invalid entries and get top 30
        car_models = [str(m).strip() for m in car_models if str(m).strip() and str(m).strip().lower() != "nan"]
        examples["car_models"] = sorted(car_models)[:30]
    
    # Extract unique providers
    if "Car Cat" in df.columns:
        providers = df["Car Cat"].dropna().unique()
        providers = [str(p).strip() for p in providers if str(p).strip() and str(p).strip().lower() != "nan"]
        examples["providers"] = sorted(providers)
    
    # Create example rows showing car model + provider combinations
    if "Car model" in df.columns and "Car Cat" in df.columns:
        # Get unique combinations
        example_df = df[["Car model", "Car Cat"]].dropna()
        example_df = example_df.drop_duplicates()
        
        # Get up to 10 example combinations
        for idx, row in example_df.head(10).iterrows():
            car_model = str(row["Car model"]).strip()
            provider = str(row["Car Cat"]).strip()
            if car_model and provider and car_model.lower() != "nan" and provider.lower() != "nan":
                examples["example_rows"].append({
                    "car_model": car_model,
                    "provider": provider
                })
    
    return examples


def normalize_provider_name(provider_text, df=None):
    """
    Normalize provider name from user input to match exact format in dataset.
    
    Args:
        provider_text: User input provider name (e.g., "getgo", "GETGO", "Getgo")
        df: DataFrame to match against (optional)
    
    Returns:
        Normalized provider name matching dataset format, or original if no match found
    """
    if not provider_text or pd.isna(provider_text):
        return None
    
    provider_text = str(provider_text).strip()
    if not provider_text:
        return None
    
    # If dataset is available, try to match against actual provider names
    if df is not None and not df.empty and "Car Cat" in df.columns:
        # Get all unique providers from dataset
        dataset_providers = df["Car Cat"].dropna().unique()
        dataset_providers = [str(p).strip() for p in dataset_providers if str(p).strip()]
        
        # Case-insensitive matching
        provider_lower = provider_text.lower()
        for dataset_provider in dataset_providers:
            if dataset_provider.lower() == provider_lower:
                return dataset_provider
        
        # Try partial matching (e.g., "getgo" matches "Getgo(EV)")
        for dataset_provider in dataset_providers:
            if provider_lower in dataset_provider.lower() or dataset_provider.lower() in provider_lower:
                return dataset_provider
    
    # Fallback: capitalize first letter of each word
    # Handle common variations
    provider_lower = provider_text.lower()
    if "getgo" in provider_lower:
        if "ev" in provider_lower or "electric" in provider_lower:
            return "Getgo(EV)"
        return "Getgo"
    elif "car club" in provider_lower:
        return "Car Club"
    elif provider_lower == "econ":
        return "Econ"
    elif provider_lower == "stand":
        return "Stand"
    elif "tribecar" in provider_lower:
        return "Tribecar"
    
    # Default: capitalize first letter of each word
    return provider_text.title()


def parse_llm_json_response(response_text):
    """
    Robustly parse JSON from LLM response, handling common formatting issues.
    
    Args:
        response_text: Raw text response from LLM
    
    Returns:
        Parsed JSON dictionary, or None if parsing fails
    """
    if not response_text:
        return None
    
    # Try to extract JSON object using multiple strategies
    strategies = [
        # Strategy 1: Find JSON between ```json and ```
        lambda text: _extract_markdown_json(text),
        # Strategy 2: Find JSON object with balanced braces
        lambda text: _extract_balanced_json(text),
        # Strategy 3: Find JSON after "{" and before last "}"
        lambda text: _extract_simple_json(text),
    ]
    
    for strategy in strategies:
        try:
            json_str = strategy(response_text)
            if json_str:
                # Clean up common JSON issues
                json_str = _fix_common_json_issues(json_str)
                # Try parsing
                parsed = json.loads(json_str)
                return parsed
        except json.JSONDecodeError as e:
            # Continue to next strategy
            continue
        except Exception as e:
            # Continue to next strategy
            continue
    
    # Last resort: try parsing the entire response
    try:
        cleaned = _fix_common_json_issues(response_text)
        return json.loads(cleaned)
    except:
        return None


def _extract_balanced_json(text):
    """Extract JSON with balanced braces - improved to handle more edge cases"""
    if not text:
        return None
    
    # Find the first { and then find the matching }
    start_idx = text.find('{')
    if start_idx == -1:
        return None
    
    brace_count = 0
    in_string = False
    escape_next = False
    start = start_idx
    
    for i in range(start, len(text)):
        char = text[i]
        
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Found complete JSON object
                    json_str = text[start:i+1]
                    # Validate it looks like JSON
                    if json_str.strip().startswith('{') and json_str.strip().endswith('}'):
                        return json_str
    
    return None


def _extract_markdown_json(text):
    """Extract JSON from markdown code blocks"""
    # Look for ```json ... ``` or ``` ... ```
    patterns = [
        r'```json\s*(\{.*?\})\s*```',  # ```json { ... } ```
        r'```\s*(\{.*?\})\s*```',      # ``` { ... } ```
        r'```json\s*(.*?)\s*```',       # ```json ... ``` (any content)
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            # If it starts with {, return it
            if content.startswith('{'):
                return content
    return None


def _extract_simple_json(text):
    """Extract JSON using simple regex (fallback) - try multiple patterns"""
    # Try to find JSON object - look for { ... } pattern
    patterns = [
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested braces
        r'\{.*?\}',  # Simple match
    ]
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.DOTALL)
        for match in matches:
            potential_json = match.group(0)
            # Quick validation - should start with { and end with }
            if potential_json.strip().startswith('{') and potential_json.strip().endswith('}'):
                return potential_json
    return None


def _fix_common_json_issues(json_str):
    """Fix common JSON formatting issues"""
    # Remove trailing commas before closing braces/brackets
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Fix unquoted keys (basic fix)
    # This is a simple fix - may not handle all cases
    json_str = re.sub(r'(\w+):', r'"\1":', json_str)
    # But then we need to fix already-quoted keys
    json_str = re.sub(r'""(\w+)":', r'"\1":', json_str)
    
    # Fix single quotes to double quotes (basic)
    json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
    json_str = re.sub(r":\s*'([^']*)'", r': "\1"', json_str)
    
    return json_str


def parse_rental_description_with_llm(description, df=None, model_name="llama2"):
    """
    Parse natural language rental description using LLM.
    
    Args:
        description: Natural language text describing the rental
        df: Historical data DataFrame for context (optional)
        model_name: Ollama model to use (default: llama2)
    
    Returns:
        Dictionary with extracted fields:
        - date: datetime or None
        - provider: str or None
        - car_model: str or None
        - distance: float or None
        - duration: float or None
        - fuel_pumped: float or None
        - total_cost: float or None
        - is_weekend: bool or None
        - consumption: float or None
        - fuel_usage: float or None
        - confidence: float (0-1)
        - reasoning: str (explanation of extraction)
    """
    try:
        # Extract dataset examples for LLM context
        dataset_examples = extract_dataset_examples_for_llm(df) if df is not None else {"car_models": [], "providers": [], "example_rows": []}
        
        # Prepare historical context if available
        historical_context = ""
        if df is not None and not df.empty:
            # Get provider statistics
            if "Car Cat" in df.columns:
                providers = df["Car Cat"].value_counts().head(5).to_dict()
                historical_context += f"Available providers: {', '.join(providers.keys())}\n"
            
            # Get typical values
            if "Distance (KM)" in df.columns:
                avg_distance = df["Distance (KM)"].mean()
                historical_context += f"Average distance: {avg_distance:.1f} km\n"
            
            if "Rental hour" in df.columns:
                avg_duration = df["Rental hour"].mean()
                historical_context += f"Average duration: {avg_duration:.1f} hours\n"
            
            if "Consumption (KM/L)" in df.columns:
                avg_consumption = df["Consumption (KM/L)"].replace(0, np.nan).mean()
                if not pd.isna(avg_consumption):
                    historical_context += f"Average consumption: {avg_consumption:.1f} km/L\n"
        
        # Build dataset format examples section
        dataset_format_section = ""
        if dataset_examples["car_models"] or dataset_examples["providers"]:
            dataset_format_section = "\n\nDATASET FORMAT EXAMPLES:\n"
            dataset_format_section += "These examples show the EXACT format used in the dataset:\n\n"
            
            # Show car model examples
            if dataset_examples["car_models"]:
                dataset_format_section += "Car Model Examples (use this exact format):\n"
                car_model_examples = ", ".join(dataset_examples["car_models"][:15])
                dataset_format_section += f"{car_model_examples}\n\n"
            
            # Show provider examples
            if dataset_examples["providers"]:
                dataset_format_section += "Provider Examples (use this EXACT format, case-sensitive):\n"
                provider_examples = ", ".join(dataset_examples["providers"])
                dataset_format_section += f"{provider_examples}\n\n"
            
            # Show example combinations
            if dataset_examples["example_rows"]:
                dataset_format_section += "Example Car Model + Provider Combinations from Dataset:\n"
                for i, example in enumerate(dataset_examples["example_rows"][:8], 1):
                    dataset_format_section += f"  {i}. Car model: \"{example['car_model']}\", Provider: \"{example['provider']}\"\n"
                dataset_format_section += "\n"
            
            dataset_format_section += "IMPORTANT PARSING RULES:\n"
            dataset_format_section += "1. When both car model and provider appear together (e.g., \"Honda shuttle under getgo\"), separate them:\n"
            dataset_format_section += "   - \"Honda shuttle under getgo\" → car_model: \"Honda Shuttle\", provider: \"Getgo\"\n"
            dataset_format_section += "   - \"Toyota Corolla from Car Club\" → car_model: \"Toyota Corolla\", provider: \"Car Club\"\n"
            dataset_format_section += "   - \"Mazda 3 via Getgo\" → car_model: \"Mazda 3\", provider: \"Getgo\"\n"
            dataset_format_section += "2. Provider names must match EXACT format from dataset (case-sensitive):\n"
            dataset_format_section += "   - \"getgo\" or \"GETGO\" → normalize to \"Getgo\"\n"
            dataset_format_section += "   - \"car club\" → normalize to \"Car Club\"\n"
            dataset_format_section += "   - \"econ\" → normalize to \"Econ\"\n"
            dataset_format_section += "   - \"stand\" → normalize to \"Stand\"\n"
            dataset_format_section += "3. Car model format should match dataset examples (e.g., \"Honda Fit\", \"Toyota Corolla Altis\")\n"
        
        # Create prompt for LLM - restructured to be direct and explicit
        # Build a concise dataset format reference
        dataset_ref = ""
        if dataset_examples["car_models"]:
            dataset_ref += f"Car models format: {', '.join(dataset_examples['car_models'][:10])}\n"
        if dataset_examples["providers"]:
            dataset_ref += f"Providers format: {', '.join(dataset_examples['providers'])}\n"
        
        # Create prompt with JSON example at the start - very explicit
        # Build few-shot example
        example_description = "Honda shuttle under getgo for 1 hour on 31 December 2025"
        example_json = """{
  "date": "2025-12-31",
  "provider": "Getgo",
  "car_model": "Honda Shuttle",
  "distance": null,
  "duration": 1.0,
  "fuel_pumped": null,
  "total_cost": null,
  "is_weekend": false,
  "consumption": null,
  "fuel_usage": null,
  "fuel_cost": null,
  "mileage_cost": null,
  "duration_cost": null,
  "kwh_used": null,
  "electricity_cost": null,
  "confidence": 0.9,
  "reasoning": "Extracted: Honda Shuttle separated from Getgo provider, 1 hour duration, Dec 31 2025"
}"""
        
        prompt = f"""Extract car rental data. Return ONLY valid JSON, nothing else.

EXAMPLE:
Description: "{example_description}"
Response: {example_json}

NOW EXTRACT FROM THIS DESCRIPTION:
Description: "{description}"

{dataset_ref if dataset_ref else ""}
Rules:
- Separate car model and provider when together (e.g., "Honda shuttle under getgo" → car_model: "Honda Shuttle", provider: "Getgo")
- Provider must match dataset format exactly (case-sensitive)
- Use null for missing values
- Date format: YYYY-MM-DD
- Extract cost fields if mentioned: fuel_cost, mileage_cost, duration_cost, electricity_cost, kwh_used

Return ONLY this JSON structure with your values:
{{
  "date": "YYYY-MM-DD or null",
  "provider": "provider name or null",
  "car_model": "car model or null",
  "distance": number or null,
  "duration": number or null,
  "fuel_pumped": number or null,
  "total_cost": number or null,
  "is_weekend": true/false/null,
  "consumption": number or null,
  "fuel_usage": number or null,
  "fuel_cost": number or null,
  "mileage_cost": number or null,
  "duration_cost": number or null,
  "kwh_used": number or null,
  "electricity_cost": number or null,
  "confidence": 0.0-1.0,
  "reasoning": "brief extraction note"
}}

JSON ONLY. NO EXPLANATIONS. NO TEXT BEFORE OR AFTER.
"""
        
        # Call Ollama API - try chat API first, with one retry on timeout
        response = None
        for attempt in range(2):
            try:
                messages = [
                    {
                        "role": "system",
                        "content": "You are a JSON extraction tool. You MUST return ONLY valid JSON objects. Never add explanations, instructions, or any text before or after the JSON. Start your response with { and end with }."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
                response = call_ollama_chat_api(messages, model_name)
                break
            except Exception as e:
                if "timed out" in str(e).lower() and attempt == 0:
                    time.sleep(2)
                    continue
                # Fallback to generate API if chat API fails (e.g. not timeout)
                print(f"Chat API failed, using generate API: {e}")
                try:
                    response = call_ollama_api(prompt, model_name)
                except Exception as e2:
                    if "timed out" in str(e2).lower() and attempt == 0:
                        time.sleep(2)
                        continue
                    raise
                break
        if response is None:
            raise Exception("Ollama request timed out. Please try again.")
        
        # Parse JSON response using robust parser
        extracted_data = parse_llm_json_response(response)
        
        if extracted_data is None:
            # If parsing fails, try one more time with direct JSON parse
            try:
                extracted_data = json.loads(response)
            except json.JSONDecodeError as e:
                # Log the error for debugging
                print(f"JSON parsing error details: {str(e)}")
                print(f"LLM response (first 500 chars): {response[:500]}")
                # Return minimal structure with error details
                return {
                    "date": None,
                    "provider": None,
                    "car_model": None,
                    "distance": None,
                    "duration": None,
                    "fuel_pumped": None,
                    "total_cost": None,
                    "is_weekend": None,
                    "consumption": None,
                    "fuel_usage": None,
                    "confidence": 0.3,
                    "reasoning": f"Failed to parse LLM response: {str(e)}. Please try rephrasing your description."
                }
        
        # Normalize provider name to match dataset format
        if extracted_data.get("provider"):
            normalized_provider = normalize_provider_name(extracted_data["provider"], df)
            extracted_data["provider"] = normalized_provider
        
        # Convert date string to datetime if provided
        if extracted_data.get("date"):
            try:
                extracted_data["date"] = pd.to_datetime(extracted_data["date"])
            except:
                extracted_data["date"] = None
        
        # Calculate fuel_usage if distance and consumption are available
        if extracted_data.get("distance") and extracted_data.get("consumption") and not extracted_data.get("fuel_usage"):
            try:
                extracted_data["fuel_usage"] = extracted_data["distance"] / extracted_data["consumption"]
            except:
                pass
        
        # Calculate consumption if distance and fuel_usage are available
        if extracted_data.get("distance") and extracted_data.get("fuel_usage") and not extracted_data.get("consumption"):
            try:
                extracted_data["consumption"] = extracted_data["distance"] / extracted_data["fuel_usage"]
            except:
                pass
        
        # Ensure confidence is a float
        if "confidence" not in extracted_data:
            extracted_data["confidence"] = 0.7
        
        return extracted_data
        
    except json.JSONDecodeError as e:
        # More specific error handling for JSON parsing
        error_msg = f"JSON parsing error: {str(e)}"
        print(f"Error parsing rental description with LLM: {error_msg}")
        return {
            "date": None,
            "provider": None,
            "car_model": None,
            "distance": None,
            "duration": None,
            "fuel_pumped": None,
            "total_cost": None,
            "is_weekend": None,
            "consumption": None,
            "fuel_usage": None,
            "fuel_cost": None,
            "mileage_cost": None,
            "duration_cost": None,
            "kwh_used": None,
            "electricity_cost": None,
            "confidence": 0.0,
            "reasoning": f"JSON parsing error: {str(e)}. The LLM response may be malformed. Please try rephrasing your description."
        }
    except Exception as e:
        error_msg = str(e)
        print(f"Error parsing rental description with LLM: {error_msg}")
        return {
            "date": None,
            "provider": None,
            "car_model": None,
            "distance": None,
            "duration": None,
            "fuel_pumped": None,
            "total_cost": None,
            "is_weekend": None,
            "consumption": None,
            "fuel_usage": None,
            "fuel_cost": None,
            "mileage_cost": None,
            "duration_cost": None,
            "kwh_used": None,
            "electricity_cost": None,
            "confidence": 0.0,
            "reasoning": f"Error: {error_msg}"
        }


def estimate_missing_fields_with_llm(form_data, df=None, model_name="llama2"):
    """
    Use LLM to estimate missing form fields based on provided fields and historical data.
    
    Args:
        form_data: Dictionary with current form field values (can have None for missing fields)
        df: Historical data DataFrame for context (optional)
        model_name: Ollama model to use (default: llama2)
    
    Returns:
        Dictionary with estimated values for missing fields:
        - Each key corresponds to a form field
        - Values are estimated numbers or None if cannot estimate
        - Includes 'confidence' and 'reasoning' keys
    """
    try:
        # Extract dataset examples for LLM context
        dataset_examples = extract_dataset_examples_for_llm(df) if df is not None else {"car_models": [], "providers": [], "example_rows": []}
        
        # Identify what's provided and what's missing
        provided_fields = {k: v for k, v in form_data.items() if v is not None and v != ""}
        missing_fields = [k for k, v in form_data.items() if v is None or v == ""]
        
        if not missing_fields:
            return {
                "confidence": 1.0,
                "reasoning": "All fields are already filled."
            }
        
        # Normalize provider name if provided
        provider = provided_fields.get("provider") or provided_fields.get("Car Cat")
        if provider:
            normalized_provider = normalize_provider_name(provider, df)
            if normalized_provider and normalized_provider != provider:
                # Update the provider in provided_fields for consistency
                if "provider" in provided_fields:
                    provided_fields["provider"] = normalized_provider
                if "Car Cat" in provided_fields:
                    provided_fields["Car Cat"] = normalized_provider
                provider = normalized_provider
        
        # Prepare historical context
        historical_context = ""
        
        if df is not None and not df.empty and provider:
            provider_data = df[df["Car Cat"] == provider] if "Car Cat" in df.columns else pd.DataFrame()
            
            if not provider_data.empty:
                historical_context += f"\nHistorical data for {provider}:\n"
                
                if "Consumption (KM/L)" in provider_data.columns:
                    avg_consumption = provider_data["Consumption (KM/L)"].replace(0, np.nan).mean()
                    if not pd.isna(avg_consumption):
                        historical_context += f"- Average consumption: {avg_consumption:.2f} km/L\n"
                
                if "Distance (KM)" in provider_data.columns and "Rental hour" in provider_data.columns:
                    avg_distance = provider_data["Distance (KM)"].mean()
                    avg_duration = provider_data["Rental hour"].mean()
                    historical_context += f"- Average distance: {avg_distance:.1f} km\n"
                    historical_context += f"- Average duration: {avg_duration:.1f} hours\n"
                
                if "Total" in provider_data.columns:
                    avg_cost = provider_data["Total"].mean()
                    historical_context += f"- Average total cost: ${avg_cost:.2f}\n"
        
        # Build dataset format examples section
        dataset_format_section = ""
        if dataset_examples["car_models"] or dataset_examples["providers"]:
            dataset_format_section = "\n\nDATASET FORMAT REFERENCE:\n"
            
            # Show car model examples if car_model is a missing field
            if any("car_model" in str(f).lower() or "car model" in str(f).lower() for f in missing_fields):
                if dataset_examples["car_models"]:
                    dataset_format_section += "Car Model Examples (use this exact format):\n"
                    car_model_examples = ", ".join(dataset_examples["car_models"][:15])
                    dataset_format_section += f"{car_model_examples}\n\n"
            
            # Show provider examples if provider is a missing field
            if any("provider" in str(f).lower() or "car cat" in str(f).lower() for f in missing_fields):
                if dataset_examples["providers"]:
                    dataset_format_section += "Provider Examples (use this EXACT format, case-sensitive):\n"
                    provider_examples = ", ".join(dataset_examples["providers"])
                    dataset_format_section += f"{provider_examples}\n\n"
        
        # Create prompt for LLM - restructured to be direct and explicit
        # Build concise format reference
        format_ref = ""
        if dataset_format_section:
            format_ref = dataset_format_section.strip() + "\n"
        
        # Create example JSON based on missing fields
        example_json_fields = []
        for field in missing_fields[:5]:  # Show first 5 missing fields as example
            if "provider" in str(field).lower() or "car cat" in str(field).lower():
                example_json_fields.append(f'  "{field}": "Getgo"')
            elif "car_model" in str(field).lower() or "car model" in str(field).lower():
                example_json_fields.append(f'  "{field}": "Honda Fit"')
            elif "distance" in str(field).lower():
                example_json_fields.append(f'  "{field}": 50.0')
            elif "duration" in str(field).lower() or "hour" in str(field).lower():
                example_json_fields.append(f'  "{field}": 2.0')
            else:
                example_json_fields.append(f'  "{field}": null')
        
        example_json = "{\n" + ",\n".join(example_json_fields) + ",\n  \"confidence\": 0.7,\n  \"reasoning\": \"Estimated based on provided data\"\n}"
        
        # Create prompt
        prompt = f"""TASK: Estimate missing rental fields and return ONLY a JSON object.

Provided Data:
{json.dumps(provided_fields, indent=2, default=str)}

Missing Fields: {', '.join(missing_fields)}

{historical_context if historical_context else ""}
{format_ref}
Pricing: Getgo $0.39/km+$8/hr, Car Club $0.33/km+$8/hr, Econ/Stand ~$15/hr+fuel

Return this exact JSON format (replace values or use null):
{example_json}

CRITICAL: Return ONLY the JSON object above with your estimates. No explanations, no text before or after. Start with {{ and end with }}.
"""
        
        # Call Ollama API - try chat API first for better structured outputs
        try:
            # Use chat API with system message for better JSON enforcement
            messages = [
                {
                    "role": "system",
                    "content": "You are a JSON estimation tool. You MUST return ONLY valid JSON objects. Never add explanations, instructions, or any text before or after the JSON. Start your response with { and end with }."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            response = call_ollama_chat_api(messages, model_name)
        except Exception as e:
            # Fallback to generate API if chat API fails
            print(f"Chat API failed, using generate API: {e}")
            response = call_ollama_api(prompt, model_name)
        
        # Parse JSON response using robust parser
        estimates = parse_llm_json_response(response)
        
        if estimates is None:
            # If parsing fails, try one more time with direct JSON parse
            try:
                estimates = json.loads(response)
            except json.JSONDecodeError as e:
                # Log the error for debugging
                print(f"JSON parsing error in estimate_missing_fields: {str(e)}")
                print(f"LLM response (first 500 chars): {response[:500]}")
                estimates = {
                    "confidence": 0.3,
                    "reasoning": f"Could not parse LLM response: {str(e)}. Using fallback calculations."
                }
        
        # Ensure confidence is present
        if "confidence" not in estimates:
            estimates["confidence"] = 0.5
        
        # Normalize provider-related fields to match dataset format
        for key in estimates:
            if key and ("provider" in str(key).lower() or "car cat" in str(key).lower()):
                if estimates[key] is not None:
                    normalized = normalize_provider_name(estimates[key], df)
                    estimates[key] = normalized
        
        return estimates
        
    except Exception as e:
        print(f"Error estimating missing fields with LLM: {e}")
        return {
            "confidence": 0.0,
            "reasoning": f"Error: {str(e)}"
        }


def create_fallback_recommendations(distance, duration, is_weekend):
    """Create intelligent fallback recommendations when Ollama is unavailable"""
    recommendations = []

    # Base providers with typical characteristics
    providers = [
        {"name": "Getgo", "base_cost": 18, "km_rate": 0.35, "hour_rate": 7.5},
        {"name": "Car Club", "base_cost": 20, "km_rate": 0.32, "hour_rate": 8.0},
        {"name": "Econ", "base_cost": 16, "km_rate": 0.38, "hour_rate": 7.0},
        {"name": "Stand", "base_cost": 22, "km_rate": 0.30, "hour_rate": 8.5},
    ]

    # Calculate costs and create recommendations
    for provider in providers:
        base_cost = provider["base_cost"]
        km_cost = distance * provider["km_rate"]
        hour_cost = duration * provider["hour_rate"]
        total_cost = base_cost + km_cost + hour_cost

        if is_weekend:
            total_cost *= 1.15  # Weekend premium

        # Create reasoning based on the customer profile
        reasoning = f"Good value for a 24-year-old driver: {provider['name']} offers competitive pricing. "
        if total_cost < 30:
            reasoning += "Budget-friendly option for cost-conscious customers."
        elif total_cost < 40:
            reasoning += "Balanced cost-quality ratio suitable for mixed usage (errands, leisure, sightseeing)."
        else:
            reasoning += "Premium option with higher comfort, good for longer trips and multiple activities."

        recommendations.append(
            {
                "provider": provider["name"],
                "model": "Standard",
                "total_cost": round(total_cost, 2),
                "reasoning": reasoning,
                "confidence": 0.7,
                "method": "Intelligent Fallback",
            }
        )

    # Sort by total cost
    recommendations.sort(key=lambda x: x["total_cost"])
    return recommendations[:3]  # Return top 3


def get_ollama_enhanced_recommendations(
    distance,
    duration,
    df,
    cost_analysis=None,
    is_weekend=False,
    top_n=5,
    use_ollama=True,
    ollama_model="llama2",
    use_ml=True,
    passenger_count=None,
    space_requirements=None,
    rental_timing=None,
    pricing_config=None,
):
    """Get enhanced recommendations combining traditional, ML, and Ollama approaches"""
    print(f"Getting recommendations: distance={distance}, duration={duration}, df_size={len(df) if df is not None else 0}, cost_analysis={cost_analysis is not None}")
    recommendations = []
    method_recommendations = {}
    
    # Get size requirements if passenger info provided
    size_requirements = None
    if passenger_count is not None:
        size_requirements = get_car_size_recommendation(passenger_count, space_requirements or "")

    # Get traditional recommendations
    if cost_analysis:
        traditional_recs = get_recommendations(
            distance, duration, cost_analysis, is_weekend, top_n
        )
        for rec in traditional_recs:
            rec["method"] = "Historical Analysis"
            rec["confidence"] = 0.8
        method_recommendations["Historical Analysis"] = traditional_recs

    # Get ML recommendations if data is available and ML is enabled
    if use_ml and len(df) >= 10:
        ml_recs = create_ml_recommendations(distance, duration, df, is_weekend, top_n)
        method_recommendations["ML Prediction"] = ml_recs

    # Get Ollama recommendations if requested
    if use_ollama:
        try:
            ollama_recs = create_ollama_recommendations(
                distance, duration, df, is_weekend, top_n, ollama_model,
                passenger_count=passenger_count,
                space_requirements=space_requirements,
                rental_timing=rental_timing
            )
            method_recommendations["Ollama Analysis"] = ollama_recs
        except Exception as e:
            print(f"Ollama recommendations failed: {e}")
            # Create fallback recommendations with reasoning when Ollama fails
            fallback_recs = create_fallback_recommendations(
                distance, duration, is_weekend
            )
            for rec in fallback_recs:
                rec["method"] = "Ollama Analysis (Fallback)"
                rec["reasoning"] = (
                    f"AI analysis unavailable. Based on historical patterns: {rec.get('reasoning', 'Good value option')}"
                )
            method_recommendations["Ollama Analysis (Fallback)"] = fallback_recs

    # If no recommendations from any method, create fallback recommendations
    if not method_recommendations:
        fallback_recs = create_fallback_recommendations(
            distance, duration, is_weekend
        )
        method_recommendations["Fallback"] = fallback_recs

    # Create balanced recommendations by taking top recommendations from each method
    available_methods = list(method_recommendations.keys())
    if available_methods:
        # Calculate how many recommendations to take from each method
        recs_per_method = max(1, top_n // len(available_methods))
        remaining_recs = top_n % len(available_methods)
        
        for i, method in enumerate(available_methods):
            method_recs = method_recommendations[method]
            # Take top recommendations from this method
            num_to_take = recs_per_method + (1 if i < remaining_recs else 0)
            recommendations.extend(method_recs[:num_to_take])

    # Filter by size if requirements provided
    if size_requirements:
        recommendations = filter_recommendations_by_size(recommendations, size_requirements, df)
    
    # Add pricing model comparison info
    if pricing_config is None:
        try:
            with open("pricing_config.json", "r") as f:
                pricing_config = json.load(f)
        except:
            pricing_config = {}
    
    pricing_comparison = compare_pricing_models(distance, duration, is_weekend, pricing_config)
    for rec in recommendations:
        rec["pricing_model"] = "mileage_included" if rec.get("provider") in ["Econ", "Stand", "Tribecar"] else "pay_per_km"
        rec["pricing_comparison"] = pricing_comparison
    
    # Sort by total cost and return top N
    recommendations.sort(key=lambda x: x["total_cost"])
    return recommendations[:top_n]


def get_calculator_pricing_recommendations(distance, duration, pricing_data, is_weekend=False, top_n=5):
    """Get recommendations using calculator pricing data with correct model"""
    recommendations = []
    
    for provider_name, pricing in pricing_data.items():
        # Get rates based on pricing type
        pricing_type = pricing["pricing_type"]
        
        # Get hour rate - check for weekend/weekday specific rates first
        if is_weekend:
            hour_rate = pricing.get("hour_rate_weekend", pricing.get("hour_rate", 10.0))
        else:
            hour_rate = pricing.get("hour_rate_weekday", pricing.get("hour_rate", 10.0))
        
        if pricing_type == "mileage":
            # Mileage-based pricing (Getgo, Getgo EV, Tribecar Car Club)
            mileage_rate = pricing["mileage_rate"]
            distance_cost = distance * mileage_rate
            fuel_cost = 0
        else:
            # Fuel-based pricing (Tribecar, Econ, Stand)
            fuel_rate = pricing.get("fuel_rate", pricing.get("usual_fuel_amount", 0))
            distance_cost = 0
            fuel_cost = fuel_rate  # Fixed fuel cost, not per km

        duration_cost = duration * hour_rate  # Total duration cost = duration * hour_rate
        subtotal = distance_cost + fuel_cost + duration_cost
        
        # Apply weekend surcharge if needed
        weekend_surcharge = subtotal * 0.2 if is_weekend else 0
        total_cost = subtotal + weekend_surcharge

        recommendations.append({
            "provider": provider_name,
            "model": "Standard",
            "total_cost": total_cost,
            "duration_cost": duration_cost,
            "mileage_cost": distance_cost,
            "fuel_cost": fuel_cost,
            "confidence": 0.9,
            "method": "Calculator Pricing",
            "reasoning": f"Based on current pricing configuration: {provider_name}"
        })

    # Sort by total cost and return top N
    recommendations.sort(key=lambda x: x["total_cost"])
    return recommendations[:top_n]


def calculate_provider_prices(distance, duration, pricing_data, day_type="weekday"):
    """Calculate prices for all providers using simplified pricing data. Supports mileage, fuel, socar (Malaysia SoCar), and skips traditional (NormalRental)."""
    def get_distance_and_fuel_cost(pricing, distance):
        pricing_type = pricing.get("pricing_type", "mileage")
        if pricing_type == "traditional":
            return None, None  # Skip in caller
        if pricing_type == "socar":
            # SoCar: mileage cost = package + excess; handled in main loop
            return None, None
        if pricing_type == "mileage":
            mileage_rate = pricing["mileage_rate"]
            return distance * mileage_rate, 0
        else:
            fuel_rate = pricing.get("fuel_rate", pricing.get("usual_fuel_amount", 0))
            return 0, fuel_rate

    results = []
    for provider_name, pricing in pricing_data.items():
        pricing_type = pricing.get("pricing_type", "mileage")

        if pricing_type == "traditional":
            continue  # NormalRental: no formula-based estimate in calculator

        if pricing_type == "socar":
            hour_rate = pricing.get("hour_rate", 8.0)
            packages = pricing.get("mileage_packages", [{"km": 10, "price": 2.5}, {"km": 50, "price": 11}, {"km": 100, "price": 15}])
            excess_km_rate = pricing.get("excess_km_rate", 0.25)
            duration_cost = (duration or 0) * hour_rate
            packages_sorted = sorted(packages, key=lambda p: p["km"])
            chosen = packages_sorted[0]
            for p in packages_sorted:
                if (distance or 0) <= p["km"]:
                    chosen = p
                    break
                chosen = p
            package_km = chosen["km"]
            package_price = chosen["price"]
            excess_km = max(0, (distance or 0) - package_km)
            mileage_cost = package_price + excess_km * excess_km_rate
            distance_cost = mileage_cost
            fuel_cost = 0
            subtotal = duration_cost + distance_cost
            weekend_surcharge = subtotal * 0.2 if day_type == "weekend" else 0
            total_cost = subtotal + weekend_surcharge
            results.append({
                "provider": provider_name,
                "base_cost": 0,
                "distance_cost": distance_cost,
                "fuel_cost": 0,
                "duration_cost": duration_cost,
                "weekend_surcharge": weekend_surcharge,
                "total_cost": total_cost
            })
            continue

        distance_cost, fuel_cost = get_distance_and_fuel_cost(pricing, distance)
        if distance_cost is None:
            continue

        if day_type == "weekend":
            hour_rate = pricing.get("hour_rate_weekend", pricing.get("hour_rate", 10.0))
        else:
            hour_rate = pricing.get("hour_rate_weekday", pricing.get("hour_rate", 10.0))

        duration_cost = duration * hour_rate
        subtotal = distance_cost + fuel_cost + duration_cost
        weekend_surcharge = subtotal * 0.2 if day_type == "weekend" else 0
        total_cost = subtotal + weekend_surcharge

        results.append({
            "provider": provider_name,
            "base_cost": 0,
            "distance_cost": distance_cost,
            "fuel_cost": fuel_cost,
            "duration_cost": duration_cost,
            "weekend_surcharge": weekend_surcharge,
            "total_cost": total_cost
        })

    results.sort(key=lambda x: x["total_cost"])
    return results


def create_ml_budget_prediction(df, monthly_budget, prediction_period, confidence_level):
    """Create ML-based budget prediction using historical data"""
    try:
        # Prepare historical data for ML - exclude calculator-generated records
        df_copy = df.copy()
        
        # Filter out calculator-generated records for spending calculations
        if "Car model" in df_copy.columns:
            df_copy = df_copy[df_copy["Car model"] != "Calculator Generated"]
        
        # Ensure Date column is datetime
        if not pd.api.types.is_datetime64_dtype(df_copy["Date"]):
            df_copy["Date"] = pd.to_datetime(df_copy["Date"])
        
        # Extract features for ML
        df_copy["Month"] = df_copy["Date"].dt.month
        df_copy["Year"] = df_copy["Date"].dt.year
        df_copy["Weekday"] = df_copy["Date"].dt.weekday
        df_copy["Is_Weekend"] = (df_copy["Weekday"] >= 5).astype(int)
        
        # Group by month-year for monthly spending analysis
        monthly_spending = df_copy.groupby(["Year", "Month"]).agg({
            "Total": "sum",
            "Distance (KM)": "sum",
            "Rental hour": "sum",
            "Is_Weekend": "mean"
        }).reset_index()
        
        # Calculate monthly statistics
        avg_monthly_spending = monthly_spending["Total"].mean()
        spending_std = monthly_spending["Total"].std()
        spending_trend = calculate_spending_trend(monthly_spending)
        
        # Apply confidence level adjustments
        confidence_multipliers = {
            "conservative": 1.2,  # 20% higher prediction
            "medium": 1.0,       # No adjustment
            "optimistic": 0.8    # 20% lower prediction
        }
        
        confidence_multiplier = confidence_multipliers.get(confidence_level, 1.0)
        
        # Generate prediction based on period
        if prediction_period == "next_month":
            predicted_spending = avg_monthly_spending * confidence_multiplier
            period_months = 1
        elif prediction_period == "next_3_months":
            predicted_spending = avg_monthly_spending * 3 * confidence_multiplier
            period_months = 3
        elif prediction_period == "next_6_months":
            predicted_spending = avg_monthly_spending * 6 * confidence_multiplier
            period_months = 6
        else:  # next_year
            predicted_spending = avg_monthly_spending * 12 * confidence_multiplier
            period_months = 12
        
        # Calculate risk assessment
        budget_remaining = monthly_budget * period_months - predicted_spending
        risk_level = assess_budget_risk(budget_remaining, predicted_spending, spending_std)
        
        # Calculate confidence score
        confidence_score = calculate_confidence_score(len(monthly_spending), spending_std)
        
        return {
            "monthly_budget": monthly_budget,
            "predicted_spending": predicted_spending,
            "budget_remaining": budget_remaining,
            "risk_level": risk_level,
            "confidence_score": confidence_score,
            "spending_trend": spending_trend,
            "avg_monthly_spending": avg_monthly_spending,
            "spending_std": spending_std,
            "data_points": len(monthly_spending),
            "period_months": period_months,
            "confidence_level": confidence_level,
            "monthly_data": monthly_spending
        }
        
    except Exception as e:
        raise Exception(f"ML prediction failed: {str(e)}")


def calculate_spending_trend(monthly_data):
    """Calculate spending trend from historical data"""
    if len(monthly_data) < 2:
        return "stable"
    
    # Calculate trend using linear regression
    x = np.arange(len(monthly_data))
    y = monthly_data["Total"].values
    
    # Simple linear regression
    slope = np.polyfit(x, y, 1)[0]
    
    # Determine trend based on slope
    if slope > monthly_data["Total"].mean() * 0.1:  # 10% of average
        return "increasing"
    elif slope < -monthly_data["Total"].mean() * 0.1:
        return "decreasing"
    else:
        return "stable"


def assess_budget_risk(budget_remaining, predicted_spending, spending_std):
    """Assess budget risk level"""
    if budget_remaining < 0:
        return "high"
    elif budget_remaining < predicted_spending * 0.2:  # Less than 20% buffer
        return "medium"
    else:
        return "low"


def calculate_confidence_score(data_points, spending_std):
    """Calculate confidence score based on data quality"""
    # Base confidence on data points and variance
    base_confidence = min(1.0, data_points / 12)  # Max confidence at 12+ months
    
    # Adjust for variance (lower variance = higher confidence)
    if spending_std > 0:
        variance_factor = max(0.5, 1.0 - (spending_std / 1000))  # Assume 1000 is high variance
    else:
        variance_factor = 1.0
    
    return base_confidence * variance_factor


def calculate_cost_requirements(target_cost, duration=None, mileage=None, provider="Getgo"):
    """Calculate cost requirements and scenarios"""
    try:
        if duration is not None and mileage is not None:
            # Both provided - calculate if target is achievable
            if provider == "Getgo":
                mileage_rate = 0.39
                hourly_rate = 8.0
            elif provider == "Car Club":
                mileage_rate = 0.33
                hourly_rate = 8.0
            else:
                return {"error": f"Provider {provider} not supported for cost planning"}
            
            calculated_cost = (mileage * mileage_rate) + (duration * hourly_rate)
            achievable = calculated_cost <= target_cost
            difference = target_cost - calculated_cost
            
            return {
                "achievable": achievable,
                "calculated_cost": calculated_cost,
                "difference": difference,
                "scenarios": []
            }
        
        elif duration is not None:
            # Duration provided - calculate required mileage
            required_mileage = calculate_required_mileage(target_cost, duration, provider)
            if required_mileage is None:
                return {"error": "Target cost too low for given duration"}
            
            scenarios = generate_booking_scenarios(target_cost, duration=duration, provider=provider)
            return {
                "required_mileage": required_mileage,
                "scenarios": scenarios
            }
        
        elif mileage is not None:
            # Mileage provided - calculate required duration
            required_duration = calculate_required_duration(target_cost, mileage, provider)
            if required_duration is None:
                return {"error": "Target cost too low for given mileage"}
            
            scenarios = generate_booking_scenarios(target_cost, mileage=mileage, provider=provider)
            return {
                "required_duration": required_duration,
                "scenarios": scenarios
            }
        
        else:
            return {"error": "Either duration or mileage must be provided"}
    
    except Exception as e:
        return {"error": f"Calculation error: {str(e)}"}


def create_trip_record(
    distance,
    duration,
    provider,
    total_cost,
    day_type="weekday",
    region="Singapore",
    car_model=None,
    deposit_rm=None,
    rental_fee_rm=None,
    additional_fee_rm=None,
):
    """Create a new trip record for saving to the dataset. Region must be Singapore or Malaysia."""
    if region not in VALID_REGIONS:
        region = "Singapore"
    allowed = get_providers_for_region(region)
    if provider not in allowed:
        provider = allowed[0] if allowed else "Getgo"

    provider_mapping = {
        "Getgo": "Getgo",
        "Getgo EV": "Getgo(EV)",
        "Tribecar": "Tribecar",
        "Car Club": "Car Club",
        "Econ": "Econ",
        "Stand": "Stand",
        "SoCar": "SoCar",
        "NormalRental": "NormalRental",
    }
    mapped_provider = provider_mapping.get(provider, provider)

    record = {
        "Date": pd.Timestamp.now(),
        "Region": region,
        "Car Cat": mapped_provider,
        "Distance (KM)": distance,
        "Rental hour": duration,
        "Total": total_cost,
        "Weekday/weekend": day_type,
        "Car model": car_model or "Calculator Generated",
        "Fuel pumped": 0,
        "Estimated fuel usage": 0,
        "Consumption (KM/L)": 0,
        "Fuel cost": 0,
        "Pumped fuel cost": 0,
        "Mileage cost ($0.39)": 0,
        "Cost per KM": total_cost / distance if distance and distance > 0 else 0,
        "Duration cost": 0,
        "Est original fuel savings": 0,
        "Cost/HR": total_cost / duration if duration and duration > 0 else 0,
    }
    if region == "Malaysia" and mapped_provider == "NormalRental":
        record["Deposit (RM)"] = deposit_rm if deposit_rm is not None else np.nan
        record["Rental fee (RM)"] = rental_fee_rm if rental_fee_rm is not None else np.nan
        record["Additional fee (RM)"] = additional_fee_rm if additional_fee_rm is not None else np.nan
    return record


# User Preference Analysis Functions

def analyze_user_preferences(df, ollama_model="llama2"):
    """
    Analyze user rental preferences using Ollama to understand patterns from historical data
    
    Args:
        df: Historical rental data DataFrame
        ollama_model: Ollama model to use for analysis
        
    Returns:
        Dictionary containing user preferences and insights
    """
    try:
        # Prepare user data summary for Ollama analysis
        user_summary = prepare_user_data_summary(df)
        
        # Check for errors in user_summary
        if isinstance(user_summary, dict) and "error" in user_summary:
            return {
                "error": user_summary["error"],
                "user_profile": {},
                "preferred_providers": [],
                "preferred_car_models": [],
                "rental_patterns": {},
                "recommendations": [],
                "insights": []
            }
        
        # Create prompt for Ollama to analyze user preferences
        prompt = create_user_preference_prompt(user_summary)
        
        # Call Ollama API
        response = call_ollama_api(prompt, ollama_model)
        
        # Parse the response to extract user preferences
        preferences = parse_user_preference_response(response, user_summary)
        
        return preferences
        
    except Exception as e:
        print(f"User preference analysis error: {e}")
        # Get user_summary if not already created, or use existing one
        if 'user_summary' not in locals():
            user_summary = prepare_user_data_summary(df)
        # Check for errors in user_summary
        if isinstance(user_summary, dict) and "error" in user_summary:
            return {
                "error": user_summary["error"],
                "user_profile": {},
                "preferred_providers": [],
                "preferred_car_models": [],
                "rental_patterns": {},
                "recommendations": [],
                "insights": []
            }
        # Return fallback preferences based on data analysis
        return create_fallback_user_preferences(user_summary)


def prepare_user_data_summary(df):
    """Prepare a comprehensive summary of user rental data for Ollama analysis"""
    if df.empty:
        return {"error": "No data available"}
    
    # Basic statistics
    total_rentals = len(df)
    total_distance = df["Distance (KM)"].sum() if "Distance (KM)" in df.columns else 0
    total_cost = df["Total"].sum() if "Total" in df.columns else 0
    avg_cost_per_rental = total_cost / total_rentals if total_rentals > 0 else 0
    
    # Provider preferences
    provider_stats = {}
    if "Car Cat" in df.columns:
        for provider in df["Car Cat"].unique():
            if pd.notna(provider):
                provider_data = df[df["Car Cat"] == provider]
                provider_stats[provider] = {
                    "count": len(provider_data),
                    "percentage": (len(provider_data) / total_rentals) * 100,
                    "avg_cost": provider_data["Total"].mean() if "Total" in provider_data.columns else 0,
                    "avg_distance": provider_data["Distance (KM)"].mean() if "Distance (KM)" in provider_data.columns else 0,
                    "avg_duration": provider_data["Rental hour"].mean() if "Rental hour" in provider_data.columns else 0
                }
    
    # Car model preferences
    car_model_stats = {}
    if "Car model" in df.columns:
        car_models = df["Car model"].value_counts().head(10)
        for model, count in car_models.items():
            if pd.notna(model):
                model_data = df[df["Car model"] == model]
                car_model_stats[model] = {
                    "count": count,
                    "percentage": (count / total_rentals) * 100,
                    "avg_cost": model_data["Total"].mean() if "Total" in model_data.columns else 0,
                    "avg_distance": model_data["Distance (KM)"].mean() if "Distance (KM)" in model_data.columns else 0
                }
    
    # Time patterns
    weekend_rentals = 0
    weekday_rentals = 0
    if "Weekday/weekend" in df.columns:
        weekend_rentals = len(df[df["Weekday/weekend"] == "weekend"])
        weekday_rentals = total_rentals - weekend_rentals
    
    # Distance patterns
    distance_stats = {
        "avg_distance": df["Distance (KM)"].mean() if "Distance (KM)" in df.columns else 0,
        "max_distance": df["Distance (KM)"].max() if "Distance (KM)" in df.columns else 0,
        "min_distance": df["Distance (KM)"].min() if "Distance (KM)" in df.columns else 0,
        "short_trips": len(df[df["Distance (KM)"] <= 30]) if "Distance (KM)" in df.columns else 0,
        "medium_trips": len(df[(df["Distance (KM)"] > 30) & (df["Distance (KM)"] <= 100)]) if "Distance (KM)" in df.columns else 0,
        "long_trips": len(df[df["Distance (KM)"] > 100]) if "Distance (KM)" in df.columns else 0
    }
    
    # Duration patterns
    duration_stats = {
        "avg_duration": df["Rental hour"].mean() if "Rental hour" in df.columns else 0,
        "max_duration": df["Rental hour"].max() if "Rental hour" in df.columns else 0,
        "min_duration": df["Rental hour"].min() if "Rental hour" in df.columns else 0,
        "short_rentals": len(df[df["Rental hour"] <= 2]) if "Rental hour" in df.columns else 0,
        "medium_rentals": len(df[(df["Rental hour"] > 2) & (df["Rental hour"] <= 6)]) if "Rental hour" in df.columns else 0,
        "long_rentals": len(df[df["Rental hour"] > 6]) if "Rental hour" in df.columns else 0
    }
    
    # Cost patterns
    cost_stats = {
        "avg_cost": df["Total"].mean() if "Total" in df.columns else 0,
        "max_cost": df["Total"].max() if "Total" in df.columns else 0,
        "min_cost": df["Total"].min() if "Total" in df.columns else 0,
        "budget_rentals": len(df[df["Total"] <= 30]) if "Total" in df.columns else 0,
        "mid_range_rentals": len(df[(df["Total"] > 30) & (df["Total"] <= 60)]) if "Total" in df.columns else 0,
        "premium_rentals": len(df[df["Total"] > 60]) if "Total" in df.columns else 0
    }
    
    return {
        "total_rentals": total_rentals,
        "total_distance": total_distance,
        "total_cost": total_cost,
        "avg_cost_per_rental": avg_cost_per_rental,
        "provider_preferences": provider_stats,
        "car_model_preferences": car_model_stats,
        "time_patterns": {
            "weekend_rentals": weekend_rentals,
            "weekday_rentals": weekday_rentals,
            "weekend_percentage": (weekend_rentals / total_rentals) * 100 if total_rentals > 0 else 0
        },
        "distance_patterns": distance_stats,
        "duration_patterns": duration_stats,
        "cost_patterns": cost_stats
    }


def create_user_preference_prompt(user_summary):
    """Create a prompt for Ollama to analyze user rental preferences"""
    
    # Format the data for the prompt
    data_summary = f"""
User Rental History Analysis:
- Total Rentals: {user_summary['total_rentals']}
- Total Distance: {user_summary['total_distance']:.1f} km
- Total Cost: ${user_summary['total_cost']:.2f}
- Average Cost per Rental: ${user_summary['avg_cost_per_rental']:.2f}

Provider Preferences:
"""
    
    for provider, stats in user_summary['provider_preferences'].items():
        data_summary += f"- {provider}: {stats['count']} rentals ({stats['percentage']:.1f}%), Avg Cost: ${stats['avg_cost']:.2f}, Avg Distance: {stats['avg_distance']:.1f}km\n"
    
    data_summary += f"""
Car Model Preferences:
"""
    for model, stats in list(user_summary['car_model_preferences'].items())[:5]:  # Top 5 models
        data_summary += f"- {model}: {stats['count']} rentals ({stats['percentage']:.1f}%), Avg Cost: ${stats['avg_cost']:.2f}\n"
    
    data_summary += f"""
Time Patterns:
- Weekend Rentals: {user_summary['time_patterns']['weekend_rentals']} ({user_summary['time_patterns']['weekend_percentage']:.1f}%)
- Weekday Rentals: {user_summary['time_patterns']['weekday_rentals']}

Distance Patterns:
- Average Distance: {user_summary['distance_patterns']['avg_distance']:.1f} km
- Short Trips (≤30km): {user_summary['distance_patterns']['short_trips']}
- Medium Trips (31-100km): {user_summary['distance_patterns']['medium_trips']}
- Long Trips (>100km): {user_summary['distance_patterns']['long_trips']}

Duration Patterns:
- Average Duration: {user_summary['duration_patterns']['avg_duration']:.1f} hours
- Short Rentals (≤2h): {user_summary['duration_patterns']['short_rentals']}
- Medium Rentals (3-6h): {user_summary['duration_patterns']['medium_rentals']}
- Long Rentals (>6h): {user_summary['duration_patterns']['long_rentals']}

Cost Patterns:
- Average Cost: ${user_summary['cost_patterns']['avg_cost']:.2f}
- Budget Rentals (≤$30): {user_summary['cost_patterns']['budget_rentals']}
- Mid-range Rentals ($31-60): {user_summary['cost_patterns']['mid_range_rentals']}
- Premium Rentals (>$60): {user_summary['cost_patterns']['premium_rentals']}
"""
    
    prompt = f"""You are an expert car rental analyst. Analyze the following user's rental history to understand their preferences and provide personalized insights.

{data_summary}

IMPORTANT: Choose ONE specific value for each field. Do NOT include multiple options or placeholders.

Based on this data, analyze the user's rental preferences and provide insights in the following JSON format:

{{
  "user_profile": {{
    "rental_frequency": "low" OR "medium" OR "high" (choose ONE based on total rentals),
    "budget_consciousness": "low" OR "medium" OR "high" (choose ONE based on average cost),
    "distance_preference": "short" OR "medium" OR "long" (choose ONE based on average distance),
    "duration_preference": "short" OR "medium" OR "long" (choose ONE based on average duration),
    "provider_loyalty": "low" OR "medium" OR "high" (choose ONE based on provider diversity),
    "weekend_vs_weekday": "weekend_preference" OR "weekday_preference" OR "balanced" (choose ONE)
  }},
  "preferred_providers": [
    {{
      "provider": "exact provider name from the data",
      "reason": "clear explanation of why this provider fits the user's patterns",
      "confidence": 0.8
    }}
  ],
  "preferred_car_models": [
    {{
      "model": "exact car model name from the data",
      "reason": "clear explanation of why this model fits the user's usage patterns",
      "confidence": 0.8
    }}
  ],
  "rental_patterns": {{
    "typical_distance": "short" OR "medium" OR "long" (choose ONE),
    "typical_duration": "short" OR "medium" OR "long" (choose ONE),
    "typical_cost_range": "budget" OR "mid-range" OR "premium" (choose ONE),
    "usage_type": "errands" OR "leisure" OR "business" OR "mixed" (choose ONE)
  }},
  "recommendations": [
    {{
      "type": "provider" OR "car_model" OR "usage_pattern" (choose ONE),
      "suggestion": "specific, actionable recommendation",
      "reasoning": "detailed explanation of why this recommendation is good for the user based on their patterns"
    }}
  ],
  "insights": [
    "specific insight about user behavior based on the data",
    "another specific insight about their preferences"
  ]
}}

CRITICAL: Return actual values, not placeholders. For example, if the user has 5 rentals, return "low" for rental_frequency, not "low/medium/high".

Provide only the JSON response, no additional text."""
    
    return prompt


def parse_user_preference_response(response, user_summary):
    """Parse Ollama response to extract user preferences"""
    try:
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            preferences = json.loads(json_str)
        else:
            # If no JSON found, create fallback preferences
            preferences = create_fallback_user_preferences(user_summary)
        
        # Validate and clean the preferences
        cleaned_preferences = validate_user_preferences(preferences, user_summary)
        return cleaned_preferences
        
    except json.JSONDecodeError:
        # If JSON parsing fails, create fallback preferences
        return create_fallback_user_preferences(user_summary)
    except Exception as e:
        print(f"Error parsing user preferences: {e}")
        return create_fallback_user_preferences(user_summary)


def validate_user_preferences(preferences, user_summary):
    """Validate and clean user preferences extracted from Ollama response"""
    # Ensure required fields exist
    if "user_profile" not in preferences:
        preferences["user_profile"] = {}
    
    if "preferred_providers" not in preferences:
        preferences["preferred_providers"] = []
    
    if "preferred_car_models" not in preferences:
        preferences["preferred_car_models"] = []
    
    if "rental_patterns" not in preferences:
        preferences["rental_patterns"] = {}
    
    if "recommendations" not in preferences:
        preferences["recommendations"] = []
    
    if "insights" not in preferences:
        preferences["insights"] = []
    
    # Validate user profile
    profile = preferences["user_profile"]
    if "rental_frequency" not in profile:
        profile["rental_frequency"] = "medium"
    if "budget_consciousness" not in profile:
        profile["budget_consciousness"] = "medium"
    if "distance_preference" not in profile:
        profile["distance_preference"] = "medium"
    if "duration_preference" not in profile:
        profile["duration_preference"] = "medium"
    if "provider_loyalty" not in profile:
        profile["provider_loyalty"] = "medium"
    if "weekend_vs_weekday" not in profile:
        profile["weekend_vs_weekday"] = "balanced"
    
    return preferences


def create_fallback_user_preferences(user_summary):
    """Create fallback user preferences when Ollama analysis fails"""
    # Validate user_summary
    if not isinstance(user_summary, dict):
        return {
            "error": "Invalid data summary provided. Please ensure your data file is loaded correctly.",
            "user_profile": {},
            "preferred_providers": [],
            "preferred_car_models": [],
            "rental_patterns": {},
            "recommendations": [],
            "insights": []
        }
    
    # Check for errors in user_summary
    if "error" in user_summary:
        return {
            "error": user_summary["error"],
            "user_profile": {},
            "preferred_providers": [],
            "preferred_car_models": [],
            "rental_patterns": {},
            "recommendations": [],
            "insights": []
        }
    
    # Check if there's any rental data
    total_rentals = user_summary.get("total_rentals", 0)
    if total_rentals == 0:
        return {
            "error": "No rental data available. Please load your rental history CSV file first.",
            "user_profile": {},
            "preferred_providers": [],
            "preferred_car_models": [],
            "rental_patterns": {},
            "recommendations": [],
            "insights": []
        }
    
    # Analyze the data to create basic preferences
    
    # Determine rental frequency
    if total_rentals < 10:
        frequency = "low"
    elif total_rentals < 30:
        frequency = "medium"
    else:
        frequency = "high"
    
    # Determine budget consciousness based on average cost
    avg_cost = user_summary.get("avg_cost_per_rental", 0)
    if avg_cost < 30:
        budget_consciousness = "high"
    elif avg_cost < 60:
        budget_consciousness = "medium"
    else:
        budget_consciousness = "low"
    
    # Determine distance preference
    avg_distance = user_summary.get("distance_patterns", {}).get("avg_distance", 0)
    if avg_distance < 30:
        distance_preference = "short"
    elif avg_distance < 80:
        distance_preference = "medium"
    else:
        distance_preference = "long"
    
    # Determine duration preference
    avg_duration = user_summary.get("duration_patterns", {}).get("avg_duration", 0)
    if avg_duration < 2:
        duration_preference = "short"
    elif avg_duration < 6:
        duration_preference = "medium"
    else:
        duration_preference = "long"
    
    # Determine weekend vs weekday preference
    time_patterns = user_summary.get("time_patterns", {})
    weekend_pct = time_patterns.get("weekend_percentage", 0)
    if weekend_pct > 60:
        weekend_preference = "weekend_preference"
    elif weekend_pct < 30:
        weekend_preference = "weekday_preference"
    else:
        weekend_preference = "balanced"
    
    # Determine provider loyalty
    provider_prefs = user_summary.get("provider_preferences", {})
    if len(provider_prefs) == 1:
        provider_loyalty = "high"
    elif len(provider_prefs) <= 2:
        provider_loyalty = "medium"
    else:
        provider_loyalty = "low"
    
    # Get most used provider with better reasoning
    most_used_provider = max(provider_prefs.items(), key=lambda x: x[1]["count"])[0] if provider_prefs else "Getgo"
    provider_count = provider_prefs.get(most_used_provider, {}).get("count", 0)
    provider_pct = provider_prefs.get(most_used_provider, {}).get("percentage", 0)
    provider_avg_cost = provider_prefs.get(most_used_provider, {}).get("avg_cost", 0)
    
    # Get most used car model with better reasoning
    car_model_prefs = user_summary.get("car_model_preferences", {})
    most_used_model = max(car_model_prefs.items(), key=lambda x: x[1]["count"])[0] if car_model_prefs else "Standard"
    model_count = car_model_prefs.get(most_used_model, {}).get("count", 0)
    model_pct = car_model_prefs.get(most_used_model, {}).get("percentage", 0)
    
    # Determine cost range
    cost_patterns = user_summary.get("cost_patterns", {})
    budget_count = cost_patterns.get("budget_rentals", 0)
    mid_count = cost_patterns.get("mid_range_rentals", 0)
    premium_count = cost_patterns.get("premium_rentals", 0)
    
    if budget_count > mid_count and budget_count > premium_count:
        cost_range = "budget"
    elif premium_count > budget_count and premium_count > mid_count:
        cost_range = "premium"
    else:
        cost_range = "mid-range"
    
    # Create better provider reason
    provider_reason = f"Your most frequently used provider with {provider_count} rentals ({provider_pct:.1f}% of all rentals). "
    if provider_avg_cost < avg_cost:
        provider_reason += f"Offers good value with average cost of ${provider_avg_cost:.2f}, below your overall average."
    else:
        provider_reason += f"Average cost of ${provider_avg_cost:.2f} per rental."
    
    # Create better model reason
    model_reason = f"Your most frequently used car model with {model_count} rentals ({model_pct:.1f}% of all rentals). "
    model_reason += "This model aligns with your typical usage patterns."
    
    # Create better recommendation reasoning
    recommendation_reasoning = f"Based on your rental history, {most_used_provider} has been your preferred choice. "
    recommendation_reasoning += f"You've used it for {provider_pct:.1f}% of your rentals, suggesting it fits your needs well. "
    if provider_avg_cost < avg_cost:
        recommendation_reasoning += "It also offers cost-effective options that align with your budget preferences."
    else:
        recommendation_reasoning += "Consider continuing with this provider for consistency and familiarity."
    
    return {
        "user_profile": {
            "rental_frequency": frequency,
            "budget_consciousness": budget_consciousness,
            "distance_preference": distance_preference,
            "duration_preference": duration_preference,
            "provider_loyalty": provider_loyalty,
            "weekend_vs_weekday": weekend_preference
        },
        "preferred_providers": [
            {
                "provider": most_used_provider,
                "reason": provider_reason,
                "confidence": 0.8
            }
        ],
        "preferred_car_models": [
            {
                "model": most_used_model,
                "reason": model_reason,
                "confidence": 0.8
            }
        ],
        "rental_patterns": {
            "typical_distance": distance_preference,
            "typical_duration": duration_preference,
            "typical_cost_range": cost_range,
            "usage_type": "mixed"
        },
        "recommendations": [
            {
                "type": "provider",
                "suggestion": f"Continue using {most_used_provider} for your rental needs",
                "reasoning": recommendation_reasoning
            }
        ],
        "insights": [
            f"You are a {frequency} frequency renter with {total_rentals} total rentals and an average cost of ${avg_cost:.2f} per rental",
            f"Your typical trip distance is {avg_distance:.1f} km, indicating a preference for {distance_preference} distance trips",
            f"You prefer {most_used_provider} ({provider_pct:.1f}% of rentals) and {most_used_model} ({model_pct:.1f}% of rentals) based on your usage patterns"
        ]
    }


# Range-based categorization functions

def get_distance_range(distance):
    """Categorize distance into range"""
    if distance < 20:
        return "<20km"
    elif distance < 50:
        return "20-50km"
    elif distance < 100:
        return "50-100km"
    else:
        return ">=100km"


def get_duration_range(duration):
    """Categorize duration into range"""
    if duration < 2:
        return "<2 hours"
    elif duration < 4:
        return "2-4 hours"
    elif duration < 8:
        return "4-8 hours"
    else:
        return ">=8 hours"


def categorize_rental_by_ranges(distance, duration):
    """Get both distance and duration range categories"""
    return {
        "distance_range": get_distance_range(distance),
        "duration_range": get_duration_range(duration)
    }


def analyze_provider_performance_by_ranges(df):
    """
    Analyze which providers/models work best for each distance and duration range.
    
    Args:
        df: Historical rental data DataFrame
        
    Returns:
        Dictionary with structure:
        {
            "distance_ranges": {
                "<20km": {provider_stats},
                "20-50km": {provider_stats},
                ...
            },
            "duration_ranges": {
                "<2 hours": {provider_stats},
                "2-4 hours": {provider_stats},
                ...
            },
            "range_combinations": {
                ("<20km", "<2 hours"): {provider_stats},
                ...
            }
        }
    """
    if df is None or df.empty:
        return {
            "distance_ranges": {},
            "duration_ranges": {},
            "range_combinations": {}
        }
    
    # Ensure required columns exist
    required_cols = ["Distance (KM)", "Rental hour", "Car Cat", "Total"]
    if not all(col in df.columns for col in required_cols):
        return {
            "distance_ranges": {},
            "duration_ranges": {},
            "range_combinations": {}
        }
    
    # Create a copy to avoid modifying original
    df_work = df.copy()
    
    # Add range columns
    df_work["distance_range"] = df_work["Distance (KM)"].apply(get_distance_range)
    df_work["duration_range"] = df_work["Rental hour"].apply(get_duration_range)
    
    result = {
        "distance_ranges": {},
        "duration_ranges": {},
        "range_combinations": {}
    }
    
    # Analyze by distance ranges
    distance_ranges = ["<20km", "20-50km", "50-100km", ">=100km"]
    for dist_range in distance_ranges:
        range_data = df_work[df_work["distance_range"] == dist_range]
        if not range_data.empty:
            provider_stats = {}
            for provider in range_data["Car Cat"].unique():
                if pd.isna(provider):
                    continue
                provider_data = range_data[range_data["Car Cat"] == provider]
                provider_stats[provider] = {
                    "avg_cost": provider_data["Total"].mean() if "Total" in provider_data.columns else 0,
                    "min_cost": provider_data["Total"].min() if "Total" in provider_data.columns else 0,
                    "max_cost": provider_data["Total"].max() if "Total" in provider_data.columns else 0,
                    "rental_count": len(provider_data),
                    "popular_models": provider_data["Car model"].value_counts().head(3).to_dict() if "Car model" in provider_data.columns else {}
                }
            result["distance_ranges"][dist_range] = provider_stats
    
    # Analyze by duration ranges
    duration_ranges = ["<2 hours", "2-4 hours", "4-8 hours", ">=8 hours"]
    for dur_range in duration_ranges:
        range_data = df_work[df_work["duration_range"] == dur_range]
        if not range_data.empty:
            provider_stats = {}
            for provider in range_data["Car Cat"].unique():
                if pd.isna(provider):
                    continue
                provider_data = range_data[range_data["Car Cat"] == provider]
                provider_stats[provider] = {
                    "avg_cost": provider_data["Total"].mean() if "Total" in provider_data.columns else 0,
                    "min_cost": provider_data["Total"].min() if "Total" in provider_data.columns else 0,
                    "max_cost": provider_data["Total"].max() if "Total" in provider_data.columns else 0,
                    "rental_count": len(provider_data),
                    "popular_models": provider_data["Car model"].value_counts().head(3).to_dict() if "Car model" in provider_data.columns else {}
                }
            result["duration_ranges"][dur_range] = provider_stats
    
    # Analyze by range combinations
    for dist_range in distance_ranges:
        for dur_range in duration_ranges:
            range_data = df_work[
                (df_work["distance_range"] == dist_range) & 
                (df_work["duration_range"] == dur_range)
            ]
            if not range_data.empty:
                provider_stats = {}
                for provider in range_data["Car Cat"].unique():
                    if pd.isna(provider):
                        continue
                    provider_data = range_data[range_data["Car Cat"] == provider]
                    provider_stats[provider] = {
                        "avg_cost": provider_data["Total"].mean() if "Total" in provider_data.columns else 0,
                        "min_cost": provider_data["Total"].min() if "Total" in provider_data.columns else 0,
                        "max_cost": provider_data["Total"].max() if "Total" in provider_data.columns else 0,
                        "rental_count": len(provider_data),
                        "popular_models": provider_data["Car model"].value_counts().head(3).to_dict() if "Car model" in provider_data.columns else {}
                    }
                result["range_combinations"][(dist_range, dur_range)] = provider_stats
    
    return result


def get_range_specific_statistics(df, distance_range, duration_range):
    """
    Get statistics for a specific range combination.
    
    Args:
        df: Historical rental data DataFrame
        distance_range: Distance range string (e.g., "20-50km")
        duration_range: Duration range string (e.g., "2-4 hours")
        
    Returns:
        Dictionary with statistics for the specified range
    """
    if df is None or df.empty:
        return {}
    
    required_cols = ["Distance (KM)", "Rental hour", "Car Cat", "Total"]
    if not all(col in df.columns for col in required_cols):
        return {}
    
    df_work = df.copy()
    df_work["distance_range"] = df_work["Distance (KM)"].apply(get_distance_range)
    df_work["duration_range"] = df_work["Rental hour"].apply(get_duration_range)
    
    # Filter by ranges
    range_data = df_work[
        (df_work["distance_range"] == distance_range) & 
        (df_work["duration_range"] == duration_range)
    ]
    
    if range_data.empty:
        return {}
    
    # Calculate overall statistics
    stats = {
        "total_rentals": len(range_data),
        "avg_cost": range_data["Total"].mean() if "Total" in range_data.columns else 0,
        "min_cost": range_data["Total"].min() if "Total" in range_data.columns else 0,
        "max_cost": range_data["Total"].max() if "Total" in range_data.columns else 0,
        "providers": {}
    }
    
    # Calculate per-provider statistics
    for provider in range_data["Car Cat"].unique():
        if pd.isna(provider):
            continue
        provider_data = range_data[range_data["Car Cat"] == provider]
        stats["providers"][provider] = {
            "avg_cost": provider_data["Total"].mean() if "Total" in provider_data.columns else 0,
            "rental_count": len(provider_data),
            "popular_models": provider_data["Car model"].value_counts().head(3).to_dict() if "Car model" in provider_data.columns else {}
        }
    
    return stats


def get_preference_based_recommendations(distance, duration, user_preferences, df, is_weekend=False, top_n=5):
    """
    Get recommendations based on user preferences analyzed from historical data with range-based analysis
    
    Args:
        distance: Travel distance in km
        duration: Rental duration in hours
        user_preferences: User preferences from analyze_user_preferences()
        df: Historical rental data
        is_weekend: Whether this is a weekend trip
        top_n: Number of recommendations to return
        
    Returns:
        List of personalized recommendations with range insights
    """
    recommendations = []
    
    # Determine ranges for this trip
    distance_range = get_distance_range(distance)
    duration_range = get_duration_range(duration)
    
    # Get range-specific statistics
    range_stats = get_range_specific_statistics(df, distance_range, duration_range)
    
    # Get user profile
    profile = user_preferences.get("user_profile", {})
    preferred_providers = user_preferences.get("preferred_providers", [])
    preferred_models = user_preferences.get("preferred_car_models", [])
    
    # Create recommendations based on user preferences with range analysis
    for pref_provider in preferred_providers:
        provider_name = pref_provider["provider"]
        confidence = pref_provider.get("confidence", 0.8)
        
        # Get historical data for this provider
        provider_data = df[df["Car Cat"] == provider_name] if "Car Cat" in df.columns else pd.DataFrame()
        
        if not provider_data.empty:
            # Filter provider data by matching ranges for better accuracy
            provider_data_work = provider_data.copy()
            provider_data_work["distance_range"] = provider_data_work["Distance (KM)"].apply(get_distance_range) if "Distance (KM)" in provider_data_work.columns else None
            provider_data_work["duration_range"] = provider_data_work["Rental hour"].apply(get_duration_range) if "Rental hour" in provider_data_work.columns else None
            
            # Get range-matched data (weight this higher)
            range_matched_data = provider_data_work[
                (provider_data_work["distance_range"] == distance_range) & 
                (provider_data_work["duration_range"] == duration_range)
            ] if provider_data_work["distance_range"] is not None else pd.DataFrame()
            
            # Calculate cost based on historical data
            # Prefer range-matched data if available, otherwise use all provider data
            if not range_matched_data.empty and "Total" in range_matched_data.columns:
                range_avg_cost = range_matched_data["Total"].mean()
                range_rental_count = len(range_matched_data)
            else:
                range_avg_cost = None
                range_rental_count = 0
            
            avg_cost_per_km = provider_data["Cost per KM"].mean() if "Cost per KM" in provider_data.columns else 0.5
            avg_cost_per_hour = provider_data["Cost/HR"].mean() if "Cost/HR" in provider_data.columns else 10.0
            
            # Calculate estimated cost
            if provider_name in ["Getgo", "Car Club"]:
                # Per km + per hour pricing
                mileage_rate = 0.39 if provider_name == "Getgo" else 0.33
                mileage_cost = distance * mileage_rate
                duration_cost = duration * avg_cost_per_hour
                total_cost = mileage_cost + duration_cost
            else:
                # Per hour + fuel cost
                duration_cost = duration * avg_cost_per_hour
                fuel_cost = (distance / 110) * 20 if distance > 0 else 0
                total_cost = duration_cost + fuel_cost
            
            # Weekend surcharge
            if is_weekend:
                total_cost *= 1.2
            
            # Get preferred car model for this provider
            preferred_model = "Standard"
            for pref_model in preferred_models:
                if pref_model["model"] in provider_data["Car model"].values:
                    preferred_model = pref_model["model"]
                    break
            
            # Build range-specific reasoning
            range_reasoning = f"Optimal for {distance_range} trips."
            range_specific_reasoning = ""
            best_for_range = False
            
            if range_avg_cost is not None and range_rental_count > 0:
                cost_diff_pct = ((total_cost - range_avg_cost) / range_avg_cost * 100) if range_avg_cost > 0 else 0
                range_specific_reasoning = f"In your {distance_range} trips, {provider_name} averages ${range_avg_cost:.2f} ({range_rental_count} rentals). "
                if abs(cost_diff_pct) < 20:  # Within 20% of range average
                    range_specific_reasoning += f"This trip is {abs(cost_diff_pct):.0f}% {'above' if cost_diff_pct > 0 else 'below'} average."
                    best_for_range = True
                else:
                    range_specific_reasoning += f"This trip is {abs(cost_diff_pct):.0f}% {'above' if cost_diff_pct > 0 else 'below'} average."
            elif range_stats and provider_name in range_stats.get("providers", {}):
                provider_range_stats = range_stats["providers"][provider_name]
                range_avg_cost = provider_range_stats.get("avg_cost", 0)
                range_rental_count = provider_range_stats.get("rental_count", 0)
                if range_rental_count > 0:
                    cost_diff_pct = ((total_cost - range_avg_cost) / range_avg_cost * 100) if range_avg_cost > 0 else 0
                    range_specific_reasoning = f"In {distance_range} trips, {provider_name} averages ${range_avg_cost:.2f} ({range_rental_count} rentals). "
                    range_specific_reasoning += f"This trip is {abs(cost_diff_pct):.0f}% {'above' if cost_diff_pct > 0 else 'below'} average."
                    if abs(cost_diff_pct) < 20:
                        best_for_range = True
            
            # Combine reasoning
            base_reasoning = f"Based on your preference for {provider_name} ({pref_provider['reason']}). {range_reasoning}"
            
            recommendations.append({
                "provider": provider_name,
                "model": preferred_model,
                "total_cost": round(total_cost, 2),
                "confidence": confidence,
                "method": "User Preference Analysis",
                "reasoning": base_reasoning,
                "personalization_score": confidence,
                "range_insights": {
                    "distance_range": distance_range,
                    "duration_range": duration_range,
                    "range_specific_reasoning": range_specific_reasoning,
                    "best_for_range": best_for_range,
                    "range_average_cost": round(range_avg_cost, 2) if range_avg_cost is not None else None,
                    "range_rental_count": range_rental_count
                }
            })
    
    # If no preferred providers or insufficient data, create fallback recommendations
    if not recommendations:
        recommendations = create_fallback_recommendations(distance, duration, is_weekend)
        for rec in recommendations:
            rec["method"] = "Fallback (No Preference Data)"
            rec["personalization_score"] = 0.3
            rec["range_insights"] = {
                "distance_range": distance_range,
                "duration_range": duration_range,
                "range_specific_reasoning": "",
                "best_for_range": False,
                "range_average_cost": None,
                "range_rental_count": 0
            }
    
    # Sort by total cost and return top N
    recommendations.sort(key=lambda x: x["total_cost"])
    return recommendations[:top_n]


def get_enhanced_preference_recommendations(distance, duration, df, user_preferences=None, is_weekend=False, top_n=5, use_ollama=True, ollama_model="llama2"):
    """
    Get enhanced recommendations combining user preferences with Ollama analysis
    
    Args:
        distance: Travel distance in km
        duration: Rental duration in hours
        df: Historical rental data
        user_preferences: Optional user preferences (will be generated if not provided)
        is_weekend: Whether this is a weekend trip
        top_n: Number of recommendations to return
        use_ollama: Whether to use Ollama for analysis
        ollama_model: Ollama model to use
        
    Returns:
        List of enhanced personalized recommendations
    """
    # Get user preferences if not provided
    if user_preferences is None:
        if use_ollama:
            try:
                user_preferences = analyze_user_preferences(df, ollama_model)
            except Exception as e:
                print(f"Ollama preference analysis failed: {e}")
                user_preferences = create_fallback_user_preferences(prepare_user_data_summary(df))
        else:
            user_preferences = create_fallback_user_preferences(prepare_user_data_summary(df))
    
    # Get preference-based recommendations
    preference_recs = get_preference_based_recommendations(
        distance, duration, user_preferences, df, is_weekend, top_n
    )
    
    # Add user insights to recommendations
    insights = user_preferences.get("insights", [])
    recommendations = user_preferences.get("recommendations", [])
    
    # Enhance recommendations with user insights
    for rec in preference_recs:
        rec["user_insights"] = insights[:2]  # Add top 2 insights
        rec["personalized_recommendations"] = recommendations[:2]  # Add top 2 recommendations
    
    return preference_recs


# New functions for enhanced recommendations

def determine_rental_timing(date_str=None, time_str=None, start_time_str=None, end_time_str=None):
    """
    Parse date/time input and determine weekday/weekend automatically.
    
    Args:
        date_str: Date string in various formats (e.g., "2024-01-15", "Jan 15", "tomorrow", "next Monday")
        time_str: Time string (e.g., "10:00", "10am", "2pm")
        start_time_str: Start time for rental
        end_time_str: End time for rental
        
    Returns:
        Dictionary with:
        - rental_date: datetime object
        - is_weekend: boolean
        - day_name: string (Monday, Tuesday, etc.)
        - start_time: datetime if provided
        - end_time: datetime if provided
        - calculated_duration: hours if start/end times provided
    """
    result = {
        "rental_date": None,
        "is_weekend": False,
        "day_name": None,
        "start_time": None,
        "end_time": None,
        "calculated_duration": None,
    }
    
    today = datetime.now()
    
    # Parse date
    if date_str:
        date_str_lower = date_str.lower().strip()
        
        # Handle relative dates
        if "today" in date_str_lower:
            rental_date = today
        elif "tomorrow" in date_str_lower:
            rental_date = today + timedelta(days=1)
        elif "next week" in date_str_lower:
            rental_date = today + timedelta(days=7)
        else:
            # Try to parse various date formats
            date_formats = [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%B %d, %Y",
                "%b %d, %Y",
                "%d %B %Y",
                "%d %b %Y",
                "%Y/%m/%d",
            ]
            
            rental_date = None
            for fmt in date_formats:
                try:
                    rental_date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            # If still not parsed, try pandas
            if rental_date is None:
                try:
                    rental_date = pd.to_datetime(date_str)
                    if isinstance(rental_date, pd.Timestamp):
                        rental_date = rental_date.to_pydatetime()
                except:
                    rental_date = today
    else:
        rental_date = today
    
    result["rental_date"] = rental_date
    result["day_name"] = rental_date.strftime("%A")
    result["is_weekend"] = rental_date.weekday() >= 5  # Saturday = 5, Sunday = 6
    
    # Parse times
    def parse_time(time_input):
        """Parse time string to datetime"""
        if not time_input:
            return None
        
        time_input = time_input.lower().strip()
        
        # Handle formats like "10am", "2pm", "14:00", "10:30"
        time_patterns = [
            (r"(\d{1,2}):(\d{2})\s*(am|pm)?", lambda m: (int(m.group(1)), int(m.group(2)), m.group(3) or "")),
            (r"(\d{1,2})\s*(am|pm)", lambda m: (int(m.group(1)), 0, m.group(2))),
        ]
        
        for pattern, extractor in time_patterns:
            match = re.search(pattern, time_input)
            if match:
                hour, minute, ampm = extractor(match)
                if ampm == "pm" and hour != 12:
                    hour += 12
                elif ampm == "am" and hour == 12:
                    hour = 0
                return datetime.combine(rental_date.date(), datetime.min.time().replace(hour=hour, minute=minute))
        
        return None
    
    if start_time_str:
        result["start_time"] = parse_time(start_time_str)
    
    if end_time_str:
        result["end_time"] = parse_time(end_time_str)
    
    # Calculate duration if both start and end times provided
    if result["start_time"] and result["end_time"]:
        duration = (result["end_time"] - result["start_time"]).total_seconds() / 3600
        if duration < 0:  # End time is next day
            duration += 24
        result["calculated_duration"] = max(0.5, duration)  # Minimum 0.5 hours
    
    return result


def get_car_size_recommendation(passenger_count, space_requirements=""):
    """
    Map passenger count + space needs to car size categories.
    
    Args:
        passenger_count: Number of passengers
        space_requirements: String describing space needs (e.g., "luggage", "cargo", "comfortable")
        
    Returns:
        Dictionary with:
        - size_category: "compact", "mid-size", "full-size", "SUV", "van"
        - min_seats: minimum seats required
        - space_level: "minimal", "moderate", "spacious", "extra"
        - description: human-readable description
    """
    space_lower = space_requirements.lower() if space_requirements else ""
    
    # Determine space level
    if any(word in space_lower for word in ["large", "big", "lots", "many", "cargo", "moving"]):
        space_level = "extra"
    elif any(word in space_lower for word in ["luggage", "bags", "suitcases", "comfortable", "roomy"]):
        space_level = "spacious"
    elif any(word in space_lower for word in ["some", "moderate", "normal"]):
        space_level = "moderate"
    else:
        space_level = "minimal"
    
    # Determine car size based on passengers and space
    if passenger_count <= 2:
        if space_level in ["extra", "spacious"]:
            size_category = "mid-size"
            min_seats = 5
        else:
            size_category = "compact"
            min_seats = 4
    elif passenger_count <= 4:
        if space_level == "extra":
            size_category = "SUV"
            min_seats = 7
        elif space_level == "spacious":
            size_category = "full-size"
            min_seats = 5
        else:
            size_category = "mid-size"
            min_seats = 5
    elif passenger_count <= 6:
        if space_level in ["extra", "spacious"]:
            size_category = "SUV"
            min_seats = 7
        else:
            size_category = "full-size"
            min_seats = 5
    else:  # 7+ passengers
        size_category = "van"
        min_seats = 8
    
    descriptions = {
        "compact": "Compact car suitable for 1-2 passengers with minimal luggage",
        "mid-size": "Mid-size sedan suitable for 2-4 passengers with moderate space",
        "full-size": "Full-size sedan suitable for 4-5 passengers with comfortable space",
        "SUV": "SUV suitable for 4-7 passengers with spacious cargo area",
        "van": "Van suitable for 7+ passengers or large cargo needs",
    }
    
    return {
        "size_category": size_category,
        "min_seats": min_seats,
        "space_level": space_level,
        "description": descriptions.get(size_category, "Standard car"),
        "passenger_count": passenger_count,
        "space_requirements": space_requirements,
    }


def filter_recommendations_by_size(recommendations, size_requirements, df=None):
    """
    Filter recommendations based on car model size/capacity.
    
    Args:
        recommendations: List of recommendation dictionaries
        size_requirements: Dictionary from get_car_size_recommendation()
        df: Historical data DataFrame to infer car sizes
        
    Returns:
        Filtered list of recommendations with size suitability scores
    """
    if not size_requirements:
        return recommendations
    
    size_category = size_requirements.get("size_category", "mid-size")
    min_seats = size_requirements.get("min_seats", 5)
    space_level = size_requirements.get("space_level", "moderate")
    
    # Car model size mapping (common models)
    car_size_map = {
        # Compact
        "compact": ["Mazda 2", "Honda Fit", "Toyota Vios", "Nissan Almera", "Hyundai Accent"],
        # Mid-size
        "mid-size": ["Toyota Corolla", "Honda Civic", "Mazda 3", "Nissan Sentra", "Hyundai Elantra"],
        # Full-size
        "full-size": ["Toyota Camry", "Honda Accord", "Nissan Altima", "Hyundai Sonata"],
        # SUV
        "SUV": ["Honda Vezel", "Toyota RAV4", "Mazda CX-5", "Nissan X-Trail", "Hyundai Tucson", "Honda CR-V"],
        # Van
        "van": ["Toyota Wish", "Toyota Alphard", "Honda Odyssey", "Nissan Serena"],
    }
    
    # Reverse mapping: model -> size
    model_to_size = {}
    for size, models in car_size_map.items():
        for model in models:
            model_to_size[model.lower()] = size
    
    # Score and filter recommendations
    scored_recommendations = []
    for rec in recommendations:
        model = rec.get("model", "").lower()
        provider = rec.get("provider", "")
        
        # Try to infer size from model name
        inferred_size = None
        for size_key, models in car_size_map.items():
            for car_model in models:
                if car_model.lower() in model:
                    inferred_size = size_key
                    break
            if inferred_size:
                break
        
        # If not found, check historical data
        if not inferred_size and df is not None and "Car model" in df.columns:
            model_data = df[df["Car model"].str.lower().str.contains(model, na=False, case=False)]
            if not model_data.empty:
                # Infer from common patterns in model names
                model_name = model_data["Car model"].iloc[0].lower()
                if any(suv in model_name for suv in ["vezel", "rav4", "cx-5", "x-trail", "tucson", "cr-v"]):
                    inferred_size = "SUV"
                elif any(van in model_name for van in ["wish", "alphard", "odyssey", "serena"]):
                    inferred_size = "van"
                elif any(compact in model_name for compact in ["vios", "fit", "almera", "accent"]):
                    inferred_size = "compact"
                elif any(full in model_name for full in ["camry", "accord", "altima", "sonata"]):
                    inferred_size = "full-size"
                else:
                    inferred_size = "mid-size"  # Default
        
        # Calculate suitability score
        if inferred_size:
            size_hierarchy = {"compact": 1, "mid-size": 2, "full-size": 3, "SUV": 4, "van": 5}
            target_size = size_hierarchy.get(size_category, 2)
            actual_size = size_hierarchy.get(inferred_size, 2)
            
            # Score: 1.0 if exact match, 0.8 if one level off, 0.5 if two levels off, 0.2 otherwise
            size_diff = abs(target_size - actual_size)
            if size_diff == 0:
                suitability_score = 1.0
            elif size_diff == 1:
                suitability_score = 0.8
            elif size_diff == 2:
                suitability_score = 0.5
            else:
                suitability_score = 0.2
        else:
            # Unknown model - give moderate score
            suitability_score = 0.6
        
        rec["size_suitability"] = suitability_score
        rec["inferred_size"] = inferred_size or "unknown"
        scored_recommendations.append(rec)
    
    # Sort by suitability score (descending) then by cost
    scored_recommendations.sort(key=lambda x: (-x.get("size_suitability", 0), x.get("total_cost", 0)))
    
    # Filter out very unsuitable options (score < 0.3) unless no better options
    suitable = [r for r in scored_recommendations if r.get("size_suitability", 0) >= 0.3]
    if suitable:
        return suitable
    else:
        return scored_recommendations[:5]  # Return top 5 if all are unsuitable


def compare_pricing_models(distance, duration, is_weekend=False, pricing_config=None):
    """
    Compare mileage-included vs pay-per-km pricing models.
    
    Args:
        distance: Travel distance in km
        duration: Rental duration in hours
        is_weekend: Whether it's a weekend
        pricing_config: Dictionary with pricing configuration (from pricing_config.json)
        
    Returns:
        Dictionary with:
        - mileage_included_cost: estimated cost for mileage-included providers
        - pay_per_km_cost: estimated cost for pay-per-km providers
        - recommended_model: "mileage_included" or "pay_per_km"
        - reasoning: explanation of recommendation
        - cost_difference: difference in costs
    """
    # Load pricing config if not provided
    if pricing_config is None:
        try:
            with open("pricing_config.json", "r") as f:
                pricing_config = json.load(f)
        except:
            pricing_config = {}
    
    # Calculate mileage-included cost (Econ, Stand, Tribecar)
    # Average rates from config
    mileage_included_hour_rate = 0
    mileage_included_fuel_cost = 0
    mileage_included_count = 0
    
    for provider in ["Econ", "Stand", "Tribecar"]:
        if provider in pricing_config:
            config = pricing_config[provider]
            day_type = "weekend" if is_weekend else "weekday"
            
            hour_rate_key = f"hour_rate_{day_type}" if f"hour_rate_{day_type}" in config else "hour_rate"
            fuel_key = "fuel_rate" if "fuel_rate" in config else "usual_fuel_amount"
            
            hour_rate = config.get(hour_rate_key, config.get("hour_rate", 25.0))
            fuel_cost = config.get(fuel_key, 20.0)
            
            mileage_included_hour_rate += hour_rate
            mileage_included_fuel_cost += fuel_cost
            mileage_included_count += 1
    
    if mileage_included_count > 0:
        avg_hour_rate = mileage_included_hour_rate / mileage_included_count
        avg_fuel_cost = mileage_included_fuel_cost / mileage_included_count
        mileage_included_cost = (duration * avg_hour_rate) + avg_fuel_cost
    else:
        # Fallback
        mileage_included_cost = (duration * 25.0) + 20.0
    
    # Calculate pay-per-km cost (Getgo, Car Club)
    pay_per_km_hour_rate = 0
    pay_per_km_km_rate = 0
    pay_per_km_count = 0
    
    for provider in ["Getgo", "Car Club", "Getgo EV"]:
        if provider in pricing_config:
            config = pricing_config[provider]
            day_type = "weekend" if is_weekend else "weekday"
            
            hour_rate_key = f"hour_rate_{day_type}" if f"hour_rate_{day_type}" in config else "hour_rate"
            km_rate_key = f"km_rate_{day_type}" if f"km_rate_{day_type}" in config else "mileage_rate"
            
            hour_rate = config.get(hour_rate_key, config.get("hour_rate", 10.0))
            km_rate = config.get(km_rate_key, config.get("mileage_rate", 0.39))
            
            pay_per_km_hour_rate += hour_rate
            pay_per_km_km_rate += km_rate
            pay_per_km_count += 1
    
    if pay_per_km_count > 0:
        avg_hour_rate = pay_per_km_hour_rate / pay_per_km_count
        avg_km_rate = pay_per_km_km_rate / pay_per_km_count
        pay_per_km_cost = (duration * avg_hour_rate) + (distance * avg_km_rate)
    else:
        # Fallback
        pay_per_km_cost = (duration * 10.0) + (distance * 0.39)
    
    # Determine recommendation
    cost_difference = abs(mileage_included_cost - pay_per_km_cost)
    
    if distance < 50:
        # Short trips: prefer mileage-included
        recommended_model = "mileage_included"
        reasoning = f"For short trips (<50km), mileage-included pricing is typically better. Estimated savings: ${cost_difference:.2f}"
    elif distance > 100:
        # Long trips: prefer pay-per-km if cheaper
        if pay_per_km_cost < mileage_included_cost:
            recommended_model = "pay_per_km"
            reasoning = f"For long trips (>100km), pay-per-km pricing is more economical. Estimated savings: ${cost_difference:.2f}"
        else:
            recommended_model = "mileage_included"
            reasoning = f"For long trips (>100km), mileage-included pricing is still better. Estimated savings: ${cost_difference:.2f}"
    else:
        # Medium trips: compare
        if pay_per_km_cost < mileage_included_cost:
            recommended_model = "pay_per_km"
            reasoning = f"For medium trips (50-100km), pay-per-km pricing is slightly better. Estimated savings: ${cost_difference:.2f}"
        else:
            recommended_model = "mileage_included"
            reasoning = f"For medium trips (50-100km), mileage-included pricing is slightly better. Estimated savings: ${cost_difference:.2f}"
    
    return {
        "mileage_included_cost": mileage_included_cost,
        "pay_per_km_cost": pay_per_km_cost,
        "recommended_model": recommended_model,
        "reasoning": reasoning,
        "cost_difference": cost_difference,
    }


# ============================================================================
# Rental Pattern Prediction Functions
# ============================================================================

def analyze_historical_patterns(df):
    """
    Extract time-based patterns from historical rental data.
    
    Args:
        df: DataFrame with rental data
        
    Returns:
        Dictionary with pattern information:
        - day_of_week_patterns: rental frequency by day of week
        - monthly_patterns: rental frequency by month
        - seasonal_patterns: seasonal variations
        - provider_patterns: provider usage patterns
        - avg_rental_frequency: average rentals per week/month
    """
    if df.empty or "Date" not in df.columns:
        return {"error": "Insufficient data for pattern analysis"}
    
    # Ensure Date is datetime
    df_copy = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_copy["Date"]):
        df_copy["Date"] = pd.to_datetime(df_copy["Date"])
    
    # Filter out calculator-generated records
    if "Car model" in df_copy.columns:
        df_copy = df_copy[df_copy["Car model"] != "Calculator Generated"]
    
    if df_copy.empty:
        return {"error": "No valid rental data for pattern analysis"}
    
    # Extract date features
    df_copy["DayOfWeek"] = df_copy["Date"].dt.dayofweek  # 0=Monday, 6=Sunday
    df_copy["Month"] = df_copy["Date"].dt.month
    df_copy["Year"] = df_copy["Date"].dt.year
    df_copy["IsWeekend"] = (df_copy["DayOfWeek"] >= 5).astype(int)
    
    patterns = {
        "day_of_week_patterns": {},
        "monthly_patterns": {},
        "seasonal_patterns": {},
        "provider_patterns": {},
        "avg_rental_frequency": {}
    }
    
    # Day of week patterns
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_counts = df_copy["DayOfWeek"].value_counts().sort_index()
    for day_num, count in day_counts.items():
        patterns["day_of_week_patterns"][day_names[day_num]] = {
            "count": int(count),
            "percentage": float((count / len(df_copy)) * 100)
        }
    
    # Monthly patterns
    month_counts = df_copy["Month"].value_counts().sort_index()
    for month_num, count in month_counts.items():
        month_name = pd.Timestamp(2022, month_num, 1).strftime("%B")
        patterns["monthly_patterns"][month_name] = {
            "count": int(count),
            "percentage": float((count / len(df_copy)) * 100)
        }
    
    # Seasonal patterns (group months into seasons)
    season_mapping = {
        12: "Winter", 1: "Winter", 2: "Winter",
        3: "Spring", 4: "Spring", 5: "Spring",
        6: "Summer", 7: "Summer", 8: "Summer",
        9: "Fall", 10: "Fall", 11: "Fall"
    }
    df_copy["Season"] = df_copy["Month"].map(season_mapping)
    season_counts = df_copy["Season"].value_counts()
    for season, count in season_counts.items():
        patterns["seasonal_patterns"][season] = {
            "count": int(count),
            "percentage": float((count / len(df_copy)) * 100)
        }
    
    # Provider patterns
    if "Car Cat" in df_copy.columns:
        provider_counts = df_copy["Car Cat"].value_counts()
        for provider, count in provider_counts.items():
            if pd.notna(provider):
                patterns["provider_patterns"][provider] = {
                    "count": int(count),
                    "percentage": float((count / len(df_copy)) * 100)
                }
    
    # Calculate average rental frequency
    date_range = (df_copy["Date"].max() - df_copy["Date"].min()).days
    if date_range > 0:
        total_rentals = len(df_copy)
        patterns["avg_rental_frequency"] = {
            "per_week": float((total_rentals / date_range) * 7),
            "per_month": float((total_rentals / date_range) * 30),
            "total_days": int(date_range),
            "total_rentals": int(total_rentals)
        }
    
    return patterns


def create_time_series_model(df):
    """
    Create a simple time series model for rental frequency prediction.
    Uses moving averages and trend analysis.
    
    Args:
        df: DataFrame with rental data
        
    Returns:
        Dictionary with model parameters and predictions
    """
    if df.empty or "Date" not in df.columns:
        return {"error": "Insufficient data for time series model"}
    
    df_copy = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_copy["Date"]):
        df_copy["Date"] = pd.to_datetime(df_copy["Date"])
    
    # Filter out calculator-generated records
    if "Car model" in df_copy.columns:
        df_copy = df_copy[df_copy["Car model"] != "Calculator Generated"]
    
    if df_copy.empty:
        return {"error": "No valid rental data for time series model"}
    
    # Group by date to get daily rental counts
    df_copy["DateOnly"] = df_copy["Date"].dt.date
    daily_counts = df_copy.groupby("DateOnly").size().reset_index(name="Rentals")
    daily_counts["DateOnly"] = pd.to_datetime(daily_counts["DateOnly"])
    daily_counts = daily_counts.sort_values("DateOnly")
    
    if len(daily_counts) < 7:
        return {"error": "Insufficient data points for time series analysis"}
    
    # Calculate moving averages
    daily_counts["MA_7"] = daily_counts["Rentals"].rolling(window=7, min_periods=1).mean()
    daily_counts["MA_30"] = daily_counts["Rentals"].rolling(window=min(30, len(daily_counts)), min_periods=1).mean()
    
    # Calculate trend (simple linear regression)
    x = np.arange(len(daily_counts))
    y = daily_counts["Rentals"].values
    slope, intercept = np.polyfit(x, y, 1)
    
    # Calculate average rental rate
    avg_daily_rentals = daily_counts["Rentals"].mean()
    avg_weekly_rentals = avg_daily_rentals * 7
    avg_monthly_rentals = avg_daily_rentals * 30
    
    return {
        "avg_daily_rentals": float(avg_daily_rentals),
        "avg_weekly_rentals": float(avg_weekly_rentals),
        "avg_monthly_rentals": float(avg_monthly_rentals),
        "trend_slope": float(slope),
        "trend_intercept": float(intercept),
        "recent_ma_7": float(daily_counts["MA_7"].iloc[-1]) if len(daily_counts) > 0 else 0,
        "recent_ma_30": float(daily_counts["MA_30"].iloc[-1]) if len(daily_counts) > 0 else 0,
        "total_days": len(daily_counts)
    }


def generate_prediction_reasoning_with_ollama(df, prediction_result, model_name="llama2"):
    """
    Generate AI reasoning for rental predictions using Ollama LLM.
    
    Args:
        df: Historical rental data DataFrame
        prediction_result: Dictionary containing prediction results
        model_name: Ollama model to use (default: llama2)
    
    Returns:
        Dictionary with reasoning and insights, or None if Ollama fails
    """
    try:
        # Prepare summary of historical data
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_copy["Date"]):
            df_copy["Date"] = pd.to_datetime(df_copy["Date"])
        
        # Filter out calculator-generated records
        if "Car model" in df_copy.columns:
            df_copy = df_copy[df_copy["Car model"] != "Calculator Generated"]
        
        if df_copy.empty:
            return None
        
        # Calculate historical statistics
        total_rentals = len(df_copy)
        avg_cost = df_copy["Total"].mean() if "Total" in df_copy.columns else 0
        avg_distance = df_copy["Distance (KM)"].mean() if "Distance (KM)" in df_copy.columns else 0
        avg_duration = df_copy["Rental hour"].mean() if "Rental hour" in df_copy.columns else 0
        
        # Day of week patterns
        df_copy["DayOfWeek"] = df_copy["Date"].dt.dayofweek
        weekday_rentals = len(df_copy[df_copy["DayOfWeek"] < 5])
        weekend_rentals = len(df_copy[df_copy["DayOfWeek"] >= 5])
        
        # Provider preferences
        provider_counts = {}
        if "Provider" in df_copy.columns:
            provider_counts = df_copy["Provider"].value_counts().to_dict()
        
        # Extract prediction data
        date_range = prediction_result.get("date_range", {})
        total_predicted = prediction_result.get("rental_frequency", {}).get("total", 0)
        total_spending = prediction_result.get("total_spending", 0)
        daily_predictions = prediction_result.get("daily_predictions", [])
        
        # Count predicted rental days
        rental_threshold = 0.3
        predicted_rental_days = sum(1 for p in daily_predictions if p.get("rental_probability", 0) >= rental_threshold)
        
        # Prepare prompt for Ollama
        prompt = f"""You are an expert car rental analyst. Analyze the following rental prediction data and provide intelligent reasoning about the predictions.

HISTORICAL DATA SUMMARY:
- Total historical rentals: {total_rentals}
- Average cost per rental: ${avg_cost:.2f}
- Average distance: {avg_distance:.1f} km
- Average duration: {avg_duration:.1f} hours
- Weekday rentals: {weekday_rentals} ({weekday_rentals/max(1,total_rentals)*100:.1f}%)
- Weekend rentals: {weekend_rentals} ({weekend_rentals/max(1,total_rentals)*100:.1f}%)
- Provider usage: {provider_counts}

PREDICTION SUMMARY:
- Date range: {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')} ({date_range.get('days', 0)} days)
- Total predicted rentals: {total_predicted}
- Predicted rental days: {predicted_rental_days}
- Total predicted spending: ${total_spending:.2f}
- Prediction method: {prediction_result.get('method', 'Unknown')}
- Confidence: {prediction_result.get('confidence', 0)*100:.0f}%

Provide:
1. A brief analysis of the prediction patterns (2-3 sentences)
2. Key insights about when rentals are most likely (mention specific days/patterns if notable)
3. Expected rental behavior explanation based on historical patterns
4. Any notable trends or anomalies

Keep the response concise, practical, and focused on actionable insights. Use bullet points for clarity."""

        # Use chat API for better structured responses
        messages = [
            {
                "role": "system",
                "content": "You are a car rental analyst providing concise, data-driven insights about rental predictions. Focus on practical patterns and actionable information."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        reasoning = call_ollama_chat_api(messages, model_name)
        
        return {
            "reasoning": reasoning,
            "model_used": model_name,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        print(f"Ollama reasoning generation failed: {e}")
        return None


def predict_with_ml_patterns(df, date_range, granularity="weekly"):
    """
    Use ML to predict rental patterns over a date range.
    
    Args:
        df: DataFrame with historical rental data
        date_range: Tuple of (start_date, end_date) as datetime objects
        granularity: "daily", "weekly", or "monthly"
        
    Returns:
        Dictionary with ML predictions
    """
    if df.empty or "Date" not in df.columns:
        return {"error": "Insufficient data for ML pattern prediction"}
    
    df_copy = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_copy["Date"]):
        df_copy["Date"] = pd.to_datetime(df_copy["Date"])
    
    # Filter out calculator-generated records
    if "Car model" in df_copy.columns:
        df_copy = df_copy[df_copy["Car model"] != "Calculator Generated"]
    
    if df_copy.empty or len(df_copy) < 10:
        return {"error": "Insufficient data for ML prediction (need at least 10 records)"}
    
    try:
        from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        
        # Prepare features from historical data
        df_copy["Month"] = df_copy["Date"].dt.month
        df_copy["DayOfWeek"] = df_copy["Date"].dt.dayofweek
        df_copy["DayOfMonth"] = df_copy["Date"].dt.day
        df_copy["IsWeekend"] = (df_copy["DayOfWeek"] >= 5).astype(int)
        
        # Calculate days since last rental for each record
        df_copy = df_copy.sort_values("Date")
        df_copy["DaysSinceLastRental"] = df_copy["Date"].diff().dt.days.fillna(0)
        
        # Features for training
        feature_cols = ["Month", "DayOfWeek", "DayOfMonth", "IsWeekend", "DaysSinceLastRental"]
        if "Distance (KM)" in df_copy.columns:
            feature_cols.append("Distance (KM)")
        if "Rental hour" in df_copy.columns:
            feature_cols.append("Rental hour")
        
        X = df_copy[feature_cols].fillna(0).values
        y_rental = np.ones(len(df_copy))  # All are rentals (1)
        
        # Train classifier for rental probability
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # For regression targets (distance, cost, duration)
        y_distance = df_copy["Distance (KM)"].fillna(df_copy["Distance (KM)"].mean()).values if "Distance (KM)" in df_copy.columns else np.zeros(len(df_copy))
        y_cost = df_copy["Total"].fillna(df_copy["Total"].mean()).values if "Total" in df_copy.columns else np.zeros(len(df_copy))
        y_duration = df_copy["Rental hour"].fillna(df_copy["Rental hour"].mean()).values if "Rental hour" in df_copy.columns else np.zeros(len(df_copy))
        
        # Train models
        rf_distance = RandomForestRegressor(n_estimators=50, random_state=42)
        rf_cost = RandomForestRegressor(n_estimators=50, random_state=42)
        rf_duration = RandomForestRegressor(n_estimators=50, random_state=42)
        
        rf_distance.fit(X_scaled, y_distance)
        rf_cost.fit(X_scaled, y_cost)
        rf_duration.fit(X_scaled, y_duration)
        
        # Generate predictions for date range
        start_date, end_date = date_range
        predictions = []
        current_date = start_date
        
        while current_date <= end_date:
            # Prepare features for this date
            month = current_date.month
            day_of_week = current_date.weekday()
            day_of_month = current_date.day
            is_weekend = 1 if day_of_week >= 5 else 0
            
            # Estimate days since last rental (use average from historical)
            avg_days_between = df_copy["DaysSinceLastRental"].mean() if len(df_copy) > 1 else 7
            
            features = np.array([[
                month,
                day_of_week,
                day_of_month,
                is_weekend,
                avg_days_between
            ]])
            
            # Add average distance and duration if available
            if "Distance (KM)" in df_copy.columns:
                features = np.append(features, [[df_copy["Distance (KM)"].mean()]], axis=1)
            if "Rental hour" in df_copy.columns:
                features = np.append(features, [[df_copy["Rental hour"].mean()]], axis=1)
            
            features_scaled = scaler.transform(features)
            
            # Predict
            pred_distance = rf_distance.predict(features_scaled)[0]
            pred_cost = rf_cost.predict(features_scaled)[0]
            pred_duration = rf_duration.predict(features_scaled)[0]
            
            # Calculate rental probability based on historical patterns
            # Check if similar dates had rentals
            similar_dates = df_copy[
                (df_copy["Date"].dt.month == month) &
                (df_copy["Date"].dt.weekday == day_of_week)
            ]
            rental_probability = len(similar_dates) / max(1, len(df_copy) / 7)  # Normalize
            rental_probability = min(1.0, rental_probability)
            
            predictions.append({
                "date": current_date,
                "rental_probability": float(rental_probability),
                "predicted_distance": float(max(0, pred_distance)),
                "predicted_cost": float(max(0, pred_cost)),
                "predicted_duration": float(max(0, pred_duration))
            })
            
            # Move to next period based on granularity
            if granularity == "daily":
                current_date += timedelta(days=1)
            elif granularity == "weekly":
                current_date += timedelta(days=7)
            elif granularity == "monthly":
                # Move to first day of next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1, day=1)
        
        return {
            "predictions": predictions,
            "granularity": granularity,
            "method": "ML"
        }
        
    except ImportError:
        return {"error": "scikit-learn not available for ML prediction"}
    except Exception as e:
        return {"error": f"ML prediction error: {str(e)}"}


def predict_rental_patterns(df, start_date, end_date, granularity="weekly", use_ollama_reasoning=False, ollama_model="llama2"):
    """
    Main function to predict rental patterns over a date range.
    Uses hybrid approach: ML + Statistical + Time Series + Ollama AI Reasoning.
    
    Args:
        df: DataFrame with historical rental data
        start_date: Start date (datetime or string)
        end_date: End date (datetime or string)
        granularity: "daily", "weekly", or "monthly"
        use_ollama_reasoning: Whether to use Ollama LLM for prediction reasoning (default: False)
        ollama_model: Ollama model to use for reasoning (default: "llama2")
        
    Returns:
        Dictionary with comprehensive predictions:
        - rental_frequency: predicted rentals per period
        - total_spending: predicted total spending
        - avg_distance: average distance per rental
        - provider_preferences: probability distribution of providers
        - peak_periods: periods with highest rental probability
        - confidence: confidence score
        - ai_reasoning: AI-generated reasoning and insights (if use_ollama_reasoning=True)
    """
    if df.empty:
        return {"error": "No data available for prediction"}
    
    # Convert dates to datetime
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)
    
    if start_date >= end_date:
        return {"error": "Start date must be before end date"}
    
    # Get historical patterns (statistical baseline)
    patterns = analyze_historical_patterns(df)
    if "error" in patterns:
        return patterns
    
    # Get time series model
    ts_model = create_time_series_model(df)
    if "error" in ts_model:
        # Use simple average if time series fails
        ts_model = {"avg_daily_rentals": 0.1, "avg_weekly_rentals": 0.7, "avg_monthly_rentals": 3.0}
    
    # Get ML predictions
    ml_predictions = predict_with_ml_patterns(df, (start_date, end_date), granularity)
    
    # Calculate date range statistics
    date_range_days = (end_date - start_date).days
    date_range_weeks = date_range_days / 7
    date_range_months = date_range_days / 30
    
    # Combine predictions (hybrid approach)
    period_rental_distribution = None  # Will store period-specific rental counts if using ML
    if "error" not in ml_predictions and "predictions" in ml_predictions:
        # Use ML predictions
        ml_preds = ml_predictions["predictions"]
        
        # Calculate total predicted rentals (sum of probabilities)
        total_predicted_rentals_raw = sum(p["rental_probability"] for p in ml_preds)
        total_predicted_spending = sum(p["predicted_cost"] * p["rental_probability"] for p in ml_preds)
        total_predicted_distance = sum(p["predicted_distance"] * p["rental_probability"] for p in ml_preds)
        
        # Round total rentals to whole number
        total_predicted_rentals = round(total_predicted_rentals_raw)
        
        # Distribute rounded rentals across periods proportionally using largest remainder method
        if total_predicted_rentals > 0 and len(ml_preds) > 0:
            # Calculate proportional allocation
            total_prob = sum(p["rental_probability"] for p in ml_preds)
            if total_prob > 0:
                # Allocate rentals proportionally
                period_allocations = []
                for p in ml_preds:
                    proportional_share = (p["rental_probability"] / total_prob) * total_predicted_rentals
                    period_allocations.append({
                        "date": p["date"],
                        "rentals": int(proportional_share),  # Integer part
                        "remainder": proportional_share - int(proportional_share),  # Fractional part for rounding
                        "predicted_cost": p["predicted_cost"],
                        "predicted_distance": p["predicted_distance"]
                    })
                
                # Use largest remainder method to distribute remaining rentals
                allocated_total = sum(a["rentals"] for a in period_allocations)
                remaining = total_predicted_rentals - allocated_total
                
                if remaining > 0:
                    # Sort by remainder (largest first) and allocate remaining rentals
                    period_allocations.sort(key=lambda x: x["remainder"], reverse=True)
                    for i in range(int(remaining)):
                        period_allocations[i]["rentals"] += 1
                
                # Create distribution dictionary keyed by date string
                period_rental_distribution = {
                    a["date"].strftime("%Y-%m-%d"): a["rentals"] for a in period_allocations
                }
                
                # Recalculate spending and distance based on actual rental distribution
                total_predicted_spending = sum(
                    a["predicted_cost"] * a["rentals"] for a in period_allocations
                )
                total_predicted_distance = sum(
                    a["predicted_distance"] * a["rentals"] for a in period_allocations
                )
        else:
            # No rentals predicted, set spending and distance to 0
            total_predicted_spending = 0.0
            total_predicted_distance = 0.0
        
        avg_distance = total_predicted_distance / max(1, total_predicted_rentals) if total_predicted_rentals > 0 else 0.0
        
        # Find peak periods
        sorted_preds = sorted(ml_preds, key=lambda x: x["rental_probability"], reverse=True)
        peak_periods = [
            {
                "date": p["date"].strftime("%Y-%m-%d"),
                "probability": p["rental_probability"]
            }
            for p in sorted_preds[:5]
        ]
    else:
        # Fallback to statistical approach
        if granularity == "daily":
            total_predicted_rentals_raw = ts_model["avg_daily_rentals"] * date_range_days
        elif granularity == "weekly":
            total_predicted_rentals_raw = ts_model["avg_weekly_rentals"] * date_range_weeks
        else:  # monthly
            total_predicted_rentals_raw = ts_model["avg_monthly_rentals"] * date_range_months
        
        # Round total rentals to whole number
        total_predicted_rentals = round(total_predicted_rentals_raw)
        
        # Estimate spending and distance from historical averages
        if "Total" in df.columns and "Distance (KM)" in df.columns:
            avg_cost = df[df["Car model"] != "Calculator Generated"]["Total"].mean() if "Car model" in df.columns else df["Total"].mean()
            avg_dist = df[df["Car model"] != "Calculator Generated"]["Distance (KM)"].mean() if "Car model" in df.columns else df["Distance (KM)"].mean()
        else:
            avg_cost = 50.0  # Fallback
            avg_dist = 50.0   # Fallback
        
        total_predicted_spending = total_predicted_rentals * avg_cost
        total_predicted_distance = total_predicted_rentals * avg_dist
        avg_distance = avg_dist
        
        peak_periods = []
    
    # Provider preferences from historical patterns
    provider_preferences = {}
    if "provider_patterns" in patterns:
        total_provider_count = sum(p["count"] for p in patterns["provider_patterns"].values())
        for provider, stats in patterns["provider_patterns"].items():
            provider_preferences[provider] = {
                "probability": stats["percentage"] / 100,
                "expected_usage": (stats["percentage"] / 100) * total_predicted_rentals
            }
    
    # Calculate confidence
    data_points = len(df[df["Car model"] != "Calculator Generated"]) if "Car model" in df.columns else len(df)
    confidence = min(1.0, data_points / 50)  # Max confidence at 50+ records
    
    # Calculate frequency per period
    if granularity == "daily":
        frequency_per_period = total_predicted_rentals / max(1, date_range_days)
    elif granularity == "weekly":
        frequency_per_period = total_predicted_rentals / max(1, date_range_weeks)
    else:  # monthly
        frequency_per_period = total_predicted_rentals / max(1, date_range_months)
    
    # Always generate daily predictions for detailed view
    daily_predictions = []
    if "error" not in ml_predictions and "predictions" in ml_predictions:
        # Use ML daily predictions
        daily_ml_predictions = predict_with_ml_patterns(df, (start_date, end_date), "daily")
        if "error" not in daily_ml_predictions and "predictions" in daily_ml_predictions:
            for pred in daily_ml_predictions["predictions"]:
                daily_predictions.append({
                    "date": pred["date"].strftime("%Y-%m-%d"),
                    "day_name": pred["date"].strftime("%A"),
                    "rental_probability": pred["rental_probability"],
                    "predicted_duration": pred.get("predicted_duration", 0.0),
                    "predicted_distance": pred.get("predicted_distance", 0.0),
                    "predicted_cost": pred.get("predicted_cost", 0.0)
                })
    else:
        # Fallback: generate simple daily predictions based on averages
        df_fallback = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_fallback["Date"]):
            df_fallback["Date"] = pd.to_datetime(df_fallback["Date"])
        
        # Filter out calculator-generated records
        if "Car model" in df_fallback.columns:
            df_fallback = df_fallback[df_fallback["Car model"] != "Calculator Generated"]
        
        current_date = start_date
        avg_duration = df_fallback["Rental hour"].mean() if "Rental hour" in df_fallback.columns else 0.0
        avg_distance = df_fallback["Distance (KM)"].mean() if "Distance (KM)" in df_fallback.columns else 0.0
        avg_cost = df_fallback["Total"].mean() if "Total" in df_fallback.columns else 0.0
        
        # Calculate average rental frequency
        if granularity == "daily":
            avg_rentals_per_day = ts_model.get("avg_daily_rentals", 0.1)
        elif granularity == "weekly":
            avg_rentals_per_day = ts_model.get("avg_weekly_rentals", 0.7) / 7
        else:
            avg_rentals_per_day = ts_model.get("avg_monthly_rentals", 3.0) / 30
        
        while current_date <= end_date:
            # Simple probability based on day of week patterns
            day_of_week = current_date.weekday()
            is_weekend = 1 if day_of_week >= 5 else 0
            
            # Check historical patterns for this day of week
            similar_days = df_fallback[df_fallback["Date"].dt.weekday == day_of_week]
            if len(similar_days) > 0 and len(df_fallback) > 0:
                rental_probability = min(1.0, len(similar_days) / max(1, len(df_fallback) / 7))
            else:
                rental_probability = avg_rentals_per_day
            
            daily_predictions.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "day_name": current_date.strftime("%A"),
                "rental_probability": float(rental_probability),
                "predicted_duration": float(avg_duration),
                "predicted_distance": float(avg_distance),
                "predicted_cost": float(avg_cost)
            })
            current_date += timedelta(days=1)
    
    # Prepare result dictionary
    result = {
        "rental_frequency": {
            "total": int(total_predicted_rentals),  # Return as integer
            "per_period": float(frequency_per_period),
            "granularity": granularity
        },
        "total_spending": float(total_predicted_spending),
        "avg_distance": float(avg_distance),
        "provider_preferences": provider_preferences,
        "peak_periods": peak_periods,
        "confidence": float(confidence),
        "date_range": {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "days": int(date_range_days)
        },
        "method": "ML" if "error" not in ml_predictions else "Statistical",
        "period_rental_distribution": period_rental_distribution,  # Period-specific rental counts
        "daily_predictions": daily_predictions  # Daily predictions with dates and duration
    }
    
    # Generate AI reasoning using Ollama if requested
    if use_ollama_reasoning:
        try:
            ai_reasoning = generate_prediction_reasoning_with_ollama(df, result, ollama_model)
            if ai_reasoning:
                result["ai_reasoning"] = ai_reasoning
        except Exception as e:
            print(f"Failed to generate Ollama reasoning: {e}")
            # Continue without reasoning - don't fail the entire prediction
    
    return result


# ============================================================================
# Rental Possibility Prediction Functions
# ============================================================================

def extract_situation_features(situation, target_date, df=None):
    """
    Extract features from situation dictionary and target date for ML model.
    
    Args:
        situation: Dictionary with:
            - distance: float (optional)
            - duration: float (optional)
            - is_weekend: bool (optional)
            - holiday: bool (optional)
            - special_event: str (optional)
            - weather: str (optional)
            - personal_schedule: str (optional, "Free", "Busy", "Maybe")
        target_date: datetime object
        df: DataFrame for historical context (optional)
        
    Returns:
        Feature vector as numpy array
    """
    # Date features
    month = target_date.month
    day_of_week = target_date.weekday()  # 0=Monday, 6=Sunday
    day_of_month = target_date.day
    is_weekend = 1 if day_of_week >= 5 else 0
    
    # Trip features
    distance = situation.get("distance", 0.0) if situation else 0.0
    duration = situation.get("duration", 0.0) if situation else 0.0
    
    # Contextual features
    holiday = 1 if (situation and situation.get("holiday", False)) else 0
    special_event = 1 if (situation and situation.get("special_event", "")) else 0
    
    # Weather encoding (if provided)
    weather_map = {"sunny": 1, "rainy": 2, "cloudy": 3, "stormy": 4}
    weather = 0
    if situation and "weather" in situation:
        weather = weather_map.get(situation["weather"].lower(), 0)
    
    # Personal schedule encoding
    schedule_map = {"Free": 1, "Maybe": 0.5, "Busy": 0}
    personal_schedule = 0.5  # Default
    if situation and "personal_schedule" in situation:
        personal_schedule = schedule_map.get(situation["personal_schedule"], 0.5)
    
    # Historical context features (if df provided)
    days_since_last_rental = 0
    recent_rental_frequency = 0
    similar_date_rental_count = 0
    
    if df is not None and not df.empty and "Date" in df.columns:
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_copy["Date"]):
            df_copy["Date"] = pd.to_datetime(df_copy["Date"])
        
        # Filter out calculator-generated records
        if "Car model" in df_copy.columns:
            df_copy = df_copy[df_copy["Car model"] != "Calculator Generated"]
        
        if not df_copy.empty:
            # Days since last rental
            last_rental_date = df_copy["Date"].max()
            days_since_last_rental = (target_date - last_rental_date).days
            
            # Recent rental frequency (rentals in last 30 days)
            recent_cutoff = target_date - timedelta(days=30)
            recent_rentals = df_copy[df_copy["Date"] >= recent_cutoff]
            recent_rental_frequency = len(recent_rentals) / 30.0  # Normalize to per day
            
            # Similar date rentals (same day of week, same month)
            similar_rentals = df_copy[
                (df_copy["Date"].dt.weekday == day_of_week) &
                (df_copy["Date"].dt.month == month)
            ]
            similar_date_rental_count = len(similar_rentals)
    
    # Combine all features
    features = np.array([[
        month,
        day_of_week,
        day_of_month,
        is_weekend,
        distance,
        duration,
        holiday,
        special_event,
        weather,
        personal_schedule,
        days_since_last_rental,
        recent_rental_frequency,
        similar_date_rental_count
    ]])
    
    return features


def create_possibility_classifier(df):
    """
    Create a binary classifier to predict rental possibility.
    
    Args:
        df: DataFrame with historical rental data
        
    Returns:
        Tuple of (model, scaler) or None if insufficient data
    """
    if df.empty or "Date" not in df.columns or len(df) < 10:
        return None, None
    
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_copy["Date"]):
            df_copy["Date"] = pd.to_datetime(df_copy["Date"])
        
        # Filter out calculator-generated records
        if "Car model" in df_copy.columns:
            df_copy = df_copy[df_copy["Car model"] != "Calculator Generated"]
        
        if df_copy.empty or len(df_copy) < 10:
            return None, None
        
        # Create training data: for each rental date, create features
        # We'll use actual rental dates as positive examples (1)
        # And generate negative examples from dates without rentals
        features_list = []
        labels_list = []
        
        # Positive examples (actual rentals)
        for _, row in df_copy.iterrows():
            rental_date = row["Date"]
            situation = {
                "distance": row.get("Distance (KM)", 0),
                "duration": row.get("Rental hour", 0),
                "is_weekend": row.get("Weekday/weekend") == "weekend" if "Weekday/weekend" in row else False
            }
            features = extract_situation_features(situation, rental_date, df_copy)
            features_list.append(features[0])
            labels_list.append(1)  # Rental occurred
        
        # Generate negative examples (dates without rentals)
        # Sample dates from the date range that don't have rentals
        date_range = (df_copy["Date"].max() - df_copy["Date"].min()).days
        rental_dates_set = set(df_copy["Date"].dt.date)
        
        negative_count = min(len(features_list), date_range - len(rental_dates_set))
        negative_count = max(10, negative_count)  # At least 10 negative examples
        
        date_range_start = df_copy["Date"].min().date()
        negative_added = 0
        current_date = date_range_start
        
        while negative_added < negative_count and current_date <= df_copy["Date"].max().date():
            if current_date not in rental_dates_set:
                # Create a random situation for this date
                situation = {
                    "distance": np.random.uniform(20, 100),
                    "duration": np.random.uniform(2, 6),
                    "is_weekend": pd.Timestamp(current_date).weekday() >= 5
                }
                features = extract_situation_features(situation, pd.Timestamp(current_date), df_copy)
                features_list.append(features[0])
                labels_list.append(0)  # No rental
                negative_added += 1
            current_date += timedelta(days=1)
        
        if len(features_list) < 10:
            return None, None
        
        # Train classifier
        X = np.array(features_list)
        y = np.array(labels_list)
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        classifier = RandomForestClassifier(n_estimators=50, random_state=42)
        classifier.fit(X_scaled, y)
        
        return classifier, scaler
        
    except ImportError:
        return None, None
    except Exception as e:
        print(f"Error creating possibility classifier: {e}")
        return None, None


def calculate_statistical_possibility(df, target_date, situation):
    """
    Calculate rental possibility using statistical methods.
    
    Args:
        df: DataFrame with historical rental data
        target_date: datetime object
        situation: Dictionary with situation details
        
    Returns:
        Dictionary with statistical possibility score and reasoning
    """
    if df.empty or "Date" not in df.columns:
        return {
            "possibility": 0.0,
            "confidence": 0.0,
            "reasoning": "No historical data available"
        }
    
    df_copy = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_copy["Date"]):
        df_copy["Date"] = pd.to_datetime(df_copy["Date"])
    
    # Filter out calculator-generated records
    if "Car model" in df_copy.columns:
        df_copy = df_copy[df_copy["Car model"] != "Calculator Generated"]
    
    if df_copy.empty:
        return {
            "possibility": 0.0,
            "confidence": 0.0,
            "reasoning": "No valid rental data available"
        }
    
    # Extract date features
    target_month = target_date.month
    target_day_of_week = target_date.weekday()
    is_weekend = target_day_of_week >= 5
    
    # Check historical rentals on same day of week
    same_weekday_rentals = df_copy[df_copy["Date"].dt.weekday == target_day_of_week]
    weekday_probability = len(same_weekday_rentals) / max(1, len(df_copy)) if len(df_copy) > 0 else 0
    
    # Check historical rentals in same month
    same_month_rentals = df_copy[df_copy["Date"].dt.month == target_month]
    month_probability = len(same_month_rentals) / max(1, len(df_copy)) if len(df_copy) > 0 else 0
    
    # Check weekend vs weekday pattern
    if is_weekend:
        weekend_rentals = df_copy[df_copy["Date"].dt.weekday >= 5]
        weekend_probability = len(weekend_rentals) / max(1, len(df_copy)) if len(df_copy) > 0 else 0
    else:
        weekday_only_rentals = df_copy[df_copy["Date"].dt.weekday < 5]
        weekend_probability = len(weekday_only_rentals) / max(1, len(df_copy)) if len(df_copy) > 0 else 0
    
    # Check similar trip patterns if situation provided
    trip_similarity = 0.5  # Default
    if situation and "distance" in situation and "duration" in situation:
        distance = situation["distance"]
        duration = situation["duration"]
        
        # Find rentals with similar distance and duration
        if "Distance (KM)" in df_copy.columns and "Rental hour" in df_copy.columns:
            distance_range = (distance * 0.7, distance * 1.3)
            duration_range = (duration * 0.7, duration * 1.3)
            
            similar_trips = df_copy[
                (df_copy["Distance (KM)"] >= distance_range[0]) &
                (df_copy["Distance (KM)"] <= distance_range[1]) &
                (df_copy["Rental hour"] >= duration_range[0]) &
                (df_copy["Rental hour"] <= duration_range[1])
            ]
            trip_similarity = len(similar_trips) / max(1, len(df_copy)) if len(df_copy) > 0 else 0.5
    
    # Calculate overall possibility (weighted average)
    base_possibility = (weekday_probability * 0.3 + month_probability * 0.3 + weekend_probability * 0.2 + trip_similarity * 0.2)
    
    # Adjust for contextual factors
    if situation:
        if situation.get("holiday", False):
            base_possibility *= 1.2  # Increase for holidays
        if situation.get("special_event", ""):
            base_possibility *= 1.1  # Slight increase for special events
        
        personal_schedule = situation.get("personal_schedule", "Maybe")
        if personal_schedule == "Free":
            base_possibility *= 1.3
        elif personal_schedule == "Busy":
            base_possibility *= 0.5
        # "Maybe" doesn't change the probability
    
    # Normalize to 0-1 range
    possibility = min(1.0, max(0.0, base_possibility))
    
    # Calculate confidence based on data availability
    data_points = len(df_copy)
    confidence = min(1.0, data_points / 30)  # Max confidence at 30+ records
    
    # Generate reasoning
    reasoning_parts = []
    if weekday_probability > 0.1:
        reasoning_parts.append(f"Historical pattern shows {weekday_probability*100:.0f}% of rentals on this day of week")
    if month_probability > 0.1:
        reasoning_parts.append(f"{month_probability*100:.0f}% of rentals occurred in this month")
    if situation and situation.get("holiday", False):
        reasoning_parts.append("Holiday period typically increases rental likelihood")
    if situation and situation.get("personal_schedule") == "Free":
        reasoning_parts.append("Free schedule suggests higher rental possibility")
    
    reasoning = ". ".join(reasoning_parts) if reasoning_parts else "Based on general historical patterns"
    
    return {
        "possibility": float(possibility),
        "confidence": float(confidence),
        "reasoning": reasoning,
        "method": "Statistical"
    }


def predict_rental_possibility(df, target_date, situation=None):
    """
    Main function to predict rental possibility for a specific date and situation.
    Uses hybrid approach: ML Classification + Statistical.
    
    Args:
        df: DataFrame with historical rental data
        target_date: Target date (datetime or string)
        situation: Dictionary with:
            - distance: float (optional)
            - duration: float (optional)
            - is_weekend: bool (optional, auto-detected if not provided)
            - holiday: bool (optional)
            - special_event: str (optional)
            - weather: str (optional, "sunny", "rainy", "cloudy", "stormy")
            - personal_schedule: str (optional, "Free", "Busy", "Maybe")
        
    Returns:
        Dictionary with:
        - possibility: float (0-1, probability of rental)
        - possibility_percentage: float (0-100)
        - confidence: float (0-1)
        - expected_cost_range: tuple (min, max)
        - recommended_provider: str
        - reasoning: str
        - method: str ("ML", "Statistical", or "Hybrid")
    """
    if df.empty:
        return {"error": "No data available for prediction"}
    
    # Convert target_date to datetime
    if isinstance(target_date, str):
        target_date = pd.to_datetime(target_date)
    
    # Default situation if not provided
    if situation is None:
        situation = {}
    
    # Auto-detect weekend if not provided
    if "is_weekend" not in situation:
        situation["is_weekend"] = target_date.weekday() >= 5
    
    # Get statistical possibility
    statistical_result = calculate_statistical_possibility(df, target_date, situation)
    
    # Try ML prediction
    classifier, scaler = create_possibility_classifier(df)
    ml_possibility = None
    ml_confidence = 0.0
    
    if classifier is not None and scaler is not None:
        try:
            features = extract_situation_features(situation, target_date, df)
            features_scaled = scaler.transform(features)
            
            # Get probability of rental (class 1)
            probabilities = classifier.predict_proba(features_scaled)[0]
            ml_possibility = float(probabilities[1])  # Probability of rental
            ml_confidence = min(1.0, len(df) / 50)  # Confidence based on data size
        except Exception as e:
            print(f"ML prediction error: {e}")
            ml_possibility = None
    
    # Combine ML and Statistical (hybrid)
    if ml_possibility is not None:
        # Weighted average: 60% ML, 40% Statistical
        final_possibility = (ml_possibility * 0.6) + (statistical_result["possibility"] * 0.4)
        final_confidence = (ml_confidence * 0.6) + (statistical_result["confidence"] * 0.4)
        method = "Hybrid"
    else:
        # Use statistical only
        final_possibility = statistical_result["possibility"]
        final_confidence = statistical_result["confidence"]
        method = "Statistical"
    
    # Estimate expected cost range
    expected_cost_range = (30.0, 100.0)  # Default
    if "Total" in df.columns:
        df_filtered = df[df["Car model"] != "Calculator Generated"] if "Car model" in df.columns else df
        if not df_filtered.empty:
            avg_cost = df_filtered["Total"].mean()
            std_cost = df_filtered["Total"].std()
            expected_cost_range = (
                float(max(0, avg_cost - std_cost)),
                float(avg_cost + std_cost)
            )
    
    # Recommend provider based on historical patterns
    recommended_provider = "Getgo"  # Default
    if "Car Cat" in df.columns:
        provider_counts = df["Car Cat"].value_counts()
        if len(provider_counts) > 0:
            recommended_provider = provider_counts.index[0]
    
    # Enhanced reasoning
    reasoning = statistical_result["reasoning"]
    if ml_possibility is not None:
        if ml_possibility > 0.7:
            reasoning += ". ML model indicates high rental probability."
        elif ml_possibility < 0.3:
            reasoning += ". ML model indicates low rental probability."
        else:
            reasoning += ". ML model indicates moderate rental probability."
    
    return {
        "possibility": float(final_possibility),
        "possibility_percentage": float(final_possibility * 100),
        "confidence": float(final_confidence),
        "expected_cost_range": expected_cost_range,
        "recommended_provider": recommended_provider,
        "reasoning": reasoning,
        "method": method,
        "ml_possibility": float(ml_possibility) if ml_possibility is not None else None,
        "statistical_possibility": float(statistical_result["possibility"])
    }
