"""Replace monolithic setup_*_tab methods with panel delegation."""
from pathlib import Path

gui_path = Path(__file__).resolve().parent.parent / "car_rental_recommender_gui.py"
lines = gui_path.read_text(encoding="utf-8").splitlines()

replacements = [
    ("setup_recommendation_tab", 304, 1922, "setup_recommendation_tab"),
    ("setup_settings_tab", 2547, 3057, "setup_settings_tab"),
    ("setup_records_management_tab", 3058, 3691, "setup_records_management_tab"),
]

# Process in reverse order so line numbers stay valid
for method, start, end, import_name in sorted(replacements, key=lambda x: -x[1]):
    wrapper = [
        f"    def {method}(self):",
        f'        """Set up the {method.replace("setup_", "").replace("_tab", "").replace("_", " ")} tab (delegates to components.panels)."""',
        f"        from components.panels import {import_name}",
        f"        {import_name}(self)",
    ]
    lines = lines[: start - 1] + wrapper + lines[end:]

# Add panels import near other component imports if not present
text = "\n".join(lines) + "\n"
if "from components.panels import" not in text:
    text = text.replace(
        "from components import LoadingDialog, GUIHelper, OllamaHelper",
        "from components import LoadingDialog, GUIHelper, OllamaHelper\nfrom components.panels import (\n    setup_records_management_tab,\n    setup_recommendation_tab,\n    setup_settings_tab,\n)",
    )

gui_path.write_text(text, encoding="utf-8")
print("GUI updated with panel delegation")
