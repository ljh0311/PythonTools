"""Canonical provider names and formula-based rental pricing."""

import json
from pathlib import Path
from typing import Optional


CANONICAL_PROVIDERS = (
    "Getgo", "Getgo(EV)", "Tribecar", "Car Club", "Econ", "Stand", "SoCar", "NormalRental",
)
_ALIASES = {
    "getgo": "Getgo",
    "getgo ev": "Getgo(EV)",
    "getgo(ev)": "Getgo(EV)",
    "getgo electric": "Getgo(EV)",
    "tribecar": "Tribecar",
    "car club": "Car Club",
    "econ": "Econ",
    "stand": "Stand",
    "socar": "SoCar",
    "normal rental": "NormalRental",
    "normalrental": "NormalRental",
}
_REGION_PROVIDERS = {
    "Singapore": ["Getgo", "Getgo(EV)", "Tribecar", "Car Club", "Econ", "Stand"],
    "Malaysia": ["SoCar", "NormalRental"],
}
_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "pricing_config.json"


def normalize_provider(name) -> str:
    """Return a known provider alias in its canonical form."""
    if not isinstance(name, str):
        return name
    name = " ".join(name.strip().split())
    return _ALIASES.get(name.casefold(), name)


def load_pricing_config(path=None) -> dict:
    """Load pricing with canonical provider keys."""
    with Path(path or _DEFAULT_CONFIG_PATH).open(encoding="utf-8") as config_file:
        config = json.load(config_file)
    return {normalize_provider(provider): rates for provider, rates in config.items()}


def estimate_provider_cost(distance, duration, provider, is_weekend=False) -> Optional[dict]:
    """Return a provider's formula price, or None when unavailable."""
    rates = load_pricing_config().get(normalize_provider(provider))
    if not rates or rates.get("pricing_type") == "traditional":
        return None
    distance, duration = float(distance or 0), float(duration or 0)
    day = "weekend" if is_weekend else "weekday"
    hour_key = f"hour_rate_{day}"
    hour_rate = rates.get(hour_key, rates.get("hour_rate", 0))
    duration_cost = duration * hour_rate
    mileage_cost, fuel_cost = 0.0, 0.0
    platform_fee = float(rates.get("platform_fee", 0) or 0)

    if rates.get("pricing_type") == "mileage":
        mileage_cost = distance * rates.get("mileage_rate", 0)
    elif rates.get("pricing_type") == "socar":
        packages = sorted(rates.get("mileage_packages", []), key=lambda package: package["km"])
        if not packages:
            return None
        package = next((item for item in packages if distance <= item["km"]), packages[-1])
        mileage_cost = package["price"] + max(0, distance - package["km"]) * rates.get("excess_km_rate", 0)
    else:
        fuel_cost = rates.get("fuel_rate", rates.get("usual_fuel_amount", 0))

    subtotal = duration_cost + mileage_cost + fuel_cost + platform_fee
    # Weekend hour rates already applied when configured; only multiply fuel-type leftovers
    if is_weekend and hour_key not in rates and rates.get("pricing_type") != "mileage":
        subtotal *= 1.2
    return {
        "total_cost": subtotal,
        "duration_cost": duration_cost,
        "mileage_cost": mileage_cost,
        "fuel_cost": fuel_cost,
        "platform_fee": platform_fee,
    }


def list_comparable_providers(region) -> list:
    """Return canonical formula-comparable providers for a region."""
    return list(_REGION_PROVIDERS.get(region, _REGION_PROVIDERS["Singapore"]))


def coerce_predicted_rental_total(raw_sum: float, probs: list[float]) -> int:
    """Avoid rounding a positive rental signal down to zero."""
    total = round(raw_sum)
    return 1 if total == 0 and raw_sum > 0 and any(probability > 0 for probability in probs) else total
