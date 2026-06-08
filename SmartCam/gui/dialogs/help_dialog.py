"""
Help dialog for SmartCam.

This module provides end-user guidance for camera setup, AI processing,
visualization interpretation, and common troubleshooting steps.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict
import logging


class HelpDialog:
    """
    Comprehensive help dialog
    """
    
    def __init__(self, parent: tk.Tk):
        """
        Initialize the help dialog.
        
        Args:
            parent: Parent window
        """
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        
        self.help_content = self._create_help_content()
        
        self.dialog = None
        self.notebook = None
        self.text_widgets = {}
        
    def _create_help_content(self) -> Dict[str, Dict[str, str]]:
        """Help text aligned with SmartCameraGUI in gui_app.py (desktop main window)."""
        return {
            "Window layout": {
                "Header and camera strip": """
The top bar shows the app title ("AI Smart Camera System") on the left.

On the right:
- Camera cards: one card per detected device; click to select.
- Refresh (🔄): re-scan for cameras.
- Initialize Camera: opens the camera, loads AI models, and starts the live preview loop.

Until the camera is initialized, the preview shows a placeholder message.
""",
                "Camera Preview": """
The large left panel is "Camera Preview".

After initialization you see the live feed. Overlays (when active) can show FPS and
detection-related hints on the preview.

If preview stays blank, confirm the correct camera is selected and no other app has locked the device.
""",
                "Status bar": """
Along the bottom of the main window:

- Status text (Ready, errors, capture events).
- FPS estimate for the preview loop.
- Detection summary (faces / objects / motion) updated with the feed.
- A progress bar for long operations (for example camera initialization with the progress dialog).
""",
            },
            "Notebook: AI Settings": {
                "Enhancement": """
Section: Enhancement

- Auto Enhancement: applies automatic image quality tuning to captures / pipeline.
- Enhancement Type: combobox with modes such as auto, denoise, sharpen, color_correction,
  exposure_correction, super_resolution.

Tip: start with "auto" unless you have a specific look you are chasing.
""",
                "Detection": """
Section: Detection

Toggles (each updates the running camera when it is active):

- Face Detection — detect and analyze faces.
- Motion Detection — movement in the frame.
- Object Detection — general object labels.

These drive overlays, Smart AI Capture triggers, and statistics in the status bar.
""",
                "Smart AI Capture": """
Section: Smart AI Capture

- Auto Capture — capture when the AI sees interesting events (subject to limits below).
- Capture Cooldown (seconds) — minimum time between auto captures.
- Max Captures/Minute — rate cap to protect disk and CPU.
- Sequence Frames — burst length for a triggered capture sequence.
- Save Detection Overlay — store frames with boxes drawn for review.
- Enable Debug Mode — richer detection text in the status/detection line.

Changes apply through the camera settings update hooks while the camera is running.
""",
            },
            "Notebook: Smart Processing": {
                "Auto-Tagging": """
When enabled, captured images receive tags derived from detected content so you can
search the captures folder later (Search by Tags in Actions).
""",
                "Scene Classification": """
Classifies context such as indoor/outdoor, lighting, crowd level, etc., when the pipeline
supports it. Used for metadata and statistics views.
""",
                "Anomaly Detection": """
Flags unusual frames or patterns.

- Sensitivity — higher reacts to smaller deviations.
- Baseline Frames — how many frames to observe before treating deviations as anomalies.

When an anomaly is reported, the app can show a structured notice with reasons.
""",
            },
            "Notebook: Actions": {
                "Capture and recording": """
- Start Capture — toggles continuous capture mode (paired with AI capture rules).
- Capture Image — single high-quality still (uses current enhancement type).
- Start Recording — toggles video recording with audio (button label updates with state).
""",
                "Camera tools": """
- Camera Settings — OpenCV-backed sliders (brightness, contrast, saturation, hue, gain,
  exposure, focus) for properties the device actually exposes.
- Camera Info — read-only summary from the active SmartCamera instance.
- Test Detections — runs face/object/motion/enhancement self-checks on one frame and shows results.
- Refresh Components — reloads AI models without restarting the whole app.
""",
                "Files, tags, and storage": """
- Open Captures — opens the configured output folder on disk (Windows: Explorer).
- Search by Tags — dialog to filter captures using metadata tags.
- View Statistics — tag and scene metadata summaries.
- Storage Cleanup — delete old capture files with a confirmation summary.
- Storage Stats — disk usage breakdown for capture directories.
""",
            },
            "Configuration and accessibility": {
                "GUI_CONFIG (settings)": """
Window geometry and behavior come from config (get_settings()['GUI_CONFIG']):

- window_size, min_window_size — initial and minimum main window size.
- splash_duration — splash screen timing (see gui.dialogs.splash_screen).
- enable_dpad_navigation — when true, keyboard / DPAD style navigation is wired for the
  camera selector and key controls (useful on Raspberry Pi setups).

Deployment builds use a separate touch UI (SmartCam - Camera Mode); options such as
deployment_fullscreen and deployment_window_size apply there.
""",
            },
            "Troubleshooting": {
                "Common problems": """
"No cameras detected" — check cable/USB, drivers, and that another program is not using the camera.

"Please initialize camera first" — pick a camera card, then Initialize Camera, wait until
the preview runs.

Capture or model failures — use Test Detections and Refresh Components; check console output
if Debug Mode is enabled.

Progress dialog stuck — use Cancel if the operation supports it, then retry with a lower
resolution or fewer AI features enabled.
""",
            },
        }
    
   
    def show(self):
        """Show the help dialog."""
        try:
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title("SmartCam - Help & Guide")
            self.dialog.geometry("900x700")
            self.dialog.resizable(True, True)
            
            # Center the dialog
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
            
            # Create main frame
            main_frame = ttk.Frame(self.dialog, padding="10")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Configure grid weights
            self.dialog.columnconfigure(0, weight=1)
            self.dialog.rowconfigure(0, weight=1)
            main_frame.columnconfigure(1, weight=1)
            main_frame.rowconfigure(1, weight=1)
            
            # Create header
            header_frame = ttk.Frame(main_frame)
            header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
            
            title_label = ttk.Label(header_frame, 
                                   text="SmartCam - Help & Guide", 
                                   font=("Arial", 16, "bold"))
            title_label.pack()
            
            subtitle_label = ttk.Label(header_frame, 
                                      text="Reference for the desktop SmartCameraGUI (gui_app.py): layout, tabs, and actions", 
                                      font=("Arial", 10))
            subtitle_label.pack()
            
            # Create notebook for tabbed interface
            self.notebook = ttk.Notebook(main_frame)
            self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Create tabs for each category
            for category_name, category_content in self.help_content.items():
                self._create_category_tab(category_name, category_content)
            
            # Create footer with close button
            footer_frame = ttk.Frame(main_frame)
            footer_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
            
            close_button = ttk.Button(footer_frame, text="Close", command=self._close_dialog)
            close_button.pack(side=tk.RIGHT)
            
            # Add keyboard shortcut
            self.dialog.bind("<Escape>", lambda e: self._close_dialog())
            
            # Focus on the dialog
            self.dialog.focus_set()
            
            self.logger.info("Help dialog opened successfully")
            
        except Exception as e:
            self.logger.error(f"Error creating help dialog: {e}")
            messagebox.showerror("Error", f"Failed to open help dialog: {str(e)}")
    
    def _create_category_tab(self, category_name: str, category_content: Dict[str, str]):
        """Create a tab for a help category."""
        # Create frame for the tab
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text=category_name)
        
        # Create scrollable text widget
        text_frame = ttk.Frame(tab_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create text widget with scrollbar
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Arial", 10), 
                             bg="white", fg="black", padx=10, pady=10)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Insert content
        self._insert_formatted_content(text_widget, category_content)
        
        # Store reference
        self.text_widgets[category_name] = text_widget
        
        # Make text widget read-only
        text_widget.config(state=tk.DISABLED)
    
    def _insert_formatted_content(self, text_widget: tk.Text, content: Dict[str, str]):
        """Insert formatted content into text widget."""
        for topic, explanation in content.items():
            # Insert topic title
            text_widget.insert(tk.END, f"{topic}\n", "title")
            text_widget.insert(tk.END, "=" * len(topic) + "\n\n", "title")
            
            # Insert explanation
            text_widget.insert(tk.END, explanation + "\n\n", "normal")
        
        # Configure tags for formatting
        text_widget.tag_configure("title", font=("Arial", 12, "bold"), foreground="navy")
        text_widget.tag_configure("normal", font=("Arial", 10))
    
    def _close_dialog(self):
        """Close the help dialog."""
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None
            self.logger.info("Help dialog closed")
    
    def is_open(self) -> bool:
        """Check if the help dialog is currently open."""
        return self.dialog is not None and self.dialog.winfo_exists() 