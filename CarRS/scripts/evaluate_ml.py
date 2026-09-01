#!/usr/bin/env python3
"""CLI for CarRS ML learning evaluation."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.ml_evaluation import format_text_report, run_ml_evaluation


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate whether CarRS ML is learning from your rental history.",
    )
    parser.add_argument("--csv", default=None, help="Path to rental CSV (default: 22 - Sheet1.csv)")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    args = parser.parse_args()

    try:
        report = run_ml_evaluation(csv=args.csv)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_text_report(report))

    return 0 if report["verdict"] == "PASS" else (1 if report["verdict"] == "WARN" else 2)


if __name__ == "__main__":
    raise SystemExit(main())
