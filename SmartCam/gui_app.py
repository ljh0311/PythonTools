import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
from PIL import Image, ImageTk, ImageDraw, ImageFont
import threading
import time
import os
from datetime import datetime
from typing import Dict, Any
from main import SmartCamera, ImageQualityEnhancer
import json
import argparse
import numpy as np
import traceback
import sys

# Import GUI components
try:
    from gui.dialogs.splash_screen import SplashScreen
    from gui.dialogs.error_dialog import show_error_dialog, show_notice_dialog, show_success_dialog
    from gui.dialogs.progress_dialog import show_progress, update_progress, close_progress, is_progress_cancelled
    from utils.error_handler import handle_error, setup_global_exception_handler
    from config.settings import get_settings
    GUI_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some GUI components not available: {e}")
    GUI_COMPONENTS_AVAILABLE = False

try:
    from gui.input.focus_nav import setup_focus_navigation
except ImportError:
    setup_focus_navigation = None

# Import modern theme
try:
    from gui.styles.modern_theme import (
        apply_modern_theme, get_color, get_spacing, get_font,
        create_card_frame, create_section_label, create_caption_label,
        SPACING, BORDER_RADIUS
    )
    THEME_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Modern theme not available: {e}")
    THEME_AVAILABLE = False
    # Fallback functions
    def get_color(name): return '#000000'
    def get_spacing(size): return 8
    def get_font(name): return ('Segoe UI', 10, 'normal')
    def apply_modern_theme(root, style=None): return style or ttk.Style()
    def create_card_frame(parent, **kwargs): return tk.Frame(parent, **kwargs)
    def create_section_label(parent, text, **kwargs): return tk.Label(parent, text=text, **kwargs)
    def create_caption_label(parent, text, **kwargs): return tk.Label(parent, text=text, **kwargs)
    SPACING = {'xs': 4, 'sm': 8, 'md': 12, 'lg': 16, 'xl': 24}
    BORDER_RADIUS = {'sm': 4, 'md': 6, 'lg': 8}

# Run detection and draw bounding boxes on this size to avoid lag (full-res is expensive).
# Profile-aware preview size (overridden once a SmartCamera with a profile is attached).
DETECTION_PREVIEW_SIZE = (640, 480)


def _preview_size_for_camera(camera, fallback=DETECTION_PREVIEW_SIZE):
    """Return the detection preview size to use for a given camera."""
    profile = getattr(camera, "processing_profile", None) if camera else None
    if profile is not None:
        return profile.detection_preview_size
    return fallback


def _frame_skip_for_camera(camera, fallback=1):
    """Return the preview frame-skip count for a given camera."""
    profile = getattr(camera, "processing_profile", None) if camera else None
    if profile is not None:
        return max(0, int(profile.preview_frame_skip))
    return fallback

# Global error handler
def handle_error(parent, error, context=None, operation="unknown"):
    """Handle errors with proper error dialog or fallback to messagebox."""
    if context is None:
        context = {}
    
    # Preserve explicit operation from context when callers pass it
    if "operation" not in context:
        context["operation"] = operation
    context["timestamp"] = datetime.now().isoformat()
    
    if GUI_COMPONENTS_AVAILABLE:
        try:
            show_error_dialog(parent, error, context)
        except Exception as dialog_error:
            print(f"Error dialog failed: {dialog_error}")
            # Fallback to messagebox
            messagebox.showerror("Error", f"An error occurred: {str(error)}")
    else:
        # Fallback to basic error handling
        error_msg = f"Error: {str(error)}\n\nOperation: {operation}"
        if context:
            error_msg += f"\nContext: {context}"
        messagebox.showerror("Error", error_msg)


def _notify_user(parent, title, message, level="info", details=None):
    """Success / info / warning notices; falls back to messagebox if dialogs are unavailable."""
    if GUI_COMPONENTS_AVAILABLE:
        try:
            show_notice_dialog(parent, title, message, level=level, details=details)
            return
        except Exception:
            pass
    fn = messagebox.showwarning if level == "warning" else messagebox.showinfo
    fn(title, message if not details else f"{message}\n\n{details}")


def _success_notify(parent, title, message, details=None):
    """Success outcome; falls back to messagebox when dialog modules did not import."""
    if GUI_COMPONENTS_AVAILABLE:
        try:
            show_success_dialog(parent, title, message, details=details)
            return
        except Exception:
            pass
    messagebox.showinfo(title, message if not details else f"{message}\n\n{details}")


# Shared camera detection function
def get_available_cameras():
    try:
        return SmartCamera.detect_available_cameras()
    except Exception as e:
        print(f"Camera detection error: {e}")
        return []


# Shared camera selector widget with modern card design
class CameraSelector(tk.Frame):
    def __init__(self, parent, on_select, on_initialize, initial_camera_id=0, after_refresh_callback=None):
        super().__init__(parent, bg=get_color('surface'))
        self.on_select = on_select
        self.on_initialize = on_initialize
        self._after_refresh_callback = after_refresh_callback
        self.cameras = []
        self.selected_camera_id = initial_camera_id
        self.init_btn = None
        self.button_refs = []
        self.card_refs = []
        self.refresh()

    def refresh(self):
        # Clear previous buttons
        for widget in self.winfo_children():
            widget.destroy()
        self.button_refs = []
        self.card_refs = []
        self.cameras = get_available_cameras()
        available = [c for c in self.cameras if c["available"]]
        
        if not available:
            no_cam_label = tk.Label(
                self,
                text="No cameras detected",
                font=get_font('body'),
                fg=get_color('error'),
                bg=get_color('surface')
            )
            no_cam_label.pack(pady=SPACING['md'])
            self.selected_camera_id = None
            self.init_btn = None
            return
        
        # Create container for camera cards
        cards_container = tk.Frame(self, bg=get_color('surface'))
        cards_container.pack(side="left", padx=SPACING['sm'])
        
        # Create modern camera selection cards (compact)
        for i, camera_info in enumerate(available):
            card = self._create_camera_card(cards_container, camera_info)
            card.pack(side="left", padx=SPACING['xs'], pady=SPACING['xs'])
            self.card_refs.append(card)
        
        # Add modern refresh button
        refresh_btn = ttk.Button(
            cards_container,
            text="🔄",
            command=self.refresh,
            width=3
        )
        refresh_btn.pack(side="left", padx=SPACING['sm'], pady=SPACING['sm'])

        # Add Initialize Camera button with modern styling
        btn_container = tk.Frame(self, bg=get_color('surface'))
        btn_container.pack(side="left", padx=SPACING['md'])
        self.init_btn = ttk.Button(
            btn_container,
            text="Initialize Camera",
            command=self._on_initialize,
            style="Action.TButton"
        )
        self.init_btn.pack(pady=SPACING['sm'])
        if self._after_refresh_callback:
            try:
                self._after_refresh_callback()
            except Exception:
                pass

    def get_focusables(self):
        """Return list of (widget, activate_callback) for DPAD/keyboard focus navigation."""
        available = [c for c in self.cameras if c.get("available", True)]
        if len(available) != len(self.card_refs):
            return []
        result = []
        for card, info in zip(self.card_refs, available):
            cid = info["camera_id"]
            result.append((card, lambda cid=cid: self._on_select(cid)))
        return result

    def _create_camera_card(self, parent, camera_info):
        """Create a modern card-style camera button."""
        camera_id = camera_info["camera_id"]
        is_selected = (camera_id == self.selected_camera_id)
        
        # Card frame with modern styling (takefocus for DPAD/keyboard nav)
        card = tk.Frame(
            parent,
            bg=get_color('surface'),
            relief='flat',
            borderwidth=2 if is_selected else 1,
            highlightthickness=0,
            cursor="hand2",
            takefocus=True
        )
        
        # Configure border color based on selection
        if is_selected:
            card.configure(highlightbackground=get_color('primary'), highlightthickness=2)
        else:
            card.configure(highlightbackground=get_color('border'), highlightthickness=1)
        
        # Card content with reduced padding
        content_frame = tk.Frame(card, bg=get_color('surface'))
        content_frame.pack(padx=SPACING['sm'], pady=SPACING['sm'])
        
        # Camera icon/indicator (smaller)
        icon_label = tk.Label(
            content_frame,
            text="📹",
            font=('Segoe UI', 14),
            bg=get_color('surface'),
            fg=get_color('primary') if is_selected else get_color('text_secondary')
        )
        icon_label.pack(pady=(0, SPACING['xs']))
        
        # Camera name (smaller font)
        name_label = tk.Label(
            content_frame,
            text=camera_info['name'],
            font=get_font('body'),
            bg=get_color('surface'),
            fg=get_color('text_primary'),
            wraplength=80
        )
        name_label.pack(pady=(0, 2))
        
        # Resolution (compact)
        res_label = tk.Label(
            content_frame,
            text=f"{camera_info['resolution'][0]}×{camera_info['resolution'][1]}",
            font=get_font('caption'),
            bg=get_color('surface'),
            fg=get_color('text_secondary')
        )
        res_label.pack()
        
        # FPS (compact, inline with resolution if possible)
        fps_label = tk.Label(
            content_frame,
            text=f"{camera_info['fps']:.0f} FPS",
            font=get_font('caption'),
            bg=get_color('surface'),
            fg=get_color('text_tertiary')
        )
        fps_label.pack()
        
        # Backend info if available (only show if not too long)
        if "backend" in camera_info and camera_info["backend"] != "Unknown":
            backend_text = camera_info["backend"]
            if len(backend_text) > 8:
                backend_text = backend_text[:6] + ".."
            backend_label = tk.Label(
                content_frame,
                text=backend_text,
                font=get_font('caption'),
                bg=get_color('surface'),
                fg=get_color('text_tertiary')
            )
            backend_label.pack()
        
        # Bind click event
        def on_card_click(event):
            self._on_select(camera_id)
        
        def on_enter(event):
            if camera_id != self.selected_camera_id:
                card.configure(highlightbackground=get_color('primary_light'), highlightthickness=2)
        
        def on_leave(event):
            if camera_id != self.selected_camera_id:
                card.configure(highlightbackground=get_color('border'), highlightthickness=1)
        
        card.bind("<Button-1>", on_card_click)
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        for widget in [content_frame, icon_label, name_label, res_label, fps_label]:
            widget.bind("<Button-1>", on_card_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
        
        return card

    def _on_select(self, camera_id):
        self.selected_camera_id = camera_id
        # Refresh to update card selection states
        self.refresh()
        self.on_select(camera_id)

    def _on_initialize(self):
        if self.selected_camera_id is not None:
            self.on_initialize(self.selected_camera_id)

    def set_init_btn_state(self, state="normal"):
        if self.init_btn:
            try:
                self.init_btn.configure(state=state)
            except tk.TclError:
                pass

    def set_init_btn_text(self, text):
        if self.init_btn:
            try:
                self.init_btn.configure(text=text)
            except tk.TclError:
                pass


# Modernized SmartCameraGUI
class SmartCameraGUI:
    """GUI application for the AI-powered Smart Camera system."""

    def __init__(self, root):
        self.root = root
        self.root.title("AI Smart Camera System")

        # Window size from config, resizable, centered, capped to screen
        gui_config = get_settings().get("GUI_CONFIG", {}) if GUI_COMPONENTS_AVAILABLE else {}
        window_size_str = gui_config.get("window_size", "1200x800")
        try:
            parts = window_size_str.lower().split("x")
            win_w, win_h = int(parts[0].strip()), int(parts[1].strip())
        except (ValueError, IndexError):
            win_w, win_h = 1200, 800
        min_size = gui_config.get("min_window_size", [800, 600])
        min_w = min_size[0] if isinstance(min_size, (list, tuple)) and len(min_size) >= 2 else 800
        min_h = min_size[1] if isinstance(min_size, (list, tuple)) and len(min_size) >= 2 else 600
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        max_w = int(screen_w * 0.95)
        max_h = int(screen_h * 0.95)
        win_w = min(max(win_w, min_w), max_w)
        win_h = min(max(win_h, min_h), max_h)
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.minsize(min_w, min_h)
        self.root.resizable(True, True)
        self.root.update_idletasks()
        x = (screen_w - win_w) // 2
        y = max(0, (screen_h - win_h) // 2)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # Apply modern theme
        if THEME_AVAILABLE:
            self.style = apply_modern_theme(self.root)
            self.root.configure(bg=get_color('background'))
        else:
            self.style = ttk.Style()
            self.root.configure(bg="#f4f4f4")

        # Initialize camera
        self.camera = None
        self.is_capturing = False
        self.is_recording = False
        self.capture_thread = None
        self.display_thread = None

        # Camera detection
        self.available_cameras = []
        self.selected_camera_id = None

        # GUI variables
        self.enhancement_type_var = tk.StringVar(value="auto")
        self.auto_enhancement_var = tk.BooleanVar(value=True)
        self.face_detection_var = tk.BooleanVar(value=True)
        self.motion_detection_var = tk.BooleanVar(value=True)
        self.object_detection_var = tk.BooleanVar(value=True)

        # Framing/composition guidance
        self.framing_assist_var = tk.BooleanVar(value=True)
        self.framing_min_score_var = tk.DoubleVar(value=0.40)
        self.framing_gate_var = tk.BooleanVar(value=False)

        # Render coalescing: only one preview render queued at a time.
        self._pending_preview_image = None
        self._preview_render_scheduled = False
        
        # Smart AI Capture variables
        self.auto_capture_var = tk.BooleanVar(value=True)
        self.capture_cooldown_var = tk.IntVar(value=5)
        self.max_captures_per_minute_var = tk.IntVar(value=12)
        self.capture_sequence_count_var = tk.IntVar(value=3)
        self.save_detection_overlay_var = tk.BooleanVar(value=True)
        
        # Debug mode
        self.debug_mode_var = tk.BooleanVar(value=False)
        
        # Smart Processing variables
        self.auto_tagging_var = tk.BooleanVar(value=True)
        self.scene_classification_var = tk.BooleanVar(value=True)
        self.anomaly_detection_var = tk.BooleanVar(value=True)
        self.anomaly_sensitivity_var = tk.DoubleVar(value=0.7)
        self.baseline_frames_var = tk.IntVar(value=30)

        # Create GUI components
        self._create_widgets()
        self._setup_layout()

        # Detect cameras on startup
        self._detect_cameras()

        # Bind events
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # DPAD/keyboard focus navigation (RPi, accessibility)
        gui_cfg = get_settings().get("GUI_CONFIG", {}) if GUI_COMPONENTS_AVAILABLE else {}
        if gui_cfg.get("enable_dpad_navigation", True) and setup_focus_navigation:
            self._setup_dpad_navigation()

        # After all widgets are created:
        if self.camera_selector.cameras:
            self._on_camera_selected(self.camera_selector.selected_camera_id)

    def _setup_dpad_navigation(self):
        """Wire Left/Right, Space/Enter, Escape for focus navigation (RPi DPAD)."""
        if not setup_focus_navigation:
            return
        focusables = self.camera_selector.get_focusables()
        if self.camera_selector.init_btn is not None:
            focusables.append(self.camera_selector.init_btn)
        setup_focus_navigation(self.root, focusables, horizontal=True, wrap=True)

    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main frame
        self.main_frame = ttk.Frame(self.root)

        # Modern header with gradient-like background
        self.top_frame = tk.Frame(
            self.main_frame,
            bg=get_color('surface'),
            relief='flat',
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=get_color('border')
        )
        self.top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=0)
        
        # Title with modern styling
        title_container = tk.Frame(self.top_frame, bg=get_color('surface'))
        title_container.pack(side="left", padx=SPACING['xl'], pady=SPACING['lg'], fill='y')
        
        self.title_label = tk.Label(
            title_container,
            text="AI Smart Camera System",
            font=get_font('heading_large'),
            bg=get_color('surface'),
            fg=get_color('primary'),
            anchor='w'
        )
        self.title_label.pack(anchor='w')
        
        # Subtitle
        subtitle_label = tk.Label(
            title_container,
            text="Intelligent Image Capture & Enhancement",
            font=get_font('caption'),
            bg=get_color('surface'),
            fg=get_color('text_tertiary'),
            anchor='w'
        )
        subtitle_label.pack(anchor='w', pady=(SPACING['xs'], 0))

        # Quick modes: presets + privacy (casual / trip use)
        preset_bar = tk.Frame(title_container, bg=get_color('surface'))
        preset_bar.pack(anchor='w', fill='x', pady=(SPACING['sm'], 0))
        tk.Label(
            preset_bar,
            text="Quick mode:",
            font=get_font('caption'),
            bg=get_color('surface'),
            fg=get_color('text_secondary'),
        ).pack(side='left', padx=(0, SPACING['sm']))
        from gui.experience_presets import PRESET_ORDER  # local import keeps startup light

        self.experience_preset_var = tk.StringVar(value=PRESET_ORDER[0])
        self.experience_preset_combo = ttk.Combobox(
            preset_bar,
            textvariable=self.experience_preset_var,
            values=PRESET_ORDER,
            state='readonly',
            width=22,
        )
        self.experience_preset_combo.pack(side='left', padx=(0, SPACING['sm']))
        ttk.Button(
            preset_bar,
            text="Apply mode",
            command=self._apply_experience_preset_from_ui,
            width=12,
        ).pack(side='left', padx=(0, SPACING['sm']))
        ttk.Button(
            preset_bar,
            text="Privacy & saves",
            command=self._show_privacy_and_storage_notice,
            width=16,
        ).pack(side='left')
        
        # Camera selector on the right
        selector_container = tk.Frame(self.top_frame, bg=get_color('surface'))
        selector_container.pack(side="right", padx=SPACING['xl'], pady=SPACING['md'], fill='y')
        
        def _after_camera_refresh():
            if getattr(self, "_setup_dpad_navigation", None):
                gui_cfg = get_settings().get("GUI_CONFIG", {}) if GUI_COMPONENTS_AVAILABLE else {}
                if gui_cfg.get("enable_dpad_navigation", True):
                    self._setup_dpad_navigation()
        self.camera_selector = CameraSelector(
            selector_container, self._on_camera_selected, self._initialize_camera,
            after_refresh_callback=_after_camera_refresh
        )
        self.camera_selector.pack()

        # Modern camera preview frame with card styling
        preview_container = tk.Frame(
            self.main_frame,
            bg=get_color('background'),
            relief='flat'
        )
        preview_container.grid(row=1, column=0, sticky="nsew", padx=SPACING['lg'], pady=SPACING['lg'])
        
        # Preview label frame with modern styling
        preview_label_frame = create_section_label(
            preview_container,
            "Camera Preview"
        )
        preview_label_frame.pack(anchor='w', pady=(0, SPACING['sm']))
        
        # Preview frame with modern card design
        self.preview_frame = tk.Frame(
            preview_container,
            bg=get_color('preview_bg'),
            relief='flat',
            borderwidth=2,
            highlightthickness=0,
            highlightbackground=get_color('border')
        )
        self.preview_frame.pack(fill="both", expand=True)
        
        # Preview label with better placeholder
        self.preview_label = tk.Label(
            self.preview_frame,
            text="Camera not initialized\n\nClick 'Initialize Camera' to start",
            background=get_color('preview_bg'),
            foreground=get_color('text_inverse'),
            font=get_font('body_large'),
            justify='center'
        )
        self.preview_label.pack(fill="both", expand=True)
        
        # FPS overlay label (will be positioned absolutely later)
        self.fps_overlay = tk.Label(
            self.preview_frame,
            text="",
            background=get_color('overlay'),
            foreground=get_color('text_inverse'),
            font=get_font('monospace_small'),
            padx=SPACING['sm'],
            pady=SPACING['xs']
        )
        
        # Resolution overlay label
        self.res_overlay = tk.Label(
            self.preview_frame,
            text="",
            background=get_color('overlay'),
            foreground=get_color('text_inverse'),
            font=get_font('monospace_small'),
            padx=SPACING['sm'],
            pady=SPACING['xs']
        )

        # Modern controls with notebook
        controls_container = tk.Frame(
            self.main_frame,
            bg=get_color('background')
        )
        controls_container.grid(row=1, column=1, sticky="nsew", padx=SPACING['lg'], pady=SPACING['lg'])
        
        self.controls_frame = ttk.Notebook(controls_container)
        self.controls_frame.pack(fill="both", expand=True)

        # AI tab with modern card layout
        self.ai_tab = tk.Frame(self.controls_frame, bg=get_color('background'))
        self.controls_frame.add(self.ai_tab, text="AI Settings")
        
        # Create scrollable canvas for AI tab
        ai_canvas = tk.Canvas(self.ai_tab, bg=get_color('background'), highlightthickness=0)
        ai_scrollbar = ttk.Scrollbar(self.ai_tab, orient="vertical", command=ai_canvas.yview)
        ai_scrollable_frame = tk.Frame(ai_canvas, bg=get_color('background'))
        
        ai_scrollable_frame.bind(
            "<Configure>",
            lambda e: ai_canvas.configure(scrollregion=ai_canvas.bbox("all"))
        )
        
        ai_canvas.create_window((0, 0), window=ai_scrollable_frame, anchor="nw")
        ai_canvas.configure(yscrollcommand=ai_scrollbar.set)

        # Enhancement section with modern card design
        enh_card = create_card_frame(ai_scrollable_frame)
        enh_card.pack(fill="x", padx=SPACING['md'], pady=SPACING['md'])
        
        enh_header = tk.Frame(enh_card, bg=get_color('surface'))
        enh_header.pack(fill="x", padx=SPACING['md'], pady=(SPACING['md'], SPACING['sm']))
        
        enh_title = create_section_label(enh_header, "Enhancement")
        enh_title.pack(anchor='w')
        
        enh_content = tk.Frame(enh_card, bg=get_color('surface'))
        enh_content.pack(fill="x", padx=SPACING['md'], pady=(0, SPACING['md']))

        # Auto enhancement toggle with modern styling
        enh_toggle_frame = tk.Frame(enh_content, bg=get_color('surface'))
        enh_toggle_frame.pack(fill="x", pady=SPACING['sm'])
        
        auto_enh_check = ttk.Checkbutton(
            enh_toggle_frame,
            text="Auto Enhancement",
            variable=self.auto_enhancement_var,
        )
        auto_enh_check.pack(side="left")
        
        enh_caption = create_caption_label(
            enh_toggle_frame,
            "Automatically enhance image quality"
        )
        enh_caption.pack(side="left", padx=(SPACING['md'], 0))

        # Enhancement type selection with modern layout
        type_frame = tk.Frame(enh_content, bg=get_color('surface'))
        type_frame.pack(fill="x", pady=SPACING['sm'])
        
        type_label = tk.Label(
            type_frame,
            text="Enhancement Type:",
            font=get_font('body'),
            bg=get_color('surface'),
            fg=get_color('text_primary'),
            anchor='w'
        )
        type_label.pack(anchor="w", pady=(SPACING['sm'], SPACING['xs']))
        
        enh_combobox = ttk.Combobox(
            type_frame,
            textvariable=self.enhancement_type_var,
            values=[
                "auto",
                "denoise",
                "sharpen",
                "color_correction",
                "exposure_correction",
                "super_resolution",
            ],
            state="readonly",
            width=25,
        )
        enh_combobox.pack(anchor="w", pady=SPACING['xs'])

        # Detection section with modern card design
        det_card = create_card_frame(ai_scrollable_frame)
        det_card.pack(fill="x", padx=SPACING['md'], pady=SPACING['md'])
        
        det_header = tk.Frame(det_card, bg=get_color('surface'))
        det_header.pack(fill="x", padx=SPACING['md'], pady=(SPACING['md'], SPACING['sm']))
        
        det_title = create_section_label(det_header, "Detection")
        det_title.pack(anchor='w')
        
        det_content = tk.Frame(det_card, bg=get_color('surface'))
        det_content.pack(fill="x", padx=SPACING['md'], pady=(0, SPACING['md']))

        # Detection toggles with modern styling
        det_options = [
            ("Face Detection", self.face_detection_var, "Detect and recognize faces"),
            ("Motion Detection", self.motion_detection_var, "Detect movement in frame"),
            ("Object Detection", self.object_detection_var, "Identify objects in scene"),
        ]

        for text, var, desc in det_options:
            option_frame = tk.Frame(det_content, bg=get_color('surface'))
            option_frame.pack(fill="x", pady=SPACING['sm'])
            
            det_check = ttk.Checkbutton(option_frame, text=text, variable=var)
            det_check.pack(side="left")
            
            det_caption = create_caption_label(option_frame, desc)
            det_caption.pack(side="left", padx=(SPACING['md'], 0))

        # Smart AI Capture section with modern card design
        ai_capture_card = create_card_frame(ai_scrollable_frame)
        ai_capture_card.pack(fill="x", padx=SPACING['md'], pady=SPACING['md'])
        
        ai_capture_header = tk.Frame(ai_capture_card, bg=get_color('surface'))
        ai_capture_header.pack(fill="x", padx=SPACING['md'], pady=(SPACING['md'], SPACING['sm']))
        
        ai_capture_title = create_section_label(ai_capture_header, "Smart AI Capture")
        ai_capture_title.pack(anchor='w')
        
        ai_capture_content = tk.Frame(ai_capture_card, bg=get_color('surface'))
        ai_capture_content.pack(fill="x", padx=SPACING['md'], pady=(0, SPACING['md']))

        # Auto capture toggle with modern styling
        auto_capture_frame = tk.Frame(ai_capture_content, bg=get_color('surface'))
        auto_capture_frame.pack(fill="x", pady=SPACING['sm'])
        
        auto_cap_check = ttk.Checkbutton(
            auto_capture_frame,
            text="Auto Capture",
            variable=self.auto_capture_var,
        )
        auto_cap_check.pack(side="left")
        
        auto_cap_caption = create_caption_label(
            auto_capture_frame,
            "Automatically capture when AI detects events"
        )
        auto_cap_caption.pack(side="left", padx=(SPACING['md'], 0))

        # Capture settings with modern layout
        capture_settings_frame = tk.Frame(ai_capture_content, bg=get_color('surface'))
        capture_settings_frame.pack(fill="x", pady=SPACING['md'])

        # Cooldown setting with modern styling
        cooldown_frame = tk.Frame(capture_settings_frame, bg=get_color('surface'))
        cooldown_frame.pack(fill="x", pady=SPACING['sm'])
        
        cooldown_label = tk.Label(
            cooldown_frame,
            text="Capture Cooldown (seconds):",
            font=get_font('body'),
            bg=get_color('surface'),
            fg=get_color('text_primary'),
            anchor='w'
        )
        cooldown_label.pack(side="left")
        
        cooldown_value_label = tk.Label(
            cooldown_frame,
            textvariable=self.capture_cooldown_var,
            font=get_font('monospace'),
            bg=get_color('surface'),
            fg=get_color('primary'),
            width=4
        )
        cooldown_value_label.pack(side="right", padx=(SPACING['sm'], 0))
        
        cooldown_scale = ttk.Scale(
            cooldown_frame,
            from_=1,
            to=30,
            variable=self.capture_cooldown_var,
            orient="horizontal"
        )
        cooldown_scale.pack(side="left", fill="x", expand=True, padx=(SPACING['md'], SPACING['sm']))

        # Max captures per minute with modern styling
        max_captures_frame = tk.Frame(capture_settings_frame, bg=get_color('surface'))
        max_captures_frame.pack(fill="x", pady=SPACING['sm'])
        
        max_captures_label = tk.Label(
            max_captures_frame,
            text="Max Captures/Minute:",
            font=get_font('body'),
            bg=get_color('surface'),
            fg=get_color('text_primary'),
            anchor='w'
        )
        max_captures_label.pack(side="left")
        
        max_captures_value_label = tk.Label(
            max_captures_frame,
            textvariable=self.max_captures_per_minute_var,
            font=get_font('monospace'),
            bg=get_color('surface'),
            fg=get_color('primary'),
            width=4
        )
        max_captures_value_label.pack(side="right", padx=(SPACING['sm'], 0))
        
        max_captures_scale = ttk.Scale(
            max_captures_frame,
            from_=1,
            to=60,
            variable=self.max_captures_per_minute_var,
            orient="horizontal"
        )
        max_captures_scale.pack(side="left", fill="x", expand=True, padx=(SPACING['md'], SPACING['sm']))

        # Sequence count with modern styling
        sequence_frame = tk.Frame(capture_settings_frame, bg=get_color('surface'))
        sequence_frame.pack(fill="x", pady=SPACING['sm'])
        
        sequence_label = tk.Label(
            sequence_frame,
            text="Sequence Frames:",
            font=get_font('body'),
            bg=get_color('surface'),
            fg=get_color('text_primary'),
            anchor='w'
        )
        sequence_label.pack(side="left")
        
        sequence_value_label = tk.Label(
            sequence_frame,
            textvariable=self.capture_sequence_count_var,
            font=get_font('monospace'),
            bg=get_color('surface'),
            fg=get_color('primary'),
            width=4
        )
        sequence_value_label.pack(side="right", padx=(SPACING['sm'], 0))
        
        sequence_scale = ttk.Scale(
            sequence_frame,
            from_=1,
            to=10,
            variable=self.capture_sequence_count_var,
            orient="horizontal"
        )
        sequence_scale.pack(side="left", fill="x", expand=True, padx=(SPACING['md'], SPACING['sm']))

        # Save detection overlay with modern styling
        overlay_frame = tk.Frame(ai_capture_content, bg=get_color('surface'))
        overlay_frame.pack(fill="x", pady=SPACING['sm'])
        
        overlay_check = ttk.Checkbutton(
            overlay_frame,
            text="Save Detection Overlay",
            variable=self.save_detection_overlay_var,
            command=self._update_ai_capture_settings
        )
        overlay_check.pack(side="left")
        
        overlay_caption = create_caption_label(
            overlay_frame,
            "Save frames with detection boxes drawn"
        )
        overlay_caption.pack(side="left", padx=(SPACING['md'], 0))

        # Debug mode toggle with modern styling
        debug_frame = tk.Frame(ai_capture_content, bg=get_color('surface'))
        debug_frame.pack(fill="x", pady=SPACING['sm'])
        
        debug_check = ttk.Checkbutton(
            debug_frame,
            text="Enable Debug Mode",
            variable=self.debug_mode_var,
            command=self._update_ai_capture_settings
        )
        debug_check.pack(side="left")
        
        debug_caption = create_caption_label(
            debug_frame,
            "Show more detailed detection information"
        )
        debug_caption.pack(side="left", padx=(SPACING['md'], 0))
        
        # Pack canvas and scrollbar for AI tab
        ai_canvas.pack(side="left", fill="both", expand=True)
        ai_scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel to AI canvas
        def _bind_mousewheel_to_descendants(parent, handler):
            parent.bind("<MouseWheel>", handler)
            parent.bind("<Button-4>", handler)  # Linux/Raspberry Pi scroll up
            parent.bind("<Button-5>", handler)  # Linux/Raspberry Pi scroll down
            for child in parent.winfo_children():
                _bind_mousewheel_to_descendants(child, handler)

        def _on_ai_mousewheel(event):
            if getattr(event, "num", None) == 4:
                step = -1
            elif getattr(event, "num", None) == 5:
                step = 1
            else:
                delta = getattr(event, "delta", 0)
                step = int(-1 * (delta / 120)) if delta else 0
            if step:
                ai_canvas.yview_scroll(step, "units")
        ai_canvas.bind("<MouseWheel>", _on_ai_mousewheel)
        _bind_mousewheel_to_descendants(ai_scrollable_frame, _on_ai_mousewheel)

        # Bind events to update settings
        self.auto_capture_var.trace('w', lambda *args: self._update_ai_capture_settings())
        self.capture_cooldown_var.trace('w', lambda *args: self._update_ai_capture_settings())
        self.max_captures_per_minute_var.trace('w', lambda *args: self._update_ai_capture_settings())
        self.capture_sequence_count_var.trace('w', lambda *args: self._update_ai_capture_settings())
        self.save_detection_overlay_var.trace('w', lambda *args: self._update_ai_capture_settings())
        self.debug_mode_var.trace('w', lambda *args: self._update_ai_capture_settings())

        self.framing_assist_var.trace('w', lambda *args: self._update_framing_settings())
        self.framing_min_score_var.trace('w', lambda *args: self._update_framing_settings())
        self.framing_gate_var.trace('w', lambda *args: self._update_framing_settings())

        # Smart Processing tab
        self.smart_processing_tab = tk.Frame(self.controls_frame, bg=get_color('background'))
        self.controls_frame.add(self.smart_processing_tab, text="Smart Processing")
        
        # Create scrollable canvas for Smart Processing tab
        sp_canvas = tk.Canvas(self.smart_processing_tab, bg=get_color('background'), highlightthickness=0)
        sp_scrollbar = ttk.Scrollbar(self.smart_processing_tab, orient="vertical", command=sp_canvas.yview)
        sp_scrollable_frame = tk.Frame(sp_canvas, bg=get_color('background'))
        
        sp_scrollable_frame.bind(
            "<Configure>",
            lambda e: sp_canvas.configure(scrollregion=sp_canvas.bbox("all"))
        )
        
        sp_canvas.create_window((0, 0), window=sp_scrollable_frame, anchor="nw")
        sp_canvas.configure(yscrollcommand=sp_scrollbar.set)
        
        # Auto-Tagging section
        auto_tag_card = create_card_frame(sp_scrollable_frame)
        auto_tag_card.pack(fill="x", padx=SPACING['md'], pady=SPACING['md'])
        
        auto_tag_header = tk.Frame(auto_tag_card, bg=get_color('surface'))
        auto_tag_header.pack(fill="x", padx=SPACING['md'], pady=(SPACING['md'], SPACING['sm']))
        
        auto_tag_title = create_section_label(auto_tag_header, "Auto-Tagging")
        auto_tag_title.pack(anchor='w')
        
        auto_tag_content = tk.Frame(auto_tag_card, bg=get_color('surface'))
        auto_tag_content.pack(fill="x", padx=SPACING['md'], pady=(0, SPACING['md']))
        
        auto_tag_toggle_frame = tk.Frame(auto_tag_content, bg=get_color('surface'))
        auto_tag_toggle_frame.pack(fill="x", pady=SPACING['sm'])
        
        auto_tag_check = ttk.Checkbutton(
            auto_tag_toggle_frame,
            text="Enable Auto-Tagging",
            variable=self.auto_tagging_var,
            command=self._update_smart_processing_settings
        )
        auto_tag_check.pack(side="left")
        
        auto_tag_caption = create_caption_label(
            auto_tag_toggle_frame,
            "Automatically tag images based on detected content"
        )
        auto_tag_caption.pack(side="left", padx=(SPACING['md'], 0))
        
        # Scene Classification section
        scene_card = create_card_frame(sp_scrollable_frame)
        scene_card.pack(fill="x", padx=SPACING['md'], pady=SPACING['md'])
        
        scene_header = tk.Frame(scene_card, bg=get_color('surface'))
        scene_header.pack(fill="x", padx=SPACING['md'], pady=(SPACING['md'], SPACING['sm']))
        
        scene_title = create_section_label(scene_header, "Scene Classification")
        scene_title.pack(anchor='w')
        
        scene_content = tk.Frame(scene_card, bg=get_color('surface'))
        scene_content.pack(fill="x", padx=SPACING['md'], pady=(0, SPACING['md']))
        
        scene_toggle_frame = tk.Frame(scene_content, bg=get_color('surface'))
        scene_toggle_frame.pack(fill="x", pady=SPACING['sm'])
        
        scene_check = ttk.Checkbutton(
            scene_toggle_frame,
            text="Enable Scene Classification",
            variable=self.scene_classification_var,
            command=self._update_smart_processing_settings
        )
        scene_check.pack(side="left")
        
        scene_caption = create_caption_label(
            scene_toggle_frame,
            "Classify scenes as indoor/outdoor, day/night, crowd level, etc."
        )
        scene_caption.pack(side="left", padx=(SPACING['md'], 0))
        
        # Anomaly Detection section
        anomaly_card = create_card_frame(sp_scrollable_frame)
        anomaly_card.pack(fill="x", padx=SPACING['md'], pady=SPACING['md'])
        
        anomaly_header = tk.Frame(anomaly_card, bg=get_color('surface'))
        anomaly_header.pack(fill="x", padx=SPACING['md'], pady=(SPACING['md'], SPACING['sm']))
        
        anomaly_title = create_section_label(anomaly_header, "Anomaly Detection")
        anomaly_title.pack(anchor='w')
        
        anomaly_content = tk.Frame(anomaly_card, bg=get_color('surface'))
        anomaly_content.pack(fill="x", padx=SPACING['md'], pady=(0, SPACING['md']))
        
        anomaly_toggle_frame = tk.Frame(anomaly_content, bg=get_color('surface'))
        anomaly_toggle_frame.pack(fill="x", pady=SPACING['sm'])
        
        anomaly_check = ttk.Checkbutton(
            anomaly_toggle_frame,
            text="Enable Anomaly Detection",
            variable=self.anomaly_detection_var,
            command=self._update_smart_processing_settings
        )
        anomaly_check.pack(side="left")
        
        anomaly_caption = create_caption_label(
            anomaly_toggle_frame,
            "Detect unusual events and unexpected patterns"
        )
        anomaly_caption.pack(side="left", padx=(SPACING['md'], 0))
        
        # Anomaly sensitivity setting
        sensitivity_frame = tk.Frame(anomaly_content, bg=get_color('surface'))
        sensitivity_frame.pack(fill="x", pady=SPACING['sm'])
        
        sensitivity_label = tk.Label(
            sensitivity_frame,
            text="Sensitivity:",
            font=get_font('body'),
            bg=get_color('surface'),
            fg=get_color('text_primary'),
            anchor='w'
        )
        sensitivity_label.pack(side="left")
        
        sensitivity_value_label = tk.Label(
            sensitivity_frame,
            textvariable=self.anomaly_sensitivity_var,
            font=get_font('monospace'),
            bg=get_color('surface'),
            fg=get_color('primary'),
            width=4
        )
        sensitivity_value_label.pack(side="right", padx=(SPACING['sm'], 0))
        
        sensitivity_scale = ttk.Scale(
            sensitivity_frame,
            from_=0.0,
            to=1.0,
            variable=self.anomaly_sensitivity_var,
            orient="horizontal"
        )
        sensitivity_scale.pack(side="left", fill="x", expand=True, padx=(SPACING['md'], SPACING['sm']))
        sensitivity_scale.configure(command=lambda v: self._update_smart_processing_settings())
        
        # Baseline frames setting
        baseline_frame = tk.Frame(anomaly_content, bg=get_color('surface'))
        baseline_frame.pack(fill="x", pady=SPACING['sm'])
        
        baseline_label = tk.Label(
            baseline_frame,
            text="Baseline Frames:",
            font=get_font('body'),
            bg=get_color('surface'),
            fg=get_color('text_primary'),
            anchor='w'
        )
        baseline_label.pack(side="left")
        
        baseline_value_label = tk.Label(
            baseline_frame,
            textvariable=self.baseline_frames_var,
            font=get_font('monospace'),
            bg=get_color('surface'),
            fg=get_color('primary'),
            width=4
        )
        baseline_value_label.pack(side="right", padx=(SPACING['sm'], 0))
        
        baseline_scale = ttk.Scale(
            baseline_frame,
            from_=10,
            to=100,
            variable=self.baseline_frames_var,
            orient="horizontal"
        )
        baseline_scale.pack(side="left", fill="x", expand=True, padx=(SPACING['md'], SPACING['sm']))
        baseline_scale.configure(command=lambda v: self._update_smart_processing_settings())
        
        baseline_caption = create_caption_label(
            anomaly_content,
            "Number of frames to use for establishing baseline patterns"
        )
        baseline_caption.pack(anchor='w', pady=(SPACING['xs'], 0))
        
        # Pack canvas and scrollbar for Smart Processing tab
        sp_canvas.pack(side="left", fill="both", expand=True)
        sp_scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel to Smart Processing canvas
        def _on_sp_mousewheel(event):
            if getattr(event, "num", None) == 4:
                step = -1
            elif getattr(event, "num", None) == 5:
                step = 1
            else:
                delta = getattr(event, "delta", 0)
                step = int(-1 * (delta / 120)) if delta else 0
            if step:
                sp_canvas.yview_scroll(step, "units")
        sp_canvas.bind("<MouseWheel>", _on_sp_mousewheel)
        _bind_mousewheel_to_descendants(sp_scrollable_frame, _on_sp_mousewheel)
        
        # Actions tab with modern card-based buttons
        self.actions_tab = tk.Frame(self.controls_frame, bg=get_color('background'))
        self.controls_frame.add(self.actions_tab, text="Actions")
        
        # Create a scrollable frame for actions
        actions_canvas = tk.Canvas(
            self.actions_tab,
            bg=get_color('background'),
            highlightthickness=0
        )
        actions_scrollbar = ttk.Scrollbar(
            self.actions_tab,
            orient="vertical",
            command=actions_canvas.yview
        )
        actions_scrollable_frame = tk.Frame(
            actions_canvas,
            bg=get_color('background')
        )
        
        actions_scrollable_frame.bind(
            "<Configure>",
            lambda e: actions_canvas.configure(scrollregion=actions_canvas.bbox("all"))
        )
        
        actions_canvas.create_window((0, 0), window=actions_scrollable_frame, anchor="nw")
        actions_canvas.configure(yscrollcommand=actions_scrollbar.set)
        
        # Action buttons with modern card styling
        action_buttons = [
            ("🎥", "Start Capture", self._toggle_capture, "Start/stop continuous capture"),
            ("📸", "Capture Image", self._capture_image, "Take a single high-quality photo"),
            ("🎬", "Start Recording", self._toggle_recording, "Record video with audio"),
            ("⚙️", "Camera Settings", self._show_camera_settings, "Configure camera parameters"),
            ("ℹ️", "Camera Info", self._show_camera_info, "View camera specifications"),
            ("🔍", "Test Detections", self._test_detections, "Test AI detection components"),
            ("🔄", "Refresh Components", self._refresh_detection_components, "Reinitialize detection components"),
            ("📁", "Open Captures", self._open_captures_folder, "Browse captured files"),
            ("🔍", "Search by Tags", self._show_tag_search, "Search captures by tags"),
            ("📊", "View Statistics", self._show_metadata_statistics, "View tag and scene statistics"),
            ("🧹", "Storage Cleanup", self._show_cleanup_dialog, "Clean old capture files"),
            ("📊", "Storage Stats", self._show_storage_stats, "View storage statistics"),
        ]
        
        for icon, text, command, tooltip in action_buttons:
            # Create modern button card
            btn_card = create_card_frame(actions_scrollable_frame)
            btn_card.pack(fill="x", pady=SPACING['sm'], padx=SPACING['md'])
            
            # Button content frame
            btn_content = tk.Frame(btn_card, bg=get_color('surface'), cursor="hand2")
            btn_content.pack(fill="x", padx=SPACING['md'], pady=SPACING['md'])
            
            # Icon and text container
            icon_text_frame = tk.Frame(btn_content, bg=get_color('surface'))
            icon_text_frame.pack(side="left", fill="x", expand=True)
            
            # Icon label
            icon_label = tk.Label(
                icon_text_frame,
                text=icon,
                font=('Segoe UI', 18),
                bg=get_color('surface'),
                fg=get_color('primary')
            )
            icon_label.pack(side="left", padx=(0, SPACING['sm']))
            
            # Text container
            text_container = tk.Frame(icon_text_frame, bg=get_color('surface'))
            text_container.pack(side="left", fill="x", expand=True)
            
            # Button text
            btn_text_label = tk.Label(
                text_container,
                text=text,
                font=get_font('body_large'),
                bg=get_color('surface'),
                fg=get_color('text_primary'),
                anchor='w'
            )
            btn_text_label.pack(anchor='w')
            
            # Tooltip caption
            tooltip_label = create_caption_label(text_container, tooltip)
            tooltip_label.pack(anchor='w', pady=(SPACING['xs'], 0))
            
            # Bind click events
            def make_command(cmd):
                def on_click(event):
                    cmd()
                return on_click
            
            click_handler = make_command(command)
            for widget in [btn_card, btn_content, icon_text_frame, text_container, icon_label, btn_text_label, tooltip_label]:
                widget.bind("<Button-1>", click_handler)
            
            # Hover effects
            def on_enter(event):
                btn_card.configure(highlightbackground=get_color('primary_light'), highlightthickness=2)
            
            def on_leave(event):
                btn_card.configure(highlightbackground=get_color('border'), highlightthickness=1)
            
            btn_card.bind("<Enter>", on_enter)
            btn_card.bind("<Leave>", on_leave)
            for widget in [btn_content, icon_text_frame, text_container, icon_label, btn_text_label]:
                widget.bind("<Enter>", on_enter)
                widget.bind("<Leave>", on_leave)
        
        # Pack canvas and scrollbar
        actions_canvas.pack(side="left", fill="both", expand=True)
        actions_scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel to actions canvas
        def _on_actions_mousewheel(event):
            if getattr(event, "num", None) == 4:
                step = -1
            elif getattr(event, "num", None) == 5:
                step = 1
            else:
                delta = getattr(event, "delta", 0)
                step = int(-1 * (delta / 120)) if delta else 0
            if step:
                actions_canvas.yview_scroll(step, "units")
        actions_canvas.bind("<MouseWheel>", _on_actions_mousewheel)
        _bind_mousewheel_to_descendants(actions_scrollable_frame, _on_actions_mousewheel)

        # Modern status bar with card styling
        status_container = tk.Frame(
            self.main_frame,
            bg=get_color('surface'),
            relief='flat',
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=get_color('border')
        )
        status_container.grid(row=2, column=0, columnspan=2, sticky="ew", pady=0)
        
        # Status content frame
        status_content = tk.Frame(status_container, bg=get_color('surface'))
        status_content.pack(fill="x", padx=SPACING['lg'], pady=SPACING['md'])
        
        # Status indicators on the left
        status_left = tk.Frame(status_content, bg=get_color('surface'))
        status_left.pack(side="left", fill="y")
        
        # Status label with icon (store reference for updates)
        self.status_icon_label = tk.Label(
            status_left,
            text="●",
            font=('Segoe UI', 12),
            bg=get_color('surface'),
            fg=get_color('success')
        )
        self.status_icon_label.pack(side="left", padx=(0, SPACING['sm']))
        
        self.status_label = tk.Label(
            status_left,
            text="Ready",
            font=get_font('body_large'),
            bg=get_color('surface'),
            fg=get_color('text_primary')
        )
        self.status_label.pack(side="left", padx=(0, SPACING['xl']))
        
        # FPS indicator with modern styling
        fps_container = tk.Frame(status_left, bg=get_color('surface'))
        fps_container.pack(side="left", padx=SPACING['md'])
        
        fps_label_text = tk.Label(
            fps_container,
            text="FPS:",
            font=get_font('caption'),
            bg=get_color('surface'),
            fg=get_color('text_tertiary')
        )
        fps_label_text.pack(side="left", padx=(0, SPACING['xs']))
        
        self.fps_label = tk.Label(
            fps_container,
            text="--",
            font=get_font('monospace'),
            bg=get_color('surface'),
            fg=get_color('primary')
        )
        self.fps_label.pack(side="left")
        
        # Detection indicator with modern styling
        detection_container = tk.Frame(status_left, bg=get_color('surface'))
        detection_container.pack(side="left", padx=SPACING['md'])
        
        detection_label_text = tk.Label(
            detection_container,
            text="Detections:",
            font=get_font('caption'),
            bg=get_color('surface'),
            fg=get_color('text_tertiary')
        )
        detection_label_text.pack(side="left", padx=(0, SPACING['xs']))
        
        self.detection_label = tk.Label(
            detection_container,
            text="--",
            font=get_font('monospace'),
            bg=get_color('surface'),
            fg=get_color('primary')
        )
        self.detection_label.pack(side="left")
        
        # Progress bar on the right
        progress_container = tk.Frame(status_content, bg=get_color('surface'))
        progress_container.pack(side="right", fill="x", expand=True, padx=(SPACING['xl'], 0))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_container,
            variable=self.progress_var,
            maximum=100,
            length=200
        )
        self.progress_bar.pack(fill="x", expand=True)

        # Configure grid weights
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=2)
        self.main_frame.grid_columnconfigure(1, weight=1)

    def _detect_cameras(self):
        """Detect available cameras and create selection buttons."""
        try:
            self._update_status("Detecting cameras...")
            self.root.update_idletasks()

            # Clear existing camera buttons
            for widget in self.camera_selector.winfo_children():
                widget.destroy()

            # Detect cameras
            self.available_cameras = get_available_cameras()

            # Check if there are any available cameras
            available = [c for c in self.available_cameras if c.get("available", False)]

            if not self.available_cameras or not available:
                # No cameras detected or no available cameras
                ttk.Label(
                    self.camera_selector, text="No cameras detected", foreground="red"
                ).pack(pady=10)
                self._update_status("No cameras detected")
                
                # Update preview label to show camera unavailable message
                if hasattr(self, 'preview_label'):
                    self.preview_label.config(
                        text="Camera not available, please restart",
                        image="",  # Clear any existing image
                        background=get_color('preview_bg'),
                        foreground=get_color('text_inverse'),
                        font=get_font('body_large'),
                        justify='center'
                    )
                    # Clear image reference if it exists
                    if hasattr(self.preview_label, 'image'):
                        self.preview_label.image = None
                
                return

            # Create camera selection buttons
            for i, camera_info in enumerate(self.available_cameras):
                if camera_info["available"]:
                    # Create button for available camera
                    btn_text = f"📹 {camera_info['name']}\n"
                    btn_text += f"Resolution: {camera_info['resolution'][0]}x{camera_info['resolution'][1]}\n"
                    btn_text += f"FPS: {camera_info['fps']:.1f}"

                    # Add backend info if available
                    if "backend" in camera_info and camera_info["backend"] != "Unknown":
                        btn_text += f"\nBackend: {camera_info['backend']}"

                    btn = ttk.Button(
                        self.camera_selector,
                        text=btn_text,
                        command=lambda cid=camera_info[
                            "camera_id"
                        ]: self._select_camera(cid),
                        width=25,
                    )
                    btn.pack(side="left", padx=5, pady=5)

            available_count = len([c for c in self.available_cameras if c["available"]])
            self._update_status(f"Detected {available_count} available camera(s)")

        except Exception as e:
            self._update_status(f"Camera detection failed: {str(e)}")
            handle_error(self.root, e, {"operation": "camera_detection"})
            
            # Update preview label to show camera unavailable message on error
            if hasattr(self, 'preview_label'):
                self.preview_label.config(
                    text="Camera not available, please restart",
                    image="",  # Clear any existing image
                    background=get_color('preview_bg'),
                    foreground=get_color('text_inverse'),
                    font=get_font('body_large'),
                    justify='center'
                )
                # Clear image reference if it exists
                if hasattr(self.preview_label, 'image'):
                    self.preview_label.image = None

    def _select_camera(self, camera_id: int):
        """Select a camera and update UI."""
        self.selected_camera_id = camera_id

        # Update button states
        for widget in self.camera_selector.winfo_children():
            if isinstance(widget, ttk.Button) and widget["state"] != "disabled":
                # Reset button style
                widget.configure(style="TButton")

        # Highlight selected camera button
        for widget in self.camera_selector.winfo_children():
            if isinstance(widget, ttk.Button) and widget["state"] != "disabled":
                if f"Camera {camera_id}" in widget["text"]:
                    # Create a custom style for selected button
                    style = ttk.Style()
                    style.configure(
                        "Selected.TButton", background="#4CAF50", foreground="white"
                    )
                    widget.configure(style="Selected.TButton")
                    break

        # Get camera info for status
        camera_info = next(
            (c for c in self.available_cameras if c["camera_id"] == camera_id), None
        )
        if camera_info:
            status_text = f"Selected: {camera_info['name']} ({camera_info['resolution'][0]}x{camera_info['resolution'][1]})"
            self._update_status(status_text)
        else:
            self._update_status(f"Selected Camera {camera_id}")

        # Automatically initialize the selected camera
        self._initialize_camera(camera_id)

    def _initialize_camera(self, camera_id=None):
        if camera_id is not None:
            self.selected_camera_id = camera_id
        
        if self.selected_camera_id is None:
            _notify_user(self.root, "Camera", "Please select a camera first.", level="warning")
            return
        
        try:
            self.status_label.config(text=f"Initializing camera {self.selected_camera_id}...")
            self.camera_selector.set_init_btn_state("disabled")
            self.camera_selector.set_init_btn_text("Initializing...")
            
            # Show progress dialog if available
            if GUI_COMPONENTS_AVAILABLE:
                self.progress_dialog = show_progress(
                    self.root, 
                    "Initializing Camera", 
                    "Setting up camera and AI components...",
                    can_cancel=True,
                    cancel_callback=self._cancel_camera_init
                )
            
            # Initialize camera in a separate thread
            def init_camera():
                try:
                    # Update progress
                    if GUI_COMPONENTS_AVAILABLE:
                        update_progress(0.2, "Loading camera drivers...")
                    
                    self.camera = SmartCamera(camera_id=self.selected_camera_id)
                    
                    if GUI_COMPONENTS_AVAILABLE:
                        update_progress(0.5, "Initializing AI components...")
                    
                    # Test detection components
                    self._test_detection_components_on_init()
                    
                    if GUI_COMPONENTS_AVAILABLE:
                        update_progress(0.8, "Finalizing setup...")
                    
                    self.root.after(0, self._on_camera_initialized)
                    
                except Exception as e:
                    self.root.after(0, lambda: self._on_camera_error(e))
            
            threading.Thread(target=init_camera, daemon=True).start()
            
        except Exception as e:
            self._on_camera_error(e)

    def _cancel_camera_init(self):
        """Cancel camera initialization."""
        try:
            if hasattr(self, 'camera') and self.camera:
                self.camera.cleanup()
                self.camera = None
            
            self.status_label.config(text="Camera initialization cancelled")
            self.camera_selector.set_init_btn_state("normal")
            self.camera_selector.set_init_btn_text("Initialize Camera")
            
            if GUI_COMPONENTS_AVAILABLE:
                close_progress()
                
        except Exception as e:
            print(f"Error cancelling camera init: {e}")

    def _on_camera_initialized(self):
        """Handle successful camera initialization."""
        try:
            if GUI_COMPONENTS_AVAILABLE:
                update_progress(1.0, "Camera ready!")
                close_progress()
            
            # Load smart processing settings from config
            try:
                from config.settings import get_smart_processing_config
                sp_config = get_smart_processing_config()
                if sp_config:
                    self.auto_tagging_var.set(sp_config.get('auto_tagging_enabled', True))
                    self.scene_classification_var.set(sp_config.get('scene_classification_enabled', True))
                    self.anomaly_detection_var.set(sp_config.get('anomaly_detection_enabled', True))
                    self.anomaly_sensitivity_var.set(sp_config.get('anomaly_sensitivity', 0.7))
                    self.baseline_frames_var.set(sp_config.get('baseline_frames', 30))
                    # Apply settings to camera
                    self._update_smart_processing_settings()
            except Exception as e:
                logger.warning(f"Failed to load smart processing config: {e}")
            
            self._update_status(f"Camera {self.selected_camera_id} Ready", "success")
            try:
                from utils.ai_stack_status import install_tier_label, probe_optional_imports

                if install_tier_label(probe_optional_imports()) == "lite":
                    self.root.after(
                        800,
                        lambda: self._update_status(
                            "Tip: pip install -r requirements-ai.txt for full AI (torch/YOLO). "
                            "See README → Install tiers.",
                            "warning",
                        ),
                    )
            except Exception:
                pass
            self.camera_selector.set_init_btn_state("normal")
            self.camera_selector.set_init_btn_text("Initialize Camera")
            
            self.is_capturing = True
            self.display_thread = threading.Thread(
                target=self._display_loop, daemon=True
            )
            self.display_thread.start()
            
            if hasattr(self, '_on_ready') and self._on_ready:
                self.root.after(0, self._on_ready)
                
        except Exception as e:
            self._on_camera_error(e)

    def _on_camera_error(self, error):
        """Handle camera initialization error."""
        try:
            if GUI_COMPONENTS_AVAILABLE:
                close_progress()
            
            self._update_status(f"Camera Error: {error}", "error")
            self.camera_selector.set_init_btn_state("normal")
            self.camera_selector.set_init_btn_text("Initialize Camera")
            
            err = error if isinstance(error, Exception) else RuntimeError(str(error))
            handle_error(
                self.root,
                err,
                {"camera_id": self.selected_camera_id},
                operation="camera_initialize",
            )
                
        except Exception as e:
            print(f"Error handling camera error: {e}")

    def _test_detection_components_on_init(self):
        """Test detection components during initialization."""
        if not self.camera:
            return
            
        print("\n" + "="*50)
        print("TESTING DETECTION COMPONENTS ON INIT")
        print("="*50)
        
        # Test with a single frame from the shared single reader
        try:
            frame = self.camera.get_preview_frame()
            if frame is not None:
                print(f"Frame captured: {frame.shape}")
                
                if self.camera.face_analyzer:
                    try:
                        faces = self.camera.face_analyzer.detect_faces(frame)
                        print(f"✅ Face detection working: {len(faces)} faces found")
                    except Exception as e:
                        print(f"❌ Face detection failed: {e}")
                else:
                    print("❌ Face analyzer not available")
                
                if self.camera.motion_detector:
                    try:
                        motion = self.camera.motion_detector.detect_motion(frame)
                        print(f"✅ Motion detection working: motion={motion}")
                    except Exception as e:
                        print(f"❌ Motion detection failed: {e}")
                else:
                    print("❌ Motion detector not available")
                
                print(f"Settings - Face: {self.face_detection_var.get()}, Motion: {self.motion_detection_var.get()}")
                
            else:
                print("❌ Could not capture test frame")
                
        except Exception as e:
            print(f"❌ Detection test failed: {e}")
        
        print("="*50)

    def _check_detection_status(self):
        """Check and display the status of detection components."""
        if not self.camera:
            return
            
        status_info = []
        
        # Check face analyzer
        if self.camera.face_analyzer:
            status_info.append("✅ Face Detection: Ready")
        else:
            status_info.append("❌ Face Detection: Not available")
            
        # Check motion detector
        if self.camera.motion_detector:
            status_info.append("✅ Motion Detection: Ready")
        else:
            status_info.append("❌ Motion Detection: Not available")
            
        # Check object detector
        if self.camera.object_detector:
            status_info.append("✅ Object Detection: Ready")
        else:
            status_info.append("❌ Object Detection: Not available")
            
        # Check image enhancer
        if self.camera.image_enhancer:
            status_info.append("✅ Image Enhancement: Ready")
        else:
            status_info.append("❌ Image Enhancement: Not available")
        
        # Display status in console for debugging
        print("\n" + "="*50)
        print("DETECTION COMPONENT STATUS:")
        print("="*50)
        for status in status_info:
            print(status)
        print("="*50)
        
        # Update status label with detection info
        ready_count = sum(1 for status in status_info if "✅" in status)
        total_count = len(status_info)
        self._update_status(f"Camera ready - {ready_count}/{total_count} AI components active")

    def _setup_layout(self):
        """Setup the layout of widgets with modern spacing."""
        self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)

    def _toggle_capture(self):
        """Toggle camera capture on/off."""
        if not self.camera:
            _notify_user(self.root, "Camera", "Please initialize the camera first.", level="warning")
            return

        if not self.is_capturing:
            self._start_capture()
        else:
            self._stop_capture()

    def _start_capture(self):
        """Start camera capture."""
        try:
            self.camera.start_capture()
            self.is_capturing = True
            self.camera_selector.set_init_btn_text("Stop Capture")
            self._update_status("Capture started")
            self.display_thread = threading.Thread(
                target=self._display_loop, daemon=True
            )
            self.display_thread.start()
        except Exception as e:
            self._update_status(f"Failed to start capture: {str(e)}")
            handle_error(self.root, e, {
                "operation": "start_capture",
                "camera_id": self.selected_camera_id,
                "is_capturing": self.is_capturing
            })

    def _stop_capture(self):
        """Stop camera capture."""
        try:
            self.camera.stop_capture()
            self.is_capturing = False
            self.camera_selector.set_init_btn_text("Initialize Camera")
            self._update_status("Capture stopped")
        except Exception as e:
            self._update_status(f"Failed to stop capture: {str(e)}")
            handle_error(self.root, e, {
                "operation": "stop_capture",
                "camera_id": self.selected_camera_id,
                "is_capturing": self.is_capturing
            })

    def _display_loop(self):
        fps_counter = 0
        fps_start_time = time.time()
        error_count = 0
        max_errors = 10  # Maximum consecutive errors before stopping
        
        # Debug counters for detection status
        detection_status = {
            'faces_detected': 0,
            'objects_detected': 0,
            'motion_detected': 0,
            'last_update': time.time()
        }
        
        while self.is_capturing and self.camera:
            try:
                frame = self.camera.get_preview_frame()
                if frame is None:
                    error_count += 1
                    if error_count > max_errors:
                        self._update_status("Camera connection lost")
                        break
                    time.sleep(0.05)
                    continue
                
                # Reset error count on successful frame
                error_count = 0
                # Per-frame detection cache for framing engine integration
                live_detections = {'faces': [], 'objects': []}
                
                # --- AI enhancement ---
                if self.auto_enhancement_var.get() and self.camera.image_enhancer:
                    try:
                        frame = self.camera.image_enhancer.enhance_image_quality(
                            frame, self.enhancement_type_var.get()
                        )
                    except Exception as e:
                        print(f"Enhancement error: {e}")
                        # Continue without enhancement
                
                # --- AI detection overlays (on downscaled frame to reduce lag) ---
                preview_size = _preview_size_for_camera(self.camera)
                small = cv2.resize(frame, preview_size)
                overlay_frame = small.copy()
                current_detections = {'faces': 0, 'objects': 0, 'motion': False}
                scene_info = None
                anomaly_info = None
                
                # Face detection
                if self.face_detection_var.get() and self.camera.face_analyzer:
                    try:
                        faces = self.camera.face_analyzer.detect_faces(overlay_frame)
                        current_detections['faces'] = len(faces)
                        live_detections['faces'] = faces
                        for face in faces:
                            x, y, w, h = face["bbox"]
                            cv2.rectangle(
                                overlay_frame, (x, y), (x + w, y + h), (0, 255, 0), 2
                            )
                            cv2.putText(
                                overlay_frame,
                                "Face",
                                (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                (0, 255, 0),
                                2,
                            )
                    except Exception as e:
                        print(f"Face detection error: {e}")
                
                # Object detection
                if self.object_detection_var.get() and self.camera.object_detector:
                    try:
                        objects = self.camera._detect_objects(overlay_frame)
                        current_detections['objects'] = len(objects)
                        live_detections['objects'] = objects
                        for obj in objects:
                            x, y, w, h = obj["bbox"]
                            label = obj.get("class_name", "Object")
                            cv2.rectangle(
                                overlay_frame, (x, y), (x + w, y + h), (255, 0, 0), 2
                            )
                            cv2.putText(
                                overlay_frame,
                                label,
                                (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                (255, 0, 0),
                                2,
                            )
                    except Exception as e:
                        print(f"Object detection error: {e}")
                
                # Motion detection
                if self.motion_detection_var.get() and self.camera.motion_detector:
                    try:
                        motion = self.camera.motion_detector.detect_motion(overlay_frame)
                        current_detections['motion'] = motion
                        if motion:
                            h, w = overlay_frame.shape[:2]
                            cv2.rectangle(
                                overlay_frame, (0, 0), (w - 1, h - 1), (0, 0, 255), 8
                            )
                            # Add motion text
                            cv2.putText(
                                overlay_frame,
                                "MOTION DETECTED",
                                (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                1,
                                (0, 0, 255),
                                2,
                            )
                    except Exception as e:
                        print(f"Motion detection error: {e}")
                
                # AI-assisted framing overlay on the live preview.
                if (
                    self.framing_assist_var.get()
                    and getattr(self.camera, "framing_engine", None) is not None
                ):
                    try:
                        framing_score = self.camera.framing_engine.score(
                            overlay_frame.shape, live_detections,
                        )
                        if framing_score.has_subject:
                            from framing_engine import draw_framing_overlay as _draw_framing
                            overlay_frame = _draw_framing(
                                overlay_frame,
                                framing_score,
                                show_grid=True,
                                show_subject=False,
                                show_score=True,
                            )
                    except Exception as e:
                        print(f"Framing overlay error: {e}")

                # Update detection status (every 2 seconds to avoid spam)
                if time.time() - detection_status['last_update'] > 2.0:
                    detection_status['faces_detected'] = current_detections['faces']
                    detection_status['objects_detected'] = current_detections['objects']
                    detection_status['motion_detected'] = current_detections['motion']
                    detection_status['last_update'] = time.time()
                    
                    detection_text = f"Detections: F:{current_detections['faces']} O:{current_detections['objects']}"
                    if current_detections['motion']:
                        detection_text += " M:YES"
                    else:
                        detection_text += " M:NO"
                    
                    if self.debug_mode_var.get():
                        debug_info = []
                        debug_info.append(f"Face Analyzer: {'✅' if self.camera.face_analyzer else '❌'}")
                        debug_info.append(f"Motion Detector: {'✅' if self.camera.motion_detector else '❌'}")
                        debug_info.append(f"Object Detector: {'✅' if self.camera.object_detector else '❌'}")
                        debug_info.append(f"Face Enabled: {'✅' if self.face_detection_var.get() else '❌'}")
                        debug_info.append(f"Motion Enabled: {'✅' if self.motion_detection_var.get() else '❌'}")
                        debug_info.append(f"Object Enabled: {'✅' if self.object_detection_var.get() else '❌'}")
                        
                        detection_text += f" | Debug: {' '.join(debug_info)}"
                    
                    self._after_safe(self.detection_label.configure, text=detection_text)
                
                # Hand off rendering to the Tk main thread (RGB color order).
                try:
                    rgb_frame = cv2.cvtColor(overlay_frame, cv2.COLOR_BGR2RGB)
                    self._schedule_preview_render(rgb_frame)
                except Exception as e:
                    print(f"Display update error: {e}")
                
                fps_counter += 1
                if time.time() - fps_start_time >= 1.0:
                    fps = fps_counter / (time.time() - fps_start_time)
                    self._after_safe(self.fps_label.configure, text=f"FPS: {fps:.1f}")
                    fps_counter = 0
                    fps_start_time = time.time()
                
                time.sleep(0.03)
                
            except Exception as e:
                error_count += 1
                print(f"Display loop error: {e}")
                if error_count > max_errors:
                    self._update_status("Display loop failed - too many errors")
                    break
                time.sleep(0.1)

    def _capture_image(self):
        """Capture a high-quality image."""
        if not self.camera:
            _notify_user(self.root, "Camera", "Please initialize the camera first.", level="warning")
            return

        try:
            filename = self.camera.capture_high_quality_image(
                self.enhancement_type_var.get()
            )
            if filename:
                self._update_status(f"Image captured: {os.path.basename(filename)}")
                _success_notify(
                    self.root,
                    "Image captured",
                    "Image saved successfully.",
                    details=filename,
                )
            else:
                self._update_status("Failed to capture image")
                handle_error(
                    self.root,
                    RuntimeError("Failed to capture image."),
                    {"camera_id": self.selected_camera_id},
                    operation="capture_image",
                )

        except Exception as e:
            self._update_status(f"Capture error: {str(e)}")
            handle_error(self.root, e, {
                "operation": "capture_image",
                "enhancement_type": self.enhancement_type_var.get(),
                "camera_id": self.selected_camera_id
            })

    def _toggle_recording(self):
        """Toggle video recording."""
        if not self.camera:
            _notify_user(self.root, "Camera", "Please initialize the camera first.", level="warning")
            return

        if not self.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        """Start video recording."""
        try:
            self.camera.start_recording()
            self.is_recording = True
            self.camera_selector.set_init_btn_text("Stop Recording")
            self._update_status("Recording started")
        except Exception as e:
            self._update_status(f"Failed to start recording: {str(e)}")
            handle_error(self.root, e, {
                "operation": "start_recording",
                "camera_id": self.selected_camera_id,
                "is_recording": self.is_recording
            })

    def _stop_recording(self):
        """Stop video recording."""
        try:
            self.camera.stop_recording()
            self.is_recording = False
            self.camera_selector.set_init_btn_text("Start Recording")
            self._update_status("Recording stopped")
        except Exception as e:
            self._update_status(f"Failed to stop recording: {str(e)}")
            handle_error(self.root, e, {
                "operation": "stop_recording",
                "camera_id": self.selected_camera_id,
                "is_recording": self.is_recording
            })

    def _show_camera_settings(self):
        """Show camera settings dialog with only real, working properties."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Camera Settings")
        dialog.transient(self.root)
        dialog.grab_set()

        # Only show real, settable camera properties
        # Map property names to OpenCV property IDs
        cam_props = [
            ("Brightness", cv2.CAP_PROP_BRIGHTNESS),
            ("Contrast", cv2.CAP_PROP_CONTRAST),
            ("Saturation", cv2.CAP_PROP_SATURATION),
            ("Hue", cv2.CAP_PROP_HUE),
            ("Gain", cv2.CAP_PROP_GAIN),
            ("Exposure", cv2.CAP_PROP_EXPOSURE),
            ("Focus", cv2.CAP_PROP_FOCUS),
        ]
        settings_frame = ttk.Frame(dialog, padding=10)
        settings_frame.pack(fill="both", expand=True)
        row = 0
        settings_vars = {}
        for label, prop_id in cam_props:
            try:
                val = self.camera.cap.get(prop_id)
                if val == -1 or val is None:
                    continue  # Property not supported
                ttk.Label(settings_frame, text=f"{label}:").grid(row=row, column=0, sticky="w", pady=2)
                var = tk.DoubleVar(value=val)
                widget = ttk.Scale(settings_frame, from_=-100, to=300, variable=var, orient="horizontal")
                widget.grid(row=row, column=1, sticky="ew", pady=2, padx=(5, 0))
                settings_vars[prop_id] = var
                row += 1
            except Exception:
                continue
        # Buttons
        button_frame = ttk.Frame(settings_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        ttk.Button(
            button_frame,
            text="Apply",
            command=lambda: self._apply_camera_settings(settings_vars, dialog),
        ).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=5)

    def _apply_camera_settings(self, settings_vars, dialog):
        """Apply camera settings using OpenCV property IDs."""
        try:
            for prop_id, var in settings_vars.items():
                self.camera.cap.set(prop_id, var.get())
            self._update_status("Camera settings applied")
            dialog.destroy()
            _success_notify(
                self.root,
                "Camera settings",
                "Camera settings were applied successfully.",
            )
        except Exception as e:
            handle_error(self.root, e, {
                "camera_id": self.selected_camera_id,
                "settings_count": len(settings_vars),
            }, operation="apply_camera_settings")

    def _show_camera_info(self):
        """Show camera information."""
        if not self.camera:
            _notify_user(self.root, "Camera", "Please initialize the camera first.", level="warning")
            return

        info = self.camera.get_camera_info()

        info_text = "Camera Information:\n\n"
        for key, value in info.items():
            info_text += f"{key.title()}: {value}\n"

        _notify_user(self.root, "Camera Info", info_text.strip(), level="info")

    def _test_detections(self):
        """Test AI detection components."""
        if not self.camera:
            _notify_user(self.root, "Camera", "Please initialize the camera first.", level="warning")
            return

        try:
            frame = self.camera.get_preview_frame()
            if frame is None:
                handle_error(
                    self.root,
                    RuntimeError("Failed to capture a test frame from the camera."),
                    {"camera_id": self.selected_camera_id},
                    operation="test_detections",
                )
                return

            test_results = []
            
            # Test face detection
            if self.camera.face_analyzer:
                try:
                    faces = self.camera.face_analyzer.detect_faces(frame)
                    test_results.append(f"✅ Face Detection: {len(faces)} faces found")
                except Exception as e:
                    test_results.append(f"❌ Face Detection: Error - {str(e)}")
            else:
                test_results.append("❌ Face Detection: Not available")

            # Test object detection
            if self.camera.object_detector:
                try:
                    objects = self.camera._detect_objects(frame)
                    test_results.append(f"✅ Object Detection: {len(objects)} objects found")
                    if objects:
                        object_types = [obj.get('class_name', 'Unknown') for obj in objects]
                        test_results.append(f"   Objects: {', '.join(object_types)}")
                except Exception as e:
                    test_results.append(f"❌ Object Detection: Error - {str(e)}")
            else:
                test_results.append("❌ Object Detection: Not available")

            # Test motion detection
            if self.camera.motion_detector:
                try:
                    motion = self.camera.motion_detector.detect_motion(frame)
                    test_results.append(f"✅ Motion Detection: {'Motion detected' if motion else 'No motion'}")
                except Exception as e:
                    test_results.append(f"❌ Motion Detection: Error - {str(e)}")
            else:
                test_results.append("❌ Motion Detection: Not available")

            # Test image enhancement
            if self.camera.image_enhancer:
                try:
                    enhanced = self.camera.image_enhancer.enhance_image_quality(frame, 'auto')
                    test_results.append("✅ Image Enhancement: Working")
                except Exception as e:
                    test_results.append(f"❌ Image Enhancement: Error - {str(e)}")
            else:
                test_results.append("❌ Image Enhancement: Not available")

            # Display results
            result_text = "AI Detection Test Results:\n\n" + "\n".join(test_results)
            _success_notify(
                self.root,
                "Detection test",
                "Component self-check finished.",
                details=result_text,
            )

        except Exception as e:
            handle_error(self.root, e, {}, operation="test_detections")

    def _refresh_detection_components(self):
        """Refresh/reinitialize detection components."""
        if not self.camera:
            _notify_user(self.root, "Camera", "Please initialize the camera first.", level="warning")
            return

        try:
            self._update_status("Refreshing detection components...")
            
            # Reinitialize detection components
            self.camera._load_ai_models()
            
            # Check status after refresh
            self._check_detection_status()
            
            _success_notify(
                self.root,
                "Detection",
                "Detection components were refreshed successfully.",
            )
            
        except Exception as e:
            handle_error(self.root, e, {}, operation="refresh_detection_components")

    def _open_captures_folder(self):
        """Open the captures folder."""
        try:
            captures_path = os.path.abspath(self.camera.storage_settings["output_dir"])
            if os.path.exists(captures_path):
                os.startfile(captures_path)  # Windows
            else:
                _notify_user(
                    self.root,
                    "Captures",
                    "Captures folder was not found.",
                    level="info",
                )
        except Exception as e:
            handle_error(self.root, e, {}, operation="open_captures_folder")

    def _show_tag_search(self):
        """Show tag search dialog."""
        if not self.camera:
            _notify_user(self.root, "Camera", "Please initialize the camera first.", level="warning")
            return

        try:
            from utils.metadata_manager import MetadataManager
            
            # Initialize metadata manager
            metadata_manager = MetadataManager(self.camera.storage_settings["output_dir"])
            
            # Get all available tags
            tag_stats = metadata_manager.get_tag_statistics()
            available_tags = list(tag_stats.keys())
            
            if not available_tags:
                _notify_user(
                    self.root,
                    "Tags",
                    "No tags were found in captured images yet.",
                    level="info",
                    details=(
                        "Tags are generated when you capture with AI features enabled "
                        "(for example auto-tagging and detection-based capture)."
                    ),
                )
                return
            
            # Create search dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("Search by Tags")
            dialog.geometry("500x600")
            dialog.transient(self.root)
            dialog.grab_set()

            main_frame = ttk.Frame(dialog, padding=10)
            main_frame.pack(fill="both", expand=True)

            # Title
            ttk.Label(main_frame, text="Search Captures by Tags", font=("Segoe UI", 16, "bold")).pack(pady=(0, 20))

            # Search entry
            search_frame = ttk.LabelFrame(main_frame, text="Search Tags", padding=10)
            search_frame.pack(fill="x", pady=5)

            search_var = tk.StringVar()
            search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40)
            search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
            search_entry.focus()

            # Match mode
            match_mode_var = tk.BooleanVar(value=False)  # False = match any, True = match all
            match_frame = ttk.Frame(search_frame)
            match_frame.pack(fill="x", pady=(10, 0))
            ttk.Radiobutton(match_frame, text="Match Any Tag", variable=match_mode_var, value=False).pack(side="left", padx=5)
            ttk.Radiobutton(match_frame, text="Match All Tags", variable=match_mode_var, value=True).pack(side="left", padx=5)

            # Available tags list
            tags_frame = ttk.LabelFrame(main_frame, text="Available Tags", padding=10)
            tags_frame.pack(fill="both", expand=True, pady=5)

            # Scrollable listbox
            tags_listbox_frame = ttk.Frame(tags_frame)
            tags_listbox_frame.pack(fill="both", expand=True)

            tags_listbox = tk.Listbox(tags_listbox_frame, selectmode=tk.MULTIPLE, height=10)
            tags_scrollbar = ttk.Scrollbar(tags_listbox_frame, orient="vertical", command=tags_listbox.yview)
            tags_listbox.configure(yscrollcommand=tags_scrollbar.set)

            tags_listbox.pack(side="left", fill="both", expand=True)
            tags_scrollbar.pack(side="right", fill="y")

            # Populate tags listbox with counts
            for tag in available_tags:
                count = tag_stats.get(tag, 0)
                tags_listbox.insert(tk.END, f"{tag} ({count})")

            # Results frame
            results_frame = ttk.LabelFrame(main_frame, text="Search Results", padding=10)
            results_frame.pack(fill="both", expand=True, pady=5)

            results_text = tk.Text(results_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
            results_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=results_text.yview)
            results_text.configure(yscrollcommand=results_scrollbar.set)

            results_text.pack(side="left", fill="both", expand=True)
            results_scrollbar.pack(side="right", fill="y")

            def perform_search():
                """Perform the tag search."""
                # Get selected tags from listbox
                selected_indices = tags_listbox.curselection()
                selected_tags = [available_tags[i] for i in selected_indices if i < len(available_tags)]
                
                # Also get tags from search entry
                search_text = search_var.get().strip()
                if search_text:
                    # Split by comma and strip whitespace
                    entry_tags = [tag.strip() for tag in search_text.split(",") if tag.strip()]
                    # Combine with selected tags, removing duplicates
                    selected_tags = list(set(selected_tags + entry_tags))

                if not selected_tags:
                    results_text.config(state=tk.NORMAL)
                    results_text.delete(1.0, tk.END)
                    results_text.insert(1.0, "Please select or enter at least one tag to search.")
                    results_text.config(state=tk.DISABLED)
                    return

                # Perform search
                match_all = match_mode_var.get()
                matching_images = metadata_manager.search_by_tags(selected_tags, match_all=match_all)

                # Display results
                results_text.config(state=tk.NORMAL)
                results_text.delete(1.0, tk.END)
                
                if matching_images:
                    results_text.insert(1.0, f"Found {len(matching_images)} matching image(s):\n\n")
                    for img_path in matching_images[:50]:  # Limit to first 50
                        results_text.insert(tk.END, f"• {os.path.basename(img_path)}\n")
                    if len(matching_images) > 50:
                        results_text.insert(tk.END, f"\n... and {len(matching_images) - 50} more")
                else:
                    results_text.insert(1.0, f"No images found matching tags: {', '.join(selected_tags)}")
                
                results_text.config(state=tk.DISABLED)

            # Buttons
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill="x", pady=10)

            ttk.Button(button_frame, text="Search", command=perform_search).pack(side="left", padx=5)
            ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side="right", padx=5)

            # Bind Enter key to search
            search_entry.bind("<Return>", lambda e: perform_search())

        except Exception as e:
            handle_error(self.root, e, {}, operation="tag_search")

    def _show_metadata_statistics(self):
        """Show metadata statistics dialog."""
        if not self.camera:
            _notify_user(self.root, "Camera", "Please initialize the camera first.", level="warning")
            return

        try:
            from utils.metadata_manager import MetadataManager
            
            # Initialize metadata manager
            metadata_manager = MetadataManager(self.camera.storage_settings["output_dir"])
            
            # Get statistics
            tag_stats = metadata_manager.get_tag_statistics()
            scene_stats = metadata_manager.get_scene_statistics()
            event_stats = metadata_manager.get_event_type_statistics()
            
            # Create statistics dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("Metadata Statistics")
            dialog.geometry("600x700")
            dialog.transient(self.root)
            dialog.grab_set()

            main_frame = ttk.Frame(dialog, padding=10)
            main_frame.pack(fill="both", expand=True)

            # Scrollable canvas
            canvas = tk.Canvas(main_frame)
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Title
            ttk.Label(scrollable_frame, text="Metadata Statistics", font=("Segoe UI", 16, "bold")).pack(pady=(0, 20))

            # Tag statistics
            if tag_stats:
                tag_frame = ttk.LabelFrame(scrollable_frame, text="Tag Statistics", padding=10)
                tag_frame.pack(fill="x", pady=5)

                tag_text = tk.Text(tag_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
                tag_scrollbar = ttk.Scrollbar(tag_frame, orient="vertical", command=tag_text.yview)
                tag_text.configure(yscrollcommand=tag_scrollbar.set)

                tag_text.pack(side="left", fill="both", expand=True)
                tag_scrollbar.pack(side="right", fill="y")

                tag_text.config(state=tk.NORMAL)
                for tag, count in list(tag_stats.items())[:30]:  # Top 30 tags
                    tag_text.insert(tk.END, f"{tag}: {count}\n")
                if len(tag_stats) > 30:
                    tag_text.insert(tk.END, f"\n... and {len(tag_stats) - 30} more tags")
                tag_text.config(state=tk.DISABLED)
            else:
                ttk.Label(scrollable_frame, text="No tag statistics available").pack(pady=5)

            # Scene statistics
            if scene_stats:
                scene_frame = ttk.LabelFrame(scrollable_frame, text="Scene Statistics", padding=10)
                scene_frame.pack(fill="x", pady=5)

                for scene_type, stats in scene_stats.items():
                    if stats:
                        type_label = ttk.Label(scene_frame, text=f"{scene_type.replace('_', ' ').title()}:", font=("Segoe UI", 10, "bold"))
                        type_label.pack(anchor="w", pady=(5, 2))
                        
                        for value, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                            ttk.Label(scene_frame, text=f"  {value}: {count}").pack(anchor="w", padx=20)

            # Event type statistics
            if event_stats:
                event_frame = ttk.LabelFrame(scrollable_frame, text="Event Type Statistics", padding=10)
                event_frame.pack(fill="x", pady=5)

                for event_type, count in event_stats.items():
                    ttk.Label(event_frame, text=f"{event_type.replace('_', ' ').title()}: {count}").pack(anchor="w")

            # Close button
            ttk.Button(scrollable_frame, text="Close", command=dialog.destroy).pack(pady=20)

        except Exception as e:
            handle_error(self.root, e, {}, operation="metadata_statistics")

    def _show_cleanup_dialog(self):
        """Show the storage cleanup dialog."""
        if not self.camera:
            _notify_user(self.root, "Camera", "Please initialize the camera first.", level="warning")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Storage Cleanup")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Main frame
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Title
        ttk.Label(main_frame, text="Storage Cleanup", font=("Segoe UI", 16, "bold")).pack(pady=(0, 20))

        # Age selection
        age_frame = ttk.LabelFrame(main_frame, text="Select Age Threshold", padding=10)
        age_frame.pack(fill="x", pady=10)

        age_var = tk.IntVar(value=24)
        age_options = [
            (1, "1 hour"),
            (6, "6 hours"),
            (12, "12 hours"),
            (24, "1 day"),
            (48, "2 days"),
            (72, "3 days"),
            (168, "1 week")
        ]

        for value, text in age_options:
            ttk.Radiobutton(age_frame, text=text, variable=age_var, value=value).pack(anchor="w", pady=2)

        # Preview button
        preview_frame = ttk.Frame(main_frame)
        preview_frame.pack(fill="x", pady=10)
        
        ttk.Button(
            preview_frame, 
            text="Preview Files to Delete", 
            command=lambda: self._preview_cleanup(age_var.get(), dialog)
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            preview_frame, 
            text="Clean Now", 
            command=lambda: self._execute_cleanup(age_var.get(), dialog)
        ).pack(side="left")

        # Status area
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding=10)
        status_frame.pack(fill="both", expand=True, pady=10)
        
        self.cleanup_status_text = tk.Text(status_frame, height=10, wrap="word")
        self.cleanup_status_text.pack(fill="both", expand=True)
        
        # Scrollbar for status text
        scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=self.cleanup_status_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.cleanup_status_text.configure(yscrollcommand=scrollbar.set)

    def _preview_cleanup(self, age_hours, dialog):
        """Preview files that would be deleted."""
        try:
            self.cleanup_status_text.delete(1.0, tk.END)
            self.cleanup_status_text.insert(tk.END, "Scanning for files to delete...\n")
            dialog.update()

            stats = self.camera.cleanup_old_captures(age_hours, dry_run=True)
            
            if 'error' in stats:
                self.cleanup_status_text.insert(tk.END, f"Error: {stats['error']}\n")
                return

            self.cleanup_status_text.insert(tk.END, f"Preview Results:\n")
            self.cleanup_status_text.insert(tk.END, f"Total files found: {stats['total_files_found']}\n")
            self.cleanup_status_text.insert(tk.END, f"Files to delete: {stats['files_to_delete']}\n")
            
            mb_freed = stats['bytes_freed'] / (1024 * 1024)
            self.cleanup_status_text.insert(tk.END, f"Space to free: {mb_freed:.2f} MB\n")
            
            if stats['files_to_delete'] == 0:
                self.cleanup_status_text.insert(tk.END, "No files to delete!\n")
            else:
                self.cleanup_status_text.insert(tk.END, "\nReady to clean. Click 'Clean Now' to proceed.\n")

        except Exception as e:
            self.cleanup_status_text.insert(tk.END, f"Error during preview: {str(e)}\n")
            handle_error(self.root, e, {
                "operation": "preview_cleanup",
                "age_hours": age_hours
            })

    def _execute_cleanup(self, age_hours, dialog):
        """Execute the cleanup operation."""
        try:
            self.cleanup_status_text.insert(tk.END, "Executing cleanup...\n")
            dialog.update()

            stats = self.camera.cleanup_old_captures(age_hours, dry_run=False)
            
            if 'error' in stats:
                self.cleanup_status_text.insert(tk.END, f"Error: {stats['error']}\n")
                return

            self.cleanup_status_text.insert(tk.END, f"Cleanup completed!\n")
            self.cleanup_status_text.insert(tk.END, f"Files deleted: {stats['files_deleted']}\n")
            
            mb_freed = stats['bytes_freed'] / (1024 * 1024)
            self.cleanup_status_text.insert(tk.END, f"Space freed: {mb_freed:.2f} MB\n")
            
            if stats['errors'] > 0:
                self.cleanup_status_text.insert(tk.END, f"Errors encountered: {stats['errors']}\n")

            _success_notify(
                self.root,
                "Storage cleanup",
                "Cleanup finished.",
                details=(
                    f"Files deleted: {stats['files_deleted']}\n"
                    f"Space freed: {mb_freed:.2f} MB"
                ),
            )

        except Exception as e:
            self.cleanup_status_text.insert(tk.END, f"Error during cleanup: {str(e)}\n")
            handle_error(self.root, e, {"age_hours": age_hours}, operation="execute_cleanup")

    def _show_storage_stats(self):
        """Show storage statistics."""
        if not self.camera:
            _notify_user(self.root, "Camera", "Please initialize the camera first.", level="warning")
            return

        try:
            stats = self.camera.get_storage_stats()
            
            if 'error' in stats:
                handle_error(
                    self.root,
                    RuntimeError(str(stats["error"])),
                    {},
                    operation="storage_stats",
                )
                return

            # Create stats dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("Storage Statistics")
            dialog.geometry("400x500")
            dialog.transient(self.root)
            dialog.grab_set()

            main_frame = ttk.Frame(dialog, padding=10)
            main_frame.pack(fill="both", expand=True)

            # Title
            ttk.Label(main_frame, text="Storage Statistics", font=("Segoe UI", 16, "bold")).pack(pady=(0, 20))

            # Overall stats
            overall_frame = ttk.LabelFrame(main_frame, text="Overall", padding=10)
            overall_frame.pack(fill="x", pady=5)

            ttk.Label(overall_frame, text=f"Total Size: {stats['total_size_mb']:.2f} MB").pack(anchor="w")
            ttk.Label(overall_frame, text=f"Total Files: {stats['file_count']}").pack(anchor="w")
            ttk.Label(overall_frame, text=f"Directories: {stats['directory_count']}").pack(anchor="w")

            if stats['oldest_file']:
                ttk.Label(overall_frame, text=f"Oldest File: {stats['oldest_file'].strftime('%Y-%m-%d %H:%M')}").pack(anchor="w")
            if stats['newest_file']:
                ttk.Label(overall_frame, text=f"Newest File: {stats['newest_file'].strftime('%Y-%m-%d %H:%M')}").pack(anchor="w")

            # By type stats
            type_frame = ttk.LabelFrame(main_frame, text="By Type", padding=10)
            type_frame.pack(fill="x", pady=5)

            for type_name, type_stats in stats['by_type'].items():
                if type_stats['count'] > 0:
                    ttk.Label(type_frame, text=f"{type_name.title()}: {type_stats['count']} files, {type_stats['size_mb']:.2f} MB").pack(anchor="w")

            # Close button
            ttk.Button(main_frame, text="Close", command=dialog.destroy).pack(pady=20)

        except Exception as e:
            handle_error(self.root, e, {
                "operation": "get_storage_stats"
            })

    def _update_ai_capture_settings(self):
        """Update AI capture settings from GUI variables."""
        if not self.camera:
            return

        try:
            settings = {
                'auto_capture_enabled': self.auto_capture_var.get(),
                'capture_cooldown_seconds': self.capture_cooldown_var.get(),
                'max_captures_per_minute': self.max_captures_per_minute_var.get(),
                'capture_sequence_count': self.capture_sequence_count_var.get(),
                'save_detection_overlay': self.save_detection_overlay_var.get(),
                'debug_mode_enabled': self.debug_mode_var.get(),
            }
            
            self.camera.set_ai_capture_settings(settings)
            self._update_status("AI capture settings updated")
            
        except Exception as e:
            self._update_status(f"Failed to update AI settings: {str(e)}")
    
    def _update_framing_settings(self):
        """Apply framing settings from GUI variables to the camera in real time."""
        if not self.camera or not hasattr(self.camera, "set_framing_settings"):
            return
        try:
            self.camera.set_framing_settings({
                'enabled': self.framing_assist_var.get(),
                'gate_capture': self.framing_gate_var.get(),
                'min_score': float(self.framing_min_score_var.get()),
            })
        except Exception as e:
            print(f"Failed to update framing settings: {e}")

    def _update_smart_processing_settings(self):
        """Update smart processing settings from GUI variables."""
        if not self.camera:
            return
        
        try:
            settings = {
                'auto_tagging_enabled': self.auto_tagging_var.get(),
                'scene_classification_enabled': self.scene_classification_var.get(),
                'anomaly_detection_enabled': self.anomaly_detection_var.get(),
                'anomaly_sensitivity': self.anomaly_sensitivity_var.get(),
                'baseline_frames': int(self.baseline_frames_var.get()),
            }
            
            self.camera.set_smart_processing_settings(settings)
            
            # Save to config
            try:
                from config.settings import update_settings
                update_settings({"SMART_PROCESSING_CONFIG": settings})
            except Exception as e:
                logger.warning(f"Failed to save smart processing settings to config: {e}")
            
            self._update_status("Smart processing settings updated", "success")
            
        except Exception as e:
            self._update_status(f"Failed to update smart processing settings: {str(e)}", "error")

    def _apply_experience_preset_from_ui(self):
        """Apply Quick mode preset to GUI variables and sync to camera when connected."""
        try:
            from gui.experience_presets import PRESETS, apply_preset

            name = self.experience_preset_var.get().strip()
            if name not in PRESETS:
                self._update_status("Unknown quick mode", "warning")
                return
            summary = apply_preset(self, name)
            if self.camera:
                self._update_ai_capture_settings()
                self._update_framing_settings()
                self._update_smart_processing_settings()
            lead = summary.split(". ")[0] + ("." if ". " in summary else "")
            self._update_status(f"Mode: {name} — {lead}", "success")
        except Exception as e:
            handle_error(self.root, e, {}, operation="apply_experience_preset")

    def _show_privacy_and_storage_notice(self):
        """Explain local storage, overlays, and auto-capture in plain language."""
        try:
            from gui.experience_presets import privacy_and_storage_notice

            output = "captures/"
            if self.camera and getattr(self.camera, "storage_settings", None):
                output = self.camera.storage_settings.get("output_dir", output)
            root_out = os.path.abspath(output)
            body = privacy_and_storage_notice(root_out)
            _notify_user(
                self.root,
                "Privacy & storage",
                "Everything below stays on this computer unless you add cloud sync yourself.",
                level="info",
                details=body,
            )
        except Exception as e:
            handle_error(self.root, e, {}, operation="privacy_notice")
    
    def _show_anomaly_alert(self, anomaly_info: Dict[str, Any]):
        """Show anomaly alert dialog."""
        try:
            reasons = anomaly_info.get('reasons', [])
            confidence = anomaly_info.get('confidence', 0.0)
            
            message = f"⚠️ Anomaly Detected!\n\n"
            message += f"Confidence: {confidence:.1%}\n\n"
            if reasons:
                message += "Reasons:\n"
                for reason in reasons:
                    message += f"• {reason}\n"
            
            summary = f"Confidence: {confidence:.1%}"
            if GUI_COMPONENTS_AVAILABLE:
                _notify_user(
                    self.root,
                    "Anomaly detected",
                    summary,
                    level="warning",
                    details=message.strip(),
                )
            else:
                messagebox.showwarning("Anomaly Detected", message)
                
        except Exception as e:
            logger.error(f"Failed to show anomaly alert: {e}")

    def _after_safe(self, fn, *args, **kwargs):
        """Schedule a callable on the Tk main thread.

        Safe to call from worker threads. Tk widgets must only be updated from
        the thread that owns the mainloop, so all background-thread UI updates
        should go through this helper.
        """
        try:
            self.root.after(0, lambda: fn(*args, **kwargs))
        except Exception:
            pass

    def _update_status(self, message, status_type="info"):
        """Update status message with visual feedback (thread-safe).

        Args:
            message: Status message text
            status_type: Type of status ("info", "success", "warning", "error")
        """
        if threading.current_thread() is not threading.main_thread():
            self._after_safe(self._update_status, message, status_type)
            return

        try:
            self.status_label.configure(text=message)

            if hasattr(self, 'status_icon_label'):
                icon_colors = {
                    "info": get_color('info'),
                    "success": get_color('success'),
                    "warning": get_color('warning'),
                    "error": get_color('error'),
                }
                self.status_icon_label.configure(
                    fg=icon_colors.get(status_type, get_color('info'))
                )

            text_colors = {
                "info": get_color('text_primary'),
                "success": get_color('success'),
                "warning": get_color('warning'),
                "error": get_color('error'),
            }
            self.status_label.configure(
                fg=text_colors.get(status_type, get_color('text_primary'))
            )
        except tk.TclError:
            pass

    def _schedule_preview_render(self, rgb_frame):
        """Hand off a fully rendered RGB frame to the main thread for display.

        Coalesces multiple worker-thread frames into a single pending render so
        the UI never falls behind by queueing more work than it can drain.
        """
        self._pending_preview_image = rgb_frame
        if self._preview_render_scheduled:
            return
        self._preview_render_scheduled = True
        self._after_safe(self._render_pending_preview)

    def _render_pending_preview(self):
        """Main-thread renderer that converts the latest pending frame to a Tk image."""
        self._preview_render_scheduled = False
        rgb_frame = self._pending_preview_image
        self._pending_preview_image = None
        if rgb_frame is None:
            return
        try:
            disp_w = self.preview_frame.winfo_width()
            disp_h = self.preview_frame.winfo_height()
            if disp_w < 50:
                disp_w = 640
            if disp_h < 50:
                disp_h = 480
            h, w = rgb_frame.shape[:2]
            scale = min(disp_w / w, disp_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            if new_w <= 0 or new_h <= 0:
                return
            resized = cv2.resize(rgb_frame, (new_w, new_h))
            bg = np.zeros((disp_h, disp_w, 3), dtype=np.uint8)
            y_offset = (disp_h - new_h) // 2
            x_offset = (disp_w - new_w) // 2
            bg[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
            pil_image = Image.fromarray(bg)
            photo = ImageTk.PhotoImage(pil_image)
            self.preview_label.configure(image=photo, text="")
            self.preview_label.image = photo
        except tk.TclError:
            pass
        except Exception as e:
            print(f"Preview render error: {e}")

    def _on_closing(self):
        """Handle application closing."""
        if self.camera:
            self.camera.cleanup()
        self.root.destroy()

    def _show_camera_preview(self, camera_id: int):
        """Show a preview of the camera when hovering over the button."""
        try:
            # Create a temporary camera capture for preview
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                show_error_dialog(
                    self.root,
                    RuntimeError(f"Could not open camera {camera_id} for preview."),
                    context={"camera_id": camera_id, "operation": "camera_preview"}
                )
                return

            ret, frame = cap.read()
            if not ret or frame is None:
                show_error_dialog(
                    self.root,
                    RuntimeError(f"Could not read frame from camera {camera_id}."),
                    context={"camera_id": camera_id, "operation": "camera_preview"}
                )
                cap.release()
                return

            # --- Detection and bounding boxes ---
            # Assume self.camera has a .detect_objects(frame) method that returns a list of detections:
            # Each detection: {'bbox': (x1, y1, x2, y2), 'label': str, 'score': float}
            detections = []
            if hasattr(self, "camera") and hasattr(self.camera, "detect_objects"):
                try:
                    detections = self.camera.detect_objects(frame)
                except Exception as det_e:
                    show_error_dialog(
                        self.root,
                        det_e,
                        context={"camera_id": camera_id, "operation": "camera_preview_detection"}
                    )
                    detections = []

            # Draw bounding boxes on the frame
            for det in detections:
                bbox = det.get("bbox")
                label = det.get("label", "")
                score = det.get("score", 0)
                if bbox:
                    x1, y1, x2, y2 = map(int, bbox)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    text = f"{label} {score:.2f}" if label else f"{score:.2f}"
                    cv2.putText(
                        frame, text, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
                    )

            # Resize for preview
            height, width = frame.shape[:2]
            preview_width = 200
            preview_height = int(height * preview_width / width)
            preview_frame = cv2.resize(frame, (preview_width, preview_height))

            # Convert to PIL Image
            preview_rgb = cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB)
            preview_pil = Image.fromarray(preview_rgb)
            preview_photo = ImageTk.PhotoImage(preview_pil)

            # Create preview window
            if hasattr(self, "preview_window"):
                try:
                    self.preview_window.destroy()
                except Exception:
                    pass

            self.preview_window = tk.Toplevel(self.root)
            self.preview_window.title(f"Camera {camera_id} Preview")
            self.preview_window.geometry(
                f"{preview_width+20}x{preview_height+40}"
            )
            self.preview_window.overrideredirect(True)  # Remove window decorations

            # Position near the mouse
            x = self.root.winfo_pointerx() + 10
            y = self.root.winfo_pointery() + 10
            self.preview_window.geometry(f"+{x}+{y}")

            # Create preview label
            preview_label = tk.Label(self.preview_window, image=preview_photo)
            preview_label.image = preview_photo
            preview_label.pack(padx=10, pady=10)

            # Auto-close after 2 seconds
            self.preview_window.after(2000, self._hide_camera_preview)

            cap.release()
        except Exception as e:
            handle_error(self.root, e, {"camera_id": camera_id}, operation="camera_preview_popup")

    def _hide_camera_preview(self):
        """Hide the camera preview window."""
        if hasattr(self, "preview_window"):
            try:
                self.preview_window.destroy()
                delattr(self, "preview_window")
            except:
                pass

    def _on_camera_selected(self, camera_id):
        self.selected_camera_id = camera_id
        self._update_status(f"Selected Camera {camera_id}")


# SplashScreen class is now imported from gui.dialogs.splash_screen


class DeploymentCameraGUI:
    """Touch-friendly, digital camera-style UI for deployment (RPi touchscreen, mobile-sized)."""

    def __init__(self, root, on_ready=None):
        self.root = root
        self.root.title("SmartCam - Camera Mode")

        # Apply modern theme for consistent styling and touch-friendly scaling
        if THEME_AVAILABLE:
            self.style = apply_modern_theme(self.root)
            self.root.configure(bg=get_color('background'))
        else:
            self.style = ttk.Style()
            self.root.configure(bg="#1a1a1a")

        # Window size from config or screen (RPi touchscreen: fullscreen or configured size)
        gui_config = get_settings().get("GUI_CONFIG", {}) if GUI_COMPONENTS_AVAILABLE else {}
        fullscreen = gui_config.get("deployment_fullscreen", False)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        if fullscreen:
            win_w, win_h = screen_w, screen_h
            self.root.geometry(f"{win_w}x{win_h}+0+0")
        else:
            size_str = gui_config.get("deployment_window_size", "480x900")
            try:
                parts = size_str.lower().split("x")
                win_w, win_h = int(parts[0].strip()), int(parts[1].strip())
            except (ValueError, IndexError):
                win_w, win_h = 480, 900
            win_w = min(win_w, screen_w)
            win_h = min(win_h, screen_h)
            self.root.geometry(f"{win_w}x{win_h}")
            self.root.update_idletasks()
            x = (screen_w - win_w) // 2
            y = max(0, (screen_h - win_h) // 2)
            self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        self._on_ready = on_ready
        self.selected_camera_id = 0
        pad = SPACING['md'] if THEME_AVAILABLE else 12
        # --- Top bar ---
        self.top_frame = tk.Frame(self.root, bg=get_color('surface') if THEME_AVAILABLE else "#2a2a2a")
        self.top_frame.grid(row=0, column=0, sticky="ew", pady=pad)
        self.root.grid_columnconfigure(0, weight=1)
        self.title_label = tk.Label(
            self.top_frame,
            text="SmartCam - Camera Mode",
            font=get_font('heading_medium') if THEME_AVAILABLE else ("Segoe UI", 18, "bold"),
            bg=self.top_frame.cget("bg"),
            fg=get_color('text_primary') if THEME_AVAILABLE else "#f1f5f9",
        )
        self.title_label.pack(side="left", padx=pad)
        def _after_refresh():
            if getattr(self, "_setup_dpad_navigation", None) and gui_config.get("enable_dpad_navigation", True):
                self._setup_dpad_navigation()
        self.camera_selector = CameraSelector(
            self.top_frame, self._on_camera_selected, self._initialize_camera,
            after_refresh_callback=_after_refresh
        )
        self.camera_selector.pack(side="right", padx=pad)
        # --- Main area (preview stays black) ---
        self.preview_frame = ttk.LabelFrame(self.root, text="Preview")
        self.preview_frame.grid(row=1, column=0, sticky="nsew", padx=pad, pady=pad)
        self.preview_label = tk.Label(self.preview_frame, bg=get_color('preview_bg') if THEME_AVAILABLE else "black")
        self.preview_label.pack(fill="both", expand=True)
        # --- Controls (bottom bar): touch-friendly buttons, min ~48px height ---
        self.controls_frame = ttk.Frame(self.root)
        self.controls_frame.grid(row=2, column=0, sticky="ew", pady=pad)
        btn_style = "Deployment.TButton" if THEME_AVAILABLE else None
        self.shutter_btn = ttk.Button(
            self.controls_frame, text="●", command=self.capture_image, style=btn_style
        )
        self.shutter_btn.pack(side="left", expand=True, padx=pad)
        self.record_btn = ttk.Button(
            self.controls_frame, text="⏺", command=self.toggle_recording, style=btn_style
        )
        self.record_btn.pack(side="left", expand=True, padx=pad)
        self.gallery_btn = ttk.Button(
            self.controls_frame, text="🖼", command=self.open_gallery, style=btn_style
        )
        self.gallery_btn.pack(side="left", expand=True, padx=pad)
        self.settings_btn = ttk.Button(
            self.controls_frame, text="⚙", command=self.open_settings, style=btn_style
        )
        self.settings_btn.pack(side="left", expand=True, padx=pad)
        # --- Status bar ---
        self.status_frame = tk.Frame(self.root, bg=get_color('surface') if THEME_AVAILABLE else "#2a2a2a")
        self.status_frame.grid(row=3, column=0, sticky="ew")
        self.status_label = tk.Label(
            self.status_frame,
            text="Ready",
            font=get_font('body_large') if THEME_AVAILABLE else ("Segoe UI", 12),
            bg=self.status_frame.cget("bg"),
            fg=get_color('text_secondary') if THEME_AVAILABLE else "#94a3b8",
        )
        self.status_label.pack(side="left", padx=pad)
        # --- Configure grid weights ---
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        # --- Camera logic ---
        self.camera = None
        self.is_capturing = False
        self.is_recording = False
        self.preview_thread = None
        self.last_image_path = None
        self.settings = {
            "auto_enhancement": True,
            "face_detection": True,
            "motion_detection": True,
            "object_detection": True,
            "enhancement_type": "auto",
            "auto_capture": True,
            "capture_cooldown": 5,
            "max_captures_per_minute": 12,
            "capture_sequence_count": 3,
            "save_detection_overlay": True,
            "debug_mode_enabled": False,
            "performance_mode": True,  # Enable frame skipping for better performance
            "framing_assist": True,
            "framing_min_score": 0.40,
            "framing_gate_capture": False,
        }
        threading.Thread(target=self._initialize_camera, daemon=True).start()

        # DPAD/keyboard focus navigation (RPi buttons, accessibility)
        if gui_config.get("enable_dpad_navigation", True) and setup_focus_navigation:
            self._setup_dpad_navigation()

        # After all widgets are created:
        if self.camera_selector.cameras:
            self._on_camera_selected(self.camera_selector.selected_camera_id)

    def _setup_dpad_navigation(self):
        """Wire Left/Right, Space/Enter, Escape for focus navigation (RPi DPAD)."""
        if not setup_focus_navigation:
            return
        focusables = self.camera_selector.get_focusables() + [
            self.shutter_btn, self.record_btn, self.gallery_btn, self.settings_btn
        ]
        setup_focus_navigation(self.root, focusables, horizontal=True, wrap=True)

    def _on_camera_selected(self, camera_id):
        self.selected_camera_id = camera_id
        self._initialize_camera()

    def _after_safe(self, fn, *args, **kwargs):
        """Schedule a callable on the Tk main thread (safe from worker threads)."""
        try:
            self.root.after(0, lambda: fn(*args, **kwargs))
        except Exception:
            pass

    def _set_status(self, text):
        """Thread-safe status_label text update."""
        if threading.current_thread() is not threading.main_thread():
            self._after_safe(self._set_status, text)
            return
        try:
            self.status_label.config(text=text)
        except tk.TclError:
            pass

    def _initialize_camera(self):
        # Render coalescing state for the deployment preview.
        self._pending_preview_image = None
        self._preview_render_scheduled = False

        try:
            self.camera = SmartCamera(camera_id=self.selected_camera_id)
            
            # Test detection components immediately
            self._test_detection_components_on_init()
            
            self._set_status(f"Camera {self.selected_camera_id} Ready")
            self.is_capturing = True
            self.preview_thread = threading.Thread(
                target=self._preview_loop, daemon=True
            )
            self.preview_thread.start()
            if self._on_ready:
                self.root.after(0, self._on_ready)
        except Exception as e:
            self._set_status(f"Camera Error: {e}")
            try:
                from gui.dialogs import error_dialog
                error_dialog.show_error_dialog(
                    self.root,
                    e,
                    {
                        "operation": "deployment_camera_initialize",
                        "camera_id": self.selected_camera_id
                    }
                )
            except Exception as import_err:
                self._set_status(f"Camera Error: {e} (Error dialog unavailable: {import_err})")

    def _test_detection_components_on_init(self):
        """Test detection components during initialization."""
        if not self.camera:
            return
            
        print("\n" + "="*50)
        print("TESTING DETECTION COMPONENTS ON INIT")
        print("="*50)
        
        try:
            frame = self.camera.get_preview_frame()
            if frame is not None:
                print(f"Frame captured: {frame.shape}")
                
                if self.camera.face_analyzer:
                    try:
                        faces = self.camera.face_analyzer.detect_faces(frame)
                        print(f"✅ Face detection working: {len(faces)} faces found")
                    except Exception as e:
                        print(f"❌ Face detection failed: {e}")
                else:
                    print("❌ Face analyzer not available")
                
                if self.camera.motion_detector:
                    try:
                        motion = self.camera.motion_detector.detect_motion(frame)
                        print(f"✅ Motion detection working: motion={motion}")
                    except Exception as e:
                        print(f"❌ Motion detection failed: {e}")
                else:
                    print("❌ Motion detector not available")
                
                print(f"Settings - Face: {self.settings['face_detection']}, Motion: {self.settings['motion_detection']}")
                
            else:
                print("❌ Could not capture test frame")
                
        except Exception as e:
            print(f"❌ Detection test failed: {e}")
        
        print("="*50)

    def _preview_loop(self):
        # Profile-driven performance knobs (set once per loop to avoid mid-loop drift).
        profile = getattr(self.camera, "processing_profile", None)
        frame_skip_modulo = (profile.preview_frame_skip + 1) if profile else 2
        max_fps = profile.recommended_max_fps if profile else 30
        frame_skip = 0  # Skip every Nth frame for performance
        frame_time = 1.0 / max(max_fps, 1)
        last_frame_time = time.time()
        
        # Detection debugging
        detection_debug = {
            'face_count': 0,
            'motion_detected': False,
            'last_debug_time': time.time(),
            'frame_count': 0
        }
        
        while self.is_capturing and self.camera:
            try:
                current_time = time.time()
                
                # Frame rate limiting
                if current_time - last_frame_time < frame_time:
                    time.sleep(0.001)  # Small sleep to prevent CPU hogging
                    continue
                
                frame = self.camera.get_preview_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue
                
                detection_debug['frame_count'] += 1
                
                # Skip frames for performance (profile-driven cadence).
                modulo = max(1, frame_skip_modulo)
                frame_skip = (frame_skip + 1) % modulo
                if frame_skip != 0 and self.settings.get("performance_mode", True):
                    self._update_display_only(frame)
                    last_frame_time = current_time
                    continue
                
                # --- Detection overlays on downscaled frame (reduces lag) ---
                preview_size = _preview_size_for_camera(self.camera)
                small = cv2.resize(frame, preview_size)
                overlay_frame = small.copy()
                live_detections = {'faces': [], 'objects': []}
                
                # Face detection (on small frame)
                if self.settings["face_detection"] and self.camera.face_analyzer:
                    try:
                        faces = self.camera.face_analyzer.detect_faces(overlay_frame)
                        detection_debug['face_count'] = len(faces)
                        live_detections['faces'] = faces
                        for face in faces:
                            x, y, w, h = face["bbox"]
                            cv2.rectangle(
                                overlay_frame, (x, y), (x + w, y + h), (0, 255, 0), 2
                            )
                            cv2.putText(
                                overlay_frame,
                                "Face",
                                (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                (0, 255, 0),
                                2,
                            )
                    except Exception as e:
                        print(f"Face detection error: {e}")
                
                # Motion detection (on small frame)
                if self.settings["motion_detection"] and self.camera.motion_detector:
                    try:
                        motion = self.camera.motion_detector.detect_motion(overlay_frame)
                        detection_debug['motion_detected'] = motion
                        if motion:
                            h, w = overlay_frame.shape[:2]
                            cv2.rectangle(
                                overlay_frame, (0, 0), (w - 1, h - 1), (0, 0, 255), 8
                            )
                            # Add motion text
                            cv2.putText(
                                overlay_frame,
                                "MOTION DETECTED",
                                (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                1,
                                (0, 0, 255),
                                2,
                            )
                    except Exception as e:
                        print(f"Motion detection error: {e}")
                
                # AI-assisted framing overlay on the live preview.
                if (
                    self.settings.get("framing_assist", True)
                    and getattr(self.camera, "framing_engine", None) is not None
                ):
                    try:
                        framing_score = self.camera.framing_engine.score(
                            overlay_frame.shape, live_detections,
                        )
                        if framing_score.has_subject:
                            from framing_engine import draw_framing_overlay as _draw_framing
                            overlay_frame = _draw_framing(
                                overlay_frame,
                                framing_score,
                                show_grid=True,
                                show_subject=False,
                                show_score=True,
                            )
                    except Exception as e:
                        print(f"Framing overlay error: {e}")

                # Object detection (skip for performance in preview)
                # if self.settings["object_detection"] and self.camera.object_detector:
                #     try:
                #         objects = self.camera._detect_objects(overlay_frame)
                #         for obj in objects:
                #             x, y, w, h = obj["bbox"]
                #             label = obj.get("class_name", "Object")
                #             cv2.rectangle(
                #                 overlay_frame, (x, y), (x + w, y + h), (255, 0, 0), 2
                #             )
                #             cv2.putText(
                #                 overlay_frame,
                #                 label,
                #                 (x, y - 10),
                #                 cv2.FONT_HERSHEY_SIMPLEX,
                #                 0.7,
                #                 (255, 0, 0),
                #                 2,
                #             )
                #     except Exception:
                #         pass
                
                # Update display with overlays
                self._update_display_with_overlays(overlay_frame)
                
                # Debug info (every 2 seconds)
                if current_time - detection_debug['last_debug_time'] > 2.0:
                    debug_text = (
                        f"Faces: {detection_debug['face_count']}, "
                        f"Motion: {'YES' if detection_debug['motion_detected'] else 'NO'}, "
                        f"FPS: {detection_debug['frame_count']/2:.1f}"
                    )
                    self._set_status(debug_text)
                    detection_debug['last_debug_time'] = current_time
                    detection_debug['frame_count'] = 0
                
                last_frame_time = current_time
                
            except Exception as e:
                print(f"Preview Error: {e}")
                time.sleep(0.1)

    def _schedule_preview_render(self, rgb_frame):
        """Hand off a fully rendered RGB frame to the main thread for display.

        Coalesces multiple worker frames so the UI never queues more renders
        than it can drain.
        """
        self._pending_preview_image = rgb_frame
        if self._preview_render_scheduled:
            return
        self._preview_render_scheduled = True
        self._after_safe(self._render_pending_preview)

    def _render_pending_preview(self):
        """Main-thread renderer for the deployment preview."""
        self._preview_render_scheduled = False
        rgb_frame = self._pending_preview_image
        self._pending_preview_image = None
        if rgb_frame is None:
            return
        try:
            disp_w = self.preview_frame.winfo_width()
            disp_h = self.preview_frame.winfo_height()
            if disp_w < 50:
                disp_w = 440
            if disp_h < 50:
                disp_h = 330
            h, w = rgb_frame.shape[:2]
            scale = min(disp_w / w, disp_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            if new_w <= 0 or new_h <= 0:
                return
            resized = cv2.resize(rgb_frame, (new_w, new_h))
            bg = np.zeros((disp_h, disp_w, 3), dtype=np.uint8)
            y_offset = (disp_h - new_h) // 2
            x_offset = (disp_w - new_w) // 2
            bg[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
            pil_image = Image.fromarray(bg)
            photo = ImageTk.PhotoImage(pil_image)
            self.preview_label.configure(image=photo)
            self.preview_label.image = photo
        except tk.TclError:
            pass
        except Exception as e:
            print(f"Display render error: {e}")

    def _update_display_only(self, frame):
        """Worker-thread step: convert BGR -> RGB and schedule a main-thread render."""
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self._schedule_preview_render(rgb)
        except Exception as e:
            print(f"Display update error: {e}")

    def _update_display_with_overlays(self, overlay_frame):
        """Worker-thread step: enhance + convert + schedule a main-thread render."""
        try:
            if self.settings["auto_enhancement"] and self.camera.image_enhancer:
                try:
                    overlay_frame = self.camera.image_enhancer.enhance_image_quality(
                        overlay_frame, self.settings["enhancement_type"]
                    )
                except Exception as e:
                    print(f"Enhancement error: {e}")
            
            rgb = cv2.cvtColor(overlay_frame, cv2.COLOR_BGR2RGB)
            self._schedule_preview_render(rgb)
        except Exception as e:
            print(f"Display update error: {e}")

    def capture_image(self):
        if not self.camera:
            self.status_label.config(text="Camera not ready")
            return
        try:
            filename = self.camera.capture_high_quality_image(
                self.settings["enhancement_type"]
            )
            if filename:
                self.last_image_path = filename
                self._update_status("Image Captured!", "success")
                # Flash effect
                self._flash_effect()
            else:
                self._update_status("Capture Failed", "error")
        except Exception as e:
            self.status_label.config(text=f"Capture Error: {e}")

    def _flash_effect(self):
        # Create a more realistic flash effect
        orig_bg = self.preview_label.cget("bg")

        # Flash sequence: bright white -> fade to normal
        self.preview_label.config(bg="white")
        self.root.after(50, lambda: self.preview_label.config(bg="#f0f0f0"))
        self.root.after(100, lambda: self.preview_label.config(bg="#e0e0e0"))
        self.root.after(150, lambda: self.preview_label.config(bg="#d0d0d0"))
        self.root.after(200, lambda: self.preview_label.config(bg=orig_bg))

    def toggle_recording(self):
        if not self.camera:
            self.status_label.config(text="Camera not ready")
            return
        if not self.is_recording:
            try:
                self.camera.start_recording()
                self.is_recording = True
                self._update_status("Recording...", "info")
                self.record_btn.config(text="⏹")
            except Exception as e:
                self.status_label.config(text=f"Record Error: {e}")
        else:
            try:
                self.camera.stop_recording()
                self.is_recording = False
                self._update_status("Recording Stopped", "success")
                self.record_btn.config(text="⏺")
            except Exception as e:
                self.status_label.config(text=f"Stop Error: {e}")

    def open_gallery(self):
        if not self.last_image_path or not os.path.exists(self.last_image_path):
            self.status_label.config(text="No image yet")
            return
        top = tk.Toplevel(self.root)
        top.title("Last Capture")
        top.geometry("480x480")
        from PIL import Image, ImageTk

        img = Image.open(self.last_image_path)
        img.thumbnail((460, 460))
        photo = ImageTk.PhotoImage(img)
        label = tk.Label(top, image=photo)
        label.image = photo
        label.pack(expand=True, fill="both")
        tk.Button(top, text="Close", command=top.destroy).pack(pady=10)

    def open_settings(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.minsize(340, 480)
        dialog.resizable(True, True)

        # --- Scrollable Frame Setup ---
        canvas = tk.Canvas(dialog, borderwidth=0, highlightthickness=0)
        scroll_frame = tk.Frame(canvas)
        vscroll = tk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)

        vscroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def _on_frame_configure(event):
            # Set scroll region to encompass the inner frame
            canvas.configure(scrollregion=canvas.bbox("all"))
        scroll_frame.bind("<Configure>", _on_frame_configure)

        def _on_mousewheel(event):
            if getattr(event, "num", None) == 4:
                step = -1
            elif getattr(event, "num", None) == 5:
                step = 1
            else:
                delta = getattr(event, "delta", 0)
                step = int(-1 * (delta / 120)) if delta else 0
            if step:
                canvas.yview_scroll(step, "units")
        def _bind_mousewheel_to_descendants(parent):
            parent.bind("<MouseWheel>", _on_mousewheel)
            parent.bind("<Button-4>", _on_mousewheel)
            parent.bind("<Button-5>", _on_mousewheel)
            for child in parent.winfo_children():
                _bind_mousewheel_to_descendants(child)

        # --- Settings Widgets ---
        enh_var = tk.BooleanVar(value=self.settings["auto_enhancement"])
        tk.Checkbutton(scroll_frame, text="Auto Enhancement", variable=enh_var).pack(
            anchor="w", pady=10, padx=20
        )
        tk.Label(scroll_frame, text="Enhancement Type:").pack(anchor="w", padx=20)
        enh_type_var = tk.StringVar(value=self.settings["enhancement_type"])
        enh_type_menu = ttk.Combobox(
            scroll_frame,
            textvariable=enh_type_var,
            values=[
                "auto",
                "denoise",
                "sharpen",
                "color_correction",
                "exposure_correction",
                "super_resolution",
            ],
            state="readonly",
        )
        enh_type_menu.pack(anchor="w", padx=20, pady=5)

        face_var = tk.BooleanVar(value=self.settings["face_detection"])
        tk.Checkbutton(scroll_frame, text="Face Detection", variable=face_var).pack(
            anchor="w", pady=5, padx=20
        )
        motion_var = tk.BooleanVar(value=self.settings["motion_detection"])
        tk.Checkbutton(scroll_frame, text="Motion Detection", variable=motion_var).pack(
            anchor="w", pady=5, padx=20
        )
        obj_var = tk.BooleanVar(value=self.settings["object_detection"])
        tk.Checkbutton(scroll_frame, text="Object Detection", variable=obj_var).pack(
            anchor="w", pady=5, padx=20
        )

        ai_capture_var = tk.BooleanVar(value=self.settings["auto_capture"])
        tk.Checkbutton(scroll_frame, text="Auto Capture", variable=ai_capture_var).pack(
            anchor="w", pady=5, padx=20
        )

        tk.Label(scroll_frame, text="Capture Cooldown (seconds):").pack(anchor="w", padx=20)
        cooldown_var = tk.IntVar(value=self.settings["capture_cooldown"])
        cooldown_scale = tk.Scale(scroll_frame, from_=1, to=30, variable=cooldown_var, orient="horizontal")
        cooldown_scale.pack(anchor="w", padx=20, pady=5)

        tk.Label(scroll_frame, text="Max Captures/Minute:").pack(anchor="w", padx=20)
        max_captures_var = tk.IntVar(value=self.settings["max_captures_per_minute"])
        max_captures_scale = tk.Scale(scroll_frame, from_=1, to=60, variable=max_captures_var, orient="horizontal")
        max_captures_scale.pack(anchor="w", padx=20, pady=5)

        overlay_var = tk.BooleanVar(value=self.settings["save_detection_overlay"])
        tk.Checkbutton(scroll_frame, text="Save Detection Overlay", variable=overlay_var).pack(
            anchor="w", pady=5, padx=20
        )

        debug_var = tk.BooleanVar(value=self.settings["debug_mode_enabled"])
        tk.Checkbutton(scroll_frame, text="Enable Debug Mode", variable=debug_var).pack(
            anchor="w", pady=5, padx=20
        )

        performance_var = tk.BooleanVar(value=self.settings.get("performance_mode", True))
        tk.Checkbutton(
            scroll_frame,
            text="Performance Mode (skip frames for smooth preview)",
            variable=performance_var
        ).pack(anchor="w", pady=5, padx=20)

        framing_var = tk.BooleanVar(value=self.settings.get("framing_assist", True))
        tk.Checkbutton(
            scroll_frame,
            text="AI Framing Assist (rule-of-thirds + score)",
            variable=framing_var
        ).pack(anchor="w", pady=5, padx=20)

        framing_gate_var = tk.BooleanVar(value=self.settings.get("framing_gate_capture", False))
        tk.Checkbutton(
            scroll_frame,
            text="Only auto-capture well-framed scenes",
            variable=framing_gate_var
        ).pack(anchor="w", pady=5, padx=20)

        tk.Label(scroll_frame, text="Min Framing Score:").pack(anchor="w", padx=20)
        framing_min_var = tk.DoubleVar(value=self.settings.get("framing_min_score", 0.40))
        tk.Scale(
            scroll_frame, from_=0.0, to=1.0, resolution=0.05,
            variable=framing_min_var, orient="horizontal"
        ).pack(anchor="w", padx=20, pady=5)

        # --- Save/Cancel Buttons (fixed at bottom) ---
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(side="bottom", fill="x", pady=10)
        def save_settings():
            self.settings["auto_enhancement"] = enh_var.get()
            self.settings["enhancement_type"] = enh_type_var.get()
            self.settings["face_detection"] = face_var.get()
            self.settings["motion_detection"] = motion_var.get()
            self.settings["object_detection"] = obj_var.get()
            self.settings["auto_capture"] = ai_capture_var.get()
            self.settings["capture_cooldown"] = cooldown_var.get()
            self.settings["max_captures_per_minute"] = max_captures_var.get()
            self.settings["save_detection_overlay"] = overlay_var.get()
            self.settings["debug_mode_enabled"] = debug_var.get()
            self.settings["performance_mode"] = performance_var.get()
            self.settings["framing_assist"] = framing_var.get()
            self.settings["framing_gate_capture"] = framing_gate_var.get()
            self.settings["framing_min_score"] = framing_min_var.get()

            if self.camera:
                self.camera.detection_settings["face_recognition_enabled"] = (
                    face_var.get()
                )
                self.camera.detection_settings["motion_detection_enabled"] = (
                    motion_var.get()
                )
                self.camera.detection_settings["object_detection_enabled"] = (
                    obj_var.get()
                )
                self.camera.detection_settings["quality_enhancement_enabled"] = (
                    enh_var.get()
                )

                ai_settings = {
                    'auto_capture_enabled': ai_capture_var.get(),
                    'capture_cooldown_seconds': cooldown_var.get(),
                    'max_captures_per_minute': max_captures_var.get(),
                    'save_detection_overlay': overlay_var.get(),
                    'debug_mode_enabled': debug_var.get(),
                }
                self.camera.set_ai_capture_settings(ai_settings)

                if hasattr(self.camera, "framing_settings"):
                    self.camera.framing_settings["enabled"] = framing_var.get()
                    self.camera.framing_settings["gate_capture"] = framing_gate_var.get()
                    self.camera.framing_settings["min_score"] = framing_min_var.get()

            dialog.destroy()
            self.status_label.config(text="Settings Applied")

        tk.Button(btn_frame, text="Save", command=save_settings).pack(side="left", expand=True, padx=20)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="right", expand=True, padx=20)
        canvas.bind("<MouseWheel>", _on_mousewheel)
        _bind_mousewheel_to_descendants(scroll_frame)

        # Size dialog to fit content so Save/Cancel are visible
        dialog.update_idletasks()
        req_h = scroll_frame.winfo_reqheight() + btn_frame.winfo_reqheight() + 40
        req_w = max(340, scroll_frame.winfo_reqwidth() + 50)
        max_h = int(dialog.winfo_screenheight() * 0.85)
        req_h = min(req_h, max_h)
        dialog.geometry(f"{req_w}x{req_h}")

    def __del__(self):
        self.is_capturing = False
        if self.camera:
            self.camera.cleanup()


def main():
    try:
        from utils.ai_stack_status import print_startup_banner

        print_startup_banner()
    except Exception:
        pass

    # Set up global exception handler if GUI components are available
    if GUI_COMPONENTS_AVAILABLE:
        setup_global_exception_handler()
    
    # Suppress TensorFlow warnings
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
    
    parser = argparse.ArgumentParser(description="AI Smart Camera System")
    parser.add_argument(
        "--device", type=int, default=1, help="1: Deployment UI (default), 2: PC UI"
    )
    parser.add_argument(
        "--splash", action="store_true", help="Show splash screen on startup"
    )
    args = parser.parse_args()

    try:
        if args.splash and GUI_COMPONENTS_AVAILABLE:
            # Run with splash screen
            _run_with_splash_screen(args.device)
        else:
            # Run without splash screen
            _run_direct(args.device)
        
    except Exception as e:
        print(f"Critical startup error: {e}")
        if GUI_COMPONENTS_AVAILABLE:
            # Create a minimal root window for error dialog
            try:
                temp_root = tk.Tk()
                temp_root.withdraw()  # Hide it
                handle_error(temp_root, e, {"operation": "startup_error"})
                temp_root.destroy()
            except:
                print(f"Failed to show error dialog: {e}")
        else:
            print(f"Application failed to start: {e}")
            print(f"Traceback: {traceback.format_exc()}")


def _run_with_splash_screen(device_type):
    """Run the application with splash screen."""
    try:
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        
        # Show splash screen
        splash = SplashScreen(root, completion_callback=lambda: _launch_main_application(root, device_type))
        
    except Exception as e:
        print(f"Error launching with splash screen: {e}")
        # Fallback to direct launch
        _run_direct(device_type)


def _launch_main_application(root, device_type):
    """Launch the main application after splash screen."""
    try:
        # Destroy the root window
        root.destroy()
        
        # Launch the main application
        _run_direct(device_type)
        
    except Exception as e:
        if GUI_COMPONENTS_AVAILABLE:
            handle_error(None, e, {
                "operation": "launch_main_application",
                "component": "application_launcher"
            })
        else:
            print(f"Error launching main application: {e}")


def _run_direct(device_type):
    """Run the application directly without splash screen."""
    try:
        root = tk.Tk()
        
        if device_type == 1:
            app = DeploymentCameraGUI(root)
        else:
            app = SmartCameraGUI(root)

        root.mainloop()
        
    except Exception as e:
        if GUI_COMPONENTS_AVAILABLE:
            handle_error(None, e, {
                "operation": "run_direct",
                "device_type": device_type
            })
        else:
            print(f"Error running application: {e}")


if __name__ == "__main__":
    main()
