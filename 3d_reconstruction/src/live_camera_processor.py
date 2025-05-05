import cv2
import numpy as np
import open3d as o3d
import threading
import time
from pathlib import Path
from typing import List, Tuple, Optional, Callable

class LiveCameraProcessor:
    """Class for processing live camera input for real-time 3D reconstruction."""
    
    def __init__(self, camera_id: int = 0, width: int = 640, height: int = 480):
        """Initialize the live camera processor.
        
        Args:
            camera_id (int): Camera device ID (usually 0 for built-in webcam)
            width (int): Desired camera frame width
            height (int): Desired camera frame height
        """
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.cap = None
        self.is_running = False
        self.capture_thread = None
        self.processing_thread = None
        self.frame_buffer = []
        self.max_buffer_size = 10
        self.lock = threading.Lock()
        
    def start_capture(self):
        """Start capturing from the camera in a separate thread."""
        if self.is_running:
            print("Camera capture already running")
            return
            
        self.cap = cv2.VideoCapture(self.camera_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        if not self.cap.isOpened():
            raise ValueError(f"Failed to open camera with ID {self.camera_id}")
            
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        print(f"Started camera capture on device {self.camera_id}")
        
    def _capture_loop(self):
        """Internal method for continuous frame capture."""
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to capture frame")
                time.sleep(0.1)
                continue
                
            with self.lock:
                self.frame_buffer.append(frame)
                # Keep buffer size limited
                if len(self.frame_buffer) > self.max_buffer_size:
                    self.frame_buffer.pop(0)
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the most recent frame from the buffer.
        
        Returns:
            numpy.ndarray: The latest camera frame or None if buffer is empty
        """
        with self.lock:
            if self.frame_buffer:
                return self.frame_buffer[-1].copy()
            return None
    
    def start_3d_reconstruction(self, callback: Optional[Callable] = None):
        """Start the 3D reconstruction process in a separate thread.
        
        Args:
            callback: Optional callback function to receive reconstruction results
        """
        if self.processing_thread and self.processing_thread.is_alive():
            print("3D reconstruction already running")
            return
            
        self.processing_thread = threading.Thread(
            target=self._reconstruction_loop,
            args=(callback,)
        )
        self.processing_thread.daemon = True
        self.processing_thread.start()
        print("Started 3D reconstruction")
    
    def _reconstruction_loop(self, callback: Optional[Callable] = None):
        """Internal method for continuous 3D reconstruction."""
        # Initialize Open3D visualizer
        vis = o3d.visualization.Visualizer()
        vis.create_window("Live 3D Reconstruction", width=1024, height=768)
        
        # Initialize point cloud
        pcd = o3d.geometry.PointCloud()
        vis.add_geometry(pcd)
        
        # Initialize feature detector
        orb = cv2.ORB_create()
        
        # Keep track of previous frame and features
        prev_frame = None
        prev_keypoints = None
        prev_descriptors = None
        
        while self.is_running:
            frame = self.get_latest_frame()
            if frame is None:
                time.sleep(0.1)
                continue
                
            # Convert to grayscale for feature detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect features
            keypoints, descriptors = orb.detectAndCompute(gray, None)
            
            if prev_frame is not None and prev_descriptors is not None:
                # Match features with previous frame
                matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                matches = matcher.match(prev_descriptors, descriptors)
                
                # Sort matches by distance
                matches = sorted(matches, key=lambda x: x.distance)
                
                # Take best matches
                good_matches = matches[:50] if len(matches) > 50 else matches
                
                if len(good_matches) >= 8:  # Minimum needed for 8-point algorithm
                    # Get matched keypoints
                    prev_pts = np.float32([prev_keypoints[m.queryIdx].pt for m in good_matches])
                    curr_pts = np.float32([keypoints[m.trainIdx].pt for m in good_matches])
                    
                    # Compute essential matrix
                    E, mask = cv2.findEssentialMat(curr_pts, prev_pts, 
                                                focal=1.0, pp=(self.width/2, self.height/2), 
                                                method=cv2.RANSAC, prob=0.999, threshold=1.0)
                    
                    if E is not None:
                        # Recover pose (rotation and translation)
                        _, R, t, mask = cv2.recoverPose(E, curr_pts, prev_pts)
                        
                        # Generate some 3D points from triangulation
                        # This is a simplified version - in real applications, you would:
                        # 1. Triangulate points
                        # 2. Create a dense point cloud
                        # 3. Apply filtering and meshing
                        points = np.random.rand(100, 3) * 2 - 1  # Dummy points for visualization
                        
                        # Update point cloud
                        pcd.points = o3d.utility.Vector3dVector(points)
                        pcd.paint_uniform_color([0.5, 0.5, 1.0])
                        
                        # Update visualizer
                        vis.update_geometry(pcd)
                        vis.poll_events()
                        vis.update_renderer()
                        
                        # Call callback if provided
                        if callback:
                            callback(pcd)
            
            # Save current frame and features for next iteration
            prev_frame = gray
            prev_keypoints = keypoints
            prev_descriptors = descriptors
            
            time.sleep(0.05)  # Small delay to prevent excessive CPU usage
            
        # Clean up
        vis.destroy_window()
    
    def stop(self):
        """Stop all processing and release resources."""
        self.is_running = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)
            
        if self.processing_thread:
            self.processing_thread.join(timeout=1.0)
            
        if self.cap and self.cap.isOpened():
            self.cap.release()
            
        print("Stopped camera capture and 3D reconstruction") 