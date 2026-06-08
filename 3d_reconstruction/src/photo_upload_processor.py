import cv2
import numpy as np
import os
import tempfile
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from concurrent.futures import ThreadPoolExecutor
import shutil

from reconstruction_engine import ReconstructionEngine
from panorama_engine import build_equirectangular_panorama

class PhotoUploadProcessor:
    """Processor for handling multiple photo uploads in panorama or 3D mode."""
    
    SUPPORTED_MODES = ("panorama", "reconstruction")

    def __init__(self, output_dir: str = "output"):
        """Initialize the photo upload processor.
        
        Args:
            output_dir: Directory to save panorama results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.uploaded_photos = []
        self.reconstruction_engine = ReconstructionEngine(
            nfeatures=4000,
            match_ratio=0.75,
        )
        self.panorama_image = None  # BGR numpy array after build
        self.mode = "panorama"
        self.processing_thread = None
        self.is_processing = False

    def set_mode(self, mode: str) -> None:
        if mode not in self.SUPPORTED_MODES:
            raise ValueError(f"Unsupported mode '{mode}'. Expected one of {self.SUPPORTED_MODES}")
        self.mode = mode
        
    def select_photos(self) -> List[str]:
        """Open file dialog to select multiple photos.
        
        Returns:
            List of selected photo file paths
        """
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        file_paths = filedialog.askopenfilenames(
            title="Select Photos for 360 Panorama",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("PNG files", "*.png"),
                ("All files", "*.*")
            ]
        )
        
        root.destroy()
        return list(file_paths)
    
    def validate_photos(self, photo_paths: List[str]) -> Tuple[List[str], List[str]]:
        """Validate uploaded photos for reconstruction.
        
        Args:
            photo_paths: List of photo file paths
            
        Returns:
            Tuple of (valid_photos, invalid_photos)
        """
        valid_photos = []
        invalid_photos = []
        
        for photo_path in photo_paths:
            try:
                # Check if file exists
                if not os.path.exists(photo_path):
                    invalid_photos.append(f"{photo_path} - File not found")
                    continue
                
                # Try to read the image
                img = cv2.imread(photo_path)
                if img is None:
                    invalid_photos.append(f"{photo_path} - Cannot read image")
                    continue
                
                # Check image dimensions
                height, width = img.shape[:2]
                if width < 100 or height < 100:
                    invalid_photos.append(f"{photo_path} - Image too small ({width}x{height})")
                    continue
                
                valid_photos.append(photo_path)
                
            except Exception as e:
                invalid_photos.append(f"{photo_path} - Error: {str(e)}")
        
        return valid_photos, invalid_photos
    
    def preprocess_photos(self, photo_paths: List[str], target_size: Tuple[int, int] = (640, 480)) -> List[np.ndarray]:
        """Preprocess photos for reconstruction.
        
        Args:
            photo_paths: List of photo file paths
            target_size: Target size for resizing (width, height)
            
        Returns:
            List of preprocessed images
        """
        processed_images = []
        
        for photo_path in photo_paths:
            try:
                # Read image
                img = cv2.imread(photo_path)
                if img is None:
                    continue
                
                # Resize to target size
                img_resized = cv2.resize(img, target_size)
                
                # Apply basic preprocessing
                # Convert to RGB for better feature detection
                img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
                
                # Apply slight Gaussian blur to reduce noise
                img_blurred = cv2.GaussianBlur(img_rgb, (3, 3), 0)
                
                # Convert back to BGR for OpenCV compatibility
                img_processed = cv2.cvtColor(img_blurred, cv2.COLOR_RGB2BGR)
                
                processed_images.append(img_processed)
                
            except Exception as e:
                print(f"Error preprocessing {photo_path}: {e}")
                continue
        
        return processed_images
    
    def create_photo_sequence(self, images: List[np.ndarray]) -> List[np.ndarray]:
        """Create an optimal sequence of photos for reconstruction.
        
        Args:
            images: List of preprocessed images
            
        Returns:
            Optimized sequence of images
        """
        if len(images) <= 2:
            return images
        
        # Simple approach: use every nth image to ensure good coverage
        # In a more sophisticated implementation, you could analyze image similarity
        # and select the most diverse set of images
        
        step = max(1, len(images) // 20)  # Use at most 20 images
        sequence = images[::step]
        
        # Always include the first and last images
        # images[0] is always included in images[::step] (starts at index 0)
        # Check if last image is included by checking if its index is divisible by step
        # Use index-based check instead of array comparison to avoid NumPy ambiguity
        last_index = len(images) - 1
        last_included = (last_index % step == 0) if step > 0 else True
        if not last_included:
            sequence.append(images[-1])
        
        return sequence
    
    def reconstruct_from_photos(self, photo_paths: List[str],
                               progress_callback: Optional[callable] = None) -> bool:
        """Run the selected photo pipeline (panorama or 3D reconstruction).
        
        Args:
            photo_paths: List of photo file paths
            progress_callback: Optional callback function for progress updates
            
        Returns:
            True if panorama was built successfully, False otherwise
        """
        try:
            self.is_processing = True
            self.panorama_image = None
            
            if progress_callback:
                progress_callback(0, "Validating photos...")
            
            valid_photos, invalid_photos = self.validate_photos(photo_paths)
            
            if len(invalid_photos) > 0:
                print("Invalid photos found:")
                for invalid in invalid_photos:
                    print(f"  - {invalid}")
            
            if len(valid_photos) < 2:
                print("Need at least 2 valid photos for panorama")
                return False
            
            if progress_callback:
                progress_callback(20, f"Processing {len(valid_photos)} photos...")
            
            processed_images = self.preprocess_photos(valid_photos)
            
            if len(processed_images) < 2:
                print("Not enough valid processed images")
                return False
            
            if progress_callback:
                progress_callback(40, "Creating optimal photo sequence...")
            
            sequence = self.create_photo_sequence(processed_images)
            
            if progress_callback:
                progress_callback(60, "Adding keyframes...")
            
            for i, img in enumerate(sequence):
                self.reconstruction_engine.process_frame(img, add_to_keyframes=True)
                if progress_callback:
                    progress = 60 + (i / len(sequence)) * 15
                    progress_callback(progress, f"Photo {i+1}/{len(sequence)}...")
            
            keyframes = self.reconstruction_engine.keyframes
            if len(keyframes) < 1:
                print("No keyframes available for processing")
                return False

            if self.mode == "panorama":
                if progress_callback:
                    progress_callback(78, "Building 360 panorama...")
                self.panorama_image = build_equirectangular_panorama(
                    keyframes,
                    self.reconstruction_engine,
                )
            else:
                if progress_callback:
                    progress_callback(78, "Running 3D reconstruction backend...")
                self.reconstruction_engine.process_keyframes()
            
            if progress_callback:
                progress_callback(100, "Panorama completed!")
            
            if self.mode == "panorama":
                return self.panorama_image is not None and self.panorama_image.size > 0
            return len(self.reconstruction_engine.point_cloud.points) > 0
            
        except Exception as e:
            print(f"Error during panorama build: {e}")
            return False
        finally:
            self.is_processing = False
    
    def save_reconstruction(self, filename_prefix: str = "photo_result") -> Dict[str, str]:
        """Save current panorama or 3D outputs based on mode.
        
        Args:
            filename_prefix: Prefix for saved files
            
        Returns:
            Dictionary of saved file paths (e.g. 'panorama', 'info')
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        saved_files = {}
        
        try:
            if self.mode == "panorama" and self.panorama_image is not None and self.panorama_image.size > 0:
                panorama_path = self.output_dir / f"{filename_prefix}_{timestamp}.png"
                cv2.imwrite(str(panorama_path), self.panorama_image)
                saved_files['panorama'] = str(panorama_path)
            if self.mode == "reconstruction":
                if len(self.reconstruction_engine.point_cloud.points) > 0:
                    pcd_path = self.output_dir / f"{filename_prefix}_pointcloud_{timestamp}.ply"
                    import open3d as o3d
                    o3d.io.write_point_cloud(str(pcd_path), self.reconstruction_engine.point_cloud)
                    saved_files["pointcloud"] = str(pcd_path)
                if self.reconstruction_engine.mesh is not None:
                    mesh_path = self.output_dir / f"{filename_prefix}_mesh_{timestamp}.ply"
                    import open3d as o3d
                    o3d.io.write_triangle_mesh(str(mesh_path), self.reconstruction_engine.mesh)
                    saved_files["mesh"] = str(mesh_path)
            
            info_path = self.output_dir / f"{filename_prefix}_info_{timestamp}.txt"
            with open(info_path, 'w') as f:
                f.write(f"Photo Processing Results\n")
                f.write(f"Generated: {timestamp}\n")
                f.write(f"Mode: {self.mode}\n")
                f.write(f"Number of photos processed: {len(self.uploaded_photos)}\n")
                f.write(f"Panorama saved: {saved_files.get('panorama', 'No')}\n")
                f.write(f"Point cloud saved: {saved_files.get('pointcloud', 'No')}\n")
                f.write(f"Mesh saved: {saved_files.get('mesh', 'No')}\n")
                f.write(f"Metrics: {self.reconstruction_engine.get_metrics_summary()}\n")
            
            saved_files['info'] = str(info_path)
            
        except Exception as e:
            print(f"Error saving panorama: {e}")
        
        return saved_files
    
    def close(self):
        """Close the processor and release resources."""
        if self.reconstruction_engine:
            self.reconstruction_engine.close()


class PhotoUploadGUI:
    """GUI for photo upload and reconstruction."""
    
    def __init__(self):
        """Initialize the GUI."""
        self.root = tk.Tk()
        self.root.title("360 Panorama from Photos")
        self.root.geometry("600x500")
        
        self.processor = PhotoUploadProcessor()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="3D Reconstruction from Photos", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Upload button
        self.upload_btn = ttk.Button(main_frame, text="Select Photos",
                                    command=self.upload_photos)
        self.upload_btn.grid(row=1, column=0, columnspan=2, pady=(0, 10))

        ttk.Label(main_frame, text="Output mode:").grid(row=2, column=0, sticky=tk.W)
        self.mode_var = tk.StringVar(value="panorama")
        self.mode_selector = ttk.Combobox(
            main_frame,
            textvariable=self.mode_var,
            values=list(PhotoUploadProcessor.SUPPORTED_MODES),
            state="readonly",
        )
        self.mode_selector.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 8))
        
        # Photo list
        list_frame = ttk.LabelFrame(main_frame, text="Selected Photos", padding="5")
        list_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.photo_listbox = tk.Listbox(list_frame, height=8)
        self.photo_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.photo_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.photo_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, 
                                           maximum=100)
        self.progress_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Status label
        self.status_var = tk.StringVar(value="Ready to upload photos")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_label.grid(row=5, column=0, columnspan=2, pady=(0, 10))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=(0, 10))
        
        self.reconstruct_btn = ttk.Button(button_frame, text="Start Reconstruction", 
                                         command=self.start_reconstruction, state=tk.DISABLED)
        self.reconstruct_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.save_btn = ttk.Button(button_frame, text="Save Results", 
                                  command=self.save_results, state=tk.DISABLED)
        self.save_btn.grid(row=0, column=1, padx=(5, 0))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
    def upload_photos(self):
        """Handle photo upload."""
        photo_paths = self.processor.select_photos()
        
        if photo_paths:
            self.processor.uploaded_photos = photo_paths
            
            # Update listbox
            self.photo_listbox.delete(0, tk.END)
            for path in photo_paths:
                filename = os.path.basename(path)
                self.photo_listbox.insert(tk.END, filename)
            
            # Enable reconstruction button
            self.reconstruct_btn.config(state=tk.NORMAL)
            self.status_var.set(f"Selected {len(photo_paths)} photos")
    
    def start_reconstruction(self):
        """Start the reconstruction process."""
        if not self.processor.uploaded_photos:
            messagebox.showwarning("No Photos", "Please select photos first.")
            return
        self.processor.set_mode(self.mode_var.get())
        
        # Disable buttons during processing
        self.upload_btn.config(state=tk.DISABLED)
        self.reconstruct_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        
        # Start reconstruction in separate thread
        def reconstruction_thread():
            success = self.processor.reconstruct_from_photos(
                self.processor.uploaded_photos,
                self.update_progress
            )
            
            # Re-enable buttons on main thread
            self.root.after(0, self.reconstruction_finished, success)
        
        threading.Thread(target=reconstruction_thread, daemon=True).start()
    
    def update_progress(self, progress: int, message: str):
        """Update progress bar and status."""
        self.root.after(0, lambda: self.progress_var.set(progress))
        self.root.after(0, lambda: self.status_var.set(message))
    
    def reconstruction_finished(self, success: bool):
        """Handle reconstruction completion."""
        # Re-enable buttons
        self.upload_btn.config(state=tk.NORMAL)
        self.reconstruct_btn.config(state=tk.NORMAL)
        
        if success:
            self.save_btn.config(state=tk.NORMAL)
            if self.processor.mode == "panorama":
                messagebox.showinfo("Success", "Panorama created successfully!")
            else:
                messagebox.showinfo("Success", "3D reconstruction completed successfully!")
        else:
            messagebox.showerror("Error", "Processing failed. Try different photos with higher overlap.")
    
    def save_results(self):
        """Save panorama results."""
        saved_files = self.processor.save_reconstruction()
        
        if saved_files and saved_files.get('panorama'):
            message = "Panorama saved:\n" + saved_files['panorama']
            messagebox.showinfo("Saved", message)
        elif saved_files and saved_files.get("pointcloud"):
            message = "3D outputs saved:\n" + "\n".join(f"{k}: {v}" for k, v in saved_files.items())
            messagebox.showinfo("Saved", message)
        elif saved_files:
            message = "Info saved:\n" + "\n".join(f"{k}: {v}" for k, v in saved_files.items())
            messagebox.showinfo("Saved", message)
        else:
            messagebox.showerror("Error", "Failed to save panorama.")
    
    def run(self):
        """Run the GUI application."""
        self.root.mainloop()
    
    def close(self):
        """Close the GUI and cleanup."""
        self.processor.close()
        self.root.destroy()


def main():
    """Main entry point for photo upload application."""
    gui = PhotoUploadGUI()
    try:
        gui.run()
    finally:
        gui.close()


if __name__ == "__main__":
    main() 