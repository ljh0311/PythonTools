"""
INF2009 Labs Consolidated Launcher
A unified GUI application for running all INF2009 edge computing lab experiments.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import threading
import os
import sys
import time
import platform
from datetime import datetime
import queue
import cv2
import numpy as np
from pathlib import Path

class LabLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("INF2009 Labs - Edge Computing Launcher")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Configuration
        self.codes_dir = Path("Codes")
        self.results_dir = Path("results")
        self.running_process = None
        self.output_queue = queue.Queue()
        self.is_running = False
        
        # Create results directories
        self.results_dir.mkdir(exist_ok=True)
        (self.results_dir / "dl_on_edge").mkdir(exist_ok=True)
        (self.results_dir / "image_analytics").mkdir(exist_ok=True)
        (self.results_dir / "video_analytics").mkdir(exist_ok=True)
        
        # Setup GUI
        self.setup_gui()
        self.check_environment()
        
        # Start output monitor
        self.monitor_output()
    
    def setup_gui(self):
        """Setup the main GUI interface"""
        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='#2c3e50')
        style.configure('Heading.TLabel', font=('Arial', 12, 'bold'), foreground='#34495e')
        style.configure('Status.TLabel', font=('Arial', 10), foreground='#27ae60')
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="INF2009 Edge Computing Labs", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        main_frame.rowconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Create tabs
        self.setup_dl_tab()
        self.setup_image_tab()
        self.setup_video_tab()
        self.setup_results_tab()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        status_label = ttk.Label(status_frame, text="Status:", font=('Arial', 9, 'bold'))
        status_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, style='Status.TLabel')
        self.status_label.pack(side=tk.LEFT)
        
        # Progress bar
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate', length=200)
        self.progress.pack(side=tk.RIGHT, padx=(10, 0))
    
    def setup_dl_tab(self):
        """Setup Deep Learning on Edge tab"""
        dl_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(dl_frame, text="Deep Learning on Edge")
        
        # Left panel - Controls
        left_panel = ttk.LabelFrame(dl_frame, text="Experiment Controls", padding="10")
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        dl_frame.columnconfigure(1, weight=1)
        dl_frame.rowconfigure(0, weight=1)
        
        # Experiment selection
        ttk.Label(left_panel, text="Select Experiment:", style='Heading.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        self.dl_experiment = tk.StringVar(value="mobile_net_basic.py")
        experiments = [
            ("Basic MobileNet", "mobile_net_basic.py"),
            ("Quantized MobileNet", "mobile_net_quantized.py"),
            ("MobileNet with Predictions", "mobile_net_quantized_predictions.py"),
        ]
        
        for i, (label, script) in enumerate(experiments):
            ttk.Radiobutton(left_panel, text=label, variable=self.dl_experiment, 
                          value=script).grid(row=i+1, column=0, sticky=tk.W, pady=2)
        
        # Options
        options_frame = ttk.LabelFrame(left_panel, text="Options", padding="10")
        options_frame.grid(row=len(experiments)+2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.dl_quantize = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Enable Quantization", 
                       variable=self.dl_quantize).grid(row=0, column=0, sticky=tk.W)
        
        self.dl_predictions = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Show Predictions", 
                       variable=self.dl_predictions).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Run button
        run_btn = ttk.Button(left_panel, text="Run Experiment", command=self.run_dl_experiment)
        run_btn.grid(row=len(experiments)+3, column=0, pady=(20, 0), sticky=(tk.W, tk.E))
        
        # Stop button
        stop_btn = ttk.Button(left_panel, text="Stop", command=self.stop_experiment, state=tk.DISABLED)
        stop_btn.grid(row=len(experiments)+4, column=0, pady=(10, 0), sticky=(tk.W, tk.E))
        self.dl_stop_btn = stop_btn
        
        # Right panel - Output
        output_frame = ttk.LabelFrame(dl_frame, text="Output", padding="10")
        output_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        self.dl_output = scrolledtext.ScrolledText(output_frame, height=30, width=60, wrap=tk.WORD)
        self.dl_output.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear button
        clear_btn = ttk.Button(output_frame, text="Clear Output", command=lambda: self.dl_output.delete(1.0, tk.END))
        clear_btn.grid(row=1, column=0, pady=(10, 0))
    
    def setup_image_tab(self):
        """Setup Image Analytics tab"""
        img_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(img_frame, text="Image Analytics")
        
        # Left panel - Controls
        left_panel = ttk.LabelFrame(img_frame, text="Experiment Controls", padding="10")
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        img_frame.columnconfigure(1, weight=1)
        img_frame.rowconfigure(0, weight=1)
        
        # Experiment selection
        ttk.Label(left_panel, text="Select Experiment:", style='Heading.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        self.img_experiment = tk.StringVar(value="image_capture_display.py")
        experiments = [
            ("Color Segmentation", "image_capture_display.py"),
            ("HOG Features", "image_hog_feature.py"),
            ("Face Detection", "image_face_capture.py"),
            ("Facial Landmarks", "image_live_facial_landmarks.py"),
            ("Human Capture (OpenCV)", "image_human_capture_opencv.py"),
            ("Human Capture (MediaPipe)", "image_human_capture.py"),
        ]
        
        for i, (label, script) in enumerate(experiments):
            ttk.Radiobutton(left_panel, text=label, variable=self.img_experiment, 
                          value=script).grid(row=i+1, column=0, sticky=tk.W, pady=2)
        
        # Options
        options_frame = ttk.LabelFrame(left_panel, text="Options", padding="10")
        options_frame.grid(row=len(experiments)+2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.img_capture = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Capture Screenshot", 
                       variable=self.img_capture).grid(row=0, column=0, sticky=tk.W)
        
        self.img_duration = tk.IntVar(value=10)
        ttk.Label(options_frame, text="Duration (seconds):").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        duration_spin = ttk.Spinbox(options_frame, from_=5, to=60, textvariable=self.img_duration, width=10)
        duration_spin.grid(row=2, column=0, sticky=tk.W, pady=(2, 0))
        
        # Run button
        run_btn = ttk.Button(left_panel, text="Run Experiment", command=self.run_image_experiment)
        run_btn.grid(row=len(experiments)+3, column=0, pady=(20, 0), sticky=(tk.W, tk.E))
        
        # Stop button
        stop_btn = ttk.Button(left_panel, text="Stop", command=self.stop_experiment, state=tk.DISABLED)
        stop_btn.grid(row=len(experiments)+4, column=0, pady=(10, 0), sticky=(tk.W, tk.E))
        self.img_stop_btn = stop_btn
        
        # Right panel - Output
        output_frame = ttk.LabelFrame(img_frame, text="Output", padding="10")
        output_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        self.img_output = scrolledtext.ScrolledText(output_frame, height=30, width=60, wrap=tk.WORD)
        self.img_output.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear button
        clear_btn = ttk.Button(output_frame, text="Clear Output", command=lambda: self.img_output.delete(1.0, tk.END))
        clear_btn.grid(row=1, column=0, pady=(10, 0))
    
    def setup_video_tab(self):
        """Setup Video Analytics tab"""
        vid_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(vid_frame, text="Video Analytics")
        
        # Left panel - Controls
        left_panel = ttk.LabelFrame(vid_frame, text="Experiment Controls", padding="10")
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        vid_frame.columnconfigure(1, weight=1)
        vid_frame.rowconfigure(0, weight=1)
        
        # Experiment selection
        ttk.Label(left_panel, text="Select Experiment:", style='Heading.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        self.vid_experiment = tk.StringVar(value="optical_flow.py")
        experiments = [
            ("Optical Flow", "optical_flow.py"),
            ("Hand Landmark Detection", "hand_landmark.py"),
            ("Hand Gesture Recognition", "hand_gesture.py"),
            ("Object Detection", "obj_detection.py"),
        ]
        
        for i, (label, script) in enumerate(experiments):
            ttk.Radiobutton(left_panel, text=label, variable=self.vid_experiment, 
                          value=script).grid(row=i+1, column=0, sticky=tk.W, pady=2)
        
        # Options
        options_frame = ttk.LabelFrame(left_panel, text="Options", padding="10")
        options_frame.grid(row=len(experiments)+2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.vid_capture = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Capture Screenshot", 
                       variable=self.vid_capture).grid(row=0, column=0, sticky=tk.W)
        
        self.vid_duration = tk.IntVar(value=10)
        ttk.Label(options_frame, text="Duration (seconds):").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        duration_spin = ttk.Spinbox(options_frame, from_=5, to=60, textvariable=self.vid_duration, width=10)
        duration_spin.grid(row=2, column=0, sticky=tk.W, pady=(2, 0))
        
        # Run button
        run_btn = ttk.Button(left_panel, text="Run Experiment", command=self.run_video_experiment)
        run_btn.grid(row=len(experiments)+3, column=0, pady=(20, 0), sticky=(tk.W, tk.E))
        
        # Stop button
        stop_btn = ttk.Button(left_panel, text="Stop", command=self.stop_experiment, state=tk.DISABLED)
        stop_btn.grid(row=len(experiments)+4, column=0, pady=(10, 0), sticky=(tk.W, tk.E))
        self.vid_stop_btn = stop_btn
        
        # Right panel - Output
        output_frame = ttk.LabelFrame(vid_frame, text="Output", padding="10")
        output_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        self.vid_output = scrolledtext.ScrolledText(output_frame, height=30, width=60, wrap=tk.WORD)
        self.vid_output.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear button
        clear_btn = ttk.Button(output_frame, text="Clear Output", command=lambda: self.vid_output.delete(1.0, tk.END))
        clear_btn.grid(row=1, column=0, pady=(10, 0))
    
    def setup_results_tab(self):
        """Setup Results/Reports tab"""
        results_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(results_frame, text="Results & Reports")
        
        # Left panel - Actions
        left_panel = ttk.LabelFrame(results_frame, text="Actions", padding="10")
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 10))
        
        ttk.Button(left_panel, text="View DL on Edge Results", 
                  command=lambda: self.view_results("dl_on_edge")).pack(fill=tk.X, pady=5)
        ttk.Button(left_panel, text="View Image Analytics Results", 
                  command=lambda: self.view_results("image_analytics")).pack(fill=tk.X, pady=5)
        ttk.Button(left_panel, text="View Video Analytics Results", 
                  command=lambda: self.view_results("video_analytics")).pack(fill=tk.X, pady=5)
        ttk.Button(left_panel, text="Generate Combined Report", 
                  command=self.generate_report).pack(fill=tk.X, pady=5)
        ttk.Button(left_panel, text="Open Results Folder", 
                  command=self.open_results_folder).pack(fill=tk.X, pady=5)
        
        # Right panel - Results display
        right_panel = ttk.LabelFrame(results_frame, text="Results", padding="10")
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(1, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        self.results_text = scrolledtext.ScrolledText(right_panel, height=35, width=70, wrap=tk.WORD)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Initial message
        self.results_text.insert(tk.END, "Select an action to view results or generate reports.\n\n")
        self.results_text.insert(tk.END, "Available result types:\n")
        self.results_text.insert(tk.END, "- Deep Learning on Edge: FPS measurements, quantization results\n")
        self.results_text.insert(tk.END, "- Image Analytics: Screenshots, feature visualizations\n")
        self.results_text.insert(tk.END, "- Video Analytics: Experiment screenshots, detection results\n")
    
    def check_environment(self):
        """Check if required packages are available"""
        missing = []
        warnings = []
        
        try:
            import torch
            self.log_output("dl", f"PyTorch version: {torch.__version__}")
        except ImportError:
            missing.append("torch")
            warnings.append("Deep Learning experiments will not work")
        
        try:
            import cv2
            self.log_output("img", f"OpenCV version: {cv2.__version__}")
        except ImportError:
            missing.append("opencv-python")
            warnings.append("Image/Video experiments will not work")
        
        try:
            import mediapipe
            self.log_output("vid", "MediaPipe available")
        except ImportError:
            missing.append("mediapipe")
            warnings.append("Some video analytics features may not work")
        
        try:
            import pyautogui
        except ImportError:
            warnings.append("Screenshot capture requires pyautogui (optional)")
        
        if missing:
            self.log_output("dl", f"\n⚠ Warning: Missing packages: {', '.join(missing)}")
            self.log_output("dl", f"Install with: pip install {' '.join(missing)}\n")
        
        if warnings:
            self.log_output("img", "\n".join([f"ℹ {w}" for w in warnings]) + "\n")
    
    def log_output(self, tab, message):
        """Log message to appropriate output window"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}\n"
        
        if tab == "dl":
            self.dl_output.insert(tk.END, formatted_msg)
            self.dl_output.see(tk.END)
        elif tab == "img":
            self.img_output.insert(tk.END, formatted_msg)
            self.img_output.see(tk.END)
        elif tab == "vid":
            self.vid_output.insert(tk.END, formatted_msg)
            self.vid_output.see(tk.END)
    
    def run_dl_experiment(self):
        """Run Deep Learning on Edge experiment"""
        if self.is_running:
            messagebox.showwarning("Already Running", "An experiment is already running. Please stop it first.")
            return
        
        script = self.dl_experiment.get()
        script_path = self.codes_dir / script
        
        if not script_path.exists():
            messagebox.showerror("Error", f"Script not found: {script_path}")
            return
        
        self.dl_stop_btn.config(state=tk.NORMAL)
        self.is_running = True
        self.status_var.set("Running DL Experiment...")
        self.progress.start()
        
        def run_thread():
            try:
                # Modify script if needed
                with open(script_path, 'r') as f:
                    content = f.read()
                
                # Apply quantization setting
                if self.dl_quantize.get():
                    content = content.replace('quantize = False', 'quantize = True')
                    content = content.replace('quantize=False', 'quantize=True')
                else:
                    content = content.replace('quantize = True', 'quantize = False')
                    content = content.replace('quantize=True', 'quantize=False')
                
                # Add auto-exit after FPS measurements
                if 'frame_count = 0' in content and 'fps_measurements' not in content:
                    content = content.replace(
                        'frame_count = 0',
                        'frame_count = 0\n        fps_measurements = 0'
                    )
                    content = content.replace(
                        'print(f"============={frame_count / (now-last_logged)} fps =================")',
                        'print(f"============={frame_count / (now-last_logged)} fps =================")\n            fps_measurements += 1\n            if fps_measurements >= 3:\n                print("Completed FPS measurements")\n                break'
                    )
                
                # Save modified script
                temp_script = self.codes_dir / "temp_dl_script.py"
                with open(temp_script, 'w') as f:
                    f.write(content)
                
                # Run the script
                self.log_output("dl", f"Starting experiment: {script}")
                self.log_output("dl", f"Quantization: {self.dl_quantize.get()}")
                self.log_output("dl", "Running...\n")
                
                process = subprocess.Popen(
                    [sys.executable, str(temp_script)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                self.running_process = process
                
                # Read output
                for line in iter(process.stdout.readline, ''):
                    if not self.is_running:
                        break
                    if line:
                        self.output_queue.put(("dl", line))
                
                process.wait()
                
                if process.returncode == 0:
                    self.log_output("dl", "\nExperiment completed successfully!")
                else:
                    self.log_output("dl", f"\nExperiment exited with code: {process.returncode}")
                
            except Exception as e:
                self.log_output("dl", f"\nError: {str(e)}")
            finally:
                # Cleanup
                temp_script = self.codes_dir / "temp_dl_script.py"
                if temp_script.exists():
                    temp_script.unlink()
                
                self.is_running = False
                self.running_process = None
                self.root.after(0, self.dl_stop_btn.config, {"state": tk.DISABLED})
                self.root.after(0, self.progress.stop)
                self.root.after(0, lambda: self.status_var.set("Ready"))
        
        threading.Thread(target=run_thread, daemon=True).start()
    
    def run_image_experiment(self):
        """Run Image Analytics experiment"""
        if self.is_running:
            messagebox.showwarning("Already Running", "An experiment is already running. Please stop it first.")
            return
        
        script = self.img_experiment.get()
        script_path = self.codes_dir / script
        
        if not script_path.exists():
            messagebox.showerror("Error", f"Script not found: {script_path}")
            return
        
        self.img_stop_btn.config(state=tk.NORMAL)
        self.is_running = True
        self.status_var.set("Running Image Analytics Experiment...")
        self.progress.start()
        
        def run_thread():
            try:
                self.log_output("img", f"Starting experiment: {script}")
                self.log_output("img", f"Duration: {self.img_duration.get()} seconds")
                self.log_output("img", "Running...\n")
                
                process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                self.running_process = process
                
                # Wait for specified duration
                start_time = time.time()
                while time.time() - start_time < self.img_duration.get() and self.is_running:
                    line = process.stdout.readline()
                    if line:
                        self.output_queue.put(("img", line))
                    time.sleep(0.1)
                
                # Capture screenshot if enabled
                if self.img_capture.get() and self.is_running:
                    self.capture_screenshot("image_analytics", script)
                
                # Terminate process
                process.terminate()
                process.wait(timeout=3)
                
                self.log_output("img", "\nExperiment completed!")
                
            except Exception as e:
                self.log_output("img", f"\nError: {str(e)}")
            finally:
                self.is_running = False
                self.running_process = None
                self.root.after(0, self.img_stop_btn.config, {"state": tk.DISABLED})
                self.root.after(0, self.progress.stop)
                self.root.after(0, lambda: self.status_var.set("Ready"))
        
        threading.Thread(target=run_thread, daemon=True).start()
    
    def run_video_experiment(self):
        """Run Video Analytics experiment"""
        if self.is_running:
            messagebox.showwarning("Already Running", "An experiment is already running. Please stop it first.")
            return
        
        script = self.vid_experiment.get()
        script_path = self.codes_dir / script
        
        if not script_path.exists():
            messagebox.showerror("Error", f"Script not found: {script_path}")
            return
        
        self.vid_stop_btn.config(state=tk.NORMAL)
        self.is_running = True
        self.status_var.set("Running Video Analytics Experiment...")
        self.progress.start()
        
        def run_thread():
            try:
                self.log_output("vid", f"Starting experiment: {script}")
                self.log_output("vid", f"Duration: {self.vid_duration.get()} seconds")
                self.log_output("vid", "Running...\n")
                
                process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                self.running_process = process
                
                # Wait for specified duration
                start_time = time.time()
                while time.time() - start_time < self.vid_duration.get() and self.is_running:
                    line = process.stdout.readline()
                    if line:
                        self.output_queue.put(("vid", line))
                    time.sleep(0.1)
                
                # Capture screenshot if enabled
                if self.vid_capture.get() and self.is_running:
                    self.capture_screenshot("video_analytics", script)
                
                # Terminate process
                process.terminate()
                process.wait(timeout=3)
                
                self.log_output("vid", "\nExperiment completed!")
                
            except Exception as e:
                self.log_output("vid", f"\nError: {str(e)}")
            finally:
                self.is_running = False
                self.running_process = None
                self.root.after(0, self.vid_stop_btn.config, {"state": tk.DISABLED})
                self.root.after(0, self.progress.stop)
                self.root.after(0, lambda: self.status_var.set("Ready"))
        
        threading.Thread(target=run_thread, daemon=True).start()
    
    def stop_experiment(self):
        """Stop the currently running experiment"""
        if self.running_process:
            self.running_process.terminate()
            self.is_running = False
            self.log_output("dl", "\nExperiment stopped by user.")
            self.log_output("img", "\nExperiment stopped by user.")
            self.log_output("vid", "\nExperiment stopped by user.")
    
    def capture_screenshot(self, category, script_name):
        """Capture a screenshot of the running experiment"""
        try:
            # Wait a bit for window to appear
            time.sleep(2)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{script_name.replace('.py', '')}_{timestamp}.png"
            result_path = self.results_dir / category / filename
            
            # Try to use pyautogui if available, otherwise fallback
            try:
                import pyautogui
                screenshot = pyautogui.screenshot()
                screenshot.save(str(result_path))
                self.log_output("img" if category == "image_analytics" else "vid", 
                              f"Screenshot saved: {filename}")
            except ImportError:
                # Fallback: just log that screenshot was requested
                self.log_output("img" if category == "image_analytics" else "vid", 
                              f"Screenshot requested: {filename} (install pyautogui for automatic capture)")
            
        except Exception as e:
            self.log_output("img" if category == "image_analytics" else "vid", 
                          f"Screenshot capture error: {str(e)}")
    
    def monitor_output(self):
        """Monitor output queue and update GUI"""
        try:
            while True:
                tab, message = self.output_queue.get_nowait()
                self.log_output(tab, message.rstrip())
        except queue.Empty:
            pass
        
        self.root.after(100, self.monitor_output)
    
    def view_results(self, category):
        """View results for a specific category"""
        result_dir = self.results_dir / category
        
        if not result_dir.exists():
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"No results found for {category}\n")
            return
        
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, f"Results for {category.replace('_', ' ').title()}\n")
        self.results_text.insert(tk.END, "=" * 60 + "\n\n")
        
        files = list(result_dir.glob("*"))
        if files:
            for file in sorted(files):
                if file.is_file():
                    size = file.stat().st_size
                    mod_time = datetime.fromtimestamp(file.stat().st_mtime)
                    self.results_text.insert(tk.END, f"File: {file.name}\n")
                    self.results_text.insert(tk.END, f"  Size: {size:,} bytes\n")
                    self.results_text.insert(tk.END, f"  Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        else:
            self.results_text.insert(tk.END, "No result files found.\n")
    
    def generate_report(self):
        """Generate a combined lab results report"""
        report_path = Path("lab_results.md")
        
        report = f"""# INF2009 Lab Results

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Environment Information

- Platform: {platform.system()} {platform.release()}
- Python Version: {sys.version.split()[0]}

## Results Summary

"""
        
        # Add results from each category
        for category in ["dl_on_edge", "image_analytics", "video_analytics"]:
            result_dir = self.results_dir / category
            if result_dir.exists():
                files = list(result_dir.glob("*"))
                if files:
                    report += f"\n### {category.replace('_', ' ').title()}\n\n"
                    for file in sorted(files):
                        if file.is_file():
                            report += f"- {file.name}\n"
        
        try:
            with open(report_path, 'w') as f:
                f.write(report)
            
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"Report generated successfully!\n")
            self.results_text.insert(tk.END, f"Location: {report_path.absolute()}\n\n")
            self.results_text.insert(tk.END, report)
            
            messagebox.showinfo("Success", f"Report generated: {report_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {str(e)}")
    
    def open_results_folder(self):
        """Open the results folder in file explorer"""
        import subprocess
        import platform as plat
        
        path = self.results_dir.absolute()
        
        if plat.system() == "Windows":
            os.startfile(path)
        elif plat.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])


def main():
    root = tk.Tk()
    app = LabLauncher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
