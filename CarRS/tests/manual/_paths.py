"""Paths for manual scripts run from tests/manual/."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DEFAULT_CSV = os.path.join(ROOT, "22 - Sheet1.csv")
