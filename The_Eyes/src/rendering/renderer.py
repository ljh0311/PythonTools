#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Renderer Module for The Eyes

This module handles visualization and export of 3D models.
"""

import numpy as np
import open3d as o3d
import logging
import os
from typing import Dict, List, Optional, Tuple, Union, Any

from src.utils.exceptions import RenderingError


class Renderer:
    """Class for visualizing and exporting 3D models."""
    
    def __init__(self, config: Dict):
        """
        Initialize renderer with configuration.
        
        Args:
            config: Dictionary containing rendering parameters
        """
        self.config = config
        self.logger = logging.getLogger("the_eyes.renderer")
        
    def render(self, point_cloud: o3d.geometry.PointCloud, 
              mesh: Optional[o3d.geometry.TriangleMesh], 
              output_path: str) -> None:
        """
        Render and save 3D model.
        
        Args:
            point_cloud: Point cloud to render
            mesh: Mesh to render (optional)
            output_path: Path to save the rendered model
            
        Raises:
            RenderingError: If rendering fails
        """
        try:
            # Save point cloud
            pc_path = output_path.replace('.ply', '_pc.ply')
            self.save_point_cloud(point_cloud, pc_path)
            
            # Save mesh if available
            if mesh is not None:
                mesh_path = output_path.replace('.ply', '_mesh.ply')
                self.save_mesh(mesh, mesh_path)
                
            self.logger.info(f"Saved models to {os.path.dirname(output_path)}")
            
        except Exception as e:
            self.logger.error(f"Error rendering model: {e}")
            raise RenderingError(f"Model rendering failed: {e}")
            
    def visualize(self, point_cloud: o3d.geometry.PointCloud, 
                 mesh: Optional[o3d.geometry.TriangleMesh]) -> None:
        """
        Visualize 3D model interactively.
        
        Args:
            point_cloud: Point cloud to visualize
            mesh: Mesh to visualize (optional)
            
        Raises:
            RenderingError: If visualization fails
        """
        try:
            # Create visualizer
            vis = o3d.visualization.Visualizer()
            vis.create_window(window_name="The Eyes - 3D Reconstruction")
            
            # Configure visualizer
            opt = vis.get_render_option()
            opt.background_color = np.array([0.1, 0.1, 0.1])
            opt.point_size = self.config.get('point_size', 2.0)
            
            # Add geometries
            point_color = self.config.get('point_cloud_color', [1.0, 0.0, 0.0])
            if isinstance(point_color, list) and len(point_color) == 3:
                colored_pc = o3d.geometry.PointCloud()
                colored_pc.points = point_cloud.points
                if len(point_cloud.points) > 0:
                    colors = np.array([point_color for _ in range(len(point_cloud.points))])
                    colored_pc.colors = o3d.utility.Vector3dVector(colors)
                vis.add_geometry(colored_pc)
            else:
                vis.add_geometry(point_cloud)
                
            if mesh is not None:
                vis.add_geometry(mesh)
                
            # Set view control
            ctr = vis.get_view_control()
            ctr.set_zoom(0.8)
            
            # Run visualizer
            vis.run()
            vis.destroy_window()
            
        except Exception as e:
            self.logger.error(f"Error visualizing model: {e}")
            raise RenderingError(f"Model visualization failed: {e}")
            
    def save_point_cloud(self, point_cloud: o3d.geometry.PointCloud, output_path: str) -> None:
        """
        Save point cloud to file.
        
        Args:
            point_cloud: Point cloud to save
            output_path: Path to save the point cloud
            
        Raises:
            RenderingError: If saving fails
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save point cloud
            o3d.io.write_point_cloud(output_path, point_cloud)
            self.logger.info(f"Saved point cloud to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving point cloud: {e}")
            raise RenderingError(f"Point cloud saving failed: {e}")
            
    def save_mesh(self, mesh: o3d.geometry.TriangleMesh, output_path: str) -> None:
        """
        Save mesh to file.
        
        Args:
            mesh: Mesh to save
            output_path: Path to save the mesh
            
        Raises:
            RenderingError: If saving fails
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save mesh
            o3d.io.write_triangle_mesh(output_path, mesh)
            self.logger.info(f"Saved mesh to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving mesh: {e}")
            raise RenderingError(f"Mesh saving failed: {e}")
            
    def create_screenshot(self, point_cloud: o3d.geometry.PointCloud, 
                         mesh: Optional[o3d.geometry.TriangleMesh], 
                         output_path: str) -> None:
        """
        Create a screenshot of the 3D model.
        
        Args:
            point_cloud: Point cloud to visualize
            mesh: Mesh to visualize (optional)
            output_path: Path to save the screenshot
            
        Raises:
            RenderingError: If screenshot creation fails
        """
        try:
            # Create visualizer
            vis = o3d.visualization.Visualizer()
            vis.create_window(visible=False)
            
            # Configure visualizer
            opt = vis.get_render_option()
            opt.background_color = np.array([0.1, 0.1, 0.1])
            opt.point_size = self.config.get('point_size', 2.0)
            
            # Add geometries
            vis.add_geometry(point_cloud)
            if mesh is not None:
                vis.add_geometry(mesh)
                
            # Set view control
            ctr = vis.get_view_control()
            ctr.set_zoom(0.8)
            
            # Capture image
            vis.poll_events()
            vis.update_renderer()
            vis.capture_screen_image(output_path)
            
            vis.destroy_window()
            self.logger.info(f"Saved screenshot to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error creating screenshot: {e}")
            raise RenderingError(f"Screenshot creation failed: {e}")
            
    def create_rotating_animation(self, point_cloud: o3d.geometry.PointCloud, 
                                mesh: Optional[o3d.geometry.TriangleMesh], 
                                output_dir: str, 
                                frames: int = 30) -> None:
        """
        Create a rotating animation of the 3D model.
        
        Args:
            point_cloud: Point cloud to visualize
            mesh: Mesh to visualize (optional)
            output_dir: Directory to save the animation frames
            frames: Number of frames in the animation
            
        Raises:
            RenderingError: If animation creation fails
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Create visualizer
            vis = o3d.visualization.Visualizer()
            vis.create_window(visible=False)
            
            # Configure visualizer
            opt = vis.get_render_option()
            opt.background_color = np.array([0.1, 0.1, 0.1])
            opt.point_size = self.config.get('point_size', 2.0)
            
            # Add geometries
            vis.add_geometry(point_cloud)
            if mesh is not None:
                vis.add_geometry(mesh)
                
            # Set initial view
            ctr = vis.get_view_control()
            ctr.set_zoom(0.8)
            
            # Create frames
            for i in range(frames):
                # Rotate view
                angle = i * 360.0 / frames
                ctr.rotate(angle, 0.0)
                
                # Capture image
                vis.poll_events()
                vis.update_renderer()
                vis.capture_screen_image(os.path.join(output_dir, f"frame_{i:04d}.png"))
                
            vis.destroy_window()
            self.logger.info(f"Saved animation frames to {output_dir}")
            
        except Exception as e:
            self.logger.error(f"Error creating animation: {e}")
            raise RenderingError(f"Animation creation failed: {e}")
            
    def export_to_web(self, point_cloud: o3d.geometry.PointCloud, 
                     mesh: Optional[o3d.geometry.TriangleMesh], 
                     output_dir: str) -> None:
        """
        Export 3D model for web visualization.
        
        Args:
            point_cloud: Point cloud to export
            mesh: Mesh to export (optional)
            output_dir: Directory to save the exported files
            
        Raises:
            RenderingError: If export fails
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Save as OBJ for web visualization
            if mesh is not None:
                mesh_path = os.path.join(output_dir, "model.obj")
                o3d.io.write_triangle_mesh(mesh_path, mesh)
                
            # Save point cloud as PLY for web visualization
            pc_path = os.path.join(output_dir, "point_cloud.ply")
            o3d.io.write_point_cloud(pc_path, point_cloud)
            
            # Create a simple HTML viewer (optional)
            html_content = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>The Eyes - 3D Model Viewer</title>
                <style>
                    body { margin: 0; overflow: hidden; }
                    canvas { width: 100%; height: 100%; display: block; }
                </style>
            </head>
            <body>
                <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/build/three.min.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/controls/OrbitControls.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/loaders/PLYLoader.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/loaders/OBJLoader.js"></script>
                <script>
                    let scene, camera, renderer, controls;
                    
                    function init() {
                        // Create scene
                        scene = new THREE.Scene();
                        scene.background = new THREE.Color(0x111111);
                        
                        // Create camera
                        camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
                        camera.position.z = 5;
                        
                        // Create renderer
                        renderer = new THREE.WebGLRenderer({ antialias: true });
                        renderer.setSize(window.innerWidth, window.innerHeight);
                        document.body.appendChild(renderer.domElement);
                        
                        // Create controls
                        controls = new THREE.OrbitControls(camera, renderer.domElement);
                        controls.enableDamping = true;
                        controls.dampingFactor = 0.25;
                        
                        // Add lights
                        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
                        scene.add(ambientLight);
                        
                        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
                        directionalLight.position.set(1, 1, 1);
                        scene.add(directionalLight);
                        
                        // Load models
                        loadPointCloud();
                        loadMesh();
                        
                        // Handle window resize
                        window.addEventListener('resize', onWindowResize, false);
                        
                        // Start animation loop
                        animate();
                    }
                    
                    function loadPointCloud() {
                        const loader = new THREE.PLYLoader();
                        loader.load('point_cloud.ply', function(geometry) {
                            geometry.computeVertexNormals();
                            
                            const material = new THREE.PointsMaterial({
                                size: 0.05,
                                vertexColors: true
                            });
                            
                            const points = new THREE.Points(geometry, material);
                            scene.add(points);
                        });
                    }
                    
                    function loadMesh() {
                        const loader = new THREE.OBJLoader();
                        loader.load('model.obj', function(object) {
                            object.traverse(function(child) {
                                if (child instanceof THREE.Mesh) {
                                    child.material = new THREE.MeshPhongMaterial({
                                        color: 0xaaaaaa,
                                        flatShading: true
                                    });
                                }
                            });
                            
                            scene.add(object);
                        });
                    }
                    
                    function onWindowResize() {
                        camera.aspect = window.innerWidth / window.innerHeight;
                        camera.updateProjectionMatrix();
                        renderer.setSize(window.innerWidth, window.innerHeight);
                    }
                    
                    function animate() {
                        requestAnimationFrame(animate);
                        controls.update();
                        renderer.render(scene, camera);
                    }
                    
                    // Initialize the viewer
                    init();
                </script>
            </body>
            </html>
            """
            
            # Save HTML viewer
            with open(os.path.join(output_dir, "viewer.html"), "w") as f:
                f.write(html_content)
                
            self.logger.info(f"Exported 3D model for web visualization to {output_dir}")
            
        except Exception as e:
            self.logger.error(f"Error exporting model for web: {e}")
            raise RenderingError(f"Web export failed: {e}") 