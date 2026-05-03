"""
Role Selection Screen
Allows users to choose between Pilot trainee and ATC trainee modes (separate apps).
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

from utils.logging_config import get_logger

logger = get_logger(__name__)

# Project root (parent of `views/`)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ICONS_DIR = _PROJECT_ROOT / "icons"


class RoleSelectionScreen:
    def __init__(self, root, on_role_selected):
        self.root = root
        self.on_role_selected = on_role_selected

        self._resize_job: str | None = None
        self._ttk_style: ttk.Style | None = None

        # Configure the window
        self.root.title("Aviation Assistant — training mode")
        self.root.geometry("800x520")
        self.root.minsize(600, 420)

        # Bind resize (debounced — <Configure> fires very often while dragging)
        self.root.bind("<Configure>", self.on_window_configure)

        # Store original window size for scaling calculations
        self.original_width = 800
        self.original_height = 520
        self.original_font_sizes = {
            "title": 20,
            "subtitle": 11,
            "role_title": 16,
            "button": 12,
            "desc": 10,
            "hint": 9,
        }
        self.original_image_size = (200, 200)

        # Set up the main frame (takefocus so keyboard shortcuts work before Tab into buttons)
        self.main_frame = ttk.Frame(self.root, padding="20", takefocus=tk.TRUE)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame.bind("<KeyPress>", self._on_role_hotkey)

        # Store UI elements for dynamic scaling
        self.ui_elements: dict = {}
        self.original_pil_images: dict = {}
        self.photo_images: dict = {}

        self.setup_ui()

        # Focus the role area so P / A shortcuts work without an extra click when possible
        self.root.after(150, lambda: self.main_frame.focus_set() if self.main_frame.winfo_exists() else None)

    def setup_ui(self):
        """Set up the user interface"""
        self._ttk_style = ttk.Style()
        self._ttk_style.configure("Role.TButton", font=("Arial", self.original_font_sizes["button"]))

        # Header — explicit difference between modes (NN/g: state differences clearly)
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 12))

        self.ui_elements["title_label"] = ttk.Label(
            header_frame,
            text="Choose training mode",
            font=("Arial", self.original_font_sizes["title"], "bold"),
        )
        self.ui_elements["title_label"].pack(anchor=tk.CENTER)

        self.ui_elements["subtitle_label"] = ttk.Label(
            header_frame,
            text=(
                "Each option opens a different workspace: pilot practice (radio, AI ATC, scenarios) "
                "vs ATC practice (traffic, clearances, airport diagram). Pick the one that matches what you are training today."
            ),
            justify=tk.CENTER,
            font=("Arial", self.original_font_sizes["subtitle"]),
            wraplength=720,
        )
        self.ui_elements["subtitle_label"].pack(anchor=tk.CENTER, pady=(8, 0))

        # Roles frame
        roles_frame = ttk.Frame(self.main_frame)
        roles_frame.pack(fill=tk.BOTH, expand=True, pady=(16, 8))
        roles_frame.columnconfigure(0, weight=1)
        roles_frame.columnconfigure(1, weight=1)

        # Load images (paths relative to project root, not CWD)
        self.original_pil_images["pilot"] = self.load_or_create_pil_image("pilot.png", self.original_image_size)
        self.original_pil_images["atc"] = self.load_or_create_pil_image("atc.png", self.original_image_size)

        self.photo_images["pilot"] = ImageTk.PhotoImage(self.original_pil_images["pilot"])
        self.photo_images["atc"] = ImageTk.PhotoImage(self.original_pil_images["atc"])

        pilot_desc_text = (
            "• AI ATC replies, readbacks, phraseology helpers\n"
            "• Scenarios and session-style pilot training\n"
            "• ATIS / comms study tools in one workspace"
        )
        atc_desc_text = (
            "• Ground / tower-style clearances and traffic list\n"
            "• Airport diagram, NPC traffic, workload hints\n"
            "• After you choose ATC, you will pick an airport next"
        )

        # Pilot role
        pilot_frame = ttk.LabelFrame(roles_frame, text="Pilot trainee", padding=10)
        pilot_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=10)

        self.ui_elements["pilot_title"] = ttk.Label(
            pilot_frame,
            text="PILOT",
            font=("Arial", self.original_font_sizes["role_title"], "bold"),
        )
        self.ui_elements["pilot_title"].pack(anchor=tk.CENTER, pady=(0, 8))

        self.ui_elements["pilot_image"] = ttk.Label(pilot_frame, image=self.photo_images["pilot"])
        self.ui_elements["pilot_image"].pack(anchor=tk.CENTER, pady=8)

        self.ui_elements["pilot_desc"] = ttk.Label(
            pilot_frame,
            text=pilot_desc_text,
            justify=tk.CENTER,
            font=("Arial", self.original_font_sizes["desc"]),
        )
        self.ui_elements["pilot_desc"].pack(anchor=tk.CENTER, pady=8, fill=tk.X)

        self.ui_elements["pilot_button"] = ttk.Button(
            pilot_frame,
            text="Pilot trainee workspace",
            command=lambda: self.on_role_selected("pilot"),
            style="Role.TButton",
            width=24,
        )
        self.ui_elements["pilot_button"].pack(anchor=tk.CENTER, pady=8)

        # ATC role
        atc_frame = ttk.LabelFrame(roles_frame, text="ATC trainee", padding=10)
        atc_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=10)

        self.ui_elements["atc_title"] = ttk.Label(
            atc_frame,
            text="AIR TRAFFIC CONTROL",
            font=("Arial", self.original_font_sizes["role_title"], "bold"),
        )
        self.ui_elements["atc_title"].pack(anchor=tk.CENTER, pady=(0, 8))

        self.ui_elements["atc_image"] = ttk.Label(atc_frame, image=self.photo_images["atc"])
        self.ui_elements["atc_image"].pack(anchor=tk.CENTER, pady=8)

        self.ui_elements["atc_desc"] = ttk.Label(
            atc_frame,
            text=atc_desc_text,
            justify=tk.CENTER,
            font=("Arial", self.original_font_sizes["desc"]),
        )
        self.ui_elements["atc_desc"].pack(anchor=tk.CENTER, pady=8, fill=tk.X)

        self.ui_elements["atc_button"] = ttk.Button(
            atc_frame,
            text="ATC trainee workspace",
            command=lambda: self.on_role_selected("atc"),
            style="Role.TButton",
            width=24,
        )
        self.ui_elements["atc_button"].pack(anchor=tk.CENTER, pady=8)

        hint = ttk.Label(
            self.main_frame,
            text="Shortcuts (when this panel has focus): P — Pilot   A — ATC",
            font=("Arial", self.original_font_sizes["hint"]),
            foreground="gray",
        )
        hint.pack(side=tk.BOTTOM, pady=(4, 0))
        self.ui_elements["hint_label"] = hint

    def _on_role_hotkey(self, event: tk.Event) -> str | None:
        if event.keysym in ("p", "P"):
            self.on_role_selected("pilot")
            return "break"
        if event.keysym in ("a", "A"):
            self.on_role_selected("atc")
            return "break"
        return None

    def on_window_configure(self, event: tk.Event) -> None:
        if event.widget != self.root:
            return
        if self._resize_job is not None:
            try:
                self.root.after_cancel(self._resize_job)
            except tk.TclError:
                pass
        self._resize_job = self.root.after(120, self._apply_resize_layout)

    def _apply_resize_layout(self) -> None:
        self._resize_job = None
        try:
            if not self.root.winfo_exists():
                return
        except tk.TclError:
            return

        current_width = self.root.winfo_width()
        current_height = self.root.winfo_height()
        width_scale = current_width / self.original_width
        height_scale = current_height / self.original_height
        scale_factor = min(width_scale, height_scale)

        self.update_fonts(scale_factor)
        self.update_images(scale_factor)
        self.update_layout(scale_factor)

    def update_fonts(self, scale_factor: float) -> None:
        scale_factor = max(0.5, min(scale_factor, 1.5))

        for key, original_size in self.original_font_sizes.items():
            new_size = max(6, int(original_size * scale_factor))

            try:
                if key == "title" and "title_label" in self.ui_elements:
                    self.ui_elements["title_label"].configure(font=("Arial", new_size, "bold"))
                elif key == "subtitle" and "subtitle_label" in self.ui_elements:
                    self.ui_elements["subtitle_label"].configure(font=("Arial", new_size))
                elif key == "role_title":
                    if "pilot_title" in self.ui_elements:
                        self.ui_elements["pilot_title"].configure(font=("Arial", new_size, "bold"))
                    if "atc_title" in self.ui_elements:
                        self.ui_elements["atc_title"].configure(font=("Arial", new_size, "bold"))
                elif key == "button":
                    if self._ttk_style is not None:
                        self._ttk_style.configure("Role.TButton", font=("Arial", new_size))
                elif key == "desc":
                    if "pilot_desc" in self.ui_elements:
                        self.ui_elements["pilot_desc"].configure(font=("Arial", new_size))
                    if "atc_desc" in self.ui_elements:
                        self.ui_elements["atc_desc"].configure(font=("Arial", new_size))
                elif key == "hint" and "hint_label" in self.ui_elements:
                    self.ui_elements["hint_label"].configure(font=("Arial", new_size))
            except tk.TclError:
                pass

    def update_images(self, scale_factor: float) -> None:
        scale_factor = max(0.5, min(scale_factor, 1.5))
        new_width = int(self.original_image_size[0] * scale_factor)
        new_height = int(self.original_image_size[1] * scale_factor)

        if new_width < 1 or new_height < 1:
            return

        for role in ("pilot", "atc"):
            try:
                if role in self.original_pil_images and f"{role}_image" in self.ui_elements:
                    resized_img = self.original_pil_images[role].resize(
                        (new_width, new_height), Image.Resampling.LANCZOS
                    )

                    self.photo_images[role] = ImageTk.PhotoImage(resized_img)
                    self.ui_elements[f"{role}_image"].configure(image=self.photo_images[role])
            except tk.TclError:
                pass

    def update_layout(self, scale_factor: float) -> None:
        scale_factor = max(0.5, min(scale_factor, 1.5))

        try:
            padding = int(20 * scale_factor)
            self.main_frame.configure(padding=padding)

            role_padding = int(10 * scale_factor)

            if "pilot_title" in self.ui_elements and "atc_title" in self.ui_elements:
                pilot_frame = self.ui_elements["pilot_title"].master
                atc_frame = self.ui_elements["atc_title"].master

                pilot_frame.configure(padding=role_padding)
                atc_frame.configure(padding=role_padding)

                frame_width = pilot_frame.winfo_width()
                if frame_width > 20:
                    wrap_pad = int(20 * scale_factor)
                    wraplength = max(120, frame_width - wrap_pad)
                    if "pilot_desc" in self.ui_elements:
                        self.ui_elements["pilot_desc"].configure(wraplength=wraplength)
                    if "atc_desc" in self.ui_elements:
                        self.ui_elements["atc_desc"].configure(wraplength=wraplength)
            if "subtitle_label" in self.ui_elements:
                sw = self.root.winfo_width()
                if sw > 40:
                    self.ui_elements["subtitle_label"].configure(wraplength=max(280, sw - 40))
        except tk.TclError:
            pass

    def load_or_create_pil_image(self, filename: str, size: tuple[int, int]) -> Image.Image:
        """Load a role image from the project icons dir, or create a placeholder."""
        try:
            _ICONS_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning("Could not create icons directory %s: %s", _ICONS_DIR, e)

        filepath = _ICONS_DIR / filename

        try:
            if not filepath.is_file():
                color = (0, 91, 187) if "pilot" in filename else (204, 0, 0)
                img = Image.new("RGB", size, color=color)
                draw = ImageDraw.Draw(img)

                if "pilot" in filename:
                    w, h = size
                    cx, cy = w // 2, h // 2
                    draw.rectangle([cx - 80, cy - 10, cx + 80, cy + 10], fill="white")
                    draw.rectangle([cx - 15, cy - 60, cx + 15, cy + 60], fill="white")
                    draw.rectangle([cx - 30, cy + 40, cx + 30, cy + 60], fill="white")
                else:
                    w, h = size
                    cx, cy = w // 2, h // 2
                    draw.rectangle([cx - 30, cy, cx + 30, cy + 80], fill="white")
                    draw.rectangle([cx - 50, cy - 20, cx + 50, cy], fill="white")
                    draw.ellipse([cx - 40, cy - 70, cx + 40, cy - 20], outline="white", width=8)

                try:
                    img.save(filepath)
                except OSError as e:
                    logger.warning("Could not save placeholder icon %s: %s", filepath, e)

            return Image.open(filepath)
        except Exception as e:
            logger.exception("Error loading/creating PIL image %s: %s", filepath, e)
            return Image.new("RGB", size, color="grey")
