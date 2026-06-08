"""
Detect optional AI / ML packages so users can see install tier at a glance.

Core app uses requirements.txt; full AI uses requirements-ai.txt on top.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from typing import Dict, List, Tuple


def probe_optional_imports() -> Dict[str, Tuple[bool, str]]:
    """
    Detect optional packages without fully loading heavy stacks at startup.

    Uses importlib.util.find_spec first (fast). For torch, if the spec exists but
    the extension fails to load (e.g. broken install), records the import error.
    """
    packages = ("torch", "torchvision", "mediapipe", "ultralytics", "tensorflow")
    result: Dict[str, Tuple[bool, str]] = {}
    for name in packages:
        try:
            if importlib.util.find_spec(name) is None:
                result[name] = (False, "not installed")
                continue
            if name == "torch":
                try:
                    __import__(name)
                except Exception as e:  # noqa: BLE001
                    result[name] = (False, str(e).split("\n")[0][:120])
                else:
                    result[name] = (True, "")
            else:
                result[name] = (True, "")
        except Exception as e:  # noqa: BLE001
            result[name] = (False, str(e).split("\n")[0][:120])
    return result


def install_tier_label(status: Dict[str, Tuple[bool, str]]) -> str:
    """Return a short tier name for messaging."""
    torch_ok = status.get("torch", (False, ""))[0]
    if torch_ok and status.get("ultralytics", (False, ""))[0]:
        return "full_ai"
    if torch_ok:
        return "pytorch_only"
    return "lite"


def format_startup_banner(status: Dict[str, Tuple[bool, str]] | None = None) -> str:
    """Multi-line banner for console (and optional logs)."""
    if status is None:
        status = probe_optional_imports()
    tier = install_tier_label(status)
    lines: List[str] = []
    lines.append("")
    lines.append(" SmartCam — install profile")
    lines.append(" " + "-" * 44)
    if tier == "full_ai":
        lines.append(" Tier: FULL AI (torch + ultralytics present)")
        lines.append(" Object detection / YOLO-style paths should be available.")
    elif tier == "pytorch_only":
        lines.append(" Tier: PYTORCH ONLY (torch present, ultralytics missing)")
        lines.append(" Some YOLO paths may be limited. Try: pip install -r requirements-ai.txt")
    else:
        lines.append(" Tier: LITE (core OpenCV only — torch not importable)")
        lines.append(" Face/object YOLO features will be degraded or disabled.")
        lines.append(" For advertised AI stack: pip install -r requirements.txt -r requirements-ai.txt")
    missing = [k for k, (ok, _) in status.items() if not ok]
    if missing:
        lines.append(f" Missing optional packages: {', '.join(missing)}")
    lines.append(" Docs: README.md → Installation (install tiers)")
    lines.append(" " + "-" * 44)
    lines.append("")
    return "\n".join(lines)


def print_startup_banner() -> None:
    """Print install tier unless SMARTCAM_QUIET_INSTALL_BANNER=1."""
    if os.environ.get("SMARTCAM_QUIET_INSTALL_BANNER", "").strip() in ("1", "true", "yes"):
        return
    sys.stdout.write(format_startup_banner())
    sys.stdout.flush()
