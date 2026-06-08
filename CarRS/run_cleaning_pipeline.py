#!/usr/bin/env python3
"""
Standalone CLI for the car rental data cleaning pipeline.
Run from the CarRS directory: python run_cleaning_pipeline.py <input.csv> [--out cleaned.csv] [--report report.json] [--outliers]
"""
import argparse
import json
import os
import sys

# Run from CarRS directory so core can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from car_rental_recommender_core import run_cleaning_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Run the automated data cleaning pipeline on a car rental CSV."
    )
    parser.add_argument("input", help="Input CSV file path")
    parser.add_argument("--out", "-o", help="Output CSV path (cleaned data)")
    parser.add_argument("--report", "-r", help="Write quality report to this JSON file")
    parser.add_argument("--outliers", action="store_true", help="Apply IQR-based outlier capping to numeric columns")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    try:
        df, report = run_cleaning_pipeline(
            args.input,
            output_path=args.out,
            handle_outliers=args.outliers,
        )
        print(f"Pipeline finished: {report['rows_in']} rows in, {report['rows_out']} rows out, {report['duplicates_removed']} duplicates removed.")
        if report.get("outliers_capped", 0) > 0:
            print(f"Outliers capped: {report['outliers_capped']}")
        if not report.get("schema_valid", True):
            print("Schema warnings:", report.get("schema_errors", []))
        if args.report:
            with open(args.report, "w") as f:
                json.dump(report, f, indent=2)
            print(f"Quality report written to {args.report}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
