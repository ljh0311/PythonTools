#!/usr/bin/env python3
"""OpenClaw helper CLI for SmartPersona user profiles."""
import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_WORKDIR = os.path.abspath(os.path.join(SKILL_DIR, "..", "..", ".."))


def workdir() -> str:
    return os.environ.get("SMARTPERSONA_WORKDIR", DEFAULT_WORKDIR)


def profile_path() -> str:
    env = os.environ.get("SMARTPERSONA_PROFILE_PATH", "").strip()
    if env:
        return os.path.abspath(env)
    return os.path.join(workdir(), "user_profile.md")


def cmd_path(_: argparse.Namespace) -> int:
    print(profile_path())
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    path = profile_path()
    if not os.path.isfile(path):
        print("No profile found. Run SmartPersona and teach it, or set SMARTPERSONA_PROFILE_PATH.", file=sys.stderr)
        return 1
    sys.path.insert(0, workdir())
    from profile_exporter import UserProfileExporter

    exporter = UserProfileExporter(workdir())
    text = exporter.extract_agent_context_from_file(path)
    if args.json:
        print(json.dumps({"path": path, "context": text}, indent=2, ensure_ascii=False))
    else:
        print(text)
    return 0 if text else 1


def cmd_profile(args: argparse.Namespace) -> int:
    path = profile_path()
    if not os.path.isfile(path):
        print("No profile found. Run SmartPersona and teach it, or set SMARTPERSONA_PROFILE_PATH.", file=sys.stderr)
        return 1
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if args.json:
        print(json.dumps({"path": path, "markdown": text}, indent=2, ensure_ascii=False))
    else:
        print(text)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SmartPersona OpenClaw helper")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("path", help="Print resolved profile markdown path")

    ctx = sub.add_parser("context", help="Agent context bullets only (for system prompts)")
    ctx.add_argument("--json", action="store_true")

    prof = sub.add_parser("profile", help="Full profile markdown")
    prof.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.command == "path":
        return cmd_path(args)
    if args.command == "context":
        return cmd_context(args)
    if args.command == "profile":
        return cmd_profile(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
