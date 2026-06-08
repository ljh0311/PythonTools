import cv2
import numpy as np
import open3d as o3d
import threading
import time
from pathlib import Path
from typing import List, Tuple, Optional, Callable

class LiveCameraProcessor:
    """Class for processing live camera input for real-time 3D reconstruction."""
    
    def __init__(
        self,
        camera_id: int = 0,
        width: int = 640,
        height: int = 480,
        nfeatures: int = 2000,
        match_ratio: float = 0.7,
        ransac_threshold: float = 1.0,
        min_matches: int = 8,
        use_preprocessing: bool = True,
    ):
        """Initialize the live camera processor.
        
        Args:
            camera_id: Camera device ID (usually 0 for built-in webcam)
            width: Desired camera frame width
            height: Desired camera frame height
            nfeatures: Max number of features to detect (ORB).
            match_ratio: Lowe's ratio test threshold for KNN matching.
            ransac_threshold: RANSAC threshold for findEssentialMat (pixels).
            min_matches: Minimum good matches required for pose estimation.
            use_preprocessing: If True, apply CLAHE and optional denoising before feature detection.
        """
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.nfeatures = nfeatures
        self.match_ratio = match_ratio
        self.ransac_threshold = ransac_threshold
        self.min_matches = min_matches
        self.use_preprocessing = use_preprocessing
        self._night_threshold = 100
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
        orb = cv2.ORB_create(nfeatures=self.nfeatures)
        
        # Keep track of previous frame and features
        prev_frame = None
        prev_keypoints = None
        prev_descriptors = None
        global_R = np.eye(3)
        global_t = np.zeros((3, 1))
        focal = float(self.width)
        camera_matrix = np.array(
            [[focal, 0, self.width / 2.0],
             [0, focal, self.height / 2.0],
             [0, 0, 1.0]], dtype=np.float32
        )
        
        while self.is_running:
            frame = self.get_latest_frame()
            if frame is None:
                time.sleep(0.1)
                continue
                
            # Convert to grayscale and optionally preprocess
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if self.use_preprocessing:
                gray = self._preprocess_for_feature_detection(gray)
            
            # Detect features
            keypoints, descriptors = orb.detectAndCompute(gray, None)
            
            if prev_frame is not None and prev_descriptors is not None:
                # Match features with previous frame using KNN + Lowe's ratio test
                matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
                knn_matches = matcher.knnMatch(prev_descriptors, descriptors, k=2)
                good_matches = []
                for m, n in knn_matches:
                    if m.distance < self.match_ratio * n.distance:
                        good_matches.append(m)
                
                if len(good_matches) >= self.min_matches:
                    # Get matched keypoints
                    prev_pts = np.float32([prev_keypoints[m.queryIdx].pt for m in good_matches])
                    curr_pts = np.float32([keypoints[m.trainIdx].pt for m in good_matches])
                    
                    # Compute essential matrix
                    E, mask = cv2.findEssentialMat(
                        prev_pts,
                        curr_pts,
                        camera_matrix,
                        method=cv2.RANSAC, prob=0.999, threshold=self.ransac_threshold
                    )
                    
                    if E is not None:
                        # Recover pose (rotation and translation)
                        _, R, t, pose_mask = cv2.recoverPose(E, prev_pts, curr_pts, camera_matrix, mask=mask)
                        inlier = pose_mask.ravel() == 1
                        prev_inliers = prev_pts[inlier]
                        curr_inliers = curr_pts[inlier]
                        if len(prev_inliers) < self.min_matches:
                            prev_frame = gray
                            prev_keypoints = keypoints
                            prev_descriptors = descriptors
                            continue

                        p1 = camera_matrix @ np.hstack((np.eye(3), np.zeros((3, 1))))
                        p2 = camera_matrix @ np.hstack((R, t))
                        points_4d = cv2.triangulatePoints(p1, p2, prev_inliers.T, curr_inliers.T)
                        local_points = (points_4d[:3] / points_4d[3]).T
                        valid = np.isfinite(local_points).all(axis=1)
                        local_points = local_points[valid]
                        if len(local_points) == 0:
                            prev_frame = gray
                            prev_keypoints = keypoints
                            prev_descriptors = descriptors
                            continue

                        # Chain relative pose into global coordinates.
                        global_points = (global_R @ local_points.T + global_t).T
                        global_R = R @ global_R
                        global_t = global_t + (global_R @ t)

                        existing = np.asarray(pcd.points) if len(pcd.points) > 0 else np.empty((0, 3))
                        merged = np.vstack([existing, global_points])
                        pcd.points = o3d.utility.Vector3dVector(merged)
                        pcd.paint_uniform_color([0.5, 0.5, 1.0])
                        if len(pcd.points) > 5000:
                            down = pcd.voxel_down_sample(voxel_size=0.02)
                            pcd.points = down.points
                            if len(down.colors) > 0:
                                pcd.colors = down.colors
                        
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
    
    def _preprocess_for_feature_detection(self, gray: np.ndarray) -> np.ndarray:
        """Preprocess grayscale for better feature detection (aligned with ReconstructionEngine)."""
        avg_brightness = float(np.mean(gray))
        if avg_brightness < self._night_threshold:
            return self._enhance_low_light(gray)
        return self._enhance_normal(gray)
    
    def _enhance_normal(self, gray: np.ndarray) -> np.ndarray:
        """CLAHE + light Gaussian blur for normal lighting."""
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        ksize = self._adaptive_blur_size(gray.shape)
        return cv2.GaussianBlur(enhanced, ksize, 0)
    
    def _enhance_low_light(self, gray: np.ndarray) -> np.ndarray:
        """CLAHE + percentile stretch + denoising for low-light."""
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        p5, p95 = np.percentile(enhanced, (5, 95))
        if p95 > p5:
            enhanced = np.clip((enhanced.astype(np.float32) - p5) * 255.0 / (p95 - p5), 0, 255).astype(np.uint8)
        return cv2.fastNlMeansDenoising(enhanced, None, h=10, templateWindowSize=7, searchWindowSize=21)
    
    @staticmethod
    def _adaptive_blur_size(shape: tuple) -> tuple:
        """Kernel size for Gaussian blur from image size (odd)."""
        min_dim = min(shape[:2])
        if min_dim < 500:
            k = 3
        elif min_dim < 1000:
            k = 5
        else:
            k = 7
        return (k, k)
    
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