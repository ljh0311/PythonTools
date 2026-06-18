#!/usr/bin/env python3
"""OpenClaw helper CLI for CarRS (wraps run_recommendations.py and cleaning pipeline)."""
import argparse
import json
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_WORKDIR = os.path.abspath(os.path.join(SKILL_DIR, "..", "..", ".."))


def workdir() -> str:
    return os.environ.get("CARRS_WORKDIR", DEFAULT_WORKDIR)


def run_py(script: str, args: list[str]) -> int:
    cmd = [sys.executable, os.path.join(workdir(), script), *args]
    return subprocess.call(cmd, cwd=workdir())


def cmd_providers(args: argparse.Namespace) -> int:
    sys.path.insert(0, workdir())
    from car_rental_recommender_core import get_providers_for_region

    region = args.region or "Singapore"
    providers = get_providers_for_region(region)
    if args.json:
        print(json.dumps({"region": region, "providers": providers}, indent=2))
    else:
        print(f"Providers ({region}): {', '.join(providers)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="CarRS OpenClaw helper")
    sub = parser.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("recommend", help="Get rental recommendations")
    rec.add_argument("--distance", type=float, required=True)
    rec.add_argument("--duration", type=float, required=True)
    rec.add_argument("--weekend", action="store_true")
    rec.add_argument("--csv", default="22 - Sheet1.csv")
    rec.add_argument("--top", type=int, default=5)
    rec.add_argument("--region", choices=["Singapore", "Malaysia"])
    rec.add_argument("--no-ml", action="store_true")
    rec.add_argument("--json", action="store_true")

    clean = sub.add_parser("clean", help="Run CSV cleaning pipeline")
    clean.add_argument("input_csv")
    clean.add_argument("--out", "-o")
    clean.add_argument("--report", "-r")
    clean.add_argument("--outliers", action="store_true")

    prov = sub.add_parser("providers", help="List providers for a region")
    prov.add_argument("--region", choices=["Singapore", "Malaysia"])
    prov.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "providers":
        return cmd_providers(args)

    if args.command == "recommend":
        cmd_args = [
            "--distance", str(args.distance),
            "--duration", str(args.duration),
            "--csv", args.csv,
            "--top", str(args.top),
        ]
        if args.weekend:
            cmd_args.append("--weekend")
        if args.region:
            cmd_args.extend(["--region", args.region])
        if args.no_ml:
            cmd_args.append("--no-ml")
        if args.json:
            cmd_args.append("--json")
        return run_py("run_recommendations.py", cmd_args)

    if args.command == "clean":
        cmd_args = [args.input_csv]
        if args.out:
            cmd_args.extend(["--out", args.out])
        if args.report:
            cmd_args.extend(["--report", args.report])
        if args.outliers:
            cmd_args.append("--outliers")
        return run_py("run_cleaning_pipeline.py", cmd_args)

    return 1


if __name__ == "__main__":
    sys.exit(main())
