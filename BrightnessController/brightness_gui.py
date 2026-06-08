"""
GUI application for controlling screen brightness based on camera or screen content.
Includes eye health monitoring for safe brightness levels.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os

# Reduce noisy OpenCV backend logs (best-effort).
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

import screen_brightness_control as sbc
from PIL import ImageGrab, Image, ImageTk
import numpy as np
import threading
import time
from typing import Optional, List, Tuple, Dict
from brightness_controller import BrightnessController
from brightness_policy import BatteryBrightnessPolicyConfig
from power_management_system import PowerManagementSystem
import cv2


class BrightnessGUI:
    """GUI application for brightness control with eye health monitoring."""

    def __init__(self):
        """Initialize the GUI application."""
        try:
            cv2.setLogLevel(cv2.LOG_LEVEL_ERROR)
        except Exception:
            pass
        self.root = tk.Tk()
        self.root.title("Brightness Control - Eye Health Monitor")
        self.root.geometry("450x550")
        self.root.resizable(True, True)

        # Initialize controllers and state
        self.controller = BrightnessController()
        self.power_system = PowerManagementSystem(self.controller)
        self.active_mode = None
        self.running = False
        self.control_thread: Optional[threading.Thread] = None
        self.screen_brightness_history = []
        self.history_size = 5

        # Session tracking
        self.camera_brightness_values: List[float] = []
        self.session_start_time: Optional[float] = None
        self.time_in_unhealthy_range: int = 0
        self.last_health_check_time: Optional[float] = None
        self.warning_shown = False

        # Camera selection
        self.available_cameras = []  # Will be populated asynchronously
        self.selected_camera_index = 0
        self.camera_enumeration_thread: Optional[threading.Thread] = None

        # Camera preview state
        self.camera_preview_active = False
        self.camera_preview_thread: Optional[threading.Thread] = None
        self.preview_cap: Optional[cv2.VideoCapture] = None
        self.camera_preview_label: Optional[ttk.Label] = None

        # Human detection tracking
        self.human_detection_enabled = tk.BooleanVar(value=True)
        self.strict_detection_enabled = tk.BooleanVar(value=True)
        self.auto_strict_enabled = tk.BooleanVar(value=True)
        self.grace_period_enabled = tk.BooleanVar(value=True)
        self.adaptive_grace_enabled = tk.BooleanVar(value=True)
        self.distance_detection_enabled = tk.BooleanVar(value=True)
        self.human_present = False
        self.last_human_detection_time = None

        # Power-aware settings
        self.power_aware_enabled = tk.BooleanVar(value=True)
        self.low_battery_threshold_var = tk.IntVar(value=20)
        self.critical_battery_threshold_var = tk.IntVar(value=10)
        self.low_battery_cap_var = tk.IntVar(value=40)
        self.critical_battery_cap_var = tk.IntVar(value=25)
        self.known_virtual_camera_keywords = (
            "nvidia",
            "broadcast",
            "obs",
            "virtual",
            "droidcam",
            "epoccam",
            "snap camera",
            "manycam",
            "xsplit",
        )
        self.issue_events: List[Dict[str, str]] = []
        self.last_issue_summary_time = 0.0
        self.issue_summary_cooldown_seconds = 90.0
        self.issue_summary_in_progress = False

        # Brightness classification thresholds (0-255 scale)
        # Adjusted for eye health recommendations
        self.brightness_categories = {
            "too_dark": (0, 40),  # Very dim, potential eye strain
            "dark": (40, 80),  # Below recommended range
            "slightly_dark": (80, 100),  # Lower edge of healthy range
            "healthy_low": (100, 130),  # Healthy range for darker environments
            "healthy_mid": (130, 160),  # Optimal eye safety range
            "healthy_high": (160, 190),  # Healthy range for brighter environments
            "bright": (190, 220),  # Above recommended range
            "too_bright": (220, 255),  # Very bright, potential eye strain
        }

        # Category colors with health indicators
        self.category_colors = {
            "too_dark": "#444444",  # Dark gray - warning
            "dark": "#666666",  # Medium gray
            "slightly_dark": "#888888",  # Light gray
            "healthy_low": "#88BB88",  # Light green
            "healthy_mid": "#44AA44",  # Medium green
            "healthy_high": "#88BB88",  # Light green
            "bright": "#CCCCCC",  # Light gray
            "too_bright": "#FF9999",  # Light red - warning
        }

        # Health recommendations for each category
        self.health_recommendations: Dict[str, str] = {
            "too_dark": "Too dark - may cause eye strain. Consider increasing ambient light.",
            "dark": "Below recommended brightness. Consider adjusting screen or room lighting.",
            "slightly_dark": "Slightly dark but acceptable for low-light environments.",
            "healthy_low": "Healthy range for darker environments.",
            "healthy_mid": "Optimal brightness range for eye health.",
            "healthy_high": "Healthy range for brighter environments.",
            "bright": "Above recommended brightness. May be fine for very bright environments.",
            "too_bright": "Too bright - may cause eye strain. Consider reducing screen brightness or ambient light.",
        }

        self._setup_gui()
        self._start_camera_enumeration()
        self._update_current_brightness()

    def _schedule_gui_update(self, func, *args, **kwargs):
        """Schedule a GUI update to run on the main thread."""
        self.root.after(0, lambda: func(*args, **kwargs))

    def _thread_safe_messagebox(self, msg_type, title, message):
        """Show a message box on the main thread."""
        self.root.after(0, lambda: getattr(messagebox, msg_type)(title, message))

    def _is_known_virtual_camera(self, camera_name: str) -> bool:
        """Return True if camera name matches known virtual/loopback devices."""
        lowered = camera_name.lower()
        return any(keyword in lowered for keyword in self.known_virtual_camera_keywords)

    def _record_issue(self, level: str, source: str, message: str) -> None:
        """Track warnings/errors and trigger concise summarization."""
        level = level.upper()
        icon = "ℹ️" if level == "INFO" else ("⚠️" if level == "WARN" else "❌")
        print(f"{icon} {source}: {message}")
        self.issue_events.append({"level": level, "source": source, "message": message})
        if len(self.issue_events) > 25:
            self.issue_events = self.issue_events[-25:]
        if level in ("WARN", "ERROR"):
            self._maybe_summarize_issues_with_ollama()

    def _summarize_issues_fallback(self) -> str:
        """Create a short local summary when Ollama is unavailable."""
        recent = self.issue_events[-6:]
        unique = []
        seen = set()
        for item in recent:
            key = (item["level"], item["source"], item["message"])
            if key not in seen:
                unique.append(item)
                seen.add(key)
        lines = ["- Keep camera in use by one app at a time to avoid backend open failures."]
        for item in unique[:3]:
            lines.append(f"- {item['level']} in {item['source']}: {item['message']}")
        return "\n".join(lines)

    def _maybe_summarize_issues_with_ollama(self) -> None:
        """Throttle and generate brief issue summary using Ollama."""
        now = time.time()
        if self.issue_summary_in_progress:
            return
        if now - self.last_issue_summary_time < self.issue_summary_cooldown_seconds:
            return
        if not self.issue_events:
            return

        self.issue_summary_in_progress = True
        self.last_issue_summary_time = now
        recent = self.issue_events[-8:]

        def run_summary():
            try:
                try:
                    import ollama  # type: ignore

                    issue_lines = "\n".join(
                        f"- [{e['level']}] {e['source']}: {e['message']}" for e in recent
                    )
                    response = ollama.chat(
                        model="llama3.1:8b",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "Summarize runtime warnings/errors in 3-5 short bullet points. "
                                    "Each bullet must include issue and recommended fix."
                                ),
                            },
                            {
                                "role": "user",
                                "content": f"Recent issues:\n{issue_lines}",
                            },
                        ],
                    )
                    summary_text = response["message"]["content"].strip()
                except Exception:
                    summary_text = self._summarize_issues_fallback()

                print("\n📌 Issue Summary")
                print(summary_text)
            finally:
                self.issue_summary_in_progress = False

        threading.Thread(target=run_summary, daemon=True).start()

    def _get_policy_config(self) -> BatteryBrightnessPolicyConfig:
        """Build battery-aware policy config from UI controls."""
        low_threshold = self.low_battery_threshold_var.get()
        critical_threshold = min(self.critical_battery_threshold_var.get(), low_threshold)
        return BatteryBrightnessPolicyConfig(
            enabled=self.power_aware_enabled.get(),
            low_battery_threshold=low_threshold,
            critical_battery_threshold=critical_threshold,
            low_battery_cap=self.low_battery_cap_var.get(),
            critical_battery_cap=self.critical_battery_cap_var.get(),
        )

    def _update_power_status_label(self, status_text: str, color: str = "black") -> None:
        """Safely update battery mode status text."""
        if hasattr(self, "power_status_label"):
            self._schedule_gui_update(
                lambda: self.power_status_label.config(text=status_text, foreground=color)
            )

    def _apply_power_aware_brightness(self, raw_brightness: float) -> None:
        """Apply brightness with optional battery-aware caps."""
        self.power_system.set_policy(self._get_policy_config())
        result = self.power_system.apply_brightness(raw_brightness)

        snapshot = result.snapshot
        decision = result.decision
        if snapshot is None:
            self._update_power_status_label("Battery: unavailable", "gray")
            return

        battery_text = (
            f"Battery: {snapshot.percentage}% ({'Charging' if snapshot.power_plugged else 'On battery'})"
        )
        if decision.max_brightness_cap is None:
            self._update_power_status_label(f"{battery_text} | {decision.reason}", "#1F6F8B")
        else:
            self._update_power_status_label(
                f"{battery_text} | Cap active: {decision.max_brightness_cap}% ({decision.reason})",
                "#AA0000",
            )

    def _get_available_displays(self) -> List[str]:
        """
        Get list of available displays/monitors.
        
        Returns:
            List of display names
        """
        try:
            displays = sbc.list_monitors()
            return displays if displays else []
        except Exception as e:
            print(f"Error listing displays: {e}")
            return []

    def _create_display_labels(self, displays: List[str]):
        """Create or update labels for each display (called on main thread)."""
        # Clear existing labels
        for widget in self.display_brightness_frame.winfo_children():
            widget.destroy()
        self.display_brightness_labels.clear()
        
        # Create labels for each display
        for display in displays:
            frame = ttk.Frame(self.display_brightness_frame)
            frame.pack(fill="x", pady=2, padx=5)
            
            label = ttk.Label(frame, text=f"{display}: N/A", anchor="w")
            label.pack(side="left", fill="x", expand=True)
            
            self.display_brightness_labels[display] = label

    def _get_camera_name(self, index: int) -> str:
        """
        Get the name of a camera by its index.
        
        Args:
            index: Camera index
            
        Returns:
            Camera name or "Camera {index}" if name cannot be retrieved
        """
        # Try to get camera name using Windows DirectShow via COM (pywin32)
        try:
            import win32com.client
            dev_enum = win32com.client.Dispatch("SystemDeviceEnum")
            moniker_enum = dev_enum.CreateClassEnumerator(
                "{860BB310-5D01-11d0-BD3B-00A0C911CE86}",  # CLSID_VideoInputDeviceCategory
                0
            )
            moniker_enum.Reset()
            device_index = 0
            while True:
                moniker = moniker_enum.Next(1)
                if not moniker:
                    break
                if device_index == index:
                    # Get the device name from property bag
                    try:
                        prop_bag = moniker.BindToStorage(None, None, "{55272A00-42CB-11CE-8135-00AA004BB851}")
                        name = prop_bag.Read("FriendlyName")
                        if name:
                            return name
                    except Exception:
                        pass
                    # Fallback: try to get display name
                    try:
                        bind_ctx = win32com.client.Dispatch("BindCtx")
                        display_name = moniker.GetDisplayName(bind_ctx, None)
                        if display_name and "\\" in display_name:
                            parts = display_name.split("\\")
                            if len(parts) > 0:
                                return parts[-1]
                    except Exception:
                        pass
                    return f"Camera {index}"
                device_index += 1
        except ImportError:
            # pywin32 not available - will fall back to default name
            pass
        except Exception:
            # Error getting name - will fall back to default name
            pass
        
        # Fallback: return default name
        return f"Camera {index}"

    def _list_available_cameras(self) -> Tuple[List[Tuple[int, str]], List[Tuple[int, str]]]:
        """
        List all available cameras by trying to open each one.
        Also detects cameras that are present but cannot be used.
        
        Returns:
            Tuple of (available_cameras, unusable_cameras)
            Each list contains tuples: (camera_index, camera_name)
        """
        # Suppress OpenCV warnings during camera enumeration
        original_log_level = None
        try:
            original_log_level = cv2.getLogLevel()
            cv2.setLogLevel(cv2.LOG_LEVEL_ERROR)  # Only show errors, suppress warnings
        except (AttributeError, cv2.error):
            # OpenCV version doesn't support log level control, continue without suppression
            pass
        
        try:
            available = []
            unusable = []
            checked_indices = set()
            skipped_virtual = []
            
            # Try up to 10 camera indices
            for i in range(10):
                cap = None
                try:
                    # Try to get camera name first to see if camera is detected
                    name = self._get_camera_name(i)
                    checked_indices.add(i)
                    if self._is_known_virtual_camera(name):
                        skipped_virtual.append((i, name))
                        continue
                    
                    # Try with DirectShow backend first (Windows)
                    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                    if cap.isOpened():
                        ret, _ = cap.read()
                        if ret:
                            available.append((i, name))
                        else:
                            # Camera opened but cannot read - mark as unusable
                            unusable.append((i, name))
                    else:
                        # Camera detected but cannot be opened - mark as unusable
                        unusable.append((i, name))
                    if cap:
                        cap.release()
                except Exception:
                    if cap:
                        cap.release()
                    # If we got a name but failed to open, it's unusable
                    if i in checked_indices:
                        try:
                            name = self._get_camera_name(i)
                            if (i, name) not in available:
                                unusable.append((i, name))
                        except Exception:
                            pass
                    continue
            
            # If no cameras found with DirectShow, try default backend
            if not available:
                for i in range(10):
                    if i in [idx for idx, _ in available]:
                        continue  # Skip already found cameras
                    cap = None
                    try:
                        # Try to get camera name first
                        name = self._get_camera_name(i)
                        checked_indices.add(i)
                        if self._is_known_virtual_camera(name):
                            skipped_virtual.append((i, name))
                            continue
                        
                        cap = cv2.VideoCapture(i)
                        if cap.isOpened():
                            ret, _ = cap.read()
                            if ret:
                                available.append((i, name))
                            else:
                                # Camera opened but cannot read - mark as unusable
                                if (i, name) not in unusable:
                                    unusable.append((i, name))
                        else:
                            # Camera detected but cannot be opened - mark as unusable
                            if (i, name) not in unusable:
                                unusable.append((i, name))
                        if cap:
                            cap.release()
                    except Exception:
                        if cap:
                            cap.release()
                        # If we got a name but failed to open, it's unusable
                        if i in checked_indices:
                            try:
                                name = self._get_camera_name(i)
                                if (i, name) not in available and (i, name) not in unusable:
                                    unusable.append((i, name))
                            except Exception:
                                pass
                        continue
            
            # Remove duplicates from unusable list
            unusable = list(dict.fromkeys(unusable))
            skipped_virtual = list(dict.fromkeys(skipped_virtual))
            
            # Default to camera 0 if none found
            if not available:
                available = [(0, "Camera 0")]

            if skipped_virtual:
                sample_names = ", ".join(name for _, name in skipped_virtual[:2])
                extra = "" if len(skipped_virtual) <= 2 else f" (+{len(skipped_virtual)-2} more)"
                self._record_issue(
                    "WARN",
                    "Camera Enumeration",
                    f"Skipped {len(skipped_virtual)} known virtual cameras: {sample_names}{extra}",
                )
            summary_level = "WARN" if unusable else "INFO"
            self._record_issue(
                summary_level,
                "Camera Enumeration",
                f"Found {len(available)} usable camera(s); {len(unusable)} unusable candidate(s).",
            )
            
            return available, unusable
        finally:
            # Restore original log level
            if original_log_level is not None:
                try:
                    cv2.setLogLevel(original_log_level)
                except (AttributeError, cv2.error):
                    pass

    def _on_camera_selected(self, event=None):
        """Handle camera selection change."""
        selection = self.camera_var.get()
        if selection:
            # Find the camera index by matching the name
            for idx, name in self.available_cameras:
                if name == selection:
                    self.selected_camera_index = idx
                    break

    def _on_mode_changed(self, *args):
        """Handle mode selection change - show/hide camera selection UI."""
        # Safety check: ensure camera selection frame exists
        if not hasattr(self, 'camera_selection_frame'):
            return
        
        mode = self.mode_var.get()
        if mode == "screen":
            # Hide camera selection frame for screen content-based mode
            self.camera_selection_frame.pack_forget()
        else:
            # Show camera selection frame for camera-based mode
            self.camera_selection_frame.pack(fill="x", padx=10, pady=3)

    def _start_camera_enumeration(self):
        """Start camera enumeration in a background thread."""
        if hasattr(self, 'camera_dropdown'):
            self.camera_dropdown.config(state="disabled")
            self.camera_dropdown['values'] = ["Loading cameras..."]
            self.camera_dropdown.current(0)
        
        def enumerate_cameras():
            available, unusable = self._list_available_cameras()
            self._schedule_gui_update(self._update_camera_dropdown, available, unusable)
        
        self.camera_enumeration_thread = threading.Thread(target=enumerate_cameras, daemon=True)
        self.camera_enumeration_thread.start()

    def _update_camera_dropdown(self, available_cameras, unusable_cameras):
        """Update camera dropdown with enumerated cameras (called on main thread)."""
        self.available_cameras = available_cameras
        self.camera_dropdown.config(state="readonly")
        self.camera_dropdown['values'] = [name for _, name in self.available_cameras]
        if self.available_cameras:
            if self.selected_camera_index in [idx for idx, _ in self.available_cameras]:
                for i, (idx, name) in enumerate(self.available_cameras):
                    if idx == self.selected_camera_index:
                        self.camera_dropdown.current(i)
                        break
            else:
                self.camera_dropdown.current(0)
                self.selected_camera_index = self.available_cameras[0][0]
        
        # Update warning label for unusable cameras
        if unusable_cameras:
            camera_names = [name for _, name in unusable_cameras]
            if len(camera_names) == 1:
                warning_text = f"Warning: Camera '{camera_names[0]}' detected but cannot be used."
            else:
                warning_text = f"Warning: {len(camera_names)} cameras detected but cannot be used: {', '.join(camera_names)}"
            self.camera_warning_label.config(text=warning_text)
        else:
            self.camera_warning_label.config(text="")

    def _refresh_camera_list(self):
        """Refresh the list of available cameras."""
        self.camera_dropdown.config(state="disabled")
        self.camera_dropdown['values'] = ["Refreshing..."]
        self.camera_dropdown.current(0)
        
        def refresh_cameras():
            available, unusable = self._list_available_cameras()
            self._schedule_gui_update(self._update_camera_dropdown, available, unusable)
            if available:
                message = f"Found {len(available)} usable camera(s)"
                if unusable:
                    message += f" and {len(unusable)} unusable camera(s)"
                self._thread_safe_messagebox("showinfo", "Camera List Refreshed", message)
            else:
                self._thread_safe_messagebox("showwarning", "No Cameras Found", "No cameras were detected. Defaulting to camera 0.")
        
        threading.Thread(target=refresh_cameras, daemon=True).start()

    def _toggle_camera_preview(self):
        """Toggle camera preview on/off."""
        if self.camera_preview_active:
            self._stop_camera_preview()
        else:
            self._start_camera_preview()

    def _toggle_diagnostics_mode(self):
        """Toggle diagnostics mode on/off."""
        self.diagnostics_mode = self.diagnostics_mode_var.get()
        if self.diagnostics_mode:
            print("🔍 Diagnostics mode enabled - detailed error logging active")
        else:
            print("🔍 Diagnostics mode disabled - error logging reduced")

    def _start_camera_preview(self):
        """Initialize camera and start preview thread."""
        if self.camera_preview_active:
            return
        
        try:
            # Initialize camera capture for preview (separate from main control camera)
            self.preview_cap = cv2.VideoCapture(self.selected_camera_index, cv2.CAP_DSHOW)
            if not self.preview_cap.isOpened():
                # Try default backend if DirectShow fails
                self.preview_cap.release()
                self.preview_cap = cv2.VideoCapture(self.selected_camera_index)
                if not self.preview_cap.isOpened():
                    raise Exception("Could not open camera")
            
            # Set camera properties for reasonable preview size
            self.preview_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
            self.preview_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
            
            self.camera_preview_active = True
            self.camera_preview_button.config(text="Stop Preview")
            
            # Start preview thread
            self.camera_preview_thread = threading.Thread(
                target=self._update_camera_preview,
                daemon=True
            )
            self.camera_preview_thread.start()
            
        except Exception as e:
            self._thread_safe_messagebox(
                "showerror",
                "Camera Preview Error",
                f"Failed to start camera preview: {e}"
            )
            if self.preview_cap:
                try:
                    self.preview_cap.release()
                except:
                    pass
                self.preview_cap = None
            self.camera_preview_active = False
            self.camera_preview_button.config(text="Start Preview")

    def _stop_camera_preview(self):
        """Stop preview and release camera."""
        self.camera_preview_active = False
        
        # Wait for thread to finish
        if self.camera_preview_thread:
            self.camera_preview_thread.join(timeout=1.0)
            self.camera_preview_thread = None
        
        # Release camera
        if self.preview_cap:
            try:
                self.preview_cap.release()
            except:
                pass
            self.preview_cap = None
        
        # Update button and clear preview
        self.camera_preview_button.config(text="Start Preview")
        if self.camera_preview_label:
            self.camera_preview_label.config(image="", text="Preview stopped")

    def _update_camera_preview(self):
        """Thread function that captures frames and updates display."""
        while self.camera_preview_active and self.preview_cap:
            try:
                ret, frame = self.preview_cap.read()
                if ret:
                    self._display_frame(frame)
                else:
                    break
                # Update at ~30 FPS
                time.sleep(1.0 / 30.0)
            except Exception as e:
                self._record_issue("ERROR", "Camera Preview", str(e))
                break
        
        # Cleanup if loop exits
        if self.camera_preview_active:
            self._schedule_gui_update(self._stop_camera_preview)

    def _display_frame(self, frame):
        """Convert OpenCV frame to PhotoImage and update label (thread-safe)."""
        try:
            # Resize frame to fit preview (max 480x360)
            height, width = frame.shape[:2]
            max_width, max_height = 480, 360
            
            # Calculate scaling to fit
            scale = min(max_width / width, max_height / height, 1.0)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            if scale < 1.0:
                frame = cv2.resize(frame, (new_width, new_height))
            
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            image = Image.fromarray(frame_rgb)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image=image)
            
            # Update label on main thread
            self._schedule_gui_update(
                lambda img=photo: self._update_preview_label(img)
            )
        except Exception as e:
            self._record_issue("ERROR", "Camera Preview", f"Frame display failed: {e}")

    def _update_preview_label(self, photo):
        """Update the preview label with new image (called on main thread)."""
        if self.camera_preview_label:
            self.camera_preview_label.config(image=photo, text="")
            # Keep a reference to prevent garbage collection
            self.camera_preview_label.image = photo

    def _setup_gui(self):
        """Set up the GUI components."""

        def create_label(parent, text, **kwargs):
            pady = kwargs.pop("pady", 0)
            label = ttk.Label(parent, text=text, **kwargs)
            label.pack(anchor="w", pady=pady)
            return label

        def create_button(parent, text, command, **kwargs):
            button = ttk.Button(parent, text=text, command=command, **kwargs)
            button.pack(side="left", padx=5)
            return button
        
        def create_frame(parent, text, **kwargs):
            pady = kwargs.pop("pady", 3)
            frame = ttk.LabelFrame(parent, text=text, **kwargs)
            frame.pack(fill="x", padx=10, pady=pady)
            return frame

        # Create notebook (tabbed interface)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Control Tab (merged with Statistics)
        control_tab = ttk.Frame(notebook)
        notebook.add(control_tab, text="Control")

        # Mode selection
        mode_frame = create_frame(control_tab, "Mode")
        self.mode_var = tk.StringVar(value="camera")
        for text, value in [("Camera-based", "camera"), ("Screen Content-based", "screen")]:
            ttk.Radiobutton(mode_frame, text=text, variable=self.mode_var, value=value).pack(anchor="w")
        
        # Bind mode changes to show/hide camera selection
        self.mode_var.trace_add("write", lambda *args: self._on_mode_changed())

        # Camera selection
        self.camera_selection_frame = create_frame(control_tab, "Camera")
        camera_label = create_label(self.camera_selection_frame, "Select Camera:")
        self.camera_var = tk.StringVar()
        self.camera_dropdown = ttk.Combobox(
            self.camera_selection_frame,
            textvariable=self.camera_var,
            values=[name for _, name in self.available_cameras],
            state="readonly",
            width=40
        )
        if self.available_cameras:
            self.camera_dropdown.current(0)
            self.selected_camera_index = self.available_cameras[0][0]
        self.camera_dropdown.pack(anchor="w", pady=2)
        self.camera_dropdown.bind("<<ComboboxSelected>>", self._on_camera_selected)
        
        # Refresh camera button
        refresh_camera_button = ttk.Button(
            self.camera_selection_frame,
            text="Refresh",
            command=self._refresh_camera_list
        )
        refresh_camera_button.pack(anchor="w", pady=2)
        
        # Camera warning label (for cameras detected but unusable)
        self.camera_warning_label = ttk.Label(
            self.camera_selection_frame,
            text="",
            foreground="orange",
            wraplength=400,
            font=("Arial", 8)
        )
        self.camera_warning_label.pack(anchor="w", pady=(5, 2))
        
        # Set initial state based on default mode (after camera frame is created)
        self._on_mode_changed()

        # Display brightness section
        brightness_frame = create_frame(control_tab, "Display Brightness")
        
        # Create scrollable frame for display list
        canvas = tk.Canvas(brightness_frame, height=100)
        scrollbar = ttk.Scrollbar(brightness_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.display_brightness_frame = scrollable_frame
        self.display_brightness_labels = {}  # Dictionary to store display labels
        
        # Display capability tracking
        self.display_read_capable = {}  # Cache: display -> bool (supports reading)
        self.display_error_count = {}  # Track error count per display
        self.display_last_error_time = {}  # Track last error time per display
        self.display_error_logged = {}  # Track if we've logged error for this display
        self.diagnostics_mode = False  # Enable detailed diagnostics

        # Session stats frame
        self.stats_frame = create_frame(control_tab, "Statistics")

        self.session_avg_label = create_label(self.stats_frame, "Avg: N/A")
        self.session_time_label = create_label(self.stats_frame, "Time: 00:00")
        self.category_label = create_label(self.stats_frame, "Level: N/A", pady=(3, 0))
        self.health_label = create_label(self.stats_frame, "Health: N/A", wraplength=380, pady=(3, 0))
        self.unhealthy_time_label = ttk.Label(
            self.stats_frame,
            text="Unhealthy: 00:00",
            foreground="#AA0000",
        )
        self.unhealthy_time_label.pack(anchor="w", pady=(3, 0))

        # Visual brightness category indicator
        category_frame = create_frame(self.stats_frame, "Brightness Category Indicator")

        # Create category indicators
        self.category_indicators = {}
        categories = list(self.brightness_categories.keys())

        for i, category in enumerate(categories):
            frame = ttk.Frame(category_frame, width=40, height=20)
            frame.grid(row=0, column=i, padx=1)
            frame.pack_propagate(False)

            if category in ["healthy_low", "healthy_mid", "healthy_high"]:
                border_frame = ttk.Frame(frame, padding=1)
                border_frame.pack(fill="both", expand=True)
                label = ttk.Label(border_frame, background=self.category_colors[category])
                label.pack(fill="both", expand=True)
                if category == "healthy_mid":
                    label.config(text="SAFE", foreground="#FFFFFF", font=("Arial", 7, "bold"))
            else:
                label = ttk.Label(frame, background=self.category_colors[category])
                label.pack(fill="both", expand=True)

            self.category_indicators[category] = label

        # Category selector (the triangle marker)
        self.category_selector = ttk.Label(
            category_frame, text="▼", foreground="red", font=("Arial", 12, "bold")
        )
        self.category_selector.place(x=0, y=-10)  # Will be positioned dynamically

        # Control buttons
        button_frame = ttk.Frame(control_tab, padding=5)
        button_frame.pack(fill="x", padx=10, pady=3)

        self.start_button = create_button(button_frame, "Start", self.start_control)
        self.stop_button = create_button(button_frame, "Stop", self.stop_control, state="disabled")
        self.test_button = create_button(button_frame, "Test (5s)", self.start_test_control)
        self.help_button = create_button(button_frame, "Health Info", self.show_health_info)
        self.human_info_button = create_button(button_frame, "Detection Info", self.show_human_detection_info)

        # Settings Tab
        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text="Settings")

        # Human detection frame
        human_detection_frame = create_frame(settings_tab, "Detection")

        # Main toggle
        main_toggle_frame = ttk.Frame(human_detection_frame)
        main_toggle_frame.pack(fill="x", pady=(0, 5))
        
        self.human_detection_checkbox = ttk.Checkbutton(
            main_toggle_frame,
            text="Enable Human Detection",
            variable=self.human_detection_enabled,
        )
        self.human_detection_checkbox.pack(anchor="w")

        # Detection modes section
        modes_frame = ttk.LabelFrame(human_detection_frame, text="Modes", padding="5")
        modes_frame.pack(fill="x", pady=(0, 5))

        self.distance_detection_checkbox = ttk.Checkbutton(
            modes_frame,
            text="Distance Detection",
            variable=self.distance_detection_enabled,
        )
        self.distance_detection_checkbox.pack(anchor="w", pady=1)

        self.strict_detection_checkbox = ttk.Checkbutton(
            modes_frame,
            text="Strict Detection",
            variable=self.strict_detection_enabled,
        )
        self.strict_detection_checkbox.pack(anchor="w", pady=1)

        self.auto_strict_checkbox = ttk.Checkbutton(
            modes_frame,
            text="Auto-Strict",
            variable=self.auto_strict_enabled,
        )
        self.auto_strict_checkbox.pack(anchor="w", pady=1)

        # Grace period section
        grace_frame = ttk.LabelFrame(human_detection_frame, text="Grace Period", padding="5")
        grace_frame.pack(fill="x", pady=(0, 5))

        self.grace_period_checkbox = ttk.Checkbutton(
            grace_frame,
            text="Grace Period",
            variable=self.grace_period_enabled,
        )
        self.grace_period_checkbox.pack(anchor="w", pady=1)

        self.adaptive_grace_checkbox = ttk.Checkbutton(
            grace_frame,
            text="Adaptive Timing",
            variable=self.adaptive_grace_enabled,
        )
        self.adaptive_grace_checkbox.pack(anchor="w", pady=1)

        # Status display
        status_frame = ttk.LabelFrame(human_detection_frame, text="Status", padding="5")
        status_frame.pack(fill="x")

        self.human_present_label = create_label(status_frame, "Present: N/A")
        self.detection_status_label = create_label(status_frame, "Status: Standard Mode")

        # Power-aware battery frame
        power_frame = create_frame(settings_tab, "Power Saver")

        self.power_aware_checkbox = ttk.Checkbutton(
            power_frame,
            text="Enable battery-aware brightness caps",
            variable=self.power_aware_enabled,
        )
        self.power_aware_checkbox.pack(anchor="w", pady=(0, 4))

        threshold_frame = ttk.Frame(power_frame)
        threshold_frame.pack(fill="x", pady=2)
        ttk.Label(threshold_frame, text="Low battery threshold (%)").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Scale(
            threshold_frame,
            from_=10,
            to=50,
            variable=self.low_battery_threshold_var,
            orient="horizontal",
        ).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Label(
            threshold_frame, textvariable=self.low_battery_threshold_var, width=4
        ).grid(row=0, column=2, sticky="e")

        ttk.Label(threshold_frame, text="Critical threshold (%)").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Scale(
            threshold_frame,
            from_=5,
            to=30,
            variable=self.critical_battery_threshold_var,
            orient="horizontal",
        ).grid(row=1, column=1, sticky="ew", padx=6)
        ttk.Label(
            threshold_frame, textvariable=self.critical_battery_threshold_var, width=4
        ).grid(row=1, column=2, sticky="e")
        threshold_frame.columnconfigure(1, weight=1)

        cap_frame = ttk.Frame(power_frame)
        cap_frame.pack(fill="x", pady=2)
        ttk.Label(cap_frame, text="Low battery max brightness (%)").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Scale(
            cap_frame,
            from_=20,
            to=80,
            variable=self.low_battery_cap_var,
            orient="horizontal",
        ).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Label(cap_frame, textvariable=self.low_battery_cap_var, width=4).grid(
            row=0, column=2, sticky="e"
        )

        ttk.Label(cap_frame, text="Critical max brightness (%)").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Scale(
            cap_frame,
            from_=10,
            to=60,
            variable=self.critical_battery_cap_var,
            orient="horizontal",
        ).grid(row=1, column=1, sticky="ew", padx=6)
        ttk.Label(cap_frame, textvariable=self.critical_battery_cap_var, width=4).grid(
            row=1, column=2, sticky="e"
        )
        cap_frame.columnconfigure(1, weight=1)

        self.power_status_label = create_label(
            power_frame,
            "Battery: waiting for first reading",
            foreground="#1F6F8B",
        )

        # Diagnostics section
        diagnostics_frame = create_frame(settings_tab, "Diagnostics")
        
        self.diagnostics_mode_var = tk.BooleanVar(value=False)
        self.diagnostics_checkbox = ttk.Checkbutton(
            diagnostics_frame,
            text="Enable Diagnostics Mode (verbose error logging)",
            variable=self.diagnostics_mode_var,
            command=self._toggle_diagnostics_mode
        )
        self.diagnostics_checkbox.pack(anchor="w", pady=2)
        
        diagnostics_info_label = create_label(
            diagnostics_frame,
            "When enabled, shows detailed error messages and diagnostics.",
            font=("Arial", 8),
            foreground="gray"
        )

        # Camera Test/Preview section
        camera_preview_frame = create_frame(settings_tab, "Camera Test")
        
        # Preview button
        preview_button_frame = ttk.Frame(camera_preview_frame)
        preview_button_frame.pack(fill="x", pady=5)
        
        self.camera_preview_button = ttk.Button(
            preview_button_frame,
            text="Start Preview",
            command=self._toggle_camera_preview
        )
        self.camera_preview_button.pack(side="left", padx=5)
        
        # Preview label for video display
        self.camera_preview_label = ttk.Label(
            camera_preview_frame,
            text="Preview will appear here",
            background="black",
            foreground="white",
            width=40,
            anchor="center"
        )
        self.camera_preview_label.pack(pady=5, padx=5)
    def show_health_info(self):
        """Show information about brightness and eye health."""
        info_message = """
Eye Health Brightness Guidelines:

• Brightness should match your environment
• Optimal range is typically 100-190 (on 0-255 scale)
• Too bright or too dark can cause eye strain
• Take regular breaks (20-20-20 rule)
• Consider blue light filtering for night use

The 20-20-20 rule: Every 20 minutes, look at something 
20 feet away for 20 seconds to reduce eye strain.

This app helps monitor your brightness levels and 
provides recommendations for healthier screen viewing.
        """
        messagebox.showinfo("Eye Health Information", info_message)

    def show_human_detection_info(self):
        """Show information about human detection functionality."""
        info_message = """
Human Detection Feature:

• Uses computer vision to detect human faces
• Automatically reduces screen brightness to 0% when no human is detected
• Helps save energy and reduce eye strain when you're away
• Uses OpenCV's Haar cascade classifier for face detection
• Requires good lighting and clear view of your face

Detection Modes:
• Standard Detection: Balanced sensitivity for most environments
• Strict Detection: Higher accuracy, reduces false positives from objects
  - Requires better lighting and clearer face positioning
  - More conservative detection parameters
  - Better for environments with many objects
• Auto-Strict Detection: Automatically switches to strict mode when instability is detected
  - Monitors detection stability in real-time
  - Switches to strict mode if too many rapid changes occur
  - Helps maintain consistent detection without manual intervention
• Grace Period: Maintains human detection for 3 seconds when face is temporarily blocked
  - Prevents flickering when you look away briefly
  - Handles temporary face blocking or turning
  - Reduces false negatives from momentary detection loss
• Adaptive Grace Period: Automatically adjusts grace period timing based on your behavior patterns
  - Learns from your recent face loss patterns (last 10 events)
  - Adjusts duration between 1-8 seconds based on your typical behavior
  - Provides personalized timing for optimal user experience
• Distance Detection: Differentiates between primary user (close to camera) and distant people
  - Only considers faces close to the camera as the primary user
  - Ignores people walking by in the background or sitting far away
  - Uses face size relative to frame to determine distance
  - Helps prevent false triggers from distant people
  - Can be calibrated for your specific setup using the test tool

How it works:
• Camera continuously monitors for human presence
• When a face is detected, normal brightness control resumes
• When no face is detected for several frames, brightness drops to 0%
• Detection uses a history buffer to reduce false positives/negatives
• Additional validation checks face quality, size, and aspect ratio

Tips for best results:
• Ensure good lighting on your face (not too dark or too bright)
• Position yourself clearly in front of the camera
• Keep the camera unobstructed
• Use "Strict Detection" if you experience false positives
• Enable "Grace Period" to handle brief moments when looking away
• Enable "Adaptive Grace Period" for personalized timing based on your behavior
• Enable "Distance Detection" to ignore people in the background
• Use the test tool (test.py) to calibrate distance detection for your setup
• The feature works best in camera-based mode

Troubleshooting:
• If detection is unstable, try enabling "Strict Detection"
• If detection is too strict, disable "Strict Detection"
• If detection flickers when looking away, enable "Grace Period"
• If grace period timing doesn't match your behavior, enable "Adaptive Grace Period"
• If people in the background trigger detection, enable "Distance Detection"
• If distance detection is too sensitive/not sensitive enough, use test.py to recalibrate
• Ensure your face takes up a reasonable portion of the camera view
• Check that lighting is consistent and not too harsh

Note: This feature requires a working webcam and may not work perfectly in all lighting conditions.
        """
        messagebox.showinfo("Human Detection Information", info_message)

    def _update_display_label(self, display: str, text: str):
        """Update a single display label (called on main thread)."""
        if display in self.display_brightness_labels:
            self.display_brightness_labels[display].config(text=text)

    def _check_display_read_capability(self, display: str) -> bool:
        """
        Check if a display supports brightness reading.
        Uses cache to avoid repeated failed attempts.
        
        Args:
            display: Display name to check
            
        Returns:
            bool: True if display supports reading, False otherwise
        """
        # If we've already determined this display doesn't support reading, skip
        if display in self.display_read_capable:
            return self.display_read_capable[display]
        
        # Try to read brightness once to determine capability
        try:
            brightness = sbc.get_brightness(display=display)
            # If successful, mark as capable
            self.display_read_capable[display] = True
            return True
        except Exception:
            # If it fails, mark as not capable and don't try again
            self.display_read_capable[display] = False
            if not self.display_error_logged.get(display, False):
                self._record_issue(
                    "WARN",
                    "Display Brightness",
                    f"'{display}' does not support brightness reading; future read attempts skipped.",
                )
                self.display_error_logged[display] = True
            return False

    def _log_display_error(self, display: str, error: Exception):
        """
        Log display reading errors with reduced frequency to avoid spam.
        
        Args:
            display: Display name that failed
            error: Exception that occurred
        """
        current_time = time.time()
        last_error_time = self.display_last_error_time.get(display, 0)
        
        # Only log errors:
        # - First time for this display
        # - Or if it's been more than 60 seconds since last log
        # - Or if diagnostics mode is enabled
        if (not self.display_error_logged.get(display, False) or 
            current_time - last_error_time > 60 or 
            self.diagnostics_mode):
            
            error_count = self.display_error_count.get(display, 0) + 1
            self.display_error_count[display] = error_count
            self.display_last_error_time[display] = current_time
            
            if error_count == 1:
                self._record_issue(
                    "WARN",
                    "Display Brightness",
                    f"Read failed for '{display}': {error}. Suppressing repeated errors.",
                )
            elif self.diagnostics_mode:
                self._record_issue(
                    "WARN",
                    "Display Brightness",
                    f"Read failed for '{display}' attempt #{error_count}: {error}",
                )
            
            self.display_error_logged[display] = True

    def _update_current_brightness(self):
        """Update the brightness display in the GUI."""
        def read_and_update():
            try:
                # Check if display brightness frame exists
                if not hasattr(self, 'display_brightness_frame'):
                    if self.running:
                        self.root.after(1000, self._update_current_brightness)
                    return
                
                # Get list of displays
                displays = self._get_available_displays()
                
                if not displays:
                    # No displays found, show message
                    if hasattr(self, 'display_brightness_labels'):
                        self._schedule_gui_update(
                            lambda: self._create_display_labels(["No displays detected"])
                        )
                    if self.running:
                        self.root.after(1000, self._update_current_brightness)
                    return
                
                # Create/update display labels if needed
                if not hasattr(self, 'display_brightness_labels') or not self.display_brightness_labels or set(displays) != set(self.display_brightness_labels.keys()):
                    self._schedule_gui_update(self._create_display_labels, displays)
                    # Reset capability cache when displays change
                    self.display_read_capable.clear()
                    self.display_error_count.clear()
                    self.display_error_logged.clear()
                    self.display_last_error_time.clear()
                
                # Read brightness for each display
                display_brightness = {}
                for display in displays:
                    # Skip displays that we know don't support reading
                    if not self._check_display_read_capability(display):
                        display_brightness[display] = None
                        continue
                    
                    try:
                        brightness = sbc.get_brightness(display=display)
                        # get_brightness can return a list or single value
                        if isinstance(brightness, list):
                            brightness = brightness[0] if brightness else 0
                        
                        # Validate brightness value
                        if brightness is not None and isinstance(brightness, (int, float)):
                            if 0 <= brightness <= 100:
                                display_brightness[display] = brightness
                            else:
                                # Invalid brightness value
                                if self.diagnostics_mode:
                                    self._record_issue(
                                        "WARN",
                                        "Display Brightness",
                                        f"Invalid value for '{display}': {brightness} (expected 0-100).",
                                    )
                                display_brightness[display] = None
                                # Mark as not capable if we get invalid values
                                self.display_read_capable[display] = False
                        else:
                            display_brightness[display] = None
                            self.display_read_capable[display] = False
                    except Exception as e:
                        self._log_display_error(display, e)
                        display_brightness[display] = None
                        # Mark as not capable after consistent failures
                        if self.display_error_count.get(display, 0) >= 3:
                            self.display_read_capable[display] = False
                
                # Update labels on main thread
                if hasattr(self, 'display_brightness_labels'):
                    for display, brightness in display_brightness.items():
                        if display in self.display_brightness_labels:
                            if brightness is not None:
                                text = f"{display}: {brightness}%"
                            else:
                                # Show different text based on whether we know it's not supported
                                if self.display_read_capable.get(display, True) is False:
                                    text = f"{display}: Not supported"
                                else:
                                    text = f"{display}: N/A"
                            self._schedule_gui_update(
                                lambda d=display, t=text: self._update_display_label(d, t)
                            )
            except Exception as e:
                if self.diagnostics_mode:
                    self._record_issue("ERROR", "Brightness Loop", str(e))
            finally:
                if self.running:
                    self.root.after(1000, self._update_current_brightness)
        
        threading.Thread(target=read_and_update, daemon=True).start()

    def is_healthy_brightness(self, category: str) -> bool:
        """Check if the brightness category is in the healthy range."""
        return category in ["healthy_low", "healthy_mid", "healthy_high"]

    def classify_brightness(self, brightness: float) -> Tuple[str, str]:
        for category, (lower, upper) in self.brightness_categories.items():
            if lower <= brightness < upper:
                # Convert category_name to display_name (e.g., "healthy_mid" -> "Healthy Mid")
                display_name = category.replace("_", " ").title()
                return category, display_name

        # Default fallback
        return "healthy_mid", "Healthy Mid"

    def update_unhealthy_time(self, is_current_healthy: bool):
        """Update the time spent in unhealthy brightness ranges."""
        current_time = time.time()

        if self.last_health_check_time is None:
            self.last_health_check_time = current_time
            return

        time_diff = current_time - self.last_health_check_time
        self.last_health_check_time = current_time

        # Only count unhealthy time when a human is present
        # When no human is present (brightness = 0), it's intentional power saving, not unhealthy
        if not is_current_healthy and self.human_present:
            self.time_in_unhealthy_range += int(time_diff)

            # Show warning if in unhealthy range for more than 5 minutes
            if self.time_in_unhealthy_range > 300 and not self.warning_shown:
                self._thread_safe_messagebox(
                    "showwarning",
                    "Eye Health Warning",
                    "You've been using a non-optimal brightness level for over 5 minutes.\n"
                    "This may contribute to eye strain. Consider adjusting your brightness "
                    "or taking a short break.",
                )
                self.warning_shown = True

        # Format and display the unhealthy time
        minutes, seconds = divmod(self.time_in_unhealthy_range, 60)
        if self.human_detection_enabled.get():
            self.unhealthy_time_label.config(
                text=f"Unhealthy (when present): {minutes:02d}:{seconds:02d}"
            )
        else:
            self.unhealthy_time_label.config(
                text=f"Unhealthy: {minutes:02d}:{seconds:02d}"
            )

    def _update_session_stats(self):
        """Update session statistics display."""
        if not (self.running and self.active_mode == "camera"):
            return
        
        def calculate_and_update():
            try:
                # Calculate session time
                session_time_text = ""
                if self.session_start_time is not None:
                    elapsed_seconds = int(time.time() - self.session_start_time)
                    minutes, seconds = divmod(elapsed_seconds, 60)
                    session_time_text = f"Time: {minutes:02d}:{seconds:02d}"

                # Calculate average brightness and category (heavy operation)
                avg_brightness = None
                category = None
                display_name = None
                is_healthy = False
                text_color = "#000000"
                
                if self.camera_brightness_values:
                    avg_brightness = float(np.mean(self.camera_brightness_values))
                    category, display_name = self.classify_brightness(avg_brightness)
                    is_healthy = self.is_healthy_brightness(category)
                    text_color = "#006600" if is_healthy else "#AA0000"

                # Update unhealthy time tracking
                self.update_unhealthy_time(is_healthy)

                # Schedule GUI updates on main thread
                if session_time_text:
                    self._schedule_gui_update(
                        lambda: self.session_time_label.config(text=session_time_text)
                    )

                if avg_brightness is not None:
                    self._schedule_gui_update(
                        lambda: self.session_avg_label.config(
                            text=f"Avg: {avg_brightness:.1f} (0-255)"
                        )
                    )
                    self._schedule_gui_update(
                        lambda: self.category_label.config(
                            text=f"Level: {display_name}", foreground=text_color
                        )
                    )
                    if category in self.health_recommendations:
                        self._schedule_gui_update(
                            lambda: self.health_label.config(
                                text=f"Health: {self.health_recommendations[category]}",
                                foreground=text_color,
                            )
                        )
                    
                    # Position the category selector
                    categories = list(self.brightness_categories.keys())
                    if category in categories:
                        index = categories.index(category)
                        x_pos = (index * 42) + 20
                        self._schedule_gui_update(
                            lambda x=x_pos: self.category_selector.place(x=x, y=-10)
                        )
            except Exception as e:
                print(f"Error updating session stats: {e}")
            finally:
                # Schedule next update
                if self.running and self.active_mode == "camera":
                    self.root.after(1000, self._update_session_stats)
        
        threading.Thread(target=calculate_and_update, daemon=True).start()

    def get_screen_brightness(self) -> float:
        """
        Calculate average brightness of screen content.

        Returns:
            float: Average brightness value from screen content
        """
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        sample_width = screen_width // 2
        sample_height = screen_height // 2
        left = (screen_width - sample_width) // 2
        top = (screen_height - sample_height) // 2

        screenshot = ImageGrab.grab(
            bbox=(left, top, left + sample_width, top + sample_height)
        )
        gray_screenshot = screenshot.convert("L")
        return float(np.mean(np.array(gray_screenshot)))

    def smooth_brightness(self, new_value: float) -> float:
        """
        Apply smoothing to brightness values.

        Args:
            new_value: New brightness value to smooth

        Returns:
            float: Smoothed brightness value
        """
        self.screen_brightness_history.append(new_value)
        if len(self.screen_brightness_history) > self.history_size:
            self.screen_brightness_history.pop(0)
        return float(np.median(self.screen_brightness_history))

    def screen_brightness_control(self):
        """Control brightness based on screen content."""
        last_update_time = 0
        update_interval = 0.2
        iteration_count = 0
        print("🖥️ Starting screen-based brightness control")

        while self.running and self.active_mode == "screen":
            current_time = time.time()
            if current_time - last_update_time >= update_interval:
                brightness = self.get_screen_brightness()
                iteration_count += 1
                
                # Only print screen brightness every 25 iterations to reduce spam
                if iteration_count % 25 == 0:
                    print(f"🖥️ Screen reading #{iteration_count}: {brightness:.1f}")
                
                smoothed_brightness = self.smooth_brightness(brightness)
                self._apply_power_aware_brightness(smoothed_brightness)
                last_update_time = current_time
            time.sleep(0.05)

    def camera_brightness_control(self):
        """Control brightness based on camera input."""
        print("📹 Starting camera-based brightness control")
        iteration_count = 0
        while self.running and self.active_mode == "camera":
            brightness = self.controller.get_brightness_from_camera()
            iteration_count += 1
            
            # Update human detection status
            if self.human_detection_enabled.get():
                # Check if brightness is 0 (no human detected)
                self.human_present = brightness > 0.0
                self.last_human_detection_time = time.time()
                
                # Update GUI label (thread-safe)
                status_text = "✅ Present" if self.human_present else "❌ Not Detected"
                self._schedule_gui_update(
                    lambda: self.human_present_label.config(
                        text=f"Present: {status_text}",
                        foreground="green" if self.human_present else "red"
                    )
                )
                
                # Update auto-strict setting if changed
                if hasattr(self.controller, 'auto_strict_detection'):
                    if self.controller.auto_strict_detection != self.auto_strict_enabled.get():
                        self.controller.update_auto_strict_setting(self.auto_strict_enabled.get())
                
                # Update grace period setting if changed
                if hasattr(self.controller, 'grace_period_enabled'):
                    if self.controller.grace_period_enabled != self.grace_period_enabled.get():
                        self.controller.update_grace_period_setting(self.grace_period_enabled.get())
                
                # Update adaptive grace period setting if changed
                if hasattr(self.controller, 'adaptive_grace_period'):
                    if self.controller.adaptive_grace_period != self.adaptive_grace_enabled.get():
                        self.controller.update_adaptive_grace_period_setting(self.adaptive_grace_enabled.get())
                
                # Update distance detection setting if changed
                if hasattr(self.controller, 'enable_distance_detection'):
                    if self.controller.enable_distance_detection != self.distance_detection_enabled.get():
                        self.controller.enable_distance_detection = self.distance_detection_enabled.get()
                
                # Update detection status (thread-safe)
                detection_status = self.controller.human_detector.get_detection_status()
                mode_text = "Strict Mode" if detection_status.get("strict_mode", False) else "Standard Mode"
                auto_text = " (Auto-switched)" if detection_status.get("auto_switched", False) else ""
                stability_text = f" - {detection_status.get('stability_percentage', 0):.0f}% stable"
                grace_text = " [Grace Period]" if detection_status.get("grace_period_active", False) else ""
                
                # Add adaptive grace period info
                if detection_status.get("adaptive_grace_period", False):
                    current_duration = detection_status.get("current_grace_duration", 3.0)
                    face_loss_count = detection_status.get("face_loss_count", 0)
                    adaptive_text = f" (adaptive: {current_duration:.1f}s, {face_loss_count} patterns)"
                else:
                    adaptive_text = ""
                
                status_text_full = f"Status: {mode_text}{auto_text}{stability_text}{grace_text}{adaptive_text}"
                status_color = "orange" if detection_status.get("strict_mode", False) else "blue"
                self._schedule_gui_update(
                    lambda: self.detection_status_label.config(
                        text=status_text_full,
                        foreground=status_color
                    )
                )
            
            # Only print camera brightness every 100 iterations to reduce spam
            if iteration_count % 100 == 0:
                human_status = "👤 Present" if self.human_present else "👤 Not Detected"
                print(f"📹 Camera reading #{iteration_count}: {brightness:.1f} ({human_status})")

            # Store the brightness value for session tracking
            self.camera_brightness_values.append(brightness)

            self._apply_power_aware_brightness(brightness)
            time.sleep(0.1)

    def start_control(self):
        """Start the brightness control."""
        self.active_mode = self.mode_var.get()
        self.running = True

        # Reset session tracking
        self.camera_brightness_values = []
        self.session_start_time = time.time()
        self.time_in_unhealthy_range = 0
        self.last_health_check_time = None
        self.warning_shown = False

        # Reset human detection status
        self.human_present = False
        self.last_human_detection_time = None

        # Disable start button immediately
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

        if self.active_mode == "camera":
            # Show loading indicator
            self._schedule_gui_update(
                lambda: self.start_button.config(text="Initializing camera...")
            )
            
            def setup_and_start():
                try:
                    # Reinitialize controller with current human detection setting and selected camera
                    self.controller = BrightnessController(
                        camera_index=self.selected_camera_index,
                        enable_human_detection=self.human_detection_enabled.get(),
                        strict_detection=self.strict_detection_enabled.get(),
                        enable_distance_detection=self.distance_detection_enabled.get()
                    )
                    self.power_system = PowerManagementSystem(self.controller)
                    self.controller.setup_camera()
                    
                    # Start control thread
                    self.control_thread = threading.Thread(
                        target=self.camera_brightness_control
                    )
                    self.control_thread.daemon = True
                    self.control_thread.start()
                    
                    # Update GUI on main thread
                    self._schedule_gui_update(
                        lambda: self.start_button.config(text="Start")
                    )
                    self._update_current_brightness()
                    self._update_session_stats()
                except Exception as e:
                    self.running = False
                    self._schedule_gui_update(
                        lambda: self.start_button.config(text="Start", state="normal")
                    )
                    self._schedule_gui_update(
                        lambda: self.stop_button.config(state="disabled")
                    )
                    self._thread_safe_messagebox(
                        "showerror",
                        "Camera Error",
                        f"Failed to initialize camera: {e}"
                    )
            
            threading.Thread(target=setup_and_start, daemon=True).start()
        else:
            self.control_thread = threading.Thread(
                target=self.screen_brightness_control
            )
            self.control_thread.daemon = True
            self.control_thread.start()
            self._update_current_brightness()

    def start_test_control(self):
        """Start a 5-second test run of the brightness control."""
        self.test_button.config(state="disabled")
        self.start_button.config(state="disabled")

        # Start the control
        self.start_control()

        # Schedule the stop after 5 seconds
        self.root.after(5000, self.stop_test_control)

    def stop_test_control(self):
        """Stop the test run and reset buttons."""
        self.stop_control()
        self.test_button.config(state="normal")
        self.start_button.config(state="normal")

    def stop_control(self):
        """Stop the brightness control."""
        self.running = False
        if self.control_thread:
            self.control_thread.join()
        if self.active_mode == "camera":
            self.controller.cleanup()

            # Calculate and display final session stats
            if self.camera_brightness_values:
                avg_brightness = np.mean(self.camera_brightness_values)
                category, display_name = self.classify_brightness(avg_brightness)
                is_healthy = self.is_healthy_brightness(category)

                min_brightness = np.min(self.camera_brightness_values)
                max_brightness = np.max(self.camera_brightness_values)

                # Calculate percentage of time in healthy range (only when human is present)
                if self.session_start_time is not None:
                    total_session_time = time.time() - self.session_start_time
                    
                    # Calculate time when human was present
                    if self.human_detection_enabled.get():
                        zero_brightness_count = sum(1 for b in self.camera_brightness_values if b == 0.0)
                        total_readings = len(self.camera_brightness_values)
                        human_present_time = total_session_time * (total_readings - zero_brightness_count) / total_readings
                        
                        # Calculate healthy percentage only for time when human was present
                        healthy_time = human_present_time - self.time_in_unhealthy_range
                        healthy_percentage = (
                            (healthy_time / human_present_time) * 100
                            if human_present_time > 0
                            else 0
                        )
                    else:
                        # If human detection is disabled, use total session time
                        healthy_time = total_session_time - self.time_in_unhealthy_range
                        healthy_percentage = (
                            (healthy_time / total_session_time) * 100
                            if total_session_time > 0
                            else 0
                        )

                print(f"Session Summary:")
                print(f"  Average Brightness: {avg_brightness:.1f} (0-255)")
                print(f"  Brightness Category: {display_name}")
                print(
                    f"  Health Status: {'Healthy' if is_healthy else 'Potentially Straining'}"
                )
                print(f"  Min Brightness: {min_brightness:.1f}")
                print(f"  Max Brightness: {max_brightness:.1f}")
                print(f"  Readings: {len(self.camera_brightness_values)}")

                # Human detection statistics
                if self.human_detection_enabled.get():
                    zero_brightness_count = sum(1 for b in self.camera_brightness_values if b == 0.0)
                    human_detection_percentage = ((len(self.camera_brightness_values) - zero_brightness_count) / len(self.camera_brightness_values)) * 100
                    print(f"  Human Detection: {human_detection_percentage:.1f}% of time")
                    print(f"  Time without human: {zero_brightness_count} readings")

                if self.session_start_time is not None:
                    elapsed_seconds = int(time.time() - self.session_start_time)
                    minutes, seconds = divmod(elapsed_seconds, 60)
                    print(f"  Session Duration: {minutes:02d}:{seconds:02d}")
                    if self.human_detection_enabled.get():
                        print(f"  Time in healthy range (when present): {healthy_percentage:.1f}%")
                    else:
                        print(f"  Time in healthy range: {healthy_percentage:.1f}%")

                    # Show session summary with health recommendations
                    unhealthy_minutes, _ = divmod(self.time_in_unhealthy_range, 60)
                    
                    # Prepare human detection summary
                    human_detection_summary = ""
                    if self.human_detection_enabled.get():
                        zero_brightness_count = sum(1 for b in self.camera_brightness_values if b == 0.0)
                        human_detection_percentage = ((len(self.camera_brightness_values) - zero_brightness_count) / len(self.camera_brightness_values)) * 100
                        human_detection_summary = f"\nHuman detection: {human_detection_percentage:.1f}% of time"
                        if zero_brightness_count > 0:
                            human_detection_summary += f"\nTime without human: {zero_brightness_count} readings"
                    
                    if unhealthy_minutes > 0:
                        self._thread_safe_messagebox(
                            "showinfo",
                            "Session Summary",
                            f"Session completed!\n\n"
                            f"Average brightness: {avg_brightness:.1f}\n"
                            f"Brightness category: {display_name}\n"
                            f"Time spent in non-optimal brightness (when present): {unhealthy_minutes} minutes"
                            f"{human_detection_summary}\n\n"
                            f"Recommendation: {self.health_recommendations.get(category, '')}",
                        )
                    else:
                        summary_msg = (
                            f"Session completed!\n\n"
                            f"Average brightness: {avg_brightness:.1f}\n"
                            f"Brightness category: {display_name}\n"
                            f"Great job! No unhealthy brightness levels detected when you were present."
                            f"{human_detection_summary}\n\n"
                            f"Recommendation: {self.health_recommendations.get(category, '')}"
                        )
                        self._thread_safe_messagebox("showinfo", "Session Summary", summary_msg)

        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.test_button.config(state="normal")  # Enable test button
        self.active_mode = None

    def run(self):
        """Start the GUI application."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        """Handle application closing."""
        self.stop_control()
        # Stop camera preview if active
        if self.camera_preview_active:
            self._stop_camera_preview()
        self.root.destroy()


def main():
    """Main entry point for the application."""
    app = BrightnessGUI()
    app.run()


if __name__ == "__main__":
    main()
