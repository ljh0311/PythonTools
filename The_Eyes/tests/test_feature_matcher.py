#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for the Feature Matcher module.
"""

import cv2
import numpy as np
import os
import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.feature_matching.matcher import FeatureMatcher
from src.utils.exceptions import FeatureMatchingError


@pytest.fixture
def test_images():
    """Create two test images with a simple pattern for feature matching."""
    # Create a 300x300 base image with some shapes
    img1 = np.zeros((300, 300), dtype=np.uint8)
    
    # Add some shapes to first image
    cv2.rectangle(img1, (50, 50), (100, 100), 255, -1)
    cv2.circle(img1, (150, 150), 30, 255, -1)
    cv2.line(img1, (200, 50), (250, 100), 255, 5)
    
    # Create second image (shifted version of first)
    img2 = np.zeros((300, 300), dtype=np.uint8)
    
    # Add same shapes but shifted
    cv2.rectangle(img2, (70, 60), (120, 110), 255, -1)
    cv2.circle(img2, (170, 160), 30, 255, -1)
    cv2.line(img2, (220, 60), (270, 110), 255, 5)
    
    # Add some noise
    noise1 = np.random.randint(0, 30, (300, 300), dtype=np.uint8)
    noise2 = np.random.randint(0, 30, (300, 300), dtype=np.uint8)
    
    img1 = cv2.add(img1, noise1)
    img2 = cv2.add(img2, noise2)
    
    return (img1, img2)


@pytest.fixture
def matcher_config():
    """Create a sample feature matcher configuration."""
    return {
        'detector': 'orb',  # Use ORB for speed in tests
        'descriptor': 'orb',
        'matcher': 'bf',
        'max_features': 500,
        'min_matches': 10,
        'lowe_ratio': 0.75
    }


@pytest.fixture
def feature_matcher(matcher_config):
    """Create a FeatureMatcher instance with test config."""
    return FeatureMatcher(matcher_config)


def test_matcher_initialization(matcher_config):
    """Test that matcher initializes correctly with config."""
    matcher = FeatureMatcher(matcher_config)
    assert matcher.config == matcher_config
    assert matcher.logger is not None
    assert matcher.detector is not None
    assert matcher.matcher is not None


def test_detector_creation():
    """Test creating different types of detectors."""
    # Test SIFT
    matcher = FeatureMatcher({'detector': 'sift'})
    assert isinstance(matcher.detector, cv2.SIFT)
    
    # Test ORB
    matcher = FeatureMatcher({'detector': 'orb'})
    assert isinstance(matcher.detector, cv2.ORB)
    
    # Test fallback for unsupported detector
    matcher = FeatureMatcher({'detector': 'unsupported'})
    assert isinstance(matcher.detector, cv2.SIFT)


def test_matcher_creation():
    """Test creating different types of matchers."""
    # Test FLANN with SIFT
    matcher = FeatureMatcher({'detector': 'sift', 'matcher': 'flann'})
    assert isinstance(matcher.matcher, cv2.FlannBasedMatcher)
    
    # Test BF with ORB
    matcher = FeatureMatcher({'detector': 'orb', 'matcher': 'bf'})
    assert isinstance(matcher.matcher, cv2.BFMatcher)


def test_detect_features(feature_matcher, test_images):
    """Test feature detection."""
    img1 = test_images[0]
    
    # Detect features
    keypoints, descriptors = feature_matcher.detect_features(img1)
    
    # Check that keypoints and descriptors are returned
    assert len(keypoints) > 0
    assert descriptors is not None
    assert descriptors.shape[0] == len(keypoints)


def test_detect_features_error_handling(feature_matcher):
    """Test error handling in feature detection."""
    # Test with invalid image
    with pytest.raises(FeatureMatchingError):
        feature_matcher.detect_features("not an image")
    
    # Test with empty image (should raise because no keypoints found)
    empty_img = np.zeros((100, 100), dtype=np.uint8)
    with pytest.raises(FeatureMatchingError):
        feature_matcher.detect_features(empty_img)


def test_match_features(feature_matcher, test_images):
    """Test matching features between images."""
    img1, img2 = test_images
    
    # Create a batch of images
    images = {
        'cam1': img1,
        'cam2': img2
    }
    
    # Match features
    result = feature_matcher.match_features(images)
    
    # Check result structure
    assert 'keypoints' in result
    assert 'descriptors' in result
    assert 'matches' in result
    
    # Check that keypoints were found for both cameras
    assert 'cam1' in result['keypoints']
    assert 'cam2' in result['keypoints']
    
    # Check that matches were found between cameras
    assert ('cam1', 'cam2') in result['matches']
    assert len(result['matches'][('cam1', 'cam2')]) > 0


def test_match_feature_pair(feature_matcher, test_images):
    """Test matching features between a pair of descriptors."""
    img1, img2 = test_images
    
    # Detect features in both images
    kp1, desc1 = feature_matcher.detect_features(img1)
    kp2, desc2 = feature_matcher.detect_features(img2)
    
    # Match features
    matches = feature_matcher.match_feature_pair(desc1, desc2)
    
    # Check that matches were found
    assert len(matches) > 0
    
    # Check that matches have expected attributes
    assert hasattr(matches[0], 'queryIdx')
    assert hasattr(matches[0], 'trainIdx')
    assert hasattr(matches[0], 'distance')


def test_get_matched_points(feature_matcher, test_images):
    """Test getting coordinates of matched points."""
    img1, img2 = test_images
    
    # Detect features in both images
    kp1, desc1 = feature_matcher.detect_features(img1)
    kp2, desc2 = feature_matcher.detect_features(img2)
    
    # Match features
    matches = feature_matcher.match_feature_pair(desc1, desc2)
    
    # Get matched points
    points1, points2 = feature_matcher.get_matched_points(kp1, kp2, matches)
    
    # Check shapes
    assert points1.shape == points2.shape
    assert points1.shape[0] == len(matches)
    assert points1.shape[1] == 2  # x, y coordinates
    
    # Check data type
    assert points1.dtype == np.float32
    assert points2.dtype == np.float32


def test_filter_matches_by_geometry(feature_matcher, test_images):
    """Test filtering matches using geometric constraints."""
    img1, img2 = test_images
    
    # Detect features in both images
    kp1, desc1 = feature_matcher.detect_features(img1)
    kp2, desc2 = feature_matcher.detect_features(img2)
    
    # Match features
    matches = feature_matcher.match_feature_pair(desc1, desc2)
    
    # Filter matches using fundamental matrix
    filtered_matches = feature_matcher.filter_matches_by_geometry(
        kp1, kp2, matches, method='fundamental')
    
    # Check that some filtering occurred
    assert len(filtered_matches) <= len(matches)
    
    # Filter matches using homography
    filtered_matches = feature_matcher.filter_matches_by_geometry(
        kp1, kp2, matches, method='homography')
    
    # Check that some filtering occurred
    assert len(filtered_matches) <= len(matches)
    
    # Test with unknown method (should return original matches)
    filtered_matches = feature_matcher.filter_matches_by_geometry(
        kp1, kp2, matches, method='unknown')
    
    # Check that no filtering occurred
    assert len(filtered_matches) == len(matches)


def test_draw_matches(feature_matcher, test_images):
    """Test drawing matches between images."""
    img1, img2 = test_images
    
    # Detect features in both images
    kp1, desc1 = feature_matcher.detect_features(img1)
    kp2, desc2 = feature_matcher.detect_features(img2)
    
    # Match features
    matches = feature_matcher.match_feature_pair(desc1, desc2)
    
    # Draw matches
    match_img = feature_matcher.draw_matches(img1, kp1, img2, kp2, matches[:10])
    
    # Check that result is an image
    assert isinstance(match_img, np.ndarray)
    
    # Check that result is larger than inputs (side by side images)
    assert match_img.shape[1] > img1.shape[1]


def test_empty_matches(feature_matcher, test_images):
    """Test handling of empty matches."""
    img1, img2 = test_images
    
    # Detect features in both images
    kp1, desc1 = feature_matcher.detect_features(img1)
    kp2, desc2 = feature_matcher.detect_features(img2)
    
    # Get matched points with empty matches
    points1, points2 = feature_matcher.get_matched_points(kp1, kp2, [])
    
    # Check that empty arrays are returned
    assert points1.shape[0] == 0
    assert points2.shape[0] == 0
    
    # Filter empty matches
    filtered_matches = feature_matcher.filter_matches_by_geometry(
        kp1, kp2, [], method='fundamental')
    
    # Check that empty list is returned
    assert len(filtered_matches) == 0


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 