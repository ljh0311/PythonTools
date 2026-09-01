"""Rebuild records_panel.py from git HEAD setup_records_management_tab."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
raw = subprocess.check_output(
    ["git", "show", "HEAD:CarRS/car_rental_recommender_gui.py"],
    cwd=ROOT.parent,
    text=True,
    errors="replace",
)
start = raw.index("    def setup_records_management_tab(self):")
rest = raw[start + 1:]
m = re.search(r"\n    def [a-z_]", rest)
end = start + m.start() + 1 if m else len(raw)
func = raw[start:end]
body = func.split("\n", 1)[1]
body = body.replace("self.", "app.")
body = re.sub(r"^        ", "", body, flags=re.MULTILINE)

header = '''"""Records Panel UI setup."""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd

from car_rental_recommender_core import (
    VALID_REGIONS,
    get_providers_for_region,
    normalize_traditional_rental_provider,
    is_traditional_rental,
    parse_rental_description_with_llm,
    call_ollama_api,
)
from components.gui_helper import GUIHelper
from components.vision_record_import import (
    DEFAULT_VISION_MODEL,
    extract_record_from_image,
    list_vision_models,
    summarize_extraction,
)


def setup_records_management_tab(app):
'''

out_path = ROOT / "components" / "panels" / "records_panel.py"
out_path.write_text(header + body, encoding="utf-8")
print(f"Wrote {out_path} ({len(header + body)} chars)")
