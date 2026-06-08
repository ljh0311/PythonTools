#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Image Processor Module for The Eyes

This module handles preprocessing of images before feature detection and matching.
"""

import cv2
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union

from src.utils.exceptions import ImageProcessingError


class ImageProcessor:
    """Class for preprocessing images before feature detection."""
    
    def __init__(self, config: Dict):
        """
        Initialize image processor with configuration.
        
        Args:
            config: Dictionary containing image processing parameters
        """
        self.config = config
        self.logger = logging.getLogger("the_eyes.image_processor")
        
    def process(self, image: np.ndarray) -> np.ndarray:
        """
        Process a single image.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Processed image
            
        Raises:
            ImageProcessingError: If processing fails
        """
        try:
            # Make a copy to avoid modifying the original
            processed = image.copy()
            
            # Resize image if configured
            if 'resize' in self.config:
                width = self.config['resize'].get('width')
                height = self.config['resize'].get('height')
                if width and height:
                    processed = cv2.resize(processed, (width, height))
            
            # Convert to grayscale if configured
            if self.config.get('grayscale', False):
                if len(processed.shape) == 3:
                    processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur if configured
            if 'blur' in self.config:
                kernel_size = self.config['blur'].get('kernel_size', 3)
                processed = cv2.GaussianBlur(processed, (kernel_size, kernel_size), 0)
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) if configured
            if 'clahe' in self.config and len(processed.shape) == 2:  # Only for grayscale
                clip_limit = self.config['clahe'].get('clip_limit', 2.0)
                tile_grid_size = tuple(self.config['clahe'].get('tile_grid_size', (8, 8)))
                clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
                processed = clahe.apply(processed)
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Error processing image: {e}")
            raise ImageProcessingError(f"Image processing failed: {e}")
    
    def process_batch(self, images: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Process multiple images.
        
        Args:
            images: Dictionary of camera ID to image
            
        Returns:
            Dictionary of camera ID to processed image
        """
        processed_images = {}
        for camera_id, image in images.items():
            try:
                processed_images[camera_id] = self.process(image)
                self.logger.debug(f"Processed image from camera {camera_id}")
            except Exception as e:
                self.logger.error(f"Error processing image from camera {camera_id}: {e}")
                # Skip this image
                
        return processed_images
    
    def undistort(self, image: np.ndarray, camera_matrix: np.ndarray, dist_coeffs: np.ndarray) -> np.ndarray:
        """
        Undistort an image using camera calibration parameters.
        
        Args:
            image: Input image
            camera_matrix: Camera matrix from calibration
            dist_coeffs: Distortion coefficients from calibration
            
        Returns:
            Undistorted image
        """
        try:
            return cv2.undistort(image, camera_matrix, dist_coeffs)
        except Exception as e:
            self.logger.error(f"Error undistorting image: {e}")
            raise ImageProcessingError(f"Image undistortion failed: {e}")
    
    def apply_mask(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Apply a mask to an image.
        
        Args:
            image: Input image
            mask: Binary mask
            
        Returns:
            Masked image
        """
        try:
            return cv2.bitwise_and(image, image, mask=mask)
        except Exception as e:
            self.logger.error(f"Error applying mask to image: {e}")
            raise ImageProcessingError(f"Mask application failed: {e}")
    
    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance image contrast.
        
        Args:
            image: Input image
            
        Returns:
            Contrast-enhanced image
        """
        try:
            # If image is grayscale
            if len(image.shape) == 2:
                return cv2.equalizeHist(image)
            
            # If image is color
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            hsv[:,:,2] = cv2.equalizeHist(hsv[:,:,2])
            return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            
        except Exception as e:
            self.logger.error(f"Error enhancing image contrast: {e}")
            raise ImageProcessingError(f"Contrast enhancement failed: {e}")
    
    def detect_edges(self, image: np.ndarray) -> np.ndarray:
        """
        Detect edges in an image using Canny edge detector.
        
        Args:
            image: Input image
            
        Returns:
            Edge image
        """
        try:
            # Ensure image is grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
                
            return cv2.Canny(gray, 50, 150)
            
        except Exception as e:
            self.logger.error(f"Error detecting edges: {e}")
            raise ImageProcessingError(f"Edge detection failed: {e}")
    
    def rectify_stereo(self, left_img: np.ndarray, right_img: np.ndarray, 
                      stereo_params: Dict) -> Tuple[np.ndarray, np.ndarray]:
        """
        Rectify stereo images using calibration parameters.
        
        Args:
            left_img: Left camera image
            right_img: Right camera image
            stereo_params: Stereo calibration parameters
            
        Returns:
            Tuple of rectified left and right images
        """
        try:
            R1 = np.array(stereo_params['R1'])
            R2 = np.array(stereo_params['R2'])
            P1 = np.array(stereo_params['P1'])
            P2 = np.array(stereo_params['P2'])
            Q = np.array(stereo_params['Q'])
            
            left_rect = cv2.remap(left_img, stereo_params['left_map_x'], 
                                stereo_params['left_map_y'], cv2.INTER_LINEAR)
            right_rect = cv2.remap(right_img, stereo_params['right_map_x'], 
                                 stereo_params['right_map_y'], cv2.INTER_LINEAR)
            
            return left_rect, right_rect
            
        except Exception as e:
            self.logger.error(f"Error rectifying stereo images: {e}")
            raise ImageProcessingError(f"Stereo rectification failed: {e}")
            
    def compute_disparity(self, left_img: np.ndarray, right_img: np.ndarray) -> np.ndarray:
        """
        Compute disparity map from stereo images.
        
        Args:
            left_img: Left camera image (rectified)
            right_img: Right camera image (rectified)
            
        Returns:
            Disparity map
        """
        try:
            # Ensure images are grayscale
            if len(left_img.shape) == 3:
                left_gray = cv2.cvtColor(left_img, cv2.COLOR_BGR2GRAY)
                right_gray = cv2.cvtColor(right_img, cv2.COLOR_BGR2GRAY)
            else:
                left_gray = left_img
                right_gray = right_img
            
            # Create stereo matcher
            stereo = cv2.StereoSGBM_create(
                minDisparity=0,
                numDisparities=16*10,  # must be divisible by 16
                blockSize=5,
                P1=8 * 3 * 5**2,
                P2=32 * 3 * 5**2,
                disp12MaxDiff=1,
                uniquenessRatio=15,
                speckleWindowSize=100,
                speckleRange=32
            )
            
            # Compute disparity
            disparity = stereo.compute(left_gray, right_gray)
            
            # Normalize for visualization
            norm_disparity = cv2.normalize(disparity, None, alpha=0, beta=255, 
                                         norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
            
            return norm_disparity
            
        except Exception as e:
            self.logger.error(f"Error computing disparity: {e}")
            raise ImageProcessingError(f"Disparity computation failed: {e}") 