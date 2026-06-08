import cv2
import numpy as np
import open3d as o3d
import logging
from typing import Dict, List, Optional, Tuple, Union, Any

class SingleCamReconstructor:
    """Simple visualization for single camera setups - not true 3D reconstruction."""
    
    # Default configuration values for easy modification
    DEFAULT_CONFIG = {
        'feature_detection': {
            'method': 'sift',        # Feature detection method (sift, orb, akaze)
            'max_features': 2000,    # Maximum number of features to detect
            'contrast_threshold': 0.04, # Lower values detect more features (SIFT)
            'edge_threshold': 10,    # Higher values detect more features on edges (SIFT)
            'nOctaveLayers': 3,      # Number of scale layers (SIFT)
        },
        'visualization': {
            'point_size': 5.0,       # Size of points in the point cloud
            'use_color': True,       # Use color from camera feed
            'color_mode': 'rgb',     # Color mode: 'rgb', 'hsv', 'feature_size'
            'min_depth': 0.0,        # Minimum depth value
            'max_depth': 3.0,        # Maximum depth value
            'color_brightness': 1.5, # Brightness multiplier for colors
        }
    }
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Initialize with default values, then override with provided config
        self.feature_config = self.DEFAULT_CONFIG['feature_detection'].copy()
        self.vis_config = self.DEFAULT_CONFIG['visualization'].copy()
        
        # Override defaults with user configuration if provided
        if 'single_cam_feature_detection' in config:
            for key, value in config['single_cam_feature_detection'].items():
                self.feature_config[key] = value
                
        if 'single_cam_visualization' in config:
            for key, value in config['single_cam_visualization'].items():
                self.vis_config[key] = value
        
        self.logger = logging.getLogger("the_eyes.single_cam_reconstructor")
        
        # Create and configure feature detector
        self._create_feature_detector()
        
    def _create_feature_detector(self):
        """Create the feature detector based on configuration."""
        method = self.feature_config.get('method', 'sift').lower()
        
        if method == 'sift':
            self.detector = cv2.SIFT_create(
                nfeatures=self.feature_config.get('max_features', 2000),
                contrastThreshold=self.feature_config.get('contrast_threshold', 0.04),
                edgeThreshold=self.feature_config.get('edge_threshold', 10),
                nOctaveLayers=self.feature_config.get('nOctaveLayers', 3)
            )
        elif method == 'orb':
            self.detector = cv2.ORB_create(
                nfeatures=self.feature_config.get('max_features', 2000),
                scaleFactor=1.2,
                nlevels=8,
                edgeThreshold=31,
                firstLevel=0,
                WTA_K=2
            )
        elif method == 'akaze':
            self.detector = cv2.AKAZE_create(
                descriptor_type=cv2.AKAZE_DESCRIPTOR_MLDB,
                descriptor_size=0,
                descriptor_channels=3,
                threshold=0.001,
                nOctaves=4,
                nOctaveLayers=4
            )
        else:
            self.logger.warning(f"Unknown feature detection method: {method}, falling back to SIFT")
            self.detector = cv2.SIFT_create(nfeatures=self.feature_config.get('max_features', 2000))
        
    def reconstruct(self, image: np.ndarray) -> Tuple[o3d.geometry.PointCloud, Any]:
        """Create a simple point cloud visualization from a single image."""
        try:
            # Store original image for color extraction
            orig_image = image.copy()
            
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
                
            # Detect features to use as points
            keypoints, descriptors = self.detector.detectAndCompute(gray, None)
            
            # Create a point cloud from the keypoints
            point_cloud = o3d.geometry.PointCloud()
            points = []
            colors = []
            
            if len(keypoints) == 0:
                self.logger.warning("No keypoints detected in the image")
                # Create an empty point cloud
                point_cloud.points = o3d.utility.Vector3dVector(np.zeros((0, 3)))
                point_cloud.colors = o3d.utility.Vector3dVector(np.zeros((0, 3)))
                # Return empty feature set
                return point_cloud, None
            
            height, width = gray.shape
            
            # Get depth scale based on keypoint size distribution
            sizes = np.array([kp.size for kp in keypoints])
            min_size = sizes.min()
            max_size = sizes.max()
            size_range = max(max_size - min_size, 1e-6)  # Avoid division by zero
            
            # Configure point cloud settings
            point_size = self.vis_config.get('point_size', 5.0)
            use_color = self.vis_config.get('use_color', True)
            color_mode = self.vis_config.get('color_mode', 'rgb')
            min_depth = self.vis_config.get('min_depth', 0.0)
            max_depth = self.vis_config.get('max_depth', 3.0)
            color_brightness = self.vis_config.get('color_brightness', 1.5)
            
            for kp in keypoints:
                x, y = kp.pt
                # Normalize coordinates
                nx = (x / width - 0.5) * 2
                ny = (y / height - 0.5) * -2  # Flip Y for proper orientation
                
                # Normalize depth based on keypoint size
                normalized_size = (kp.size - min_size) / size_range
                nz = min_depth + normalized_size * (max_depth - min_depth)
                
                points.append([nx, ny, nz])
                
                # Sample color from the original image
                if use_color and len(orig_image.shape) == 3:
                    # Ensure coordinates are within image bounds
                    img_y = min(max(int(y), 0), height - 1)
                    img_x = min(max(int(x), 0), width - 1)
                    
                    if color_mode == 'rgb':
                        # Extract RGB color and normalize
                        b, g, r = orig_image[img_y, img_x] / 255.0
                        # Enhance color brightness
                        r = min(r * color_brightness, 1.0)
                        g = min(g * color_brightness, 1.0)
                        b = min(b * color_brightness, 1.0)
                        colors.append([r, g, b])
                        
                    elif color_mode == 'hsv':
                        # Convert to HSV for more vibrant colors
                        hsv = cv2.cvtColor(np.uint8([[orig_image[img_y, img_x]]]), cv2.COLOR_BGR2HSV)[0][0]
                        h, s, v = hsv
                        # Enhance saturation and value
                        s = min(int(s * 1.2), 255)
                        v = min(int(v * color_brightness), 255)
                        # Convert back to RGB
                        rgb = cv2.cvtColor(np.uint8([[[h, s, v]]]), cv2.COLOR_HSV2RGB)[0][0]
                        colors.append(rgb / 255.0)
                        
                    elif color_mode == 'feature_size':
                        # Color by feature size (larger = more red)
                        normalized_size = (kp.size - min_size) / size_range
                        colors.append([normalized_size, 0.5-normalized_size/2, 1.0-normalized_size])
                        
                else:
                    # Grayscale or no color requested
                    if len(orig_image.shape) == 3:
                        # Get grayscale value
                        val = gray[img_y, img_x] / 255.0
                    else:
                        val = gray[int(y), int(x)] / 255.0
                    colors.append([val, val, val])
            
            point_cloud.points = o3d.utility.Vector3dVector(np.array(points))
            point_cloud.colors = o3d.utility.Vector3dVector(np.array(colors))
            
            # Set the point size
            render_option = o3d.visualization.RenderOption()
            render_option.point_size = point_size
            
            # Create a feature object to return with the keypoints and descriptors
            feature_data = type('FeatureData', (), {})
            feature_data.keypoints = keypoints
            feature_data.descriptors = descriptors
            
            return point_cloud, feature_data
            
        except Exception as e:
            self.logger.error(f"Error in single camera visualization: {e}")
            raise Exception(f"Single camera visualization failed: {e}")
