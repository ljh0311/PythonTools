import cv2
import numpy as np
import open3d as o3d
import time
import json
from typing import List, Optional, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor

class ReconstructionEngine:
    """Engine for 3D reconstruction from camera images."""
    
    def __init__(
        self,
        camera_params: Optional[Dict[str, Any]] = None,
        nfeatures: int = 2000,
        match_ratio: float = 0.7,
        ransac_threshold: float = 2.0,
        min_matches: int = 8,
        use_preprocessing: bool = True,
        use_sift: bool = False,
        min_inliers_after_ransac: Optional[int] = None,
        min_inlier_ratio_after_ransac: float = 0.08,
    ):
        """Initialize the reconstruction engine.
        
        Args:
            camera_params: Optional camera parameters (intrinsics)
                If None, will attempt to estimate from images
            nfeatures: Max number of features to detect (ORB/SIFT).
            match_ratio: Lowe's ratio test threshold (good if m.distance < match_ratio * n.distance).
            ransac_threshold: RANSAC threshold for findEssentialMat (pixels).
            min_matches: Minimum good matches required for pose estimation (8-point algorithm).
            use_preprocessing: If True, apply CLAHE and optional denoising before feature detection.
            use_sift: If True, use SIFT detector (L2 matcher); otherwise ORB (Hamming). Requires opencv-contrib for SIFT.
            min_inliers_after_ransac: If set, keyframe pairs with fewer RANSAC inliers are skipped (reduces drift). None = use min_matches.
        """
        self.camera_params = camera_params
        self.nfeatures = nfeatures
        self.match_ratio = match_ratio
        self.ransac_threshold = ransac_threshold
        self.min_matches = min_matches
        self.use_preprocessing = use_preprocessing
        self.use_sift = use_sift
        self.min_inliers_after_ransac = min_inliers_after_ransac
        self.min_inlier_ratio_after_ransac = min_inlier_ratio_after_ransac
        self._night_threshold = 100  # Brightness below this triggers low-light preprocessing
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.point_cloud = o3d.geometry.PointCloud()
        self.mesh = None
        self.frames = []
        self.keyframes = []
        self.poses = []
        self.visualizer = None
        self._geometry_added = False  # Track if geometry has been added to visualizer
        self.metrics: List[Dict[str, Any]] = []
        self.active_backend: str = "manual"

    def _compute_inlier_ratio_threshold(self, good_match_count: int) -> float:
        """Adaptive inlier-ratio threshold.

        Fewer good matches require stricter geometric consistency.
        Many good matches can tolerate lower ratios because the absolute
        inlier count can still be high enough for stable triangulation.
        """
        base = float(self.min_inlier_ratio_after_ransac)
        if good_match_count >= 1200:
            return max(0.03, base * 0.5)
        if good_match_count >= 800:
            return max(0.05, base * 0.7)
        return max(0.07, base)

    def _iter_candidate_keyframe_pairs(self) -> List[Tuple[int, int]]:
        """Return candidate keyframe pairs in a robust priority order.

        Strategy:
        1) Adjacent pairs (best feature overlap)
        2) Skip-one pairs (adds baseline if adjacent overlap is weak)
        """
        total = len(self.keyframes)
        candidates: List[Tuple[int, int]] = []
        seen = set()
        for offset in (1, 2):
            for i in range(0, total - offset):
                pair = (i, i + offset)
                if pair not in seen:
                    seen.add(pair)
                    candidates.append(pair)
        return candidates
    
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
    
    def estimate_camera_pose(self, frame1: np.ndarray, frame2: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Estimate relative camera pose between two frames.
        
        Args:
            frame1: First frame
            frame2: Second frame
            
        Returns:
            Tuple of (rotation matrix, translation vector, inlier points in the first frame, inlier points in the second frame)
        """
        # Apply lens correction when calibration is available.
        frame1 = self._undistort_frame(frame1)
        frame2 = self._undistort_frame(frame2)

        # Convert to grayscale and optionally preprocess for better feature detection
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        if self.use_preprocessing:
            gray1 = self._preprocess_for_feature_detection(gray1)
            gray2 = self._preprocess_for_feature_detection(gray2)
        
        # Detect features (SIFT or ORB)
        if self.use_sift:
            detector = cv2.SIFT_create(nfeatures=self.nfeatures)
        else:
            detector = cv2.ORB_create(nfeatures=self.nfeatures)
        kp1, des1 = detector.detectAndCompute(gray1, None)
        kp2, des2 = detector.detectAndCompute(gray2, None)
        
        if des1 is None or des2 is None:
            return np.eye(3), np.zeros((3, 1)), None, None

        # Match features using BFMatcher with KNN (L2 for SIFT, Hamming for ORB)
        matcher = cv2.BFMatcher() if self.use_sift else cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        knn_matches = matcher.knnMatch(des1, des2, k=2)
        
        # Apply Lowe's ratio test to find good matches
        good_matches = []
        for m, n in knn_matches:
            if m.distance < self.match_ratio * n.distance:
                good_matches.append(m)
        
        if len(good_matches) < self.min_matches:
            print(f"Feature matching: Only {len(good_matches)} good matches found (need at least {self.min_matches}). "
                  f"Total KNN matches: {len(knn_matches)}")
            return np.eye(3), np.zeros((3, 1)), None, None
        
        print(f"Feature matching: Found {len(good_matches)} good matches from {len(knn_matches)} KNN matches")
        
        # Get matched keypoints
        pts1 = np.float32([kp1[m.queryIdx].pt for m in good_matches])
        pts2 = np.float32([kp2[m.trainIdx].pt for m in good_matches])
        
        # Get frame dimensions and camera intrinsics
        h, w = gray1.shape
        camera_matrix = self._get_camera_matrix(h, w)
        
        # Find essential matrix
        E, mask = cv2.findEssentialMat(
            pts1, pts2, camera_matrix,
            method=cv2.RANSAC, prob=0.999, threshold=self.ransac_threshold
        )
        
        if E is None:
            return np.eye(3), np.zeros((3, 1)), None, None
        
        # Recover pose
        _, R, t, mask = cv2.recoverPose(E, pts1, pts2, camera_matrix, mask=mask)
        
        # Return only inlier points
        pts1_inliers = pts1[mask.ravel() == 1]
        pts2_inliers = pts2[mask.ravel() == 1]
        
        inlier_ratio = float(len(pts1_inliers)) / float(len(good_matches)) if good_matches else 0.0
        ratio_threshold = self._compute_inlier_ratio_threshold(len(good_matches))
        if inlier_ratio < ratio_threshold:
            print(
                f"Skipping pair due to low inlier ratio: {inlier_ratio:.3f} "
                f"(threshold {ratio_threshold:.3f})"
            )
            self._record_metric(
                stage="pose_estimation",
                good_matches=len(good_matches),
                inliers=len(pts1_inliers),
                inlier_ratio=inlier_ratio,
                inlier_ratio_threshold=ratio_threshold,
                accepted=False,
            )
            return np.eye(3), np.zeros((3, 1)), None, None

        # Log match statistics for debugging
        if len(pts1_inliers) < self.min_matches:
            print(f"Warning: Only {len(pts1_inliers)} inlier matches after RANSAC (had {len(good_matches)} good matches)")
        self._record_metric(
            stage="pose_estimation",
            good_matches=len(good_matches),
            inliers=len(pts1_inliers),
            inlier_ratio=inlier_ratio,
            inlier_ratio_threshold=ratio_threshold,
            accepted=True,
        )
        
        return R, t, pts1_inliers, pts2_inliers
    
    def _preprocess_for_feature_detection(self, gray: np.ndarray) -> np.ndarray:
        """Preprocess grayscale image for better feature detection (CLAHE, optional denoising)."""
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
        """CLAHE + percentile stretch + denoising for low-light frames."""
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        p5, p95 = np.percentile(enhanced, (5, 95))
        if p95 > p5:
            enhanced = np.clip((enhanced.astype(np.float32) - p5) * 255.0 / (p95 - p5), 0, 255).astype(np.uint8)
        denoised = cv2.fastNlMeansDenoising(enhanced, None, h=10, templateWindowSize=7, searchWindowSize=21)
        return denoised
    
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
    
    def _validate_3d_points(self, points_3d: np.ndarray, max_distance: float = 1000.0) -> np.ndarray:
        """Validate and filter 3D points, removing invalid ones.
        
        Args:
            points_3d: Array of 3D points (N, 3)
            max_distance: Maximum distance from origin to consider valid (increased for more tolerance)
            
        Returns:
            Boolean mask of valid points
        """
        if points_3d.shape[0] == 0:
            return np.array([], dtype=bool)
        
        initial_count = len(points_3d)
        
        # Check for NaN and Inf values
        valid_mask = np.isfinite(points_3d).all(axis=1)
        nan_inf_count = initial_count - valid_mask.sum()
        
        # Check for points that are too far away (likely outliers)
        # Use a much larger max_distance to avoid filtering valid points
        distances = np.linalg.norm(points_3d, axis=1)
        valid_mask = valid_mask & (distances < max_distance) & (distances > 0.001)  # Relaxed minimum distance
        
        # Check for points behind camera - be more lenient
        # Allow negative Z values within reasonable bounds
        valid_mask = valid_mask & (points_3d[:, 2] > -max_distance * 0.5)  # More lenient Z filtering
        
        filtered_count = initial_count - valid_mask.sum()
        if filtered_count > 0:
            print(f"Point validation: {initial_count} -> {valid_mask.sum()} valid points (filtered {filtered_count}, including {nan_inf_count} NaN/Inf)")
        
        return valid_mask
    
    def triangulate_points(self, pts1: np.ndarray, pts2: np.ndarray, R: np.ndarray, t: np.ndarray, camera_matrix: np.ndarray) -> np.ndarray:
        """Triangulate 3D points from two sets of 2D points and relative pose.
        
        Args:
            pts1: 2D points in the first frame
            pts2: 2D points in the second frame
            R: Rotation matrix
            t: Translation vector
            camera_matrix: Camera intrinsic matrix
            
        Returns:
            Array of 3D points
        """
        # Camera projection matrices
        P1 = camera_matrix @ np.hstack((np.eye(3), np.zeros((3, 1))))
        P2 = camera_matrix @ np.hstack((R, t))
        
        # Triangulate points
        points_4d = cv2.triangulatePoints(P1, P2, pts1.T, pts2.T)
        
        # Convert to 3D points by dividing by the 4th coordinate
        points_3d = points_4d[:3, :] / points_4d[3, :]
        
        return points_3d.T
    
    def _normalize_point_cloud_scale(self, scale_to_unit_box: bool = True) -> None:
        """Center and scale the point cloud so it fits in a box of size 2.0 ([-1, 1] per axis).
        Makes the model viewable regardless of triangulation scale.
        """
        if len(self.point_cloud.points) == 0:
            return
        pts = np.asarray(self.point_cloud.points)
        centroid = np.mean(pts, axis=0)
        pts_centered = pts - centroid
        extent = np.max(pts_centered, axis=0) - np.min(pts_centered, axis=0)
        max_extent = float(np.max(extent))
        if scale_to_unit_box and max_extent > 1e-10:
            scale = 1.0 / (max_extent * 0.5)
            pts_centered = pts_centered * scale
        self.point_cloud.points = o3d.utility.Vector3dVector(pts_centered)
    
    def update_point_cloud(self, points_3d: np.ndarray, colors: Optional[np.ndarray] = None) -> None:
        """Update the point cloud with new points.
        
        Args:
            points_3d: 3D points to add
            colors: Optional colors for points (RGB format)
        """
        if points_3d.shape[0] == 0:
            return
        
        # Validate and filter invalid points
        initial_count = len(points_3d)
        valid_mask = self._validate_3d_points(points_3d)
        if not valid_mask.any():
            print(f"Warning: All {initial_count} points were filtered as invalid")
            return
        
        if initial_count != valid_mask.sum():
            print(f"Added {valid_mask.sum()} valid points (from {initial_count} triangulated)")
        
        # Filter points and colors
        points_3d = points_3d[valid_mask]
        if colors is None:
            colors = np.ones_like(points_3d) * 0.5  # Default gray color
        else:
            colors = colors[valid_mask]
            
        # Create point cloud from points
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points_3d)
        pcd.colors = o3d.utility.Vector3dVector(colors)
        
        # Merge with existing point cloud
        self.point_cloud += pcd
        
        # Adaptive voxel downsampling: voxel size from extent to avoid over-merging small clouds
        if len(self.point_cloud.points) > 100:
            try:
                pts = np.asarray(self.point_cloud.points)
                extent = np.max(pts, axis=0) - np.min(pts, axis=0)
                max_extent = float(np.max(extent))
                voxel_size = max_extent / 50.0
                voxel_size = max(0.001, min(0.5, voxel_size))
                self.point_cloud = self.point_cloud.voxel_down_sample(voxel_size=voxel_size)
            except Exception as e:
                print(f"Warning: Downsampling failed: {e}")
    
    def start_visualization(self) -> None:
        """Start the visualization window for the 3D reconstruction."""
        self.visualizer = o3d.visualization.Visualizer()
        self.visualizer.create_window("3D Reconstruction", width=1024, height=768)
        
        # Only add geometry if point cloud has points to avoid bounding box warnings
        if len(self.point_cloud.points) > 0:
            self.visualizer.add_geometry(self.point_cloud)
            self._geometry_added = True
        
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
        
        # Only update if point cloud has points
        if len(self.point_cloud.points) > 0:
            # Add geometry if it wasn't added initially (point cloud was empty)
            if not self._geometry_added:
                self.visualizer.add_geometry(self.point_cloud, reset_bounding_box=True)
                self._geometry_added = True
            else:
                self.visualizer.update_geometry(self.point_cloud)
            self.visualizer.poll_events()
            self.visualizer.update_renderer()
    
    def _manual_reconstruction(self):
        """Fallback reconstruction using simple pairwise triangulation."""
        print("Falling back to simple triangulation...")
        
        # Get camera matrix from the first frame
        frame1 = self.keyframes[0]
        h, w, _ = frame1.shape
        camera_matrix = self._get_camera_matrix(h, w)
        
        # Initialize final point cloud and poses
        global_points = o3d.geometry.PointCloud()
        global_R = np.eye(3)
        global_t = np.zeros((3, 1))

        pair_candidates = self._iter_candidate_keyframe_pairs()
        print(f"Manual reconstruction: evaluating {len(pair_candidates)} keyframe pairs")
        used_pairs = 0
        for i, j in pair_candidates:
            frame1 = self.keyframes[i]
            frame2 = self.keyframes[j]
            
            # Estimate pose and get inlier points
            R, t, pts1, pts2 = self.estimate_camera_pose(frame1, frame2)
            
            min_inliers = self.min_inliers_after_ransac if self.min_inliers_after_ransac is not None else self.min_matches
            if pts1 is None or len(pts1) < min_inliers:
                if pts1 is None:
                    print(f"Frame {i} to {j}: No feature matches found. Images may be too different or too similar.")
                else:
                    print(f"Frame {i} to {j}: Only {len(pts1)} inliers (need at least {min_inliers}). Skipping pair.")
                continue
            
            # Triangulate points
            points_3d = self.triangulate_points(pts1, pts2, R, t, camera_matrix)
            
            # Transform points to global coordinate system
            points_3d = (global_R @ points_3d.T + global_t).T
            
            # Update global pose
            global_R = R @ global_R
            global_t = global_t + (global_R @ t)
            
            # Extract colors for the 3D points from the first frame
            colors = np.zeros_like(points_3d)
            for j, pt in enumerate(pts1):
                x, y = int(pt[0]), int(pt[1])
                if 0 <= y < frame1.shape[0] and 0 <= x < frame1.shape[1]:
                    colors[j] = frame1[y, x, ::-1] / 255.0  # BGR to RGB
                    
            # Update the main point cloud
            self.update_point_cloud(points_3d, colors)
            self._record_metric(
                stage="pair_reconstruction",
                pair_index=i,
                pair_target=j,
                inliers=len(pts1),
                triangulated_points=len(points_3d),
            )
            used_pairs += 1
        
        # Final cleanup of the point cloud with adaptive parameters
        point_count = len(self.point_cloud.points)
        if point_count > 10:  # Lower threshold to allow cleaning with fewer points
            print(f"Cleaning final point cloud with statistical outlier removal ({point_count} points)...")
            # Use adaptive neighbor count based on point cloud size
            # Use at most 20 neighbors, but at least 3, and no more than 30% of total points
            nb_neighbors = min(20, max(3, int(point_count * 0.3)))
            # Use more lenient std_ratio for small point clouds
            std_ratio = 3.0 if point_count < 50 else 2.0
            
            try:
                cl, ind = self.point_cloud.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
                self.point_cloud = self.point_cloud.select_by_index(ind)
                print(f"Cleaned point cloud: {point_count} -> {len(self.point_cloud.points)} points (removed {point_count - len(self.point_cloud.points)})")
            except Exception as e:
                print(f"Warning: Statistical outlier removal failed: {e}. Keeping original {point_count} points.")
        else:
            print(f"Skipping outlier removal (only {point_count} points, need at least 10)")

        # Normalize scale so the model fills a canonical box and is viewable
        self._normalize_point_cloud_scale(scale_to_unit_box=True)

        print(
            f"Manual reconstruction finished. "
            f"Used {used_pairs}/{len(pair_candidates)} pairs. "
            f"Total points: {len(self.point_cloud.points)}"
        )
        self.update_visualization()

    def process_keyframes(self, include_neural_scaffold: bool = False) -> None:
        """Process all collected keyframes to create a dense reconstruction."""
        if len(self.keyframes) < 2:
            print("Need at least 2 keyframes for reconstruction")
            return
            
        print(f"Starting dense reconstruction with {len(self.keyframes)} keyframes")
        from reconstruction_backends import ColmapSfMBackend, ManualSfMBackend, NeuralStreamingBackend
        backends = [ColmapSfMBackend(), ManualSfMBackend()]
        if include_neural_scaffold:
            backends.append(NeuralStreamingBackend())
        for backend in backends:
            try:
                self.active_backend = backend.name
                print(f"Trying backend: {backend.name}")
                success = backend.run(self)
                self._record_metric(stage="backend", backend=backend.name, success=bool(success))
                if success:
                    print(f"Backend '{backend.name}' completed successfully")
                    return
            except Exception as e:
                print(f"Backend '{backend.name}' failed: {e}")
                self._record_metric(stage="backend", backend=backend.name, success=False, error=str(e))
        print("All reconstruction backends failed.")
                
    def close(self) -> None:
        """Close the visualizer and release resources."""
        if self.visualizer is not None:
            self.visualizer.destroy_window()
            self.visualizer = None
            
        self.executor.shutdown(wait=False)

    def _record_metric(self, stage: str, **kwargs: Any) -> None:
        record = {"timestamp": time.time(), "stage": stage}
        record.update(kwargs)
        self.metrics.append(record)

    def get_metrics_summary(self) -> Dict[str, Any]:
        pose_records = [m for m in self.metrics if m.get("stage") == "pose_estimation"]
        if not pose_records:
            return {"records": len(self.metrics)}
        ratios = [float(m.get("inlier_ratio", 0.0)) for m in pose_records]
        return {
            "records": len(self.metrics),
            "pose_estimates": len(pose_records),
            "avg_inlier_ratio": float(np.mean(ratios)),
            "max_inlier_ratio": float(np.max(ratios)),
            "min_inlier_ratio": float(np.min(ratios)),
            "active_backend": self.active_backend,
        }

    def load_camera_params(self, calibration_path: str) -> bool:
        """Load camera calibration JSON with camera_matrix and dist_coeffs."""
        try:
            with open(calibration_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.camera_params = raw
            return True
        except Exception as e:
            print(f"Failed to load camera calibration '{calibration_path}': {e}")
            return False

    def _get_camera_matrix(self, h: int, w: int) -> np.ndarray:
        if self.camera_params and "camera_matrix" in self.camera_params:
            matrix = np.array(self.camera_params["camera_matrix"], dtype=np.float32)
            if matrix.shape == (3, 3):
                return matrix
        focal_length = float(w)
        return np.array(
            [[focal_length, 0, w / 2.0],
             [0, focal_length, h / 2.0],
             [0, 0, 1]], dtype=np.float32
        )

    def _get_distortion_coeffs(self) -> Optional[np.ndarray]:
        if not self.camera_params:
            return None
        coeffs = self.camera_params.get("dist_coeffs")
        if coeffs is None:
            return None
        arr = np.array(coeffs, dtype=np.float32).reshape(-1, 1)
        return arr

    def _undistort_frame(self, frame: np.ndarray) -> np.ndarray:
        dist = self._get_distortion_coeffs()
        if dist is None:
            return frame
        h, w = frame.shape[:2]
        k = self._get_camera_matrix(h, w)
        return cv2.undistort(frame, k, dist)
        
def create_point_cloud_from_depth(depth_map, frame, camera_intrinsics) -> o3d.geometry.PointCloud:
    """Create a point cloud from a depth map and a color frame."""
    depth_o3d = o3d.geometry.Image(depth_map)
    color_o3d = o3d.geometry.Image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(
        color_o3d, depth_o3d, convert_rgb_to_intensity=False)
        
    pcd = o3d.geometry.PointCloud.create_from_rgbd_image(
        rgbd_image, camera_intrinsics)
        
    return pcd 