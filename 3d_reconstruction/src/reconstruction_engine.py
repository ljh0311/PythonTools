import cv2
import numpy as np
import open3d as o3d
import os
import tempfile
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor

class ReconstructionEngine:
    """Engine for 3D reconstruction from camera images."""
    
    def __init__(self, camera_params: Optional[Dict[str, Any]] = None):
        """Initialize the reconstruction engine.
        
        Args:
            camera_params: Optional camera parameters (intrinsics)
                If None, will attempt to estimate from images
        """
        self.camera_params = camera_params
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.point_cloud = o3d.geometry.PointCloud()
        self.mesh = None
        self.frames = []
        self.keyframes = []
        self.poses = []
        self.visualizer = None
    
    def process_frame(self, frame: np.ndarray, add_to_keyframes: bool = False) -> None:
        """Process a new frame for reconstruction.
        
        Args:
            frame: Camera frame (BGR format)
            add_to_keyframes: Whether to add this frame to keyframes for reconstruction
        """
        # Store this frame for tracking
        self.frames.append(frame.copy())
        
        # Limit number of frames in memory
        if len(self.frames) > 30:
            self.frames.pop(0)
            
        # If requested, save this as a keyframe for later reconstruction
        if add_to_keyframes:
            self.keyframes.append(frame.copy())
            print(f"Added keyframe #{len(self.keyframes)}")
    
    def estimate_camera_pose(self, frame1: np.ndarray, frame2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Estimate relative camera pose between two frames.
        
        Args:
            frame1: First frame
            frame2: Second frame
            
        Returns:
            Tuple of (rotation matrix, translation vector)
        """
        # Convert to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # Detect ORB features
        orb = cv2.ORB_create(nfeatures=1000)
        kp1, des1 = orb.detectAndCompute(gray1, None)
        kp2, des2 = orb.detectAndCompute(gray2, None)
        
        # Match features
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = matcher.match(des1, des2)
        
        # Sort matches by distance
        matches = sorted(matches, key=lambda x: x.distance)
        
        # Take best matches 
        good_matches = matches[:int(len(matches) * 0.75)]
        
        if len(good_matches) < 8:
            return np.eye(3), np.zeros((3, 1))
        
        # Get matched keypoints
        pts1 = np.float32([kp1[m.queryIdx].pt for m in good_matches])
        pts2 = np.float32([kp2[m.trainIdx].pt for m in good_matches])
        
        # Get frame dimensions (for camera intrinsics estimation)
        h, w = gray1.shape
        
        # Estimate camera matrix if not provided
        # This is a simplification - in practice, you'd calibrate your camera
        focal_length = w
        camera_matrix = np.array(
            [[focal_length, 0, w/2],
             [0, focal_length, h/2],
             [0, 0, 1]], dtype=np.float32
        )
        
        # Find essential matrix
        E, mask = cv2.findEssentialMat(pts1, pts2, camera_matrix, method=cv2.RANSAC, prob=0.999, threshold=1.0)
        
        if E is None:
            return np.eye(3), np.zeros((3, 1))
        
        # Recover pose
        _, R, t, mask = cv2.recoverPose(E, pts1, pts2, camera_matrix)
        
        return R, t
    
    def triangulate_points(self, frame1: np.ndarray, frame2: np.ndarray, R: np.ndarray, t: np.ndarray) -> np.ndarray:
        """Triangulate 3D points from two frames and relative pose.
        
        Args:
            frame1: First frame
            frame2: Second frame
            R: Rotation matrix
            t: Translation vector
            
        Returns:
            Array of 3D points
        """
        # Convert to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # Detect features
        orb = cv2.ORB_create(nfeatures=1000)
        kp1, des1 = orb.detectAndCompute(gray1, None)
        kp2, des2 = orb.detectAndCompute(gray2, None)
        
        # Match features
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = matcher.match(des1, des2)
        
        # Sort matches by distance
        matches = sorted(matches, key=lambda x: x.distance)
        
        # Take best matches
        good_matches = matches[:int(len(matches) * 0.75)]
        
        if len(good_matches) < 8:
            return np.zeros((0, 3))
        
        # Get matched keypoints
        pts1 = np.float32([kp1[m.queryIdx].pt for m in good_matches])
        pts2 = np.float32([kp2[m.trainIdx].pt for m in good_matches])
        
        # Get frame dimensions
        h, w = gray1.shape
        
        # Estimate camera matrix if not provided
        focal_length = w
        camera_matrix = np.array(
            [[focal_length, 0, w/2],
             [0, focal_length, h/2],
             [0, 0, 1]], dtype=np.float32
        )
        
        # Camera projection matrices
        P1 = camera_matrix @ np.hstack((np.eye(3), np.zeros((3, 1))))
        P2 = camera_matrix @ np.hstack((R, t))
        
        # Triangulate points
        points_4d = cv2.triangulatePoints(P1, P2, pts1.T, pts2.T)
        
        # Convert to 3D points
        points_3d = points_4d[:3, :] / points_4d[3, :]
        
        return points_3d.T
    
    def update_point_cloud(self, points_3d: np.ndarray, colors: Optional[np.ndarray] = None) -> None:
        """Update the point cloud with new points.
        
        Args:
            points_3d: 3D points to add
            colors: Optional colors for points (RGB format)
        """
        if points_3d.shape[0] == 0:
            return
            
        if colors is None:
            colors = np.ones_like(points_3d) * 0.5  # Default gray color
            
        # Create point cloud from points
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points_3d)
        pcd.colors = o3d.utility.Vector3dVector(colors)
        
        # Merge with existing point cloud
        self.point_cloud += pcd
        
        # Downsample to manage size - using a larger voxel size to avoid errors
        if len(self.point_cloud.points) > 100:  # Only downsample if we have enough points
            try:
                self.point_cloud = self.point_cloud.voxel_down_sample(voxel_size=0.05)
            except Exception as e:
                print(f"Warning: Downsampling failed: {e}")
    
    def start_visualization(self) -> None:
        """Start the visualization window for the 3D reconstruction."""
        self.visualizer = o3d.visualization.Visualizer()
        self.visualizer.create_window("3D Reconstruction", width=1024, height=768)
        self.visualizer.add_geometry(self.point_cloud)
        
        # Set rendering options
        opt = self.visualizer.get_render_option()
        opt.point_size = 2.0
        opt.background_color = np.array([0.1, 0.1, 0.1])
        
        # Set camera position
        view_control = self.visualizer.get_view_control()
        view_control.set_zoom(0.5)
    
    def update_visualization(self) -> None:
        """Update the visualization with the current point cloud."""
        if self.visualizer is None:
            self.start_visualization()
            
        self.visualizer.update_geometry(self.point_cloud)
        self.visualizer.poll_events()
        self.visualizer.update_renderer()
    
    def process_keyframes(self) -> None:
        """Process all collected keyframes to create a dense reconstruction."""
        if len(self.keyframes) < 2:
            print("Need at least 2 keyframes for reconstruction")
            return
            
        print(f"Starting dense reconstruction with {len(self.keyframes)} keyframes")
        
        # Create temporary directory for keyframes
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Save keyframes as images
            for i, frame in enumerate(self.keyframes):
                cv2.imwrite(str(temp_dir_path / f"frame_{i:06d}.jpg"), frame)
                
            # Run COLMAP SfM if available (simplified command, adjust as needed)
            try:
                # Check if COLMAP is installed
                try:
                    # Use 'where' on Windows to check if COLMAP is in PATH
                    subprocess.run(["where", "colmap"], 
                                  check=True, 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  text=True)
                except subprocess.CalledProcessError:
                    print("COLMAP not found in PATH. Using built-in reconstruction methods instead.")
                    raise FileNotFoundError("COLMAP executable not found")
                
                colmap_cmd = [
                    "colmap", "automatic_reconstructor",
                    "--workspace_path", str(temp_dir_path),
                    "--image_path", str(temp_dir_path)
                ]
                
                print("Running COLMAP reconstruction...")
                subprocess.run(colmap_cmd, check=True)
                
                # Load sparse reconstruction
                sparse_model_path = temp_dir_path / "sparse" / "0"
                if sparse_model_path.exists():
                    print("Loading COLMAP sparse reconstruction")
                    pcd = o3d.io.read_point_cloud(str(sparse_model_path / "points3D.ply"))
                    self.point_cloud += pcd
                    self.update_visualization()
                    
                # Load dense reconstruction
                dense_model_path = temp_dir_path / "dense" / "0"
                if dense_model_path.exists():
                    print("Loading COLMAP dense reconstruction")
                    
                    # Load dense point cloud
                    dense_pcd = o3d.io.read_point_cloud(str(dense_model_path / "fused.ply"))
                    self.point_cloud += dense_pcd
                    
                    # Create mesh
                    self.mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(
                        self.point_cloud, alpha=0.05)
                    
                    self.update_visualization()
            except Exception as e:
                if isinstance(e, FileNotFoundError):
                    print("COLMAP not installed. Using built-in reconstruction methods.")
                else:
                    print(f"COLMAP processing failed: {e}")
                print("Falling back to simple triangulation...")
                
                # Fall back to simple triangulation
                for i in range(len(self.keyframes) - 1):
                    frame1 = self.keyframes[i]
                    frame2 = self.keyframes[i + 1]
                    
                    R, t = self.estimate_camera_pose(frame1, frame2)
                    points_3d = self.triangulate_points(frame1, frame2, R, t)
                    
                    # Extract colors from the first frame for the points
                    if points_3d.shape[0] > 0:
                        colors = np.zeros_like(points_3d)
                        for j, point in enumerate(points_3d):
                            # This is a simplification - in practice, you'd project points and get accurate colors
                            # Avoid out-of-bounds errors
                            y = min(int(j % frame1.shape[0]), frame1.shape[0] - 1)
                            x = min(int(j % frame1.shape[1]), frame1.shape[1] - 1)
                            colors[j] = frame1[y, x] / 255.0
                            
                        self.update_point_cloud(points_3d, colors)
                        
                self.update_visualization()
                
    def close(self) -> None:
        """Close the visualizer and release resources."""
        if self.visualizer is not None:
            self.visualizer.destroy_window()
            self.visualizer = None
            
        self.executor.shutdown(wait=False) 