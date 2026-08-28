#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Append-only security audit log (ISO timestamp | action | details)."""

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("the_eyes.audit_log")

_write_lock = threading.Lock()


def write_audit(log_path: Path, action: str, details: str = "") -> None:
    """
    Append one audit line: ``ISO timestamp | action | details``.

    Args:
        log_path: Destination file (created under parent dirs if needed).
        action: Short action label (e.g. ``motion_started``).
        details: Optional context (camera id, counts, paths).
    """
    try:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().isoformat(timespec="seconds")
        line = f"{ts} | {action} | {details}\n"
        with _write_lock:
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(line)
    except OSError as exc:
        logger.error("Failed to write audit log %s: %s", log_path, exc)


def format_delete_summary(result: dict) -> str:
    """Build a compact details string for media delete / auto-delete results."""
    count = result.get("count", 0)
    days = result.get("older_than_days")
    parts = [f"deleted={count}"]
    if days is not None:
        parts.append(f"older_than_days={days}")
    errors = result.get("errors") or []
    if errors:
        parts.append(f"errors={len(errors)}")
    return ", ".join(parts)
