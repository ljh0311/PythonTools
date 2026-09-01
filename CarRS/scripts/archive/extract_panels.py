"""Extract setup_*_tab methods from GUI into panel modules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
gui_path = ROOT / "car_rental_recommender_gui.py"
lines = gui_path.read_text(encoding="utf-8").splitlines()


def find_method_range(method_name):
    start = None
    for i, line in enumerate(lines):
        if line == f"    def {method_name}(self):":
            start = i
            break
    if start is None:
        raise ValueError(f"Method not found: {method_name}")
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line.startswith("    def ") and not line.startswith("        "):
            break
        end += 1
    return start, end


targets = {
    "setup_recommendation_tab": "recommendations_panel.py",
    "setup_settings_tab": "settings_panel.py",
    "setup_records_management_tab": "records_panel.py",
}

header_tpl = (
    '"""{title} UI setup (extracted from car_rental_recommender_gui)."""\n\n'
    "import tkinter as tk\n"
    "from tkinter import ttk, filedialog, messagebox\n\n"
    "import pandas as pd\n\n"
    "from car_rental_recommender_core import (\n"
    "    VALID_REGIONS,\n"
    "    get_providers_for_region,\n"
    "    normalize_traditional_rental_provider,\n"
    "    is_traditional_rental,\n"
    ")\n"
    "from components.gui_helper import GUIHelper\n\n\n"
    "def {func}(app):\n"
)

out_dir = ROOT / "components" / "panels"
out_dir.mkdir(parents=True, exist_ok=True)
ranges = {}

for func, fname in targets.items():
    start, end = find_method_range(func)
    ranges[func] = (start, end)
    body_lines = lines[start + 1 : end]
    converted = []
    for ln in body_lines:
        if ln.startswith("        "):
            converted.append("    " + ln[8:].replace("self.", "app."))
        elif ln.strip() == "":
            converted.append("")
        else:
            converted.append("    " + ln.replace("self.", "app."))
    title = fname.replace("_panel.py", "").replace("_", " ").title() + " Panel"
    content = header_tpl.format(title=title, func=func) + "\n".join(converted) + "\n"
    (out_dir / fname).write_text(content, encoding="utf-8")
    print(f"{fname}: lines {start + 2}-{end} ({len(converted)} body lines)")

(out_dir / "__init__.py").write_text(
    "from .records_panel import setup_records_management_tab\n"
    "from .recommendations_panel import setup_recommendation_tab\n"
    "from .settings_panel import setup_settings_tab\n\n"
    "__all__ = [\n"
    '    "setup_records_management_tab",\n'
    '    "setup_recommendation_tab",\n'
    '    "setup_settings_tab",\n'
    "]\n",
    encoding="utf-8",
)

new_lines = lines[:]
for func in sorted(ranges.keys(), key=lambda k: ranges[k][0], reverse=True):
    start, end = ranges[func]
    wrapper = [
        f"    def {func}(self):",
        f'        """Set up tab UI via components.panels.{func}."""',
        f"        from components.panels import {func}",
        f"        {func}(self)",
    ]
    new_lines = new_lines[:start] + wrapper + new_lines[end:]

gui_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
print("Patched car_rental_recommender_gui.py")
