#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Visualization Module for The Eyes

This module provides specialized visualization tools for displaying
camera views, feature matches, and 3D reconstruction results.
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import open3d as o3d
import logging
from typing import Dict, List, Optional, Tuple, Union, Any
from matplotlib.figure import Figure
from matplotlib.axes import Axes

from src.utils.exceptions import RenderingError


class Visualizer:
    """Class for visualizing inputs, intermediate results, and outputs."""
    
    def __init__(self, config: Dict):
        """
        Initialize visualizer with configuration.
        
        Args:
            config: Dictionary containing visualization parameters
        """
        self.config = config
        self.logger = logging.getLogger("the_eyes.visualizer")
        self.interactive = config.get('interactive', True)
        self.output_dir = config.get('output_dir', '../output/visualization')
        self.current_figure = None
        
    def show_camera_views(self, frames: Dict[str, np.ndarray], 
                        with_keypoints: Optional[Dict[str, List]] = None) -> Figure:
        """
        Display frames from all cameras, optionally with keypoints.
        
        Args:
            frames: Dictionary of camera ID to frame
            with_keypoints: Optional dictionary of camera ID to keypoints
            
        Returns:
            Matplotlib figure object
        """
        try:
            # Determine grid size based on number of cameras
            n_cameras = len(frames)
            cols = min(3, n_cameras)
            rows = (n_cameras + cols - 1) // cols
            
            # Create figure
            fig, axes = plt.subplots(rows, cols, figsize=(4*cols, 4*rows))
            
            # Ensure axes is an array even if there's only one subplot
            if n_cameras == 1:
                axes = np.array([axes])
            elif rows == 1:
                axes = axes.reshape(1, -1)
            
            # Plot camera views
            for i, (cam_id, frame) in enumerate(frames.items()):
                row, col = i // cols, i % cols
                ax = axes[row, col] if rows > 1 else axes[col]
                
                # Convert frame to RGB if it's BGR
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                else:
                    frame_rgb = frame
                
                # Display frame
                ax.imshow(frame_rgb)
                
                # Draw keypoints if provided
                if with_keypoints and cam_id in with_keypoints:
                    kps = with_keypoints[cam_id]
                    for kp in kps:
                        ax.plot(kp.pt[0], kp.pt[1], 'ro', markersize=3)
                
                ax.set_title(f"Camera {cam_id}")
                ax.axis('off')
            
            # Hide unused subplots
            for i in range(n_cameras, rows * cols):
                row, col = i // cols, i % cols
                fig.delaxes(axes[row, col] if rows > 1 else axes[col])
            
            plt.tight_layout()
            
            # Save figure if configured
            if self.config.get('save_visualizations', False):
                fig.savefig(f"{self.output_dir}/camera_views.png", dpi=300, bbox_inches='tight')
            
            # Show figure if interactive
            if self.interactive:
                plt.show()
            else:
                plt.close(fig)
            
            self.current_figure = fig
            return fig
            
        except Exception as e:
            self.logger.error(f"Error visualizing camera views: {e}")
            raise RenderingError(f"Camera view visualization failed: {e}")
    
    def show_feature_matches(self, img1: np.ndarray, kp1: List, 
                           img2: np.ndarray, kp2: List, 
                           matches: List, title: str = "Feature Matches") -> Figure:
        """
        Display feature matches between two images.
        
        Args:
            img1: First image
            kp1: Keypoints from first image
            img2: Second image
            kp2: Keypoints from second image
            matches: List of matches
            title: Title for the visualization
            
        Returns:
            Matplotlib figure object
        """
        try:
            # Draw matches using OpenCV
            match_img = cv2.drawMatches(
                img1, kp1, img2, kp2, matches, None,
                flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
            )
            
            # Convert to RGB for matplotlib
            match_img_rgb = cv2.cvtColor(match_img, cv2.COLOR_BGR2RGB)
            
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.imshow(match_img_rgb)
            ax.set_title(f"{title} ({len(matches)} matches)")
            ax.axis('off')
            
            plt.tight_layout()
            
            # Save figure if configured
            if self.config.get('save_visualizations', False):
                filename = title.lower().replace(' ', '_')
                fig.savefig(f"{self.output_dir}/{filename}.png", dpi=300, bbox_inches='tight')
            
            # Show figure if interactive
            if self.interactive:
                plt.show()
            else:
                plt.close(fig)
            
            self.current_figure = fig
            return fig
            
        except Exception as e:
            self.logger.error(f"Error visualizing feature matches: {e}")
            raise RenderingError(f"Feature match visualization failed: {e}")
    
    def show_epipolar_lines(self, img1: np.ndarray, img2: np.ndarray, 
                          points1: np.ndarray, points2: np.ndarray, 
                          F: np.ndarray, title: str = "Epipolar Lines") -> Figure:
        """
        Display epipolar lines between two images.
        
        Args:
            img1: First image
            img2: Second image
            points1: Points in first image
            points2: Points in second image
            F: Fundamental matrix
            title: Title for the visualization
            
        Returns:
            Matplotlib figure object
        """
        try:
            # Create figure with two subplots
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
            
            # Convert images to RGB for matplotlib
            img1_rgb = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
            img2_rgb = cv2.cvtColor(img2, cv2.COLOR_BGR2RGB)
            
            # Display images
            ax1.imshow(img1_rgb)
            ax2.imshow(img2_rgb)
            
            # Plot points on first image and epipolar lines on second image
            ax1.set_title('Points in first image')
            ax2.set_title('Epipolar lines in second image')
            
            # Draw points and epipolar lines
            for i in range(len(points1)):
                # Draw point in first image
                x1, y1 = points1[i].ravel()
                ax1.plot(x1, y1, 'ro')
                
                # Compute epipolar line in second image
                line = F.dot(np.array([x1, y1, 1.0]))
                a, b, c = line
                
                # Get image dimensions
                height, width = img2.shape[:2]
                
                # Calculate line endpoints at image borders
                if abs(b) > 1e-8:
                    # Line is not horizontal
                    x_min, x_max = 0, width-1
                    y_min = -(a*x_min + c) / b
                    y_max = -(a*x_max + c) / b
                    
                    # Clip to image boundaries
                    if y_min < 0:
                        y_min = 0
                        x_min = -(b*y_min + c) / a
                    if y_min >= height:
                        y_min = height-1
                        x_min = -(b*y_min + c) / a
                    if y_max < 0:
                        y_max = 0
                        x_max = -(b*y_max + c) / a
                    if y_max >= height:
                        y_max = height-1
                        x_max = -(b*y_max + c) / a
                else:
                    # Line is horizontal
                    y_min, y_max = 0, height-1
                    x_min = x_max = -c / a
                
                # Draw epipolar line
                ax2.plot([x_min, x_max], [y_min, y_max], 'b-')
                
                # Draw corresponding point in second image
                x2, y2 = points2[i].ravel()
                ax2.plot(x2, y2, 'go')
            
            # Turn off axes
            ax1.axis('off')
            ax2.axis('off')
            
            plt.tight_layout()
            plt.suptitle(title, fontsize=16)
            plt.subplots_adjust(top=0.9)
            
            # Save figure if configured
            if self.config.get('save_visualizations', False):
                filename = title.lower().replace(' ', '_')
                fig.savefig(f"{self.output_dir}/{filename}.png", dpi=300, bbox_inches='tight')
            
            # Show figure if interactive
            if self.interactive:
                plt.show()
            else:
                plt.close(fig)
            
            self.current_figure = fig
            return fig
            
        except Exception as e:
            self.logger.error(f"Error visualizing epipolar lines: {e}")
            raise RenderingError(f"Epipolar line visualization failed: {e}")
    
    def show_point_cloud(self, point_cloud: o3d.geometry.PointCloud, 
                       title: str = "Point Cloud Visualization") -> None:
        """
        Display point cloud using Open3D.
        
        Args:
            point_cloud: Point cloud to visualize
            title: Title for the visualization window
        """
        try:
            # Create visualizer
            vis = o3d.visualization.Visualizer()
            vis.create_window(window_name=title)
            
            # Configure visualizer
            opt = vis.get_render_option()
            opt.background_color = np.array([0.1, 0.1, 0.1])
            opt.point_size = self.config.get('point_size', 2.0)
            
            # Add point cloud
            vis.add_geometry(point_cloud)
            
            # Set view control
            ctr = vis.get_view_control()
            ctr.set_zoom(0.8)
            
            # Save image if configured
            if self.config.get('save_visualizations', False):
                filename = title.lower().replace(' ', '_')
                # Poll events to render the scene
                vis.poll_events()
                vis.update_renderer()
                vis.capture_screen_image(f"{self.output_dir}/{filename}.png")
            
            # Run visualizer if interactive
            if self.interactive:
                vis.run()
            
            vis.destroy_window()
            
        except Exception as e:
            self.logger.error(f"Error visualizing point cloud: {e}")
            raise RenderingError(f"Point cloud visualization failed: {e}")
    
    def show_reconstruction_progress(self, data: Dict[str, Any], 
                                   title: str = "Reconstruction Progress") -> Figure:
        """
        Visualize reconstruction progress metrics.
        
        Args:
            data: Dictionary containing reconstruction metrics over time
            title: Title for the visualization
            
        Returns:
            Matplotlib figure object
        """
        try:
            # Ensure data has required keys
            required_keys = ['timestamps', 'num_points', 'reprojection_error']
            if not all(key in data for key in required_keys):
                self.logger.warning("Missing required keys in reconstruction progress data")
                missing = [key for key in required_keys if key not in data]
                raise RenderingError(f"Missing data for reconstruction progress: {missing}")
            
            # Create figure with multiple subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
            
            # Plot number of points
            ax1.plot(data['timestamps'], data['num_points'], 'b-o')
            ax1.set_ylabel('Number of Points')
            ax1.set_title('Point Cloud Growth')
            ax1.grid(True)
            
            # Plot reprojection error
            ax2.plot(data['timestamps'], data['reprojection_error'], 'r-o')
            ax2.set_xlabel('Time')
            ax2.set_ylabel('Reprojection Error')
            ax2.set_title('Reconstruction Accuracy')
            ax2.grid(True)
            
            # Add additional metrics if available
            if 'processing_time' in data:
                ax3 = ax1.twinx()
                ax3.plot(data['timestamps'], data['processing_time'], 'g--')
                ax3.set_ylabel('Processing Time (s)', color='g')
                ax3.tick_params(axis='y', labelcolor='g')
            
            plt.tight_layout()
            plt.suptitle(title, fontsize=16)
            plt.subplots_adjust(top=0.9)
            
            # Save figure if configured
            if self.config.get('save_visualizations', False):
                filename = title.lower().replace(' ', '_')
                fig.savefig(f"{self.output_dir}/{filename}.png", dpi=300, bbox_inches='tight')
            
            # Show figure if interactive
            if self.interactive:
                plt.show()
            else:
                plt.close(fig)
            
            self.current_figure = fig
            return fig
            
        except Exception as e:
            self.logger.error(f"Error visualizing reconstruction progress: {e}")
            raise RenderingError(f"Reconstruction progress visualization failed: {e}")
    
    def show_comparison(self, images: List[np.ndarray], titles: List[str], 
                      title: str = "Image Comparison") -> Figure:
        """
        Display multiple images side by side for comparison.
        
        Args:
            images: List of images to compare
            titles: List of titles for each image
            title: Main title for the visualization
            
        Returns:
            Matplotlib figure object
        """
        try:
            # Determine grid size
            n_images = len(images)
            cols = min(4, n_images)
            rows = (n_images + cols - 1) // cols
            
            # Create figure
            fig, axes = plt.subplots(rows, cols, figsize=(4*cols, 4*rows))
            
            # Ensure axes is an array
            if n_images == 1:
                axes = np.array([axes])
            elif rows == 1:
                axes = axes.reshape(1, -1)
            
            # Plot images
            for i, (img, img_title) in enumerate(zip(images, titles)):
                row, col = i // cols, i % cols
                ax = axes[row, col] if rows > 1 else axes[col]
                
                # Convert image to RGB if it's BGR
                if len(img.shape) == 3 and img.shape[2] == 3:
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                else:
                    img_rgb = img
                
                # Display image
                ax.imshow(img_rgb)
                ax.set_title(img_title)
                ax.axis('off')
            
            # Hide unused subplots
            for i in range(n_images, rows * cols):
                row, col = i // cols, i % cols
                fig.delaxes(axes[row, col] if rows > 1 else axes[col])
            
            plt.tight_layout()
            plt.suptitle(title, fontsize=16)
            plt.subplots_adjust(top=0.9)
            
            # Save figure if configured
            if self.config.get('save_visualizations', False):
                filename = title.lower().replace(' ', '_')
                fig.savefig(f"{self.output_dir}/{filename}.png", dpi=300, bbox_inches='tight')
            
            # Show figure if interactive
            if self.interactive:
                plt.show()
            else:
                plt.close(fig)
            
            self.current_figure = fig
            return fig
            
        except Exception as e:
            self.logger.error(f"Error visualizing image comparison: {e}")
            raise RenderingError(f"Image comparison visualization failed: {e}")
    
    def save_current_figure(self, filename: str) -> None:
        """
        Save the current figure to a file.
        
        Args:
            filename: Name of the file to save
            
        Raises:
            RenderingError: If saving fails
        """
        try:
            if self.current_figure is None:
                self.logger.warning("No current figure to save")
                return
                
            self.current_figure.savefig(filename, dpi=300, bbox_inches='tight')
            self.logger.info(f"Saved figure to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving figure: {e}")
            raise RenderingError(f"Figure saving failed: {e}") 