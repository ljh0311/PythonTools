"""
Visual Odometry using Lucas-Kanade Optical Flow
Based on INF2009_VideoAnalytics optical_flow.py
"""

import cv2
import numpy as np
import time
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)

class VisualOdometry:
    """Visual odometry using Lucas-Kanade optical flow"""
    
    def __init__(self, max_corners: int = 100, quality_level: float = 0.1, 
                 min_distance: int = 5, block_size: int = 7):
        """
        Initialize visual odometry
        
        Args:
            max_corners: Maximum number of corners to detect
            quality_level: Minimum quality of corner below which everyone is rejected
            min_distance: Minimum possible euclidean distance between corners
            block_size: Size of an average block for computing a derivative covariation matrix
        """
        self.max_corners = max_corners
        self.quality_level = quality_level
        self.min_distance = min_distance
        self.block_size = block_size
        
        # Feature detection parameters
        self.feature_params = dict(
            maxCorners=max_corners,
            qualityLevel=quality_level,
            minDistance=min_distance,
            blockSize=block_size
        )
        
        # Lucas-Kanade optical flow parameters
        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        
        # State variables
        self.old_gray = None
        self.p0 = None
        self.first_frame = True
        
        # Camera calibration (assumed for now - should be calibrated)
        self.focal_length = 1000.0  # pixels
        self.principal_point = (320, 240)  # (cx, cy)
        
        # Motion history for smoothing
        self.motion_history = []
        self.max_history = 5
        
        logger.info("Visual Odometry initialized")
    
    def initialize(self, frame: np.ndarray) -> bool:
        """
        Initialize with first frame
        
        Args:
            frame: First frame (BGR format)
            
        Returns:
            True if initialization successful
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect corners
            self.p0 = cv2.goodFeaturesToTrack(gray, mask=None, **self.feature_params)
            
            if self.p0 is None or len(self.p0) < 5:
                logger.warning("Not enough features detected for visual odometry")
                return False
            
            self.old_gray = gray.copy()
            self.first_frame = False
            
            logger.info(f"Visual odometry initialized with {len(self.p0)} features")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize visual odometry: {e}")
            return False
    
    def process_frame(self, frame: np.ndarray) -> Optional[Tuple[float, float, float]]:
        """
        Process frame and estimate motion
        
        Args:
            frame: Current frame (BGR format)
            
        Returns:
            Tuple of (dx, dy, dtheta) in meters/radians, or None if failed
        """
        if self.first_frame:
            success = self.initialize(frame)
            return None if not success else (0.0, 0.0, 0.0)  # Return zero motion after initialization
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Calculate optical flow
            if self.p0 is None or len(self.p0) < 3:
                # Re-detect features if too few
                self.p0 = cv2.goodFeaturesToTrack(gray, mask=None, **self.feature_params)
                if self.p0 is None:
                    return None
            
            p1, st, err = cv2.calcOpticalFlowPyrLK(self.old_gray, gray, self.p0, None, **self.lk_params)
            
            if p1 is None:
                return None
            
            # Select good points
            good_new = p1[st == 1]
            good_old = self.p0[st == 1]
            
            if len(good_new) < 3:
                return None
            
            # Estimate motion using essential matrix
            motion = self._estimate_motion(good_old, good_new)
            
            if motion is not None:
                # Add to history for smoothing
                self.motion_history.append(motion)
                if len(self.motion_history) > self.max_history:
                    self.motion_history.pop(0)
                
                # Return smoothed motion
                return self._smooth_motion()
            
            # Update for next frame
            self.old_gray = gray.copy()
            self.p0 = good_new.reshape(-1, 1, 2)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in visual odometry: {e}")
            return None
    
    def _estimate_motion(self, points_old: np.ndarray, points_new: np.ndarray) -> Optional[Tuple[float, float, float]]:
        """
        Estimate motion from point correspondences
        
        Args:
            points_old: Previous frame points
            points_new: Current frame points
            
        Returns:
            Tuple of (dx, dy, dtheta) in meters/radians
        """
        try:
            # Normalize points
            points_old_norm = self._normalize_points(points_old)
            points_new_norm = self._normalize_points(points_new)
            
            # Estimate essential matrix
            E, mask = cv2.findEssentialMat(points_old_norm, points_new_norm, 
                                         focal=self.focal_length, pp=self.principal_point)
            
            if E is None:
                return None
            
            # Recover pose
            _, R, t, mask = cv2.recoverPose(E, points_old_norm, points_new_norm,
                                          focal=self.focal_length, pp=self.principal_point)
            
            # Extract translation and rotation
            dx = float(t[0, 0])
            dy = float(t[1, 0])
            
            # Extract rotation angle from rotation matrix
            dtheta = np.arctan2(R[1, 0], R[0, 0])
            
            # Scale translation (this is approximate - should use proper calibration)
            scale = 0.01  # meters per pixel (approximate)
            dx *= scale
            dy *= scale
            
            return (dx, dy, dtheta)
            
        except Exception as e:
            logger.error(f"Error estimating motion: {e}")
            return None
    
    def _normalize_points(self, points: np.ndarray) -> np.ndarray:
        """Normalize points for essential matrix estimation"""
        points_norm = points.astype(np.float32)
        return points_norm
    
    def _smooth_motion(self) -> Tuple[float, float, float]:
        """Smooth motion using history"""
        if not self.motion_history:
            return (0.0, 0.0, 0.0)
        
        # Simple moving average
        dx = np.mean([m[0] for m in self.motion_history])
        dy = np.mean([m[1] for m in self.motion_history])
        dtheta = np.mean([m[2] for m in self.motion_history])
        
        return (dx, dy, dtheta)
    
    def get_status(self) -> dict:
        """Get status information"""
        return {
            'initialized': not self.first_frame,
            'features_count': len(self.p0) if self.p0 is not None else 0,
            'motion_history_length': len(self.motion_history)
        }
    
    def reset(self):
        """Reset visual odometry"""
        self.old_gray = None
        self.p0 = None
        self.first_frame = True
        self.motion_history.clear()
        logger.info("Visual odometry reset") 