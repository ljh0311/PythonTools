#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for the Image Processor module.
"""

import cv2
import numpy as np
import os
import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.image_processing.processor import ImageProcessor
from src.utils.exceptions import ImageProcessingError


@pytest.fixture
def test_image():
    """Create a simple test image."""
    # Create a 100x100 test image with some patterns
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Add a red square
    img[20:40, 20:40] = [0, 0, 255]
    
    # Add a green circle
    cv2.circle(img, (70, 70), 15, (0, 255, 0), -1)
    
    # Add some noise
    noise = np.random.randint(0, 30, (100, 100, 3), dtype=np.uint8)
    img = cv2.add(img, noise)
    
    return img


@pytest.fixture
def processor_config():
    """Create a sample processor configuration."""
    return {
        'resize': {
            'width': 50,
            'height': 50
        },
        'grayscale': True,
        'blur': {
            'kernel_size': 3
        },
        'clahe': {
            'clip_limit': 2.0,
            'tile_grid_size': (8, 8)
        }
    }


@pytest.fixture
def image_processor(processor_config):
    """Create an ImageProcessor instance with test config."""
    return ImageProcessor(processor_config)


def test_processor_initialization(processor_config):
    """Test that processor initializes correctly with config."""
    processor = ImageProcessor(processor_config)
    assert processor.config == processor_config
    assert processor.logger is not None


def test_process_resize(image_processor, test_image):
    """Test image resizing."""
    processed = image_processor.process(test_image)
    
    # Check dimensions
    assert processed.shape[:2] == (50, 50)


def test_process_grayscale(image_processor, test_image):
    """Test conversion to grayscale."""
    processed = image_processor.process(test_image)
    
    # Check that result is grayscale (2D)
    assert len(processed.shape) == 2
    

def test_process_without_grayscale(processor_config, test_image):
    """Test processing without grayscale conversion."""
    # Modify config to disable grayscale
    config = processor_config.copy()
    config['grayscale'] = False
    
    processor = ImageProcessor(config)
    processed = processor.process(test_image)
    
    # Check that result is still color (3D)
    assert len(processed.shape) == 3


def test_process_batch(image_processor, test_image):
    """Test batch processing of multiple images."""
    # Create a batch of images
    images = {
        'cam1': test_image,
        'cam2': test_image.copy(),
    }
    
    processed = image_processor.process_batch(images)
    
    # Check that all images were processed
    assert len(processed) == 2
    assert 'cam1' in processed
    assert 'cam2' in processed
    
    # Check that processing was applied
    assert processed['cam1'].shape[:2] == (50, 50)
    assert len(processed['cam1'].shape) == 2  # Grayscale


def test_process_error_handling():
    """Test error handling during processing."""
    processor = ImageProcessor({})
    
    # Test with invalid image
    with pytest.raises(ImageProcessingError):
        processor.process("not an image")


def test_undistort(image_processor, test_image):
    """Test image undistortion."""
    # Create dummy calibration data
    camera_matrix = np.array([
        [100, 0, 50],
        [0, 100, 50],
        [0, 0, 1]
    ], dtype=np.float32)
    
    dist_coeffs = np.zeros(5, dtype=np.float32)
    
    # Test undistort
    undistorted = image_processor.undistort(test_image, camera_matrix, dist_coeffs)
    
    # Since our dist_coeffs are zeros, the image should be unchanged in shape
    assert undistorted.shape == test_image.shape
    

def test_enhance_contrast(image_processor, test_image):
    """Test contrast enhancement."""
    # Convert to grayscale first
    gray = cv2.cvtColor(test_image, cv2.COLOR_BGR2GRAY)
    
    # Enhance contrast
    enhanced = image_processor.enhance_contrast(gray)
    
    # Check that result is still grayscale
    assert len(enhanced.shape) == 2
    
    # Test with color image
    enhanced_color = image_processor.enhance_contrast(test_image)
    
    # Check that result is still color
    assert len(enhanced_color.shape) == 3


def test_detect_edges(image_processor, test_image):
    """Test edge detection."""
    edges = image_processor.detect_edges(test_image)
    
    # Check that result is grayscale
    assert len(edges.shape) == 2
    
    # Edge image should be binary (mostly 0s with some 255s)
    assert np.all((edges == 0) | (edges == 255))


def test_apply_mask(image_processor, test_image):
    """Test applying a mask to an image."""
    # Create a simple mask (circle in the center)
    mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 30, 255, -1)
    
    # Apply mask
    masked = image_processor.apply_mask(test_image, mask)
    
    # Check that result has same shape as input
    assert masked.shape == test_image.shape
    
    # Check that pixels outside mask are black
    assert np.all(masked[0, 0] == [0, 0, 0])  # Corner should be masked out


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 