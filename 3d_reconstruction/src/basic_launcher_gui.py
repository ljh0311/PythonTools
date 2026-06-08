#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Basic 3D Reconstruction Launcher GUI
Simple launcher for 3D reconstruction applications.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import sys
import os
from pathlib import Path
import glob
import threading

# Import the processor to use its logic directly
from photo_upload_processor import PhotoUploadProcessor

class BasicLauncherGUI:
    """Basic launcher GUI for 3D reconstruction applications."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("3D Reconstruction Launcher")
        self.root.geometry("500x450")
        self.root.resizable(False, False)
        
        # Center the window
        self.center_window()
        
        self.setup_ui()
        
    def center_window(self):
        """Center the window on screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """Setup the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="3D Reconstruction Suite", 
                               font=("Arial", 20, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 30))
        
        # Subtitle
        subtitle_label = ttk.Label(main_frame, text="Choose an option:", 
                                  font=("Arial", 12))
        subtitle_label.grid(row=1, column=0, pady=(0, 20))
        
        # Buttons frame
        self.buttons_frame = ttk.Frame(main_frame)
        self.buttons_frame.grid(row=2, column=0, pady=(0, 30))
        
        # Live reconstruction button
        self.live_btn = ttk.Button(self.buttons_frame, text="📹 Live Camera Reconstruction", 
                             command=self.launch_live_reconstruction,
                             style="Action.TButton")
        self.live_btn.grid(row=0, column=0, pady=10, padx=10, sticky=(tk.W, tk.E))
        
        # Photo to 360 Panorama button
        self.photo_btn = ttk.Button(self.buttons_frame, text="📸 Photo to 360 Panorama", 
                              command=self.launch_photo_reconstruction,
                              style="Action.TButton")
        self.photo_btn.grid(row=1, column=0, pady=10, padx=10, sticky=(tk.W, tk.E))
        
        # View Panorama button
        self.view_btn = ttk.Button(self.buttons_frame, text="👁️ View Panorama", 
                             command=self.view_panorama,
                             style="Action.TButton")
        self.view_btn.grid(row=2, column=0, pady=10, padx=10, sticky=(tk.W, tk.E))
        
        # Separator
        separator = ttk.Separator(main_frame, orient=tk.HORIZONTAL)
        separator.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=20)
        
        # Utility buttons frame
        utils_frame = ttk.Frame(main_frame)
        utils_frame.grid(row=4, column=0, pady=(0, 20))
        
        # Help button
        help_btn = ttk.Button(utils_frame, text="❓ Help", 
                             command=self.show_help)
        help_btn.grid(row=0, column=0, pady=5, padx=5)
        
        # Exit button
        exit_btn = ttk.Button(utils_frame, text="🚪 Exit", 
                             command=self.root.quit)
        exit_btn.grid(row=0, column=1, pady=5, padx=5)
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.status_var = tk.StringVar(value="Ready to launch applications")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.grid(row=0, column=0, sticky=tk.W)

        self.progress_bar = ttk.Progressbar(status_frame, orient="horizontal", length=100, mode="determinate")
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5,0))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        self.buttons_frame.columnconfigure(0, weight=1)
        utils_frame.columnconfigure(0, weight=1)
        utils_frame.columnconfigure(1, weight=1)
        status_frame.columnconfigure(0, weight=1)
        
        # Configure button styles
        style = ttk.Style()
        style.configure("Action.TButton", font=("Arial", 12, "bold"), padding=10)
    
    def set_buttons_state(self, state):
        """Enable or disable the main action buttons."""
        for button in [self.live_btn, self.photo_btn, self.view_btn]:
            button.config(state=state)

    def launch_live_reconstruction(self):
        """Launch the live camera reconstruction in a new console window."""
        self.status_var.set("Launching live reconstruction in a new window...")
        try:
            src_dir = Path(__file__).parent
            script_path = src_dir / "live_reconstruction_app.py"
            
            # On Windows, 'start' runs the command in a new window.
            # /k keeps the window open after the script finishes.
            command = f"start cmd /k python \"{script_path}\""
            subprocess.Popen(command, shell=True, cwd=src_dir)
            
            self.status_var.set("Live reconstruction launched. See new window.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch live reconstruction: {e}")
            self.status_var.set("Error launching live reconstruction")
    
    def launch_photo_reconstruction(self):
        """Open file dialog and launch photo reconstruction in a thread."""
        photo_paths = filedialog.askopenfilenames(
            title="Select Photos for 360 Panorama",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png"),
                ("All files", "*.*")
            ]
        )
        
        if not photo_paths:
            self.status_var.set("Photo reconstruction cancelled.")
            return

        self.set_buttons_state(tk.DISABLED)
        self.status_var.set("Starting photo reconstruction...")
        
        # Run reconstruction in a background thread
        thread = threading.Thread(
            target=self._run_photo_reconstruction_thread,
            args=(photo_paths,),
            daemon=True
        )
        thread.start()

    def _run_photo_reconstruction_thread(self, photo_paths):
        """The actual reconstruction logic that runs in a thread."""
        try:
            processor = PhotoUploadProcessor()

            # The reconstruct_from_photos method will call self.update_status
            success = processor.reconstruct_from_photos(
                photo_paths, 
                progress_callback=self.update_status
            )

            if success and processor.panorama_image is not None and processor.panorama_image.size > 0:
                self.update_status(100, "Saving panorama...")
                saved_files = processor.save_reconstruction()
                if saved_files and saved_files.get('panorama'):
                    saved_path = saved_files['panorama']
                    self.root.after(0, messagebox.showinfo, "Success", f"Panorama created!\nSaved to:\n{saved_path}")
                    self.update_status(100, "Panorama complete!")
                else:
                    self.root.after(0, messagebox.showerror, "Error", "Panorama built but failed to save.")
                    self.update_status(100, "Failed to save panorama.")
            else:
                self.root.after(0, messagebox.showerror, "Error", "Panorama failed. Try different photos (rotate camera in place for best results).")
                self.update_status(100, "Panorama failed.")

        except Exception as e:
            self.root.after(0, messagebox.showerror, "Critical Error", f"An unexpected error occurred during reconstruction: {e}")
            self.update_status(100, "A critical error occurred.")
        finally:
            self.root.after(0, self.set_buttons_state, tk.NORMAL)

    def update_status(self, progress, message):
        """Thread-safe method to update the GUI's status and progress bar."""
        def do_update():
            self.status_var.set(message)
            self.progress_bar['value'] = progress
        
        self.root.after(0, do_update)

    def view_panorama(self):
        """Open output folder and let user select a panorama image to view."""
        self.status_var.set("Opening panorama...")
        try:
            output_dir = Path(__file__).parent.parent / "output"
            if not output_dir.exists():
                messagebox.showwarning("No Output Directory",
                                     "No output directory found. Run Photo to 360 Panorama first.")
                self.status_var.set("No output directory found")
                return
            panorama_files = list(output_dir.glob("*panorama*.png")) + list(output_dir.glob("*.png"))
            panorama_files = sorted(set(panorama_files), key=lambda p: p.stat().st_mtime, reverse=True)
            if not panorama_files:
                messagebox.showwarning("No Panoramas",
                                     "No panorama images found in the output directory.")
                self.status_var.set("No panoramas found")
                return
            file_path = filedialog.askopenfilename(
                title="Select Panorama to View",
                initialdir=str(output_dir),
                filetypes=[("PNG images", "*.png"), ("All files", "*.*")]
            )
            if not file_path:
                self.status_var.set("No file selected")
                return
            self.launch_panorama_viewer(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open panorama viewer: {e}")
            self.status_var.set("Error opening panorama")

    def launch_panorama_viewer(self, file_path: str):
        """Open the panorama image with the default system viewer."""
        self.status_var.set(f"Opening {Path(file_path).name}...")
        try:
            path = Path(file_path).resolve()
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
            self.status_var.set("Panorama opened in default viewer.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open panorama: {e}")
            self.status_var.set("Error opening panorama")
    
    def show_help(self):
        """Show help information."""
        help_text = """
3D Reconstruction Suite - Help

📹 Live Camera Reconstruction:
- Uses your computer's camera to capture images in real-time
- Launches in a separate window; press 'S' to save.

📸 Photo to 360 Panorama:
- Select multiple photos taken by rotating the camera in place
- Builds a 360-degree equirectangular panorama image
- Result is saved as a PNG in the output/ directory (viewable in any image or 360 viewer)

👁️ View Panorama:
- Open a saved panorama image with your default image viewer
- Panoramas are equirectangular and can be used in 360 viewers

Requirements:
- Python 3.7 or higher
- Webcam (for live reconstruction)

For more detailed information, check the README files in the project directory.
        """
        messagebox.showinfo("Help", help_text)
    
    def run(self):
        """Run the GUI application."""
        self.root.mainloop()

def main():
    """Main function to launch the GUI."""
    app = BasicLauncherGUI()
    app.run()

if __name__ == "__main__":
    main() 