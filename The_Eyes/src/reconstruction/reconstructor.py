#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
3D Reconstructor Module for The Eyes

This module handles 3D reconstruction from matched features.
"""

import cv2
import numpy as np
import open3d as o3d
import logging
from typing import Dict, List, Optional, Tuple, Union, Any

from src.utils.exceptions import ReconstructionError


class Reconstructor:
    """Class for 3D reconstruction from matched features."""
    
    def __init__(self, config: Dict):
        """
        Initialize reconstructor with configuration.
        
        Args:
            config: Dictionary containing reconstruction parameters
        """
        self.config = config
        self.logger = logging.getLogger("the_eyes.reconstructor")
        
    def reconstruct(self, features: Dict[str, Any]) -> Tuple[o3d.geometry.PointCloud, Optional[o3d.geometry.TriangleMesh]]:
        """
        Reconstruct 3D model from matched features.
        
        Args:
            features: Dictionary containing keypoints, descriptors, and matches
            
        Returns:
            Tuple of (point_cloud, mesh)
            
        Raises:
            ReconstructionError: If reconstruction fails
        """
        try:
            # Get camera IDs
            camera_ids = list(features['keypoints'].keys())
            
            if len(camera_ids) < 2:
                raise ReconstructionError("Need at least two cameras for reconstruction")
                
            # Create point cloud from triangulated points
            point_cloud = self.create_point_cloud(features)
            
            # Create mesh from point cloud
            mesh = self.create_mesh(point_cloud)
            
            return point_cloud, mesh
            
        except Exception as e:
            self.logger.error(f"Error during 3D reconstruction: {e}")
            raise ReconstructionError(f"3D reconstruction failed: {e}")
            
    def create_point_cloud(self, features: Dict[str, Any]) -> o3d.geometry.PointCloud:
        """
        Create point cloud from matched features.
        
        Args:
            features: Dictionary containing keypoints, descriptors, and matches
            
        Returns:
            Point cloud object
            
        Raises:
            ReconstructionError: If point cloud creation fails
        """
        try:
            # Create empty point cloud
            point_cloud = o3d.geometry.PointCloud()
            points = []
            colors = []
            
            # Get camera IDs
            camera_ids = list(features['keypoints'].keys())
            
            # Triangulate points for each pair of cameras
            for i in range(len(camera_ids)):
                for j in range(i+1, len(camera_ids)):
                    cam_id1 = camera_ids[i]
                    cam_id2 = camera_ids[j]
                    
                    match_key = (cam_id1, cam_id2)
                    if match_key not in features['matches'] or not features['matches'][match_key]:
                        self.logger.warning(f"No matches between cameras {cam_id1} and {cam_id2}")
                        continue
                        
                    # Get matched points
                    kp1 = features['keypoints'][cam_id1]
                    kp2 = features['keypoints'][cam_id2]
                    matches = features['matches'][match_key]
                    
                    # Get coordinates of matched points
                    points1 = np.float32([kp1[m.queryIdx].pt for m in matches])
                    points2 = np.float32([kp2[m.trainIdx].pt for m in matches])
                    
                    # Triangulate points
                    triangulated_points = self.triangulate_points(points1, points2, cam_id1, cam_id2)
                    
                    if triangulated_points is None or len(triangulated_points) == 0:
                        self.logger.warning(f"Failed to triangulate points between cameras {cam_id1} and {cam_id2}")
                        continue
                        
                    # Add to point cloud
                    points.extend(triangulated_points)
                    
                    # Add colors (for visualization)
                    for _ in range(len(triangulated_points)):
                        # Use a default color (can be improved by sampling from images)
                        colors.append([0.5, 0.5, 0.5])
                        
            # Create Open3D point cloud
            point_cloud.points = o3d.utility.Vector3dVector(np.array(points))
            point_cloud.colors = o3d.utility.Vector3dVector(np.array(colors))
            
            # Remove outliers
            point_cloud, _ = point_cloud.remove_statistical_outlier(
                nb_neighbors=20,
                std_ratio=2.0
            )
            
            return point_cloud
            
        except Exception as e:
            self.logger.error(f"Error creating point cloud: {e}")
            raise ReconstructionError(f"Point cloud creation failed: {e}")
            
    def triangulate_points(self, points1: np.ndarray, points2: np.ndarray, 
                          cam_id1: str, cam_id2: str) -> List[List[float]]:
        """
        Triangulate 3D points from 2D correspondences.
        
        Args:
            points1: 2D points from first camera
            points2: 2D points from second camera
            cam_id1: ID of first camera
            cam_id2: ID of second camera
            
        Returns:
            List of 3D points
            
        Raises:
            ReconstructionError: If triangulation fails
        """
        try:
            # In a real implementation, we would use actual camera matrices from calibration
            # Here we use a simplified approach with dummy projection matrices
            # These would normally come from camera calibration data
            
            # Dummy projection matrices (for demonstration purposes)
            # In a real implementation, these would come from the camera calibration
            P1 = np.array([[1, 0, 0, 0],
                          [0, 1, 0, 0],
                          [0, 0, 1, 0]], dtype=np.float32)  # First camera is at origin
                          
            P2 = np.array([[1, 0, 0, -100],  # Second camera is 100 units to the left
                          [0, 1, 0, 0],
                          [0, 0, 1, 0]], dtype=np.float32)
                          
            # Triangulate points
            triangulation_method = self.config.get('triangulation', 'opencv')
            
            if triangulation_method == 'opencv':
                # OpenCV triangulation
                points_4d = cv2.triangulatePoints(P1, P2, points1.T, points2.T)
                
                # Convert from homogeneous coordinates to 3D
                points_3d = []
                for i in range(points_4d.shape[1]):
                    x = points_4d[0, i] / points_4d[3, i]
                    y = points_4d[1, i] / points_4d[3, i]
                    z = points_4d[2, i] / points_4d[3, i]
                    
                    # Check if point is within depth limits
                    min_depth = self.config.get('min_depth', 0.1)
                    max_depth = self.config.get('max_depth', 10.0)
                    
                    if min_depth <= z <= max_depth:
                        points_3d.append([x, y, z])
                        
                return points_3d
                
            else:
                # Direct Linear Transformation (DLT) method
                points_3d = []
                for i in range(len(points1)):
                    x1, y1 = points1[i]
                    x2, y2 = points2[i]
                    
                    # Construct DLT matrix
                    A = np.zeros((4, 4))
                    A[0] = x1 * P1[2] - P1[0]
                    A[1] = y1 * P1[2] - P1[1]
                    A[2] = x2 * P2[2] - P2[0]
                    A[3] = y2 * P2[2] - P2[1]
                    
                    # Solve for the 3D point (using SVD)
                    _, _, Vt = np.linalg.svd(A)
                    X = Vt[-1]
                    
                    # Convert to non-homogeneous coordinates
                    X = X / X[3]
                    
                    # Check if point is within depth limits
                    min_depth = self.config.get('min_depth', 0.1)
                    max_depth = self.config.get('max_depth', 10.0)
                    
                    if min_depth <= X[2] <= max_depth:
                        points_3d.append([X[0], X[1], X[2]])
                        
                return points_3d
                
        except Exception as e:
            self.logger.error(f"Error triangulating points: {e}")
            raise ReconstructionError(f"Point triangulation failed: {e}")
            
    def create_mesh(self, point_cloud: o3d.geometry.PointCloud) -> Optional[o3d.geometry.TriangleMesh]:
        """
        Create mesh from point cloud.
        
        Args:
            point_cloud: Input point cloud
            
        Returns:
            Triangle mesh object or None if meshing fails
            
        Raises:
            ReconstructionError: If mesh creation fails
        """
        try:
            if len(point_cloud.points) < 10:
                self.logger.warning("Not enough points for mesh creation")
                return None
                
            # Estimate normals if not already computed
            point_cloud.estimate_normals(
                search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
                
            # Orient normals consistently
            point_cloud.orient_normals_consistent_tangent_plane(k=20)
            
            mesh_method = self.config.get('mesh_method', 'poisson').lower()
            
            if mesh_method == 'poisson':
                # Poisson surface reconstruction
                mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
                    point_cloud, depth=self.config.get('mesh_resolution', 8), width=0, scale=1.1, linear_fit=False)
                    
                # Remove low density vertices
                vertices_to_remove = densities < np.quantile(densities, 0.1)
                mesh.remove_vertices_by_mask(vertices_to_remove)
                
                return mesh
                
            elif mesh_method == 'alpha_shape':
                # Alpha shape reconstruction
                alpha = 0.03  # Alpha value can be adjusted
                mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(point_cloud, alpha)
                
                # Clean mesh
                mesh.compute_vertex_normals()
                
                return mesh
                
            else:
                # Ball pivoting algorithm
                distances = point_cloud.compute_nearest_neighbor_distance()
                avg_distance = np.mean(distances)
                radius = 3 * avg_distance
                
                mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
                    point_cloud, o3d.utility.DoubleVector([radius, radius * 2]))
                    
                # Clean mesh
                mesh.compute_vertex_normals()
                
                return mesh
                
        except Exception as e:
            self.logger.error(f"Error creating mesh: {e}")
            # Return None instead of raising exception to allow visualization of point cloud
            return None
            
    def refine_reconstruction(self, point_cloud: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
        """
        Refine reconstruction using bundle adjustment.
        
        Args:
            point_cloud: Input point cloud
            
        Returns:
            Refined point cloud
            
        Note:
            This is a placeholder. Real bundle adjustment would be more complex.
        """
        # This would typically involve nonlinear optimization to minimize reprojection errors
        # For simplicity, we just return the original point cloud
        self.logger.info("Bundle adjustment is not implemented in this version")
        return point_cloud 