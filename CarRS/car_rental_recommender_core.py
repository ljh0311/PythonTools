import os
import pandas as pd
import numpy as np
import requests
import json
from typing import List, Dict, Optional


def load_data(file_path):
    """Load and validate data from CSV file"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")

    df = pd.read_csv(file_path)
    print(f"Loaded {len(df)} records from {file_path}")
    return df


def enhance_dataframe(df):
    """Fix and enhance dataframe with proper formatting for all analyses to work"""
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

    # Ensure numeric columns are properly formatted
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
    df = df.fillna(
        {
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
    )

    print(f"Enhanced dataframe: {len(df)} rows ready for analysis")
    return df


def create_complete_cost_analysis(df):
    """Create a comprehensive cost analysis for providers with all required fields"""
    providers = ["Getgo", "Car Club", "Econ", "Stand"]
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
    distance, duration, provider, car_model=None, cost_analysis=None, is_weekend=False
):
    """Calculate estimated cost for a rental"""
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
    distance, duration, df, is_weekend=False, top_n=5, model_name="llama2"
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

    Returns:
        List of recommendation dictionaries
    """
    try:
        # Prepare context data for the LLM
        context_data = prepare_context_for_ollama(distance, duration, df, is_weekend)

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


def prepare_context_for_ollama(distance, duration, df, is_weekend):
    """Prepare historical data context for Ollama analysis"""
    context = {
        "user_request": {
            "distance_km": distance,
            "duration_hours": duration,
            "is_weekend": is_weekend,
        },
        "historical_data": {},
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

    prompt = f"""You are an expert in car rental recommendations. Your task is to suggest the best value options for a 24-year-old driver with 3 years of experience, prioritizing cost-effectiveness and reliability.

Customer Request:
- Distance: {context_data['user_request']['distance_km']} km
- Duration: {context_data['user_request']['duration_hours']} hours
- Weekend: {'Yes' if context_data['user_request']['is_weekend'] else 'No'}

Historical Data:{historical_summary}

Instructions:
- Recommend exactly 3 car rental options based only on providers and models present in the historical data.
- Focus on: 
  • Lowest total cost for the requested trip
  • Provider reliability and popularity
  • Value for money (cost per km/hour)
  • Suitability for errands, leisure, or sightseeing
  • Frequency of rentals (popularity)
- Exclude any cars not found in the historical data.

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

        # Use shorter timeout for faster models
        timeout = 15 if "3b" in model_name else 30
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
):
    """Get enhanced recommendations combining traditional, ML, and Ollama approaches"""
    recommendations = []
    method_recommendations = {}

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
                distance, duration, df, is_weekend, top_n, ollama_model
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

    # Sort by total cost and return top N
    recommendations.sort(key=lambda x: x["total_cost"])
    return recommendations[:top_n]
