#!/usr/bin/env python3
"""
Headless CLI for car rental recommendations (no tkinter).
Run from the CarRS directory or pass --csv with an absolute path.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from car_rental_recommender_core import (
    create_complete_cost_analysis,
    get_enhanced_recommendations,
    run_cleaning_pipeline,
)


def _resolve_csv(path: str) -> str:
    if os.path.isabs(path) and os.path.exists(path):
        return path
    base = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(base, path)
    if os.path.exists(candidate):
        return candidate
    if os.path.exists(path):
        return os.path.abspath(path)
    raise FileNotFoundError(f"CSV not found: {path}")


def _format_table(recommendations: list) -> str:
    from tabulate import tabulate

    rows = []
    for i, rec in enumerate(recommendations, 1):
        rows.append(
            [
                i,
                rec.get("provider", ""),
                rec.get("model", ""),
                f"${rec.get('total_cost', 0):.2f}",
                f"${rec.get('duration_cost', 0):.2f}",
                f"${rec.get('mileage_cost', 0):.2f}",
                f"${rec.get('fuel_cost', 0):.2f}",
                rec.get("method", ""),
                rec.get("confidence", ""),
            ]
        )
    headers = [
        "#",
        "Provider",
        "Model",
        "Total",
        "Duration",
        "Mileage",
        "Fuel",
        "Method",
        "Confidence",
    ]
    return tabulate(rows, headers=headers, tablefmt="simple")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Get car rental recommendations from historical CSV data."
    )
    parser.add_argument(
        "--distance",
        type=float,
        required=True,
        help="Trip distance in km",
    )
    parser.add_argument(
        "--duration",
        type=float,
        required=True,
        help="Rental duration in hours",
    )
    parser.add_argument(
        "--weekend",
        action="store_true",
        help="Apply weekend pricing surcharge",
    )
    parser.add_argument(
        "--csv",
        default="22 - Sheet1.csv",
        help='Input CSV (default: "22 - Sheet1.csv" in CarRS folder)',
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of recommendations to return (default: 5)",
    )
    parser.add_argument(
        "--region",
        choices=["Singapore", "Malaysia"],
        default=None,
        help="Filter analysis to Singapore or Malaysia providers",
    )
    parser.add_argument(
        "--no-ml",
        action="store_true",
        help="Skip ML-based recommendations (historical analysis only)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON to stdout instead of a table",
    )
    args = parser.parse_args()

    try:
        csv_path = _resolve_csv(args.csv)
        df, report = run_cleaning_pipeline(csv_path)
        cost_analysis = create_complete_cost_analysis(df, region=args.region)
        recommendations = get_enhanced_recommendations(
            args.distance,
            args.duration,
            df,
            cost_analysis=cost_analysis,
            is_weekend=args.weekend,
            top_n=args.top,
            use_ml=not args.no_ml,
        )
        payload = {
            "distance_km": args.distance,
            "duration_hours": args.duration,
            "weekend": args.weekend,
            "region": args.region,
            "csv": csv_path,
            "rows_loaded": report.get("rows_out", len(df)),
            "recommendations": recommendations,
        }
        if args.json:
            print(json.dumps(payload, indent=2, default=str))
        else:
            print(
                f"Recommendations for {args.distance} km, {args.duration} h"
                f"{' (weekend)' if args.weekend else ''}:"
            )
            print(_format_table(recommendations))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
