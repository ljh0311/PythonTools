#!/usr/bin/env python3
"""Headless smoke test for mcollama — no Minecraft client needed."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def jar_paths() -> tuple[Path, Path]:
  version = None
  props = ROOT / "gradle.properties"
  for line in props.read_text(encoding="utf-8").splitlines():
    if line.startswith("mod_version="):
      version = line.split("=", 1)[1].strip()
      break
  if not version:
    raise RuntimeError("mod_version not found in gradle.properties")
  fabric = ROOT / "fabric" / "build" / "libs" / f"ollamamod-fabric-{version}.jar"
  forge = ROOT / "forge" / "build" / "libs" / f"ollamamod-forge-{version}.jar"
  return fabric, forge


FABRIC_JAR, FORGE_JAR = jar_paths()
DEFAULT_OLLAMA = "http://localhost:11434"


def run_step(name: str, fn) -> bool:
    try:
        fn()
        print(f"PASS  {name}")
        return True
    except Exception as exc:
        print(f"FAIL  {name}: {exc}")
        return False


def run_gradle(task: str) -> None:
    gradlew = ROOT / ("gradlew.bat" if sys.platform == "win32" else "gradlew")
    result = subprocess.run(
        [str(gradlew), task, "--console=plain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip().splitlines()[-12:]
        detail = "\n".join(tail) if tail else f"exit code {result.returncode}"
        raise RuntimeError(detail)


def gradle_build() -> None:
    run_gradle("build")


def gradle_unit_tests() -> None:
    run_gradle(":common:test")


def check_jar(path: Path, loader_marker: str) -> None:
    if not path.exists():
        raise FileNotFoundError(path)
    with zipfile.ZipFile(path) as jar:
        names = jar.namelist()
    if "assets/ollamamod/lang/en_us.json" not in names:
        raise AssertionError(f"{path.name} missing lang file")
    if not any(n.startswith("com/ollamamod/") and n.endswith(".class") for n in names):
        raise AssertionError(f"{path.name} missing mod classes")
    if loader_marker not in names:
        raise AssertionError(f"{path.name} missing {loader_marker}")


def check_lang_keys() -> None:
    lang = ROOT / "common" / "src" / "main" / "resources" / "assets" / "ollamamod" / "lang" / "en_us.json"
    data = json.loads(lang.read_text(encoding="utf-8"))
    for key in ("gui.ollamamod.chat.title", "gui.ollamamod.chat.send"):
        if key not in data:
            raise AssertionError(f"Missing lang key: {key}")


def ping_ollama(url: str) -> None:
    req = urllib.request.Request(f"{url.rstrip('/')}/api/tags", method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        if resp.status != 200:
            raise AssertionError(f"Ollama returned HTTP {resp.status}")


def optional_ollama_chat(url: str, model: str) -> None:
    body = json.dumps({
        "model": model,
        "prompt": "Reply with exactly: pong",
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if "response" not in payload:
        raise AssertionError("Ollama response missing 'response' field")


def main() -> int:
    parser = argparse.ArgumentParser(description="Headless mcollama smoke test")
    parser.add_argument("--skip-build", action="store_true", help="Skip gradlew build")
    parser.add_argument("--skip-unit-tests", action="store_true", help="Skip JUnit tests")
    parser.add_argument("--skip-ollama", action="store_true", help="Skip Ollama connectivity checks")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA)
    parser.add_argument("--model", default="llama2", help="Model for live generate test")
    parser.add_argument("--live-chat", action="store_true", help="Send one real prompt to Ollama")
    args = parser.parse_args()

    print("mcollama headless smoke test")
    print("=" * 40)

    steps: list[tuple[str, callable]] = [
        ("lang keys present", check_lang_keys),
    ]
    if not args.skip_build:
        steps.insert(0, ("gradle build", gradle_build))
    if not args.skip_unit_tests:
        steps.append(("junit unit tests", gradle_unit_tests))
    steps.extend([
        ("fabric jar packaged", lambda: check_jar(FABRIC_JAR, "fabric.mod.json")),
        ("forge jar packaged", lambda: check_jar(FORGE_JAR, "META-INF/mods.toml")),
    ])

    if not args.skip_ollama:
        def ollama_ping() -> None:
            try:
                ping_ollama(args.ollama_url)
            except urllib.error.URLError as exc:
                raise AssertionError(
                    f"Ollama not reachable at {args.ollama_url}. "
                    f"Start it with: ollama serve ({exc})"
                ) from exc

        steps.append(("ollama reachable", ollama_ping))
        if args.live_chat:
            steps.append((
                "ollama live prompt",
                lambda: optional_ollama_chat(args.ollama_url, args.model),
            ))

    passed = sum(run_step(name, fn) for name, fn in steps)
    failed = len(steps) - passed
    print("=" * 40)
    print(f"Done: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
