#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Feature Matcher Module for The Eyes

This module handles feature detection and matching between images from different cameras.
"""

import cv2
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union, Any

from src.utils.exceptions import FeatureMatchingError


class FeatureMatcher:
    """Class for detecting and matching features across images."""
    
    def __init__(self, config: Dict):
        """
        Initialize feature matcher with configuration.
        
        Args:
            config: Dictionary containing feature matching parameters
        """
        self.config = config
        self.logger = logging.getLogger("the_eyes.feature_matcher")
        
        # Initialize feature detector
        self.detector = self._create_detector()
        
        # Initialize feature matcher
        self.matcher = self._create_matcher()
        
    def _create_detector(self) -> Any:
        """
        Create feature detector based on configuration.
        
        Returns:
            Feature detector object
            
        Raises:
            FeatureMatchingError: If detector creation fails
        """
        detector_type = self.config.get('detector', 'sift').lower()
        max_features = self.config.get('max_features', 2000)
        
        try:
            if detector_type == 'sift':
                return cv2.SIFT_create(nfeatures=max_features)
            elif detector_type == 'orb':
                return cv2.ORB_create(nfeatures=max_features)
            elif detector_type == 'surf':
                # SURF is patented and may not be available in all OpenCV builds
                return cv2.xfeatures2d.SURF_create(hessianThreshold=400)
            elif detector_type == 'akaze':
                return cv2.AKAZE_create()
            else:
                self.logger.warning(f"Unsupported detector type '{detector_type}', falling back to SIFT")
                return cv2.SIFT_create(nfeatures=max_features)
                
        except Exception as e:
            self.logger.error(f"Error creating feature detector: {e}")
            self.logger.info("Falling back to ORB detector")
            return cv2.ORB_create(nfeatures=max_features)
            
    def _create_matcher(self) -> Any:
        """
        Create feature matcher based on configuration.
        
        Returns:
            Feature matcher object
            
        Raises:
            FeatureMatchingError: If matcher creation fails
        """
        matcher_type = self.config.get('matcher', 'flann').lower()
        detector_type = self.config.get('detector', 'sift').lower()
        
        try:
            if matcher_type == 'flann':
                # FLANN parameters depend on the detector type
                if detector_type in ['sift', 'surf']:
                    # FLANN parameters for SIFT and SURF
                    FLANN_INDEX_KDTREE = 1
                    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
                    search_params = dict(checks=50)
                else:
                    # FLANN parameters for ORB and AKAZE
                    FLANN_INDEX_LSH = 6
                    index_params = dict(algorithm=FLANN_INDEX_LSH,
                                     table_number=6,
                                     key_size=12,
                                     multi_probe_level=1)
                    search_params = dict(checks=50)
                
                return cv2.FlannBasedMatcher(index_params, search_params)
            else:
                # Brute force matcher
                if detector_type in ['orb', 'akaze']:
                    # ORB and AKAZE use Hamming distance
                    return cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                else:
                    # SIFT and SURF use L2 distance
                    return cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
                    
        except Exception as e:
            self.logger.error(f"Error creating feature matcher: {e}")
            self.logger.info("Falling back to brute force matcher")
            return cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
            
    def detect_features(self, image: np.ndarray) -> Tuple[List[cv2.KeyPoint], np.ndarray]:
        """
        Detect features in an image.
        
        Args:
            image: Input image
            
        Returns:
            Tuple of (keypoints, descriptors)
            
        Raises:
            FeatureMatchingError: If feature detection fails
        """
        try:
            keypoints, descriptors = self.detector.detectAndCompute(image, None)
            
            if keypoints is None or len(keypoints) == 0:
                raise FeatureMatchingError("No keypoints detected in image")
                
            self.logger.debug(f"Detected {len(keypoints)} features")
            return keypoints, descriptors
            
        except Exception as e:
            self.logger.error(f"Error detecting features: {e}")
            raise FeatureMatchingError(f"Feature detection failed: {e}")
            
    def match_features(self, images: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """
        Detect and match features across multiple images.
        
        Args:
            images: Dictionary of camera ID to processed image
            
        Returns:
            Dictionary containing features, descriptors, and matches
        """
        result = {
            'keypoints': {},     # Camera ID -> list of keypoints
            'descriptors': {},   # Camera ID -> descriptors array
            'matches': {}        # (cam_id1, cam_id2) -> list of matches
        }
        
        # Detect features in all images
        for camera_id, image in images.items():
            try:
                keypoints, descriptors = self.detect_features(image)
                result['keypoints'][camera_id] = keypoints
                result['descriptors'][camera_id] = descriptors
                
            except Exception as e:
                self.logger.error(f"Error detecting features for camera {camera_id}: {e}")
                # Skip this image
                
        # Match features between pairs of images
        camera_ids = list(result['keypoints'].keys())
        for i in range(len(camera_ids)):
            for j in range(i+1, len(camera_ids)):
                cam_id1 = camera_ids[i]
                cam_id2 = camera_ids[j]
                
                try:
                    matches = self.match_feature_pair(
                        result['descriptors'][cam_id1],
                        result['descriptors'][cam_id2]
                    )
                    
                    result['matches'][(cam_id1, cam_id2)] = matches
                    self.logger.debug(f"Matched {len(matches)} features between cameras {cam_id1} and {cam_id2}")
                    
                except Exception as e:
                    self.logger.error(f"Error matching features between cameras {cam_id1} and {cam_id2}: {e}")
                    # Skip this pair
                    
        return result
        
    def match_feature_pair(self, descriptors1: np.ndarray, descriptors2: np.ndarray) -> List:
        """
        Match features between two sets of descriptors.
        
        Args:
            descriptors1: Feature descriptors from first image
            descriptors2: Feature descriptors from second image
            
        Returns:
            List of matches
            
        Raises:
            FeatureMatchingError: If matching fails
        """
        try:
            matcher_type = self.config.get('matcher', 'flann').lower()
            min_matches = self.config.get('min_matches', 10)
            
            if matcher_type == 'flann':
                # FLANN matcher with ratio test
                matches = self.matcher.knnMatch(descriptors1, descriptors2, k=2)
                
                # Apply Lowe's ratio test
                good_matches = []
                lowe_ratio = self.config.get('lowe_ratio', 0.7)
                
                for m, n in matches:
                    if m.distance < lowe_ratio * n.distance:
                        good_matches.append(m)
                        
                return good_matches
            else:
                # Brute force matcher
                matches = self.matcher.match(descriptors1, descriptors2)
                
                # Sort by distance
                matches = sorted(matches, key=lambda x: x.distance)
                
                # Take only good matches
                return matches[:min(len(matches), min_matches * 2)]
                
        except Exception as e:
            self.logger.error(f"Error matching features: {e}")
            raise FeatureMatchingError(f"Feature matching failed: {e}")
            
    def draw_matches(self, img1: np.ndarray, kp1: List[cv2.KeyPoint], 
                    img2: np.ndarray, kp2: List[cv2.KeyPoint], 
                    matches: List) -> np.ndarray:
        """
        Draw matches between two images.
        
        Args:
            img1: First image
            kp1: Keypoints from first image
            img2: Second image
            kp2: Keypoints from second image
            matches: List of matches
            
        Returns:
            Image with matches drawn
        """
        try:
            return cv2.drawMatches(
                img1, kp1, img2, kp2, matches, None,
                flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
            )
        except Exception as e:
            self.logger.error(f"Error drawing matches: {e}")
            raise FeatureMatchingError(f"Drawing matches failed: {e}")
            
    def get_matched_points(self, 
                         kp1: List[cv2.KeyPoint], 
                         kp2: List[cv2.KeyPoint], 
                         matches: List) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get coordinates of matched points.
        
        Args:
            kp1: Keypoints from first image
            kp2: Keypoints from second image
            matches: List of matches
            
        Returns:
            Tuple of (points1, points2) as numpy arrays
        """
        points1 = np.float32([kp1[m.queryIdx].pt for m in matches])
        points2 = np.float32([kp2[m.trainIdx].pt for m in matches])
        return points1, points2
        
    def filter_matches_by_geometry(self, 
                                 kp1: List[cv2.KeyPoint], 
                                 kp2: List[cv2.KeyPoint], 
                                 matches: List,
                                 method: str = 'fundamental') -> List:
        """
        Filter matches using geometric constraints.
        
        Args:
            kp1: Keypoints from first image
            kp2: Keypoints from second image
            matches: List of matches
            method: Geometric constraint method ('fundamental' or 'homography')
            
        Returns:
            Filtered list of matches
        """
        try:
            # Get matched points
            points1, points2 = self.get_matched_points(kp1, kp2, matches)
            
            if len(points1) < 8:
                self.logger.warning("Not enough matches to apply geometric filtering")
                return matches
                
            if method == 'fundamental':
                # Use fundamental matrix
                F, mask = cv2.findFundamentalMat(points1, points2, cv2.FM_RANSAC, 3, 0.99)
                
                if F is None or mask is None:
                    self.logger.warning("Failed to find fundamental matrix, returning unfiltered matches")
                    return matches
                    
                # Create mask of inliers
                inliers_mask = mask.ravel().astype(bool)
                
            elif method == 'homography':
                # Use homography matrix
                H, mask = cv2.findHomography(points1, points2, cv2.RANSAC, 3.0)
                
                if H is None or mask is None:
                    self.logger.warning("Failed to find homography matrix, returning unfiltered matches")
                    return matches
                    
                inliers_mask = mask.ravel().astype(bool)
                
            else:
                self.logger.warning(f"Unknown geometric filtering method '{method}'")
                return matches
                
            # Return filtered matches
            return [m for i, m in enumerate(matches) if inliers_mask[i]]
            
        except Exception as e:
            self.logger.error(f"Error filtering matches by geometry: {e}")
            return matches  # Return original matches if filtering fails 