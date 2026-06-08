#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Camera Manager Module for The Eyes

This module provides a unified interface for managing multiple cameras,
handling their initialization, calibration, and synchronization.
"""

import cv2
import numpy as np
import os
import threading
import time
import logging
from typing import Dict, List, Optional, Tuple, Union
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

# Try importing specific camera SDKs
try:
    import pyrealsense2 as rs
    REALSENSE_AVAILABLE = True
except ImportError:
    REALSENSE_AVAILABLE = False
    rs = None  # Set to None to avoid undefined variable errors

from ..utils.exceptions import CameraError


class Camera:
    """Base class for camera implementations."""
    
    def __init__(self, camera_id: Union[int, str], config: Dict):
        """
        Initialize a camera instance.
        
        Args:
            camera_id: Unique identifier for the camera
            config: Camera configuration parameters
        """
        self.camera_id = camera_id
        self.config = config
        self.logger = logging.getLogger(f"the_eyes.camera.{camera_id}")
        self.is_open = False
        self.calibration_data = None
        
    def open(self) -> bool:
        """Open the camera connection."""
        raise NotImplementedError("Subclasses must implement this method")
        
    def close(self) -> None:
        """Close the camera connection."""
        raise NotImplementedError("Subclasses must implement this method")
        
    def capture(self) -> np.ndarray:
        """Capture a frame from the camera."""
        raise NotImplementedError("Subclasses must implement this method")
        
    def get_calibration_data(self) -> Dict:
        """Get camera calibration data."""
        return self.calibration_data
        
    def set_calibration_data(self, data: Dict) -> None:
        """Set camera calibration data."""
        self.calibration_data = data


class WebCamera(Camera):
    """Implementation for standard webcams using OpenCV."""
    
    def __init__(self, camera_id: Union[int, str], config: Dict):
        super().__init__(camera_id, config)
        self.cap = None
        
    def open(self) -> bool:
        try:
            self.cap = cv2.VideoCapture(self.config.get('id', self.camera_id))
            
            # Configure camera parameters
            if 'width' in self.config and 'height' in self.config:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config['width'])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config['height'])
            
            if 'fps' in self.config:
                self.cap.set(cv2.CAP_PROP_FPS, self.config['fps'])
                
            self.is_open = self.cap.isOpened()
            if not self.is_open:
                self.logger.error(f"Failed to open camera {self.camera_id}")
                return False
                
            self.logger.info(f"Opened camera {self.camera_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error opening camera {self.camera_id}: {e}")
            return False
            
    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
        self.is_open = False
        self.logger.info(f"Closed camera {self.camera_id}")
        
    def capture(self) -> np.ndarray:
        if not self.is_open:
            raise CameraError(f"Camera {self.camera_id} is not open")
            
        ret, frame = self.cap.read()
        if not ret:
            raise CameraError(f"Failed to capture frame from camera {self.camera_id}")
            
        return frame


class RealSenseCamera(Camera):
    """Implementation for Intel RealSense cameras."""
    
    def __init__(self, camera_id: Union[int, str], config: Dict):
        if not REALSENSE_AVAILABLE:
            raise ImportError("pyrealsense2 is not installed. Cannot use RealSense cameras.")
            
        super().__init__(camera_id, config)
        self.pipeline = rs.pipeline()
        self.config_rs = rs.config()
        
    def open(self) -> bool:
        try:
            # Configure streams
            width = self.config.get('width', 640)
            height = self.config.get('height', 480)
            fps = self.config.get('fps', 30)
            
            self.config_rs.enable_device(self.camera_id)
            self.config_rs.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
            
            if self.config.get('depth_stream', False):
                self.config_rs.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
            
            # Start streaming
            self.pipeline.start(self.config_rs)
            self.is_open = True
            
            self.logger.info(f"Opened RealSense camera {self.camera_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error opening RealSense camera {self.camera_id}: {e}")
            return False
            
    def close(self) -> None:
        if self.is_open:
            self.pipeline.stop()
            self.is_open = False
            self.logger.info(f"Closed RealSense camera {self.camera_id}")
            
    def capture(self) -> np.ndarray:
        if not self.is_open:
            raise CameraError(f"RealSense camera {self.camera_id} is not open")
            
        frames = self.pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        
        if not color_frame:
            raise CameraError(f"Failed to capture color frame from RealSense camera {self.camera_id}")
            
        # Convert to numpy array
        return np.asanyarray(color_frame.get_data())


class CameraManager:
    """Manager class for handling multiple cameras."""
    
    def __init__(self, config: Dict, enable_threading: bool = True, frame_buffer_size: int = 2):
        """
        Initialize the camera manager.
        
        Args:
            config: Camera configuration dictionary
            enable_threading: Whether to use threading for parallel frame capture
            frame_buffer_size: Size of frame buffer per camera (for synchronization)
        """
        self.config = config
        self.cameras = {}
        self.logger = logging.getLogger("the_eyes.camera_manager")
        self.exit_flag = False
        self.enable_threading = enable_threading
        self.frame_buffer_size = frame_buffer_size
        
        # Frame buffers for each camera (thread-safe)
        self.frame_buffers = {}
        self.frame_locks = {}
        
        # Thread pool for parallel capture
        self.executor = None
        if self.enable_threading:
            self.executor = ThreadPoolExecutor(max_workers=10)
        
        self._initialize_cameras()
        
    def _initialize_cameras(self) -> None:
        """Initialize all cameras based on configuration."""
        if not self.config:
            # If no cameras configured, try to auto-detect them
            self.logger.info("No camera configuration provided, scanning for available cameras...")
            self.scan_for_cameras()
            return
            
        for camera_id, camera_config in self.config.items():
            camera_type = camera_config.get('type', 'webcam').lower()
            
            try:
                if camera_type == 'webcam':
                    camera = WebCamera(camera_id, camera_config)
                elif camera_type == 'realsense':
                    camera = RealSenseCamera(camera_id, camera_config)
                else:
                    self.logger.warning(f"Unsupported camera type '{camera_type}' for camera {camera_id}")
                    continue
                    
                if camera.open():
                    self.cameras[camera_id] = camera
                    # Initialize frame buffer and lock for this camera
                    self.frame_buffers[camera_id] = deque(maxlen=self.frame_buffer_size)
                    self.frame_locks[camera_id] = threading.Lock()
                    
            except Exception as e:
                self.logger.error(f"Error initializing camera {camera_id}: {e}")
                
        self.logger.info(f"Initialized {len(self.cameras)} cameras")
        
        # If no cameras were initialized from the configuration, try auto-detection
        if not self.cameras:
            self.logger.info("No cameras initialized from configuration, scanning for available cameras...")
            self.scan_for_cameras()
            
        # Initialize frame buffers for auto-detected cameras
        for camera_id in self.cameras:
            if camera_id not in self.frame_buffers:
                self.frame_buffers[camera_id] = deque(maxlen=self.frame_buffer_size)
                self.frame_locks[camera_id] = threading.Lock()
        
    def scan_for_cameras(self) -> Dict[str, Union[int, str]]:
        """
        Scan for available cameras and add them to the manager.
        
        Returns:
            Dictionary of detected camera IDs
        """
        self.logger.info("Scanning for available webcams...")
        detected_cameras = {}
        
        # Scan for regular webcams
        max_webcam_id = 10  # Maximum number of webcams to try
        for i in range(max_webcam_id):
            try:
                # Try to open the camera
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # Camera is available
                    self.logger.info(f"Found webcam at index {i}")
                    detected_cameras[f"webcam_{i}"] = i
                    
                    # Create a default configuration for this camera
                    camera_config = {
                        'type': 'webcam',
                        'id': i,
                        'width': 640,
                        'height': 480,
                        'fps': 30
                    }
                    
                    # Initialize the camera
                    camera = WebCamera(f"webcam_{i}", camera_config)
                    if camera.open():
                        camera_id = f"webcam_{i}"
                        self.cameras[camera_id] = camera
                        # Initialize frame buffer and lock
                        if camera_id not in self.frame_buffers:
                            self.frame_buffers[camera_id] = deque(maxlen=self.frame_buffer_size)
                            self.frame_locks[camera_id] = threading.Lock()
                    
                # Release the camera
                cap.release()
                
            except Exception as e:
                self.logger.debug(f"No camera at index {i}: {e}")
                
        # Scan for RealSense cameras if available
        if REALSENSE_AVAILABLE:
            try:
                self.logger.info("Scanning for RealSense cameras...")
                context = rs.context()
                devices = context.query_devices()
                
                for i in range(devices.size()):
                    device = devices[i]
                    serial = device.get_info(rs.camera_info.serial_number)
                    self.logger.info(f"Found RealSense camera with serial {serial}")
                    
                    # Create a default configuration for this camera
                    camera_config = {
                        'type': 'realsense',
                        'id': serial,
                        'width': 640,
                        'height': 480,
                        'fps': 30
                    }
                    
                    # Initialize the camera
                    camera_id = f"realsense_{serial}"
                    camera = RealSenseCamera(camera_id, camera_config)
                    if camera.open():
                        self.cameras[camera_id] = camera
                        # Initialize frame buffer and lock
                        if camera_id not in self.frame_buffers:
                            self.frame_buffers[camera_id] = deque(maxlen=self.frame_buffer_size)
                            self.frame_locks[camera_id] = threading.Lock()
                    
                    detected_cameras[camera_id] = serial
                    
            except Exception as e:
                self.logger.warning(f"Error scanning for RealSense cameras: {e}")
                
        self.logger.info(f"Found {len(detected_cameras)} cameras during scanning")
        return detected_cameras
        
    def refresh_cameras(self) -> Dict:
        """
        Re-scan for available cameras, updating the camera list.
        
        Returns:
            Dictionary of camera IDs
        """
        # Release all current cameras
        self.release_all()
        
        # Clear the cameras dictionary
        self.cameras = {}
        
        # Scan for new cameras
        return self.scan_for_cameras()
        
    def release_all(self) -> None:
        """Release all camera resources."""
        # Shutdown thread pool if it exists
        if self.executor:
            self.executor.shutdown(wait=True)
            self.executor = None
        
        for camera_id, camera in self.cameras.items():
            try:
                camera.close()
            except Exception as e:
                self.logger.error(f"Error closing camera {camera_id}: {e}")
        
        # Clear frame buffers
        self.frame_buffers.clear()
        self.frame_locks.clear()
                
    def _capture_single(self, camera_id: str, camera) -> Tuple[str, Optional[np.ndarray]]:
        """
        Capture a frame from a single camera (for threading).
        
        Returns:
            Tuple of (camera_id, frame or None)
        """
        try:
            frame = camera.capture()
            # Store in buffer
            with self.frame_locks.get(camera_id, threading.Lock()):
                if camera_id in self.frame_buffers:
                    self.frame_buffers[camera_id].append((time.time(), frame))
            return (camera_id, frame)
        except Exception as e:
            self.logger.error(f"Error capturing from camera {camera_id}: {e}")
            return (camera_id, None)
    
    def capture_all(self, use_buffer: bool = False) -> Dict[str, np.ndarray]:
        """
        Capture frames from all cameras.
        
        Args:
            use_buffer: If True, use buffered frames for better synchronization
            
        Returns:
            Dictionary mapping camera_id to frame
        """
        if use_buffer and self.frame_buffers:
            # Get latest frames from buffers (synchronized by timestamp)
            frames = {}
            sync_time = time.time()
            
            for camera_id in self.cameras:
                with self.frame_locks.get(camera_id, threading.Lock()):
                    if camera_id in self.frame_buffers and self.frame_buffers[camera_id]:
                        # Get most recent frame
                        _, frame = self.frame_buffers[camera_id][-1]
                        frames[camera_id] = frame
            return frames
        
        # Direct capture (with optional threading)
        if self.enable_threading and self.executor and len(self.cameras) > 1:
            # Use threading for parallel capture
            frames = {}
            futures = {
                self.executor.submit(self._capture_single, camera_id, camera): camera_id
                for camera_id, camera in self.cameras.items()
            }
            
            for future in as_completed(futures):
                camera_id, frame = future.result()
                if frame is not None:
                    frames[camera_id] = frame
            return frames
        else:
            # Sequential capture (fallback)
            frames = {}
            for camera_id, camera in self.cameras.items():
                try:
                    frame = camera.capture()
                    frames[camera_id] = frame
                    # Also store in buffer
                    with self.frame_locks.get(camera_id, threading.Lock()):
                        if camera_id in self.frame_buffers:
                            self.frame_buffers[camera_id].append((time.time(), frame))
                except Exception as e:
                    self.logger.error(f"Error capturing from camera {camera_id}: {e}")
            return frames
        
    def calibrate(self) -> Dict:
        """
        Perform camera calibration using chessboard pattern.
        
        Returns:
            Dictionary containing calibration parameters for all cameras
        """
        # Camera calibration parameters
        pattern_size = self.config.get('calibration', {}).get('pattern_size', (9, 6))
        square_size = self.config.get('calibration', {}).get('square_size', 0.025)  # in meters
        num_images = self.config.get('calibration', {}).get('num_images', 10)
        
        # Prepare object points (3D points in real world space)
        objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2) * square_size
        
        calibration_data = {}
        
        # Calibrate each camera
        for camera_id, camera in self.cameras.items():
            self.logger.info(f"Calibrating camera {camera_id}")
            
            # Arrays to store object points and image points
            objpoints = []  # 3D points in real world space
            imgpoints = []  # 2D points in image plane
            
            count = 0
            last_time = time.time()
            
            while count < num_images:
                try:
                    frame = camera.capture()
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    # Find the chessboard corners
                    ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)
                    
                    # If found, add object points and image points
                    if ret and (time.time() - last_time) > 1.0:  # Take images at 1 second intervals
                        objpoints.append(objp)
                        corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1),
                                                        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
                        imgpoints.append(corners_refined)
                        
                        # Draw and display the corners
                        cv2.drawChessboardCorners(frame, pattern_size, corners_refined, ret)
                        cv2.putText(frame, f"Images: {count+1}/{num_images}", (50, 50), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        cv2.imshow(f"Calibration - Camera {camera_id}", frame)
                        
                        count += 1
                        last_time = time.time()
                        self.logger.info(f"Captured calibration image {count}/{num_images} for camera {camera_id}")
                    else:
                        # Show the current frame with instructions
                        cv2.putText(frame, "Position chessboard in view", (50, 50), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                        cv2.imshow(f"Calibration - Camera {camera_id}", frame)
                        
                    # Check for user exit
                    if cv2.waitKey(1) & 0xFF == 27:  # ESC key
                        break
                        
                except Exception as e:
                    self.logger.error(f"Error during calibration of camera {camera_id}: {e}")
                    break
                    
            cv2.destroyAllWindows()
            
            # Calculate calibration if we have enough images
            if len(objpoints) > 5:
                self.logger.info(f"Computing calibration for camera {camera_id}")
                ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                    objpoints, imgpoints, gray.shape[::-1], None, None
                )
                
                if ret:
                    # Calculate reprojection error
                    mean_error = 0
                    for i in range(len(objpoints)):
                        imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
                        error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
                        mean_error += error
                        
                    camera_calib = {
                        'camera_matrix': mtx.tolist(),
                        'dist_coeffs': dist.tolist(),
                        'reprojection_error': mean_error / len(objpoints)
                    }
                    
                    calibration_data[camera_id] = camera_calib
                    camera.set_calibration_data(camera_calib)
                    
                    self.logger.info(f"Calibration for camera {camera_id} completed with "
                                     f"reprojection error: {camera_calib['reprojection_error']:.6f}")
                else:
                    self.logger.error(f"Calibration failed for camera {camera_id}")
            else:
                self.logger.warning(f"Not enough calibration images for camera {camera_id}")
                
        # Save calibration data
        return calibration_data
        
    def should_exit(self) -> bool:
        """Check if the camera manager should exit."""
        return self.exit_flag
        
    def set_exit_flag(self) -> None:
        """Set the exit flag to stop processing."""
        self.exit_flag = True 