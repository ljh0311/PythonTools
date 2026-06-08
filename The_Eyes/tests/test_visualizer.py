#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for the Visualizer module.
"""

import cv2
import numpy as np
import os
import pytest
import matplotlib.pyplot as plt
from unittest.mock import patch, MagicMock

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.visualization.visualizer import Visualizer
from src.utils.exceptions import RenderingError


@pytest.fixture
def test_images():
    """Create test images for visualization."""
    # Create a 100x100 test image with a pattern
    img1 = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(img1, (20, 20), (80, 80), (0, 0, 255), -1)
    
    # Create a second image
    img2 = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.circle(img2, (50, 50), 30, (0, 255, 0), -1)
    
    return (img1, img2)


@pytest.fixture
def mock_point_cloud():
    """Create a mock Open3D point cloud."""
    mock_pc = MagicMock()
    mock_pc.points = MagicMock()
    return mock_pc


@pytest.fixture
def visualizer_config():
    """Create a sample visualizer configuration."""
    return {
        'interactive': False,  # Non-interactive for testing
        'output_dir': 'test_output',
        'save_visualizations': False,
        'point_size': 2.0
    }


@pytest.fixture
def visualizer(visualizer_config):
    """Create a Visualizer instance with test config."""
    return Visualizer(visualizer_config)


def test_visualizer_initialization(visualizer_config):
    """Test that visualizer initializes correctly with config."""
    visualizer = Visualizer(visualizer_config)
    assert visualizer.config == visualizer_config
    assert visualizer.logger is not None
    assert visualizer.interactive == False
    assert visualizer.output_dir == 'test_output'


def test_show_camera_views(visualizer, test_images):
    """Test showing camera views."""
    img1, img2 = test_images
    
    # Create frames dictionary
    frames = {
        'cam1': img1,
        'cam2': img2
    }
    
    # Mock plt.show to avoid displaying
    with patch.object(plt, 'show') as mock_show:
        # Test show_camera_views
        fig = visualizer.show_camera_views(frames)
        
        # Check that figure was created
        assert fig is not None
        
        # Check that current_figure was set
        assert visualizer.current_figure is fig
        
        # Check that plt.show was not called (non-interactive)
        mock_show.assert_not_called()


def test_show_camera_views_with_keypoints(visualizer, test_images):
    """Test showing camera views with keypoints."""
    img1, img2 = test_images
    
    # Create frames dictionary
    frames = {
        'cam1': img1,
        'cam2': img2
    }
    
    # Create mock keypoints
    class MockKeypoint:
        def __init__(self, x, y):
            self.pt = (x, y)
    
    keypoints = {
        'cam1': [MockKeypoint(30, 30), MockKeypoint(70, 70)],
        'cam2': [MockKeypoint(40, 40), MockKeypoint(60, 60)]
    }
    
    # Mock plt.show to avoid displaying
    with patch.object(plt, 'show') as mock_show:
        # Test show_camera_views with keypoints
        fig = visualizer.show_camera_views(frames, with_keypoints=keypoints)
        
        # Check that figure was created
        assert fig is not None
        
        # Check that current_figure was set
        assert visualizer.current_figure is fig
        
        # Check that plt.show was not called (non-interactive)
        mock_show.assert_not_called()


def test_show_feature_matches(visualizer, test_images):
    """Test showing feature matches."""
    img1, img2 = test_images
    
    # Create mock keypoints and matches
    class MockKeypoint:
        def __init__(self, x, y):
            self.pt = (x, y)
    
    class MockDMatch:
        def __init__(self, q_idx, t_idx, dist):
            self.queryIdx = q_idx
            self.trainIdx = t_idx
            self.distance = dist
    
    kp1 = [MockKeypoint(30, 30), MockKeypoint(70, 70)]
    kp2 = [MockKeypoint(40, 40), MockKeypoint(60, 60)]
    matches = [MockDMatch(0, 0, 10.0), MockDMatch(1, 1, 15.0)]
    
    # Patch cv2.drawMatches to return a dummy image
    with patch.object(cv2, 'drawMatches', return_value=np.zeros((100, 200, 3))), \
         patch.object(plt, 'show') as mock_show:
        
        # Test show_feature_matches
        fig = visualizer.show_feature_matches(img1, kp1, img2, kp2, matches)
        
        # Check that figure was created
        assert fig is not None
        
        # Check that current_figure was set
        assert visualizer.current_figure is fig
        
        # Check that plt.show was not called (non-interactive)
        mock_show.assert_not_called()


def test_show_epipolar_lines(visualizer, test_images):
    """Test showing epipolar lines."""
    img1, img2 = test_images
    
    # Create mock points and fundamental matrix
    points1 = np.array([[30, 30], [70, 70]])
    points2 = np.array([[40, 40], [60, 60]])
    F = np.array([[0.01, 0, -0.2], [0, 0.01, -0.1], [-0.2, -0.1, 1]])
    
    # Mock plt.show to avoid displaying
    with patch.object(plt, 'show') as mock_show:
        # Test show_epipolar_lines
        fig = visualizer.show_epipolar_lines(img1, img2, points1, points2, F)
        
        # Check that figure was created
        assert fig is not None
        
        # Check that current_figure was set
        assert visualizer.current_figure is fig
        
        # Check that plt.show was not called (non-interactive)
        mock_show.assert_not_called()


def test_show_point_cloud(visualizer, mock_point_cloud):
    """Test showing point cloud."""
    # Mock Open3D visualization
    with patch('open3d.visualization.Visualizer') as MockVisualizer:
        # Setup mock visualizer
        mock_vis = MagicMock()
        MockVisualizer.return_value = mock_vis
        
        mock_vis.create_window.return_value = None
        mock_vis.get_render_option.return_value = MagicMock()
        mock_vis.add_geometry.return_value = None
        mock_vis.get_view_control.return_value = MagicMock()
        mock_vis.poll_events.return_value = None
        mock_vis.update_renderer.return_value = None
        mock_vis.capture_screen_image.return_value = None
        mock_vis.run.return_value = None
        mock_vis.destroy_window.return_value = None
        
        # Test show_point_cloud
        visualizer.show_point_cloud(mock_point_cloud)
        
        # Check that visualization was created
        mock_vis.create_window.assert_called_once()
        mock_vis.add_geometry.assert_called_once_with(mock_point_cloud)
        
        # Since interactive is False, run should not be called
        mock_vis.run.assert_not_called()
        
        # destroy_window should be called
        mock_vis.destroy_window.assert_called_once()


def test_show_reconstruction_progress(visualizer):
    """Test showing reconstruction progress."""
    # Create sample progress data
    data = {
        'timestamps': [0, 1, 2, 3, 4],
        'num_points': [100, 200, 300, 400, 500],
        'reprojection_error': [0.5, 0.4, 0.3, 0.25, 0.2],
        'processing_time': [0.1, 0.15, 0.2, 0.25, 0.3]
    }
    
    # Mock plt.show to avoid displaying
    with patch.object(plt, 'show') as mock_show:
        # Test show_reconstruction_progress
        fig = visualizer.show_reconstruction_progress(data)
        
        # Check that figure was created
        assert fig is not None
        
        # Check that current_figure was set
        assert visualizer.current_figure is fig
        
        # Check that plt.show was not called (non-interactive)
        mock_show.assert_not_called()
        
        # Test with missing data
        with pytest.raises(RenderingError):
            visualizer.show_reconstruction_progress({'timestamps': [0, 1]})


def test_show_comparison(visualizer, test_images):
    """Test showing image comparison."""
    img1, img2 = test_images
    
    # Create images and titles
    images = [img1, img2, img1, img2]
    titles = ['Image 1', 'Image 2', 'Image 3', 'Image 4']
    
    # Mock plt.show to avoid displaying
    with patch.object(plt, 'show') as mock_show:
        # Test show_comparison
        fig = visualizer.show_comparison(images, titles)
        
        # Check that figure was created
        assert fig is not None
        
        # Check that current_figure was set
        assert visualizer.current_figure is fig
        
        # Check that plt.show was not called (non-interactive)
        mock_show.assert_not_called()


def test_save_current_figure(visualizer, test_images):
    """Test saving current figure."""
    img1, img2 = test_images
    
    # Create frames dictionary
    frames = {
        'cam1': img1,
        'cam2': img2
    }
    
    # Create a figure first
    with patch.object(plt, 'show'):
        fig = visualizer.show_camera_views(frames)
    
    # Mock savefig
    with patch.object(fig, 'savefig') as mock_savefig:
        # Test save_current_figure
        visualizer.save_current_figure('test.png')
        
        # Check that savefig was called
        mock_savefig.assert_called_once()
        
        # Test with no current figure
        visualizer.current_figure = None
        visualizer.save_current_figure('test2.png')
        
        # Check that savefig was not called again
        assert mock_savefig.call_count == 1


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 