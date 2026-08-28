"""
ML learning evaluation for CarRS.

Shared by pytest (tests/test_ml_evaluation.py) and CLI (scripts/evaluate_ml.py).
Verifies ML recommendations and predictions track historical patterns.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from car_rental_recommender_core import (
    calculate_estimated_cost,
    create_complete_cost_analysis,
    create_ml_budget_prediction,
    create_ml_recommendations,
    enhance_dataframe,
    get_ollama_enhanced_recommendations,
    load_data,
    predict_rental_possibility,
)

DEFAULT_CSV = "22 - Sheet1.csv"

# Ratio of ML predicted cost vs median of similar historical trips
RATIO_PASS = (0.5, 2.5)
RATIO_WARN = (0.35, 3.0)


@dataclass
class Scenario:
    name: str
    distance_km: float
    duration_h: float
    is_weekend: bool
    region: str
    similar_km: tuple[float, float]
    similar_hr: tuple[float, float]


DEFAULT_SCENARIOS = [
    Scenario("SG short Getgo weekday", 40, 1, False, "Singapore", (30, 50), (0.5, 2)),
    Scenario("SG medium weekday", 80, 3, False, "Singapore", (60, 100), (2, 5)),
    Scenario("SG weekend trip", 60, 4, True, "Singapore", (50, 80), (3, 6)),
]


@dataclass
class CheckResult:
    name: str
    status: str  # pass | warn | fail | skip
    message: str
    details: dict[str, Any] = field(default_factory=dict)


def resolve_csv_path(csv: Optional[str] = None) -> str:
    path = csv or os.environ.get("CARRS_CSV", DEFAULT_CSV)
    if os.path.isabs(path):
        return path
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, path)


def load_evaluation_data(csv: Optional[str] = None):
    path = resolve_csv_path(csv)
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")
    df = enhance_dataframe(load_data(path))
    return df, path


def _median_similar(df, km_lo: float, km_hi: float, hr_lo: float, hr_hi: float) -> Optional[float]:
    sub = df[
        df["Distance (KM)"].between(km_lo, km_hi) & df["Rental hour"].between(hr_lo, hr_hi)
    ]
    if sub.empty:
        return None
    return float(sub["Total"].median())


def _ratio_status(ratio: Optional[float]) -> str:
    if ratio is None:
        return "skip"
    lo, hi = RATIO_PASS
    if lo <= ratio <= hi:
        return "pass"
    wlo, whi = RATIO_WARN
    if wlo <= ratio <= whi:
        return "warn"
    return "fail"


def evaluate_scenario(df, scenario: Scenario, cost_analysis_sg, cost_analysis_my) -> dict[str, Any]:
    ca = cost_analysis_sg if scenario.region == "Singapore" else cost_analysis_my
    pricing = calculate_estimated_cost(
        scenario.distance_km,
        scenario.duration_h,
        "Getgo",
        None,
        ca,
        scenario.is_weekend,
    )
    ml_recs = create_ml_recommendations(
        scenario.distance_km,
        scenario.duration_h,
        df,
        scenario.is_weekend,
        top_n=4,
    )
    blended = get_ollama_enhanced_recommendations(
        scenario.distance_km,
        scenario.duration_h,
        df,
        ca,
        scenario.is_weekend,
        top_n=6,
        use_ollama=False,
        use_ml=True,
    )
    med = _median_similar(
        df, scenario.similar_km[0], scenario.similar_km[1],
        scenario.similar_hr[0], scenario.similar_hr[1],
    )
    ml_top = ml_recs[0] if ml_recs else None
    ml_cost = ml_top["total_cost"] if ml_top else None
    ratio = (ml_cost / med) if med and ml_cost else None

    return {
        "name": scenario.name,
        "distance_km": scenario.distance_km,
        "duration_h": scenario.duration_h,
        "is_weekend": scenario.is_weekend,
        "region": scenario.region,
        "pricing_getgo": pricing["total_cost"] if pricing else None,
        "ml_top_cost": ml_cost,
        "ml_top_provider": ml_top.get("provider") if ml_top else None,
        "ml_confidence": ml_top.get("confidence") if ml_top else None,
        "median_similar_actual": med,
        "ml_vs_median_ratio": round(ratio, 3) if ratio is not None else None,
        "ratio_status": _ratio_status(ratio),
        "methods_in_results": sorted({r.get("method") for r in blended}),
        "cheapest_blended": round(blended[0]["total_cost"], 2) if blended else None,
        "ml_provider_count": len(ml_recs),
    }


def run_checks(df, scenarios: list[Scenario], scenario_results: list[dict]) -> list[CheckResult]:
    checks: list[CheckResult] = []

    if len(df) < 10:
        checks.append(CheckResult("minimum_data", "fail", f"Need >=10 rows for ML, got {len(df)}"))
    else:
        checks.append(CheckResult("minimum_data", "pass", f"{len(df)} rental rows loaded"))

    ml_recs = create_ml_recommendations(40, 1, df, False, top_n=4)
    if not ml_recs:
        checks.append(CheckResult("ml_produces_output", "fail", "create_ml_recommendations returned empty"))
    else:
        bad = [r for r in ml_recs if r["total_cost"] <= 0 or not (0 < r.get("confidence", 0) <= 1)]
        if bad:
            checks.append(CheckResult("ml_produces_output", "fail", "Invalid ML recommendation values"))
        else:
            checks.append(
                CheckResult(
                    "ml_produces_output", "pass",
                    f"{len(ml_recs)} provider predictions",
                    {"providers": [r["provider"] for r in ml_recs]},
                )
            )

    ca = create_complete_cost_analysis(df, region="Singapore")
    blended = get_ollama_enhanced_recommendations(40, 1, df, ca, False, top_n=10, use_ollama=False, use_ml=True)
    methods = {r.get("method") for r in blended}
    if {"ML Prediction", "Historical Analysis"}.issubset(methods):
        checks.append(CheckResult("gui_path_methods", "pass", f"Methods present: {sorted(methods)}"))
    else:
        checks.append(CheckResult("gui_path_methods", "fail", f"Missing methods, got {sorted(methods)}"))

    ratio_fails = [s for s in scenario_results if s.get("ratio_status") == "fail"]
    ratio_warns = [s for s in scenario_results if s.get("ratio_status") == "warn"]
    if ratio_fails:
        checks.append(
            CheckResult(
                "ml_tracks_history", "fail",
                f"{len(ratio_fails)} scenario(s) outside tolerance",
                {"failed": [s["name"] for s in ratio_fails]},
            )
        )
    elif ratio_warns:
        checks.append(
            CheckResult(
                "ml_tracks_history", "warn",
                f"{len(ratio_warns)} scenario(s) borderline vs history",
                {"warned": [s["name"] for s in ratio_warns]},
            )
        )
    else:
        checks.append(CheckResult("ml_tracks_history", "pass", "All scenarios within median ratio band"))

    poss = predict_rental_possibility(
        df, datetime(2026, 9, 6), {"distance": 40, "duration": 1, "is_weekend": True}
    )
    if "error" in poss:
        checks.append(CheckResult("rental_possibility", "fail", poss["error"]))
    elif not (0 <= poss.get("possibility", -1) <= 1):
        checks.append(CheckResult("rental_possibility", "fail", f"Invalid possibility: {poss.get('possibility')}"))
    else:
        checks.append(
            CheckResult(
                "rental_possibility", "pass",
                f"{poss.get('possibility_percentage', 0):.1f}% via {poss.get('method')}",
                {"provider": poss.get("recommended_provider")},
            )
        )

    try:
        budget = create_ml_budget_prediction(df, 500, "next_month", "medium")
        if budget["predicted_spending"] > 0 and budget["data_points"] >= 1:
            checks.append(
                CheckResult(
                    "budget_prediction", "pass",
                    f"Predicted ${budget['predicted_spending']:.0f}/month from {budget['data_points']} months",
                )
            )
        else:
            checks.append(CheckResult("budget_prediction", "fail", "Invalid budget prediction"))
    except Exception as exc:
        checks.append(CheckResult("budget_prediction", "fail", str(exc)))

    return checks


def _overall_verdict(checks: list[CheckResult]) -> str:
    if any(c.status == "fail" for c in checks):
        return "FAIL"
    if any(c.status == "warn" for c in checks):
        return "WARN"
    return "PASS"


def run_ml_evaluation(csv: Optional[str] = None, scenarios: Optional[list[Scenario]] = None) -> dict[str, Any]:
    """Run full ML evaluation. Returns structured report with checks and verdict."""
    scenarios = scenarios or DEFAULT_SCENARIOS
    df, csv_path = load_evaluation_data(csv)

    ca_sg = create_complete_cost_analysis(df, region="Singapore")
    my_df = df[df["Region"].fillna("Singapore") == "Malaysia"] if "Region" in df.columns else df.iloc[0:0]
    ca_my = create_complete_cost_analysis(my_df, region="Malaysia") if len(my_df) else ca_sg

    scenario_results = [
        evaluate_scenario(df, s, ca_sg, ca_my) for s in scenarios
    ]
    checks = run_checks(df, scenarios, scenario_results)

    return {
        "csv_path": csv_path,
        "csv_rows": len(df),
        "verdict": _overall_verdict(checks),
        "checks": [
            {"name": c.name, "status": c.status, "message": c.message, "details": c.details}
            for c in checks
        ],
        "scenarios": scenario_results,
        "learning_summary": {
            "median_ratios": [
                s["ml_vs_median_ratio"] for s in scenario_results if s.get("ml_vs_median_ratio") is not None
            ],
            "avg_median_ratio": round(
                sum(s["ml_vs_median_ratio"] for s in scenario_results if s.get("ml_vs_median_ratio")) /
                max(1, sum(1 for s in scenario_results if s.get("ml_vs_median_ratio") is not None)),
                3,
            ),
            "pass_band": RATIO_PASS,
        },
    }


def format_text_report(report: dict[str, Any]) -> str:
    lines = [
        f"ML Evaluation — {report['verdict']}",
        f"CSV: {report['csv_path']} ({report['csv_rows']} rows)",
        "",
        "Checks:",
    ]
    for c in report["checks"]:
        icon = {"pass": "OK", "warn": "!!", "fail": "XX", "skip": "--"}.get(c["status"], "??")
        lines.append(f"  [{icon}] {c['name']}: {c['message']}")

    lines.extend(["", "Scenarios:"])
    for s in report["scenarios"]:
        ratio = s.get("ml_vs_median_ratio")
        ratio_s = f"{ratio:.2f}" if ratio is not None else "n/a"
        lines.append(
            f"  - {s['name']}: ML ${s.get('ml_top_cost', 0):.2f} "
            f"(median similar ${s.get('median_similar_actual', 0):.2f}, ratio {ratio_s}) "
            f"[{s.get('ratio_status', 'skip')}]"
        )

    ls = report.get("learning_summary", {})
    lines.extend([
        "",
        f"Avg median ratio: {ls.get('avg_median_ratio', 'n/a')} (target band {RATIO_PASS})",
    ])
    return "\n".join(lines)
