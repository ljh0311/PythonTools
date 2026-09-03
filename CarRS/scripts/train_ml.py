#!/usr/bin/env python3
"""Run multi-pass CarRS ML training on local CSV."""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from car_rental_recommender_core import enhance_dataframe, load_data
from components.ml_trainer import format_training_report, run_training_passes


def main() -> int:
    parser = argparse.ArgumentParser(description="Train CarRS ML cost model (multi-pass)")
    parser.add_argument("--csv", default="22 - Sheet1.csv")
    parser.add_argument("--passes", type=int, default=3, choices=[1, 2, 3])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    csv_path = args.csv
    if not os.path.isabs(csv_path):
        csv_path = os.path.join(ROOT, csv_path)
    if not os.path.exists(csv_path):
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 2

    df = enhance_dataframe(load_data(csv_path))
    meta = run_training_passes(df, passes=args.passes)
    if args.json:
        print(json.dumps(meta, indent=2))
    else:
        print(format_training_report(meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
