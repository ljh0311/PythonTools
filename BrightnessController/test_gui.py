"""
GUI Test Application for Distance-Based Human Detection
Provides an intuitive interface for testing and calibrating human detection features.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import cv2
import numpy as np
import threading
import time
from PIL import Image, ImageTk
from brightness_controller import HumanDetector


class TestGUI:
    """GUI application for testing and calibrating human detection."""
    
    def __init__(self):
        """Initialize the GUI application."""
        self.root = tk.Tk()
        self.root.title("Human Detection Test & Calibration Tool")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)
        
        # Initialize controller
        self.controller = HumanDetector(
            enable_human_detection=True,
            strict_detection=False,
            enable_distance_detection=True
        )
        self.controller._setup_face_detection()
        
        # Camera setup
        self.cap = None
        self.camera_active = False
        self.calibration_mode = False
        self.calibration_samples = []
        
        # GUI state
        self.distance_detection_enabled = tk.BooleanVar(value=True)
        self.strict_detection_enabled = tk.BooleanVar(value=False)
        self.auto_strict_enabled = tk.BooleanVar(value=True)
        
        # Detection info
        self.detection_info = {
            'faces_detected': 0,
            'primary_user_detected': False,
            'distant_person_detected': False,
            'largest_face_percentage': 0.0,
            'face_details': []
        }
        
        self._setup_gui()
        self._setup_camera()
        
    def _setup_gui(self):
        """Set up the GUI components."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Left panel - Controls
        left_panel = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        left_panel.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Camera controls
        camera_frame = ttk.LabelFrame(left_panel, text="Camera", padding="5")
        camera_frame.pack(fill="x", pady=(0, 10))
        
        self.camera_button = ttk.Button(camera_frame, text="Start Camera", command=self._toggle_camera)
        self.camera_button.pack(fill="x", pady=2)
        
        self.calibration_button = ttk.Button(camera_frame, text="Start Calibration", command=self._toggle_calibration)
        self.calibration_button.pack(fill="x", pady=2)
        
        # Detection settings
        detection_frame = ttk.LabelFrame(left_panel, text="Detection Settings", padding="5")
        detection_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Checkbutton(detection_frame, text="Distance Detection", variable=self.distance_detection_enabled, 
                       command=self._update_distance_detection).pack(anchor="w", pady=2)
        ttk.Checkbutton(detection_frame, text="Strict Detection", variable=self.strict_detection_enabled,
                       command=self._update_strict_detection).pack(anchor="w", pady=2)
        ttk.Checkbutton(detection_frame, text="Auto-Strict", variable=self.auto_strict_enabled,
                       command=self._update_auto_strict).pack(anchor="w", pady=2)
        
        # Calibration controls
        calibration_frame = ttk.LabelFrame(left_panel, text="Calibration", padding="5")
        calibration_frame.pack(fill="x", pady=(0, 10))
        
        self.add_primary_button = ttk.Button(calibration_frame, text="Add Primary User Sample", 
                                           command=self._add_primary_sample, state="disabled")
        self.add_primary_button.pack(fill="x", pady=2)
        
        self.add_distant_button = ttk.Button(calibration_frame, text="Add Distant Person Sample", 
                                           command=self._add_distant_sample, state="disabled")
        self.add_distant_button.pack(fill="x", pady=2)
        
        self.reset_thresholds_button = ttk.Button(calibration_frame, text="Reset to Defaults", 
                                                command=self._reset_thresholds)
        self.reset_thresholds_button.pack(fill="x", pady=2)
        
        # Status display
        status_frame = ttk.LabelFrame(left_panel, text="Status", padding="5")
        status_frame.pack(fill="x", pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="Camera: Inactive", foreground="red")
        self.status_label.pack(anchor="w", pady=2)
        
        self.calibration_status_label = ttk.Label(status_frame, text="Calibration: Inactive", foreground="gray")
        self.calibration_status_label.pack(anchor="w", pady=2)
        
        self.samples_label = ttk.Label(status_frame, text="Samples: 0")
        self.samples_label.pack(anchor="w", pady=2)
        
        # Right panel - Video and Info
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        
        # Video display
        video_frame = ttk.LabelFrame(right_panel, text="Camera Feed", padding="5")
        video_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        video_frame.columnconfigure(0, weight=1)
        video_frame.rowconfigure(0, weight=1)
        
        self.video_label = ttk.Label(video_frame, text="Camera not started", background="black", foreground="white")
        self.video_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Detection info
        info_frame = ttk.LabelFrame(right_panel, text="Detection Information", padding="5")
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        info_frame.columnconfigure(0, weight=1)
        
        # Detection results
        results_frame = ttk.Frame(info_frame)
        results_frame.pack(fill="x", pady=(0, 10))
        
        # Primary user detection
        primary_frame = ttk.Frame(results_frame)
        primary_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(primary_frame, text="Primary User:").pack(anchor="w")
        self.primary_status_label = ttk.Label(primary_frame, text="Not Detected", foreground="red")
        self.primary_status_label.pack(anchor="w")
        
        # Distant person detection
        distant_frame = ttk.Frame(results_frame)
        distant_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(distant_frame, text="Distant Person:").pack(anchor="w")
        self.distant_status_label = ttk.Label(distant_frame, text="Not Detected", foreground="gray")
        self.distant_status_label.pack(anchor="w")
        
        # Face count
        face_frame = ttk.Frame(results_frame)
        face_frame.pack(side="left", fill="x", expand=True)
        ttk.Label(face_frame, text="Faces Detected:").pack(anchor="w")
        self.face_count_label = ttk.Label(face_frame, text="0")
        self.face_count_label.pack(anchor="w")
        
        # Thresholds display
        thresholds_frame = ttk.LabelFrame(info_frame, text="Current Thresholds", padding="5")
        thresholds_frame.pack(fill="x", pady=(0, 10))
        
        self.thresholds_text = scrolledtext.ScrolledText(thresholds_frame, height=4, width=50)
        self.thresholds_text.pack(fill="x")
        
        # Log display
        log_frame = ttk.LabelFrame(info_frame, text="Activity Log", padding="5")
        log_frame.pack(fill="x")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, width=50)
        self.log_text.pack(fill="both", expand=True)
        
        # Bottom panel - Help
        help_frame = ttk.LabelFrame(main_frame, text="Help", padding="5")
        help_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        help_text = """
        How to use this tool:
        1. Start the camera to begin testing
        2. Enable Distance Detection to differentiate between close and distant people
        3. Use Calibration mode to train the system for your environment
        4. Add samples at different distances during calibration
        5. Monitor detection results in real-time
        """
        help_label = ttk.Label(help_frame, text=help_text, justify="left")
        help_label.pack(anchor="w")
        
        # Initialize thresholds display
        self._update_thresholds_display()
        
    def _setup_camera(self):
        """Initialize camera."""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    raise RuntimeError("Could not open camera")
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.log("Camera initialized successfully")
        except Exception as e:
            self.log(f"Error initializing camera: {e}")
            messagebox.showerror("Camera Error", f"Could not initialize camera: {e}")
    
    def _toggle_camera(self):
        """Toggle camera on/off."""
        if not self.camera_active:
            self.camera_active = True
            self.camera_button.config(text="Stop Camera")
            self.status_label.config(text="Camera: Active", foreground="green")
            self.log("Camera started")
            self._start_video_thread()
        else:
            self.camera_active = False
            self.camera_button.config(text="Start Camera")
            self.status_label.config(text="Camera: Inactive", foreground="red")
            self.log("Camera stopped")
    
    def _toggle_calibration(self):
        """Toggle calibration mode."""
        if not self.calibration_mode:
            self.calibration_mode = True
            self.calibration_button.config(text="Stop Calibration")
            self.calibration_status_label.config(text="Calibration: Active", foreground="orange")
            self.add_primary_button.config(state="normal")
            self.add_distant_button.config(state="normal")
            self.controller.start_calibration()
            self.log("Calibration mode started")
        else:
            success = self.controller.stop_calibration()
            if success:
                self.calibration_mode = False
                self.calibration_button.config(text="Start Calibration")
                self.calibration_status_label.config(text="Calibration: Complete", foreground="green")
                self.add_primary_button.config(state="disabled")
                self.add_distant_button.config(state="disabled")
                self.log("Calibration completed successfully")
                self._update_thresholds_display()
            else:
                messagebox.showwarning("Calibration", "Need at least 5 samples to complete calibration")
    
    def _add_primary_sample(self):
        """Add primary user sample during calibration."""
        if self.detection_info['largest_face_percentage'] > 0:
            self.controller.add_calibration_sample(
                self.detection_info['largest_face_percentage'], 'primary_user'
            )
            self.calibration_samples.append({
                'type': 'primary_user',
                'percentage': self.detection_info['largest_face_percentage'],
                'timestamp': time.time()
            })
            self._update_samples_display()
            self.log(f"Added primary user sample: {self.detection_info['largest_face_percentage']:.3f}")
        else:
            messagebox.showwarning("No Face", "No face detected to add as primary user sample")
    
    def _add_distant_sample(self):
        """Add distant person sample during calibration."""
        if self.detection_info['largest_face_percentage'] > 0:
            self.controller.add_calibration_sample(
                self.detection_info['largest_face_percentage'], 'distant_person'
            )
            self.calibration_samples.append({
                'type': 'distant_person',
                'percentage': self.detection_info['largest_face_percentage'],
                'timestamp': time.time()
            })
            self._update_samples_display()
            self.log(f"Added distant person sample: {self.detection_info['largest_face_percentage']:.3f}")
        else:
            messagebox.showwarning("No Face", "No face detected to add as distant person sample")
    
    def _reset_thresholds(self):
        """Reset thresholds to default values."""
        self.controller.calibrated_thresholds = {
            'primary_user_min': 0.025,
            'primary_user_max': 0.15,
            'distant_person_min': 0.008,
            'distant_person_max': 0.025
        }
        self._update_thresholds_display()
        self.log("Reset to default thresholds")
    
    def _update_distance_detection(self):
        """Update distance detection setting."""
        self.controller.enable_distance_detection = self.distance_detection_enabled.get()
        status = "enabled" if self.distance_detection_enabled.get() else "disabled"
        self.log(f"Distance detection {status}")
    
    def _update_strict_detection(self):
        """Update strict detection setting."""
        self.controller.strict_detection = self.strict_detection_enabled.get()
        status = "enabled" if self.strict_detection_enabled.get() else "disabled"
        self.log(f"Strict detection {status}")
    
    def _update_auto_strict(self):
        """Update auto-strict detection setting."""
        self.controller.auto_strict_detection = self.auto_strict_enabled.get()
        status = "enabled" if self.auto_strict_enabled.get() else "disabled"
        self.log(f"Auto-strict detection {status}")
    
    def _update_samples_display(self):
        """Update the samples count display."""
        count = len(self.calibration_samples)
        self.samples_label.config(text=f"Samples: {count}")
    
    def _update_thresholds_display(self):
        """Update the thresholds display."""
        thresholds = self.controller.calibrated_thresholds
        text = f"""Primary User:
  Min: {thresholds['primary_user_min']:.4f}
  Max: {thresholds['primary_user_max']:.4f}

Distant Person:
  Min: {thresholds['distant_person_min']:.4f}
  Max: {thresholds['distant_person_max']:.4f}"""
        
        self.thresholds_text.delete(1.0, tk.END)
        self.thresholds_text.insert(1.0, text)
    
    def _start_video_thread(self):
        """Start the video processing thread."""
        self.video_thread = threading.Thread(target=self._video_loop, daemon=True)
        self.video_thread.start()
    
    def _video_loop(self):
        """Main video processing loop."""
        while self.camera_active:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    # Process frame for detection
                    self._process_frame(frame)
                    
                    # Update video display
                    self._update_video_display(frame)
                    
                    # Update detection info
                    self._update_detection_display()
                    
                    # Small delay to prevent excessive CPU usage
                    time.sleep(0.033)  # ~30 FPS
                else:
                    break
            else:
                break
    
    def _process_frame(self, frame):
        """Process frame for human detection."""
        try:
            # Get detection info
            self.detection_info = self.controller.get_detection_info(frame)
            
            # Check for detection instability
            self.controller._check_detection_instability()
            
        except Exception as e:
            self.log(f"Error processing frame: {e}")
    
    def _update_video_display(self, frame):
        """Update the video display with detection overlays."""
        try:
            # Draw detection results on frame
            display_frame = frame.copy()
            
            # Draw rectangles around detected faces
            for face_detail in self.detection_info['face_details']:
                x, y, w, h = face_detail['x'], face_detail['y'], face_detail['w'], face_detail['h']
                face_type = face_detail['face_type']
                
                # Choose color based on face type
                if face_type == "primary_user":
                    color = (0, 255, 0)  # Green
                    label = "PRIMARY USER"
                elif face_type == "distant_person":
                    color = (0, 165, 255)  # Orange
                    label = "DISTANT PERSON"
                else:
                    color = (128, 128, 128)  # Gray
                    label = "TOO SMALL"
                
                # Draw rectangle
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
                
                # Draw label
                cv2.putText(display_frame, label, (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                # Draw face percentage
                cv2.putText(display_frame, f"{face_detail['face_percentage']:.3f}", 
                           (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Convert to PIL Image for Tkinter
            display_frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(display_frame_rgb)
            
            # Resize for display (maintain aspect ratio)
            display_width = 640
            display_height = 480
            pil_image = pil_image.resize((display_width, display_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_image)
            
            # Update display (use after_idle to avoid threading issues)
            self.root.after_idle(self._update_video_label, photo)
            
        except Exception as e:
            self.log(f"Error updating video display: {e}")
    
    def _update_video_label(self, photo):
        """Update the video label with new image (called from main thread)."""
        self.video_label.config(image=photo)
        self.video_label.image = photo  # Keep a reference
    
    def _update_detection_display(self):
        """Update the detection information display."""
        try:
            # Update primary user status
            if self.detection_info['primary_user_detected']:
                self.primary_status_label.config(text="✅ Detected", foreground="green")
            else:
                self.primary_status_label.config(text="❌ Not Detected", foreground="red")
            
            # Update distant person status
            if self.detection_info['distant_person_detected']:
                self.distant_status_label.config(text="✅ Detected", foreground="orange")
            else:
                self.distant_status_label.config(text="❌ Not Detected", foreground="gray")
            
            # Update face count
            self.face_count_label.config(text=str(self.detection_info['faces_detected']))
            
        except Exception as e:
            self.log(f"Error updating detection display: {e}")
    
    def log(self, message):
        """Add message to log display."""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # Use after_idle to update from any thread
        self.root.after_idle(self._add_log_message, log_message)
    
    def _add_log_message(self, message):
        """Add message to log (called from main thread)."""
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        
        # Limit log size
        if self.log_text.index(tk.END).split('.')[0] > '1000':
            self.log_text.delete('1.0', '2.0')
    
    def run(self):
        """Start the GUI application."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()
    
    def _on_closing(self):
        """Handle application closing."""
        self.camera_active = False
        if self.cap:
            self.cap.release()
        self.root.destroy()


def main():
    """Main entry point."""
    app = TestGUI()
    app.run()


if __name__ == "__main__":
    main()
