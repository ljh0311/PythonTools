#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Camera View Component

A reusable widget for displaying a single camera feed with controls and status indicators.
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import time
from typing import Optional, Callable


class CameraView(ttk.Frame):
    """A reusable widget for displaying a camera feed."""
    
    def __init__(self, parent, camera_id: str, camera_name: str = None, 
                 on_fullscreen: Optional[Callable] = None,
                 on_snapshot: Optional[Callable] = None,
                 on_settings: Optional[Callable] = None,
                 **kwargs):
        """
        Initialize a camera view widget.
        
        Args:
            parent: Parent widget
            camera_id: Unique identifier for the camera
            camera_name: Display name for the camera (defaults to camera_id)
            on_fullscreen: Callback for fullscreen button (camera_id)
            on_snapshot: Callback for snapshot button (camera_id)
            on_settings: Callback for settings button (camera_id)
        """
        super().__init__(parent, **kwargs)
        
        self.camera_id = camera_id
        self.camera_name = camera_name or camera_id
        self.on_fullscreen = on_fullscreen
        self.on_snapshot = on_snapshot
        self.on_settings = on_settings
        
        # State variables
        self.current_image = None
        self.last_frame_time = None
        self.fps = 0.0
        self.status = "offline"  # offline, online, error, recording
        
        # Create UI
        self._create_ui()
        
    def _create_ui(self):
        """Create the UI components."""
        # Main container frame
        container = ttk.LabelFrame(self, text=self.camera_name)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for video feed
        self.canvas = tk.Canvas(
            container, 
            bg="black", 
            width=320, 
            height=240,
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Bind click events for fullscreen
        self.canvas.bind("<Button-1>", lambda e: self._on_canvas_click())
        self.canvas.bind("<Double-Button-1>", lambda e: self._on_fullscreen())
        
        # Status bar at bottom
        status_frame = ttk.Frame(container)
        status_frame.pack(fill=tk.X, padx=2, pady=(0, 2))
        
        # Status indicator
        self.status_label = ttk.Label(
            status_frame, 
            text="Offline", 
            foreground="red",
            font=("Arial", 9)
        )
        self.status_label.pack(side=tk.LEFT, padx=2)
        
        # FPS label
        self.fps_label = ttk.Label(
            status_frame,
            text="FPS: 0.0",
            font=("Arial", 8),
            foreground="gray"
        )
        self.fps_label.pack(side=tk.LEFT, padx=5)
        
        # Controls frame
        controls_frame = ttk.Frame(status_frame)
        controls_frame.pack(side=tk.RIGHT, padx=2)
        
        # Fullscreen button
        if self.on_fullscreen:
            self.fullscreen_btn = ttk.Button(
                controls_frame,
                text="🔍",
                width=3,
                command=self._on_fullscreen
            )
            self.fullscreen_btn.pack(side=tk.LEFT, padx=1)
            ToolTip(self.fullscreen_btn, "Fullscreen view")
        
        # Snapshot button
        if self.on_snapshot:
            self.snapshot_btn = ttk.Button(
                controls_frame,
                text="📷",
                width=3,
                command=self._on_snapshot
            )
            self.snapshot_btn.pack(side=tk.LEFT, padx=1)
            ToolTip(self.snapshot_btn, "Take snapshot")
        
        # Settings button
        if self.on_settings:
            self.settings_btn = ttk.Button(
                controls_frame,
                text="⚙️",
                width=3,
                command=self._on_settings
            )
            self.settings_btn.pack(side=tk.LEFT, padx=1)
            ToolTip(self.settings_btn, "Camera settings")
        
        # Recording indicator (hidden by default)
        self.recording_indicator = ttk.Label(
            status_frame,
            text="● REC",
            foreground="red",
            font=("Arial", 8, "bold")
        )
        # Will be shown/hidden via show_recording_indicator()
        
    def _on_canvas_click(self):
        """Handle canvas click (single click)."""
        # Could be used for selection or other actions
        pass
    
    def _on_fullscreen(self):
        """Handle fullscreen button click."""
        if self.on_fullscreen:
            self.on_fullscreen(self.camera_id)
    
    def _on_snapshot(self):
        """Handle snapshot button click."""
        if self.on_snapshot:
            self.on_snapshot(self.camera_id)
    
    def _on_settings(self):
        """Handle settings button click."""
        if self.on_settings:
            self.on_settings(self.camera_id)
    
    def update_frame(self, frame, show_fps: bool = True):
        """
        Update the camera view with a new frame.
        
        Args:
            frame: OpenCV frame (numpy array)
            show_fps: Whether to display FPS
        """
        if frame is None or frame.size == 0:
            self.set_status("error", "No frame")
            return
        
        try:
            # Calculate FPS
            current_time = time.time()
            if self.last_frame_time is not None and show_fps:
                elapsed = current_time - self.last_frame_time
                if elapsed > 0:
                    self.fps = 1.0 / elapsed
                    self.fps_label.config(text=f"FPS: {self.fps:.1f}")
            self.last_frame_time = current_time
            
            # Get canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # Skip if canvas isn't properly sized yet
            if canvas_width <= 1 or canvas_height <= 1:
                return
            
            # Resize frame to fit canvas while maintaining aspect ratio
            frame_height, frame_width = frame.shape[:2]
            
            # Calculate scaling factor
            scale_w = canvas_width / frame_width
            scale_h = canvas_height / frame_height
            scale = min(scale_w, scale_h)
            
            new_width = int(frame_width * scale)
            new_height = int(frame_height * scale)
            
            if new_width > 0 and new_height > 0:
                # Resize frame
                resized_frame = cv2.resize(
                    frame, 
                    (new_width, new_height), 
                    interpolation=cv2.INTER_AREA
                )
                
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
                
                # Convert to PIL Image
                img = Image.fromarray(frame_rgb)
                
                # Convert to PhotoImage
                self.current_image = ImageTk.PhotoImage(image=img)
                
                # Update canvas
                self.canvas.delete("all")
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                self.canvas.create_image(x, y, anchor=tk.NW, image=self.current_image)
                
                # Update status
                if self.status != "recording":
                    self.set_status("online", "Active")
            
        except Exception as e:
            self.set_status("error", f"Error: {str(e)[:20]}")
    
    def set_status(self, status: str, message: str = None):
        """
        Update the status indicator.
        
        Args:
            status: Status type (offline, online, error, recording)
            message: Optional status message
        """
        self.status = status
        
        status_colors = {
            "offline": "red",
            "online": "green",
            "error": "orange",
            "recording": "blue"
        }
        
        status_texts = {
            "offline": "Offline",
            "online": "Active",
            "error": "Error",
            "recording": "Recording"
        }
        
        color = status_colors.get(status, "gray")
        text = message or status_texts.get(status, status)
        
        self.status_label.config(text=text, foreground=color)
    
    def show_recording_indicator(self, show: bool = True):
        """
        Show or hide the recording indicator.
        
        Args:
            show: Whether to show the indicator
        """
        if show:
            self.recording_indicator.pack(side=tk.LEFT, padx=5)
            self.set_status("recording", "Recording")
        else:
            self.recording_indicator.pack_forget()
            if self.status == "recording":
                self.set_status("online", "Active")
    
    def clear(self):
        """Clear the camera view."""
        self.canvas.delete("all")
        self.current_image = None
        self.set_status("offline", "Offline")


class ToolTip:
    """Create a tooltip for a given widget."""
    
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        """Show the tooltip."""
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        # Create toplevel window
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # Create tooltip content
        label = tk.Label(
            self.tooltip_window, 
            text=self.text, 
            justify=tk.LEFT,
            background="#ffffe0", 
            relief=tk.SOLID, 
            borderwidth=1,
            font=("Segoe UI", 9)
        )
        label.pack(padx=2, pady=2)
    
    def hide_tooltip(self, event=None):
        """Hide the tooltip."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

