"""Electric-versus-traditional rental analysis and plotting helpers."""

from __future__ import annotations

import math

import pandas as pd


# Keep aliases here because imported/legacy CSVs may not yet be normalized.
EV_CAR_CATEGORIES = frozenset({"getgo(ev)", "getgo ev", "getgo electric"})
ELECTRIC = "Electric"
TRADITIONAL = "Traditional"
DEFAULT_EV_EFFICIENCY_KM_PER_KWH = 6.0


def is_electric_row(row: pd.Series) -> bool:
    """Return whether a row represents an EV by provider category or metered kWh."""
    category = str(row.get("Car Cat", "")).strip().casefold()
    kwh = pd.to_numeric(pd.Series([row.get("kWh Used")]), errors="coerce").iat[0]
    return category in EV_CAR_CATEGORIES or bool(pd.notna(kwh) and kwh > 0)


def classify_vehicle_type(df: pd.DataFrame) -> pd.Series:
    """Classify each rental as Electric or Traditional without mutating ``df``."""
    if df.empty:
        return pd.Series(index=df.index, dtype="object")
    return df.apply(
        lambda row: ELECTRIC if is_electric_row(row) else TRADITIONAL, axis=1
    )


def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df:
        return pd.Series(0.0, index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce")


def _summary(df: pd.DataFrame, efficiency: pd.Series) -> dict[str, float | int]:
    distance = _numeric_series(df, "Distance (KM)")
    return {
        "trip_count": len(df),
        "avg_cost": _numeric_series(df, "Total").mean(skipna=True) or 0.0,
        "total_cost": _numeric_series(df, "Total").sum(skipna=True),
        "avg_distance": distance.mean(skipna=True) or 0.0,
        "total_distance": distance.sum(skipna=True),
        "avg_duration": _numeric_series(df, "Rental hour").mean(skipna=True) or 0.0,
        "total_duration": _numeric_series(df, "Rental hour").sum(skipna=True),
        "avg_cost_per_km": _numeric_series(df, "Cost per KM").mean(skipna=True) or 0.0,
        "avg_cost_per_hour": _numeric_series(df, "Cost/HR").mean(skipna=True) or 0.0,
        "avg_efficiency": efficiency.mean(skipna=True) or 0.0,
    }


def _safe_number(value: float | int) -> float:
    return float(value) if pd.notna(value) and math.isfinite(float(value)) else 0.0


def _trip_type_counts(df: pd.DataFrame) -> pd.Series:
    distance = _numeric_series(df, "Distance (KM)")
    labels = pd.Series(
        pd.NA, index=df.index, dtype="object"
    )
    labels.loc[distance < 50] = "Short"
    labels.loc[(distance >= 50) & (distance <= 100)] = "Medium"
    labels.loc[distance > 100] = "Long"
    return labels.value_counts()


def compute_ev_traditional_stats(
    df: pd.DataFrame, fuel_price: float, cost_per_kwh: float
) -> dict[str, object]:
    """Classify rentals and calculate comparison metrics for both vehicle types."""
    classified = df.copy()
    classified["Vehicle_Type"] = classify_vehicle_type(classified)
    ev_df = classified[classified["Vehicle_Type"] == ELECTRIC].copy()
    traditional_df = classified[
        classified["Vehicle_Type"] == TRADITIONAL
    ].copy()

    ev_kwh = _numeric_series(ev_df, "kWh Used")
    ev_distance = _numeric_series(ev_df, "Distance (KM)")
    ev_efficiency = ev_distance.where(
        (ev_kwh > 0) & (ev_distance > 0)
    ) / ev_kwh.where((ev_kwh > 0) & (ev_distance > 0))
    ev_stats = _summary(ev_df, ev_efficiency)
    estimated_ev_kwh = ev_kwh.where(
        ev_kwh > 0, ev_distance / DEFAULT_EV_EFFICIENCY_KM_PER_KWH
    )
    ev_stats["total_kwh"] = estimated_ev_kwh.sum(skipna=True)
    electricity_cost = _numeric_series(ev_df, "Electricity Cost")
    ev_stats["total_electricity_cost"] = (
        electricity_cost.sum(skipna=True)
        if electricity_cost.notna().any()
        else ev_stats["total_kwh"] * cost_per_kwh
    )

    pumped = _numeric_series(traditional_df, "Fuel pumped")
    estimated = _numeric_series(traditional_df, "Estimated fuel usage")
    fuel_used = pumped.where(pumped > 0, estimated)
    traditional_distance = _numeric_series(traditional_df, "Distance (KM)")
    traditional_efficiency = traditional_distance.where(
        (fuel_used > 0) & (traditional_distance > 0)
    ) / fuel_used.where((fuel_used > 0) & (traditional_distance > 0))
    traditional_stats = _summary(traditional_df, traditional_efficiency)
    traditional_stats["total_fuel"] = fuel_used.sum(skipna=True)
    fuel_cost = _numeric_series(traditional_df, "Fuel cost")
    traditional_stats["total_fuel_cost"] = (
        fuel_cost.sum(skipna=True)
        if fuel_cost.notna().any()
        else traditional_stats["total_fuel"] * fuel_price
    )

    ev_stats["total_co2"] = ev_stats["total_kwh"] * 0.4
    ev_stats["avg_co2_per_trip"] = (
        ev_stats["total_co2"] / ev_stats["trip_count"]
        if ev_stats["trip_count"]
        else 0.0
    )
    traditional_stats["total_co2"] = traditional_stats["total_fuel"] * 2.31
    traditional_stats["avg_co2_per_trip"] = (
        traditional_stats["total_co2"] / traditional_stats["trip_count"]
        if traditional_stats["trip_count"]
        else 0.0
    )

    cost_savings: dict[str, float] = {}
    if ev_stats["total_distance"] > 0 and traditional_stats["avg_efficiency"] > 0:
        estimated_fuel = ev_stats["total_distance"] / traditional_stats["avg_efficiency"]
        traditional_cost = estimated_fuel * fuel_price
        savings = traditional_cost - ev_stats["total_electricity_cost"]
        cost_savings["ev_savings"] = savings
        cost_savings["ev_savings_pct"] = savings / traditional_cost * 100
    if traditional_stats["total_distance"] > 0 and ev_stats["avg_efficiency"] > 0:
        estimated_kwh = traditional_stats["total_distance"] / ev_stats["avg_efficiency"]
        electric_cost = estimated_kwh * cost_per_kwh
        savings = traditional_stats["total_fuel_cost"] - electric_cost
        cost_savings["traditional_savings"] = savings
        cost_savings["traditional_savings_pct"] = (
            savings / traditional_stats["total_fuel_cost"] * 100
            if traditional_stats["total_fuel_cost"] > 0
            else 0.0
        )

    co2_savings_pct = 0.0
    if ev_stats["total_distance"] > 0 and traditional_stats["total_distance"] > 0:
        ev_per_km = ev_stats["total_co2"] / ev_stats["total_distance"]
        traditional_per_km = (
            traditional_stats["total_co2"] / traditional_stats["total_distance"]
        )
        if traditional_per_km > 0:
            co2_savings_pct = (traditional_per_km - ev_per_km) / traditional_per_km * 100

    return {
        "ev": {key: _safe_number(value) for key, value in ev_stats.items()},
        "traditional": {
            key: _safe_number(value) for key, value in traditional_stats.items()
        },
        "cost_savings": cost_savings,
        "co2_savings_pct": co2_savings_pct,
        "ev_df": ev_df,
        "traditional_df": traditional_df,
        "trip_type_counts": {
            ELECTRIC: _trip_type_counts(ev_df),
            TRADITIONAL: _trip_type_counts(traditional_df),
        },
    }


def _add_value_labels(ax, bars, values, prefix: str = "", precision: int = 2) -> None:
    if not values:
        return
    offset = max(values) * 0.02 if max(values) else 0.02
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + offset,
            f"{prefix}{value:.{precision}f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )


def build_comparison_figure(fig, stats: dict[str, object], ev_df, traditional_df):
    """Draw six EV/traditional charts without ``tight_layout``."""
    fig.clear()
    fig.subplots_adjust(
        left=0.07, right=0.98, bottom=0.10, top=0.92, wspace=0.35, hspace=0.40
    )
    axes = fig.subplots(2, 3)

    summaries = [(ELECTRIC, stats["ev"]), (TRADITIONAL, stats["traditional"])]
    colors = {ELECTRIC: "#00CED1", TRADITIONAL: "#FF6347"}
    labels = [name for name, values in summaries if values["trip_count"] > 0]
    chart_colors = [colors[name] for name in labels]

    def bar_chart(ax, values, title, ylabel, prefix="", precision=2):
        if values:
            bars = ax.bar(labels, values, color=chart_colors, alpha=0.7)
            _add_value_labels(ax, bars, values, prefix, precision)
        ax.set_title(title, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.grid(axis="y", linestyle="--", alpha=0.3)

    metrics = (
        (axes[0, 0], "Average Cost", "Average Cost ($)", "avg_cost", "$", 2),
        (axes[0, 1], "Trip Count", "Trips", "trip_count", "", 0),
        (axes[1, 0], "Cost per km", "Cost per km ($)", "avg_cost_per_km", "$", 3),
        (axes[1, 2], "CO2 per km", "CO2 per km (kg)", "total_co2", "", 3),
    )
    for ax, title, ylabel, key, prefix, precision in metrics:
        if key == "total_co2":
            values = [
                values["total_co2"] / values["total_distance"]
                if values["total_distance"] > 0
                else 0.0
                for _, values in summaries
                if values["trip_count"] > 0
            ]
        else:
            values = [
                values[key] for _, values in summaries if values["trip_count"] > 0
            ]
        bar_chart(ax, values, title, ylabel, prefix, precision)

    efficiency_labels, efficiency_values, efficiency_colors = [], [], []
    for name, values in summaries:
        if values["avg_efficiency"] > 0:
            unit = "km/kWh" if name == ELECTRIC else "km/L"
            efficiency_labels.append(f"{name}\n({unit})")
            efficiency_values.append(values["avg_efficiency"])
            efficiency_colors.append(colors[name])
    if efficiency_values:
        bars = axes[0, 2].bar(
            efficiency_labels, efficiency_values, color=efficiency_colors, alpha=0.7
        )
        _add_value_labels(axes[0, 2], bars, efficiency_values)
    axes[0, 2].set_title("Energy Efficiency", fontsize=10)
    axes[0, 2].set_ylabel("Efficiency", fontsize=9)
    axes[0, 2].grid(axis="y", linestyle="--", alpha=0.3)

    distance_sets = [
        _numeric_series(frame, "Distance (KM)").dropna().tolist()
        for frame in (ev_df, traditional_df)
    ]
    present = [(label, values) for label, values in zip(labels, distance_sets) if values]
    if present:
        axes[1, 1].hist(
            [values for _, values in present],
            bins=15,
            label=[label for label, _ in present],
            color=[colors[label] for label, _ in present],
            alpha=0.6,
        )
        if len(present) > 1:
            axes[1, 1].legend(fontsize=8)
    axes[1, 1].set_title("Distance Distribution", fontsize=10)
    axes[1, 1].set_xlabel("Distance (km)", fontsize=9)
    axes[1, 1].set_ylabel("Frequency", fontsize=9)
    return axes
