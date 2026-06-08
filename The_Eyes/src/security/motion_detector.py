#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Motion Detection Module

Provides motion detection capabilities using background subtraction and frame differencing.
"""

import cv2
import numpy as np
import time
import logging
from typing import Dict, Optional, Tuple, List, Callable
from enum import Enum


class MotionDetectionMethod(Enum):
    """Motion detection algorithm methods."""
    MOG2 = "mog2"
    KNN = "knn"
    FRAME_DIFF = "frame_diff"


class MotionDetector:
    """Motion detection using background subtraction."""
    
    def __init__(self, 
                 method: MotionDetectionMethod = MotionDetectionMethod.MOG2,
                 sensitivity: float = 0.5,
                 min_area: int = 500,
                 history: int = 500,
                 var_threshold: float = 16.0,
                 detect_shadows: bool = True):
        """
        Initialize motion detector.
        
        Args:
            method: Motion detection method to use
            sensitivity: Sensitivity level (0.0 to 1.0, higher = more sensitive)
            min_area: Minimum contour area to consider as motion (pixels)
            history: Number of frames for background model (MOG2/KNN)
            var_threshold: Variance threshold for background subtraction
            detect_shadows: Whether to detect shadows (MOG2/KNN)
        """
        self.method = method
        self.sensitivity = max(0.0, min(1.0, sensitivity))
        self.min_area = min_area
        self.history = history
        self.var_threshold = var_threshold * (2.0 - sensitivity)  # Adjust based on sensitivity
        self.detect_shadows = detect_shadows
        
        self.logger = logging.getLogger("the_eyes.motion_detector")
        
        # Initialize background subtractor based on method
        if method == MotionDetectionMethod.MOG2:
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=history,
                varThreshold=var_threshold,
                detectShadows=detect_shadows
            )
        elif method == MotionDetectionMethod.KNN:
            self.bg_subtractor = cv2.createBackgroundSubtractorKNN(
                history=history,
                dist2Threshold=var_threshold,
                detectShadows=detect_shadows
            )
        else:
            self.bg_subtractor = None
        
        # For frame differencing
        self.previous_frame = None
        
        # Detection zones (list of rectangles: [(x, y, w, h), ...])
        self.detection_zones = []
        
        # Motion event callbacks
        self.motion_callbacks: List[Callable] = []
        
        # Statistics
        self.motion_detected = False
        self.last_motion_time = None
        self.motion_count = 0
        self.total_frames_processed = 0
        
    def add_detection_zone(self, x: int, y: int, width: int, height: int):
        """
        Add a detection zone (only detect motion in this area).
        
        Args:
            x, y: Top-left corner coordinates
            width, height: Zone dimensions
        """
        self.detection_zones.append((x, y, width, height))
        self.logger.info(f"Added detection zone: ({x}, {y}, {width}, {height})")
    
    def clear_detection_zones(self):
        """Clear all detection zones."""
        self.detection_zones.clear()
        self.logger.info("Cleared all detection zones")
    
    def add_motion_callback(self, callback: Callable):
        """
        Add a callback function to be called when motion is detected.
        
        Args:
            callback: Function that takes (frame, contours, motion_mask) as arguments
        """
        self.motion_callbacks.append(callback)
    
    def remove_motion_callback(self, callback: Callable):
        """Remove a motion callback."""
        if callback in self.motion_callbacks:
            self.motion_callbacks.remove(callback)
    
    def detect(self, frame: np.ndarray) -> Tuple[bool, np.ndarray, List]:
        """
        Detect motion in a frame.
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            Tuple of (motion_detected, motion_mask, contours)
        """
        if frame is None or frame.size == 0:
            return (False, None, [])
        
        self.total_frames_processed += 1
        
        # Convert to grayscale for processing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Get motion mask based on method
        if self.method == MotionDetectionMethod.FRAME_DIFF:
            motion_mask = self._frame_difference(blurred)
        else:
            # Use background subtractor
            motion_mask = self.bg_subtractor.apply(blurred)
        
        # Apply detection zones if any are defined
        if self.detection_zones:
            zone_mask = np.zeros_like(motion_mask)
            for x, y, w, h in self.detection_zones:
                zone_mask[y:y+h, x:x+w] = 255
            motion_mask = cv2.bitwise_and(motion_mask, zone_mask)
        
        # Apply morphological operations to reduce noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, kernel)
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area
        significant_contours = [
            c for c in contours 
            if cv2.contourArea(c) >= self.min_area
        ]
        
        # Determine if motion was detected
        motion_detected = len(significant_contours) > 0
        
        # Update statistics
        if motion_detected:
            self.motion_detected = True
            self.last_motion_time = time.time()
            self.motion_count += 1
            
            # Call motion callbacks
            for callback in self.motion_callbacks:
                try:
                    callback(frame, significant_contours, motion_mask)
                except Exception as e:
                    self.logger.error(f"Error in motion callback: {e}")
        else:
            self.motion_detected = False
        
        return (motion_detected, motion_mask, significant_contours)
    
    def _frame_difference(self, gray_frame: np.ndarray) -> np.ndarray:
        """
        Frame differencing method for motion detection.
        
        Args:
            gray_frame: Grayscale frame
            
        Returns:
            Motion mask
        """
        if self.previous_frame is None:
            self.previous_frame = gray_frame
            return np.zeros_like(gray_frame)
        
        # Calculate absolute difference
        frame_diff = cv2.absdiff(self.previous_frame, gray_frame)
        
        # Threshold
        _, motion_mask = cv2.threshold(
            frame_diff, 
            int(30 * (2.0 - self.sensitivity)),  # Adjust threshold based on sensitivity
            255, 
            cv2.THRESH_BINARY
        )
        
        # Update previous frame
        self.previous_frame = gray_frame
        
        return motion_mask
    
    def draw_detection_zones(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw detection zones on a frame.
        
        Args:
            frame: Input frame
            
        Returns:
            Frame with zones drawn
        """
        result = frame.copy()
        for x, y, w, h in self.detection_zones:
            cv2.rectangle(result, (x, y), (x + w, y + h), (0, 255, 255), 2)
            cv2.putText(result, "Zone", (x, y - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        return result
    
    def draw_motion(self, frame: np.ndarray, contours: List) -> np.ndarray:
        """
        Draw motion contours on a frame.
        
        Args:
            frame: Input frame
            contours: List of contours to draw
            
        Returns:
            Frame with motion drawn
        """
        result = frame.copy()
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(result, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(result, "Motion", (x, y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        return result
    
    def get_statistics(self) -> Dict:
        """
        Get motion detection statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'motion_detected': self.motion_detected,
            'last_motion_time': self.last_motion_time,
            'motion_count': self.motion_count,
            'total_frames_processed': self.total_frames_processed,
            'detection_zones': len(self.detection_zones),
            'method': self.method.value,
            'sensitivity': self.sensitivity
        }
    
    def reset_statistics(self):
        """Reset motion detection statistics."""
        self.motion_detected = False
        self.last_motion_time = None
        self.motion_count = 0
        self.total_frames_processed = 0
    
    def update_settings(self, sensitivity: Optional[float] = None,
                       min_area: Optional[int] = None,
                       var_threshold: Optional[float] = None):
        """
        Update motion detection settings.
        
        Args:
            sensitivity: New sensitivity level (0.0 to 1.0)
            min_area: New minimum contour area
            var_threshold: New variance threshold
        """
        if sensitivity is not None:
            self.sensitivity = max(0.0, min(1.0, sensitivity))
            if var_threshold is None:
                self.var_threshold = self.var_threshold * (2.0 - self.sensitivity) / (2.0 - sensitivity)
        
        if min_area is not None:
            self.min_area = min_area
        
        if var_threshold is not None:
            self.var_threshold = var_threshold
        
        self.logger.info(f"Updated motion detection settings: sensitivity={self.sensitivity}, "
                        f"min_area={self.min_area}, var_threshold={self.var_threshold}")

