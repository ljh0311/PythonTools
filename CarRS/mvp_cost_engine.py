"""Deterministic, configuration-backed MVP pricing recommendations."""

from typing import Any, Iterable

from components.provider_pricing import (
    estimate_provider_cost,
    list_comparable_providers,
    normalize_provider,
)


def safe_predicted_rental_total(raw: Any, probs: Iterable[Any]) -> int:
    """Round totals without turning a positive probability into zero rentals."""
    try:
        total = max(0, round(float(raw)))
    except (TypeError, ValueError):
        total = 0

    def _probability(item: Any) -> float:
        try:
            return float(item.get("rental_probability", 0) if isinstance(item, dict) else item)
        except (TypeError, ValueError):
            return 0.0

    return max(1, total) if any(_probability(item) > 0 for item in probs) else total


def format_predicted_rental_display(shown: Any, expected: Any) -> str:
    """UI label: never fake a lone '0' when expected rentals are positive."""
    try:
        expected_f = float(expected)
    except (TypeError, ValueError):
        expected_f = 0.0
    try:
        shown_i = int(shown)
    except (TypeError, ValueError):
        shown_i = 0

    if expected_f > 0:
        if shown_i <= 0:
            shown_i = 1
        return f"Expected ~{expected_f:.1f} → shown as {shown_i}"
    return str(shown_i)


def get_mvp_recommendations(
    distance: float, duration: float, is_weekend: bool, region: str = "Singapore"
) -> list[dict[str, Any]]:
    """Return sorted formula-priced providers; skipped providers retain a reason."""
    distance, duration = float(distance), float(duration)
    if distance < 0 or duration < 0:
        raise ValueError("distance and duration cannot be negative")

    recommendations = []
    skipped_providers = []
    for provider in list_comparable_providers(region):
        provider = normalize_provider(provider)
        cost = estimate_provider_cost(distance, duration, provider, is_weekend)
        if cost is None:
            skipped_providers.append(
                {"provider": provider, "reason": "Traditional rental has no formula pricing"}
            )
            continue
        recommendations.append(
            {
                "provider": provider,
                "model": "Standard",
                "method": "Pricing estimate",
                "confidence": 1.0,
                "reasoning": "Based on rates in pricing_config.json — no AI required",
                "pricing_model": "formula",
                **cost,
            }
        )
    for recommendation in recommendations:
        recommendation["metadata"] = {"skipped_providers": skipped_providers}
    return sorted(recommendations, key=lambda recommendation: recommendation["total_cost"])
