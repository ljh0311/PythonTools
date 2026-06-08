#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Command-line interface for The Eyes visualization tools.

This module provides a command-line interface for visualizing camera views,
feature matches, and 3D reconstruction results from The Eyes project.
"""

import argparse
import cv2
import glob
import json
import logging
import numpy as np
import os
import sys
import yaml

# Add the project directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import open3d as o3d
from typing import Dict, List, Optional, Tuple, Union, Any

from src.visualization.visualizer import Visualizer
from src.utils.config import load_config
from src.utils.logger import setup_logger


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="The Eyes - Visualization Tools")
    
    # General options
    parser.add_argument("-c", "--config", default="../config/config.json", 
                       help="Path to configuration file")
    parser.add_argument("-o", "--output", default="../output/visualization",
                       help="Output directory for visualizations")
    parser.add_argument("--debug", action="store_true", 
                       help="Enable debug logging")
    parser.add_argument("--non-interactive", action="store_true",
                       help="Run in non-interactive mode (save visualizations without displaying)")
    
    # Commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Camera views command
    camera_parser = subparsers.add_parser("cameras", help="Visualize camera views")
    camera_parser.add_argument("--images", nargs="+", required=True,
                             help="Paths to camera images")
    camera_parser.add_argument("--labels", nargs="+",
                             help="Labels for camera images")
    
    # Feature matching command
    match_parser = subparsers.add_parser("matches", help="Visualize feature matches")
    match_parser.add_argument("--image1", required=True,
                            help="Path to first image")
    match_parser.add_argument("--image2", required=True,
                            help="Path to second image")
    match_parser.add_argument("--matches", required=True,
                            help="Path to matches JSON file")
    
    # 3D model visualization command
    model_parser = subparsers.add_parser("model", help="Visualize 3D model")
    model_parser.add_argument("--point-cloud", required=True,
                            help="Path to point cloud file (.ply)")
    model_parser.add_argument("--mesh",
                            help="Path to mesh file (.ply, .obj)")
    
    # Image comparison command
    compare_parser = subparsers.add_parser("compare", help="Compare multiple images")
    compare_parser.add_argument("--images", nargs="+", required=True,
                              help="Paths to images to compare")
    compare_parser.add_argument("--labels", nargs="+",
                              help="Labels for images")
    compare_parser.add_argument("--title", default="Image Comparison",
                              help="Title for comparison")
    
    # Progress visualization command
    progress_parser = subparsers.add_parser("progress", help="Visualize reconstruction progress")
    progress_parser.add_argument("--data", required=True,
                               help="Path to progress data JSON file")
    
    return parser.parse_args()


def load_image(path: str) -> np.ndarray:
    """Load an image from file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image file not found: {path}")
        
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Failed to load image: {path}")
        
    return img


def load_point_cloud(path: str) -> o3d.geometry.PointCloud:
    """Load a point cloud from file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Point cloud file not found: {path}")
        
    try:
        return o3d.io.read_point_cloud(path)
    except Exception as e:
        raise ValueError(f"Failed to load point cloud: {e}")


def load_mesh(path: str) -> o3d.geometry.TriangleMesh:
    """Load a mesh from file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Mesh file not found: {path}")
        
    try:
        return o3d.io.read_triangle_mesh(path)
    except Exception as e:
        raise ValueError(f"Failed to load mesh: {e}")


def load_matches(path: str) -> Tuple[List, List, List]:
    """
    Load keypoints and matches from JSON file.
    
    Returns:
        Tuple of (keypoints1, keypoints2, matches)
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Matches file not found: {path}")
        
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            
        # Convert keypoints dictionary to objects
        class KeyPoint:
            def __init__(self, x, y):
                self.pt = (x, y)
                
        class DMatch:
            def __init__(self, queryIdx, trainIdx, distance):
                self.queryIdx = queryIdx
                self.trainIdx = trainIdx
                self.distance = distance
        
        keypoints1 = [KeyPoint(kp[0], kp[1]) for kp in data['keypoints1']]
        keypoints2 = [KeyPoint(kp[0], kp[1]) for kp in data['keypoints2']]
        matches = [DMatch(m[0], m[1], m[2]) for m in data['matches']]
        
        return keypoints1, keypoints2, matches
        
    except Exception as e:
        raise ValueError(f"Failed to load matches: {e}")


def load_progress_data(path: str) -> Dict:
    """Load reconstruction progress data from JSON file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Progress data file not found: {path}")
        
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to load progress data: {e}")


def visualize_cameras(args, visualizer: Visualizer) -> None:
    """Visualize camera views."""
    logger = logging.getLogger("the_eyes.visualize.cameras")
    
    try:
        # Load images
        images = {}
        for i, path in enumerate(args.images):
            label = args.labels[i] if args.labels and i < len(args.labels) else f"Camera {i}"
            images[label] = load_image(path)
            
        # Show camera views
        logger.info(f"Visualizing {len(images)} camera views")
        fig = visualizer.show_camera_views(images)
        
        # Save figure if configured
        if args.non_interactive or visualizer.config.get('save_visualizations', False):
            os.makedirs(args.output, exist_ok=True)
            output_path = os.path.join(args.output, "camera_views.png")
            fig.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved camera views to {output_path}")
            
    except Exception as e:
        logger.error(f"Error visualizing camera views: {e}")
        return 1
        
    return 0


def visualize_matches(args, visualizer: Visualizer) -> None:
    """Visualize feature matches."""
    logger = logging.getLogger("the_eyes.visualize.matches")
    
    try:
        # Load images
        img1 = load_image(args.image1)
        img2 = load_image(args.image2)
        
        # Load matches
        keypoints1, keypoints2, matches = load_matches(args.matches)
        
        # Show matches
        logger.info(f"Visualizing {len(matches)} feature matches")
        fig = visualizer.show_feature_matches(img1, keypoints1, img2, keypoints2, matches)
        
        # Save figure if configured
        if args.non_interactive or visualizer.config.get('save_visualizations', False):
            os.makedirs(args.output, exist_ok=True)
            output_path = os.path.join(args.output, "feature_matches.png")
            fig.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved feature matches to {output_path}")
            
    except Exception as e:
        logger.error(f"Error visualizing feature matches: {e}")
        return 1
        
    return 0


def visualize_model(args, visualizer: Visualizer) -> None:
    """Visualize 3D model."""
    logger = logging.getLogger("the_eyes.visualize.model")
    
    try:
        # Load point cloud
        point_cloud = load_point_cloud(args.point_cloud)
        
        # Load mesh if specified
        mesh = None
        if args.mesh:
            mesh = load_mesh(args.mesh)
        
        # Show point cloud and mesh
        logger.info(f"Visualizing 3D model with {len(point_cloud.points)} points")
        title = "The Eyes - 3D Model Visualization"
        visualizer.show_point_cloud(point_cloud, title)
        
        # In non-interactive mode, save a screenshot
        if args.non_interactive or visualizer.config.get('save_visualizations', False):
            os.makedirs(args.output, exist_ok=True)
            output_path = os.path.join(args.output, "model.png")
            
            # Create Open3D visualizer to save screenshot
            vis = o3d.visualization.Visualizer()
            vis.create_window(visible=False)
            vis.add_geometry(point_cloud)
            if mesh:
                vis.add_geometry(mesh)
            vis.poll_events()
            vis.update_renderer()
            vis.capture_screen_image(output_path)
            vis.destroy_window()
            
            logger.info(f"Saved model visualization to {output_path}")
            
    except Exception as e:
        logger.error(f"Error visualizing 3D model: {e}")
        return 1
        
    return 0


def visualize_comparison(args, visualizer: Visualizer) -> None:
    """Visualize image comparison."""
    logger = logging.getLogger("the_eyes.visualize.compare")
    
    try:
        # Load images
        images = []
        for path in args.images:
            images.append(load_image(path))
            
        # Get labels
        if args.labels and len(args.labels) == len(images):
            labels = args.labels
        else:
            labels = [f"Image {i+1}" for i in range(len(images))]
            
        # Show comparison
        logger.info(f"Comparing {len(images)} images")
        fig = visualizer.show_comparison(images, labels, args.title)
        
        # Save figure if configured
        if args.non_interactive or visualizer.config.get('save_visualizations', False):
            os.makedirs(args.output, exist_ok=True)
            output_path = os.path.join(args.output, "image_comparison.png")
            fig.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved image comparison to {output_path}")
            
    except Exception as e:
        logger.error(f"Error visualizing image comparison: {e}")
        return 1
        
    return 0


def visualize_progress(args, visualizer: Visualizer) -> None:
    """Visualize reconstruction progress."""
    logger = logging.getLogger("the_eyes.visualize.progress")
    
    try:
        # Load progress data
        data = load_progress_data(args.data)
        
        # Show progress
        logger.info("Visualizing reconstruction progress")
        fig = visualizer.show_reconstruction_progress(data)
        
        # Save figure if configured
        if args.non_interactive or visualizer.config.get('save_visualizations', False):
            os.makedirs(args.output, exist_ok=True)
            output_path = os.path.join(args.output, "reconstruction_progress.png")
            fig.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved reconstruction progress to {output_path}")
            
    except Exception as e:
        logger.error(f"Error visualizing reconstruction progress: {e}")
        return 1
        
    return 0


def main():
    """Main entry point for the visualization CLI."""
    # Parse arguments
    args = parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logger("the_eyes.visualize", log_level)
    logger.info("Starting The Eyes Visualization Tools")
    
    # Load configuration
    try:
        config = load_config(args.config)
        
        # Override configuration with command line arguments
        config['visualization'] = config.get('visualization', {})
        config['visualization']['interactive'] = not args.non_interactive
        config['visualization']['output_dir'] = args.output
        config['visualization']['save_visualizations'] = True
        
        logger.info(f"Loaded configuration from {args.config}")
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1
    
    # Create visualizer
    visualizer = Visualizer(config['visualization'])
    
    # Run requested command
    if args.command == 'cameras':
        return visualize_cameras(args, visualizer)
    elif args.command == 'matches':
        return visualize_matches(args, visualizer)
    elif args.command == 'model':
        return visualize_model(args, visualizer)
    elif args.command == 'compare':
        return visualize_comparison(args, visualizer)
    elif args.command == 'progress':
        return visualize_progress(args, visualizer)
    else:
        logger.error("No command specified")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 