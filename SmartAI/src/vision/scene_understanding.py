"""
Scene Understanding using Color Segmentation and Edge Detection
Provides semantic information about the environment for path planning
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SceneElement(Enum):
    """Types of scene elements"""
    OPEN_SPACE = "open_space"
    WALL = "wall"
    DOOR = "door"
    OBSTACLE = "obstacle"
    FLOOR = "floor"
    CEILING = "ceiling"
    UNKNOWN = "unknown"

@dataclass
class SceneRegion:
    """Represents a region in the scene"""
    element_type: SceneElement
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    confidence: float
    color: Tuple[int, int, int]  # BGR color for visualization
    properties: Dict[str, float]  # Additional properties (area, aspect_ratio, etc.)

class SceneUnderstanding:
    """Scene understanding using computer vision techniques"""
    
    def __init__(self, frame_width: int = 640, frame_height: int = 480):
        """
        Initialize scene understanding
        
        Args:
            frame_width: Frame width in pixels
            frame_height: Frame height in pixels
        """
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        # Color ranges for different scene elements (HSV)
        self.color_ranges = {
            SceneElement.FLOOR: [
                ((0, 0, 100), (180, 30, 255)),  # Light colors (floors, walls)
            ],
            SceneElement.WALL: [
                ((0, 0, 50), (180, 50, 200)),   # Grayish colors
            ],
            SceneElement.DOOR: [
                ((0, 0, 0), (180, 255, 100)),   # Dark colors
            ],
            SceneElement.OBSTACLE: [
                ((0, 50, 50), (180, 255, 255)),  # Saturated colors
            ]
        }
        
        # Edge detection parameters
        self.edge_threshold1 = 50
        self.edge_threshold2 = 150
        
        # Region analysis parameters
        self.min_region_area = 1000
        self.max_region_area = 50000
        
        # Scene map (grid-based representation)
        self.scene_grid = None
        self.grid_size = 20  # pixels per grid cell
        
        logger.info("Scene understanding initialized")
    
    def process_frame(self, frame: np.ndarray) -> Dict[str, any]:
        """
        Process frame and extract scene understanding
        
        Args:
            frame: Current frame (BGR format)
            
        Returns:
            Dictionary containing scene analysis results
        """
        try:
            # Convert to HSV for better color segmentation
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Detect scene elements
            regions = self._detect_scene_regions(hsv, frame)
            
            # Analyze spatial relationships
            spatial_analysis = self._analyze_spatial_relationships(regions)
            
            # Generate scene map
            scene_map = self._generate_scene_map(regions, frame.shape)
            
            # Analyze navigation-relevant features
            navigation_features = self._analyze_navigation_features(regions, frame)
            
            return {
                'regions': regions,
                'spatial_analysis': spatial_analysis,
                'scene_map': scene_map,
                'navigation_features': navigation_features,
                'frame_processed': frame.copy()
            }
            
        except Exception as e:
            logger.error(f"Error in scene understanding: {e}")
            return {
                'regions': [],
                'spatial_analysis': {},
                'scene_map': None,
                'navigation_features': {},
                'frame_processed': frame.copy()
            }
    
    def _detect_scene_regions(self, hsv: np.ndarray, frame: np.ndarray) -> List[SceneRegion]:
        """Detect scene regions using color segmentation and edge detection"""
        regions = []
        
        # Detect edges
        edges = cv2.Canny(frame, self.edge_threshold1, self.edge_threshold2)
        
        # Find contours from edges
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_region_area or area > self.max_region_area:
                continue
            
            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # Analyze region properties
            region_props = self._analyze_region_properties(contour, hsv, frame)
            
            # Classify region
            element_type, confidence = self._classify_region(region_props, hsv[y:y+h, x:x+w])
            
            # Create region object
            region = SceneRegion(
                element_type=element_type,
                bbox=(x, y, w, h),
                confidence=confidence,
                color=self._get_region_color(element_type),
                properties=region_props
            )
            
            regions.append(region)
        
        return regions
    
    def _analyze_region_properties(self, contour: np.ndarray, hsv: np.ndarray, frame: np.ndarray) -> Dict[str, float]:
        """Analyze properties of a region"""
        # Get region mask
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.fillPoly(mask, [contour], 255)
        
        # Calculate properties
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        
        # Aspect ratio
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / h if h > 0 else 0
        
        # Circularity
        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
        
        # Color statistics
        mean_color = cv2.mean(hsv, mask=mask)
        
        # Edge density
        edges = cv2.Canny(frame, self.edge_threshold1, self.edge_threshold2)
        edge_density = cv2.countNonZero(cv2.bitwise_and(edges, mask)) / area if area > 0 else 0
        
        return {
            'area': area,
            'perimeter': perimeter,
            'aspect_ratio': aspect_ratio,
            'circularity': circularity,
            'mean_hue': mean_color[0],
            'mean_saturation': mean_color[1],
            'mean_value': mean_color[2],
            'edge_density': edge_density
        }
    
    def _classify_region(self, properties: Dict[str, float], region_hsv: np.ndarray) -> Tuple[SceneElement, float]:
        """Classify a region based on its properties"""
        # Default classification
        element_type = SceneElement.UNKNOWN
        confidence = 0.0
        
        # Check color ranges
        for elem_type, color_ranges in self.color_ranges.items():
            for lower, upper in color_ranges:
                mask = cv2.inRange(region_hsv, np.array(lower), np.array(upper))
                color_ratio = np.sum(mask > 0) / (region_hsv.shape[0] * region_hsv.shape[1])
                
                if color_ratio > 0.3:  # At least 30% of region matches color
                    element_type = elem_type
                    confidence = color_ratio
                    break
        
        # Use geometric properties for additional classification
        if properties['aspect_ratio'] > 3.0 and properties['edge_density'] > 0.1:
            # Long, thin regions with many edges are likely walls
            if confidence < 0.5:
                element_type = SceneElement.WALL
                confidence = 0.6
        
        elif properties['circularity'] > 0.7 and properties['area'] > 5000:
            # Circular regions might be obstacles
            if confidence < 0.5:
                element_type = SceneElement.OBSTACLE
                confidence = 0.6
        
        elif properties['edge_density'] < 0.05 and properties['mean_value'] > 150:
            # Low edge density, bright regions are likely open space
            if confidence < 0.5:
                element_type = SceneElement.OPEN_SPACE
                confidence = 0.6
        
        return element_type, confidence
    
    def _get_region_color(self, element_type: SceneElement) -> Tuple[int, int, int]:
        """Get BGR color for visualization"""
        colors = {
            SceneElement.OPEN_SPACE: (0, 255, 0),    # Green
            SceneElement.WALL: (128, 128, 128),      # Gray
            SceneElement.DOOR: (0, 0, 255),          # Red
            SceneElement.OBSTACLE: (0, 165, 255),    # Orange
            SceneElement.FLOOR: (255, 255, 0),       # Cyan
            SceneElement.CEILING: (255, 0, 255),     # Magenta
            SceneElement.UNKNOWN: (128, 128, 128)    # Gray
        }
        return colors.get(element_type, (128, 128, 128))
    
    def _analyze_spatial_relationships(self, regions: List[SceneRegion]) -> Dict[str, any]:
        """Analyze spatial relationships between regions"""
        analysis = {
            'open_paths': [],
            'blocked_areas': [],
            'narrow_passages': [],
            'large_open_areas': []
        }
        
        # Find open paths (regions between walls)
        walls = [r for r in regions if r.element_type == SceneElement.WALL]
        open_spaces = [r for r in regions if r.element_type == SceneElement.OPEN_SPACE]
        
        for open_space in open_spaces:
            # Check if open space is between walls
            x, y, w, h = open_space.bbox
            center_x = x + w // 2
            center_y = y + h // 2
            
            # Count walls on left and right
            walls_left = sum(1 for wall in walls if wall.bbox[0] + wall.bbox[2] < center_x)
            walls_right = sum(1 for wall in walls if wall.bbox[0] > center_x)
            
            if walls_left > 0 and walls_right > 0:
                analysis['open_paths'].append({
                    'region': open_space,
                    'width': w,
                    'height': h
                })
        
        # Find blocked areas (obstacles)
        obstacles = [r for r in regions if r.element_type == SceneElement.OBSTACLE]
        for obstacle in obstacles:
            analysis['blocked_areas'].append({
                'region': obstacle,
                'risk_level': 'high' if obstacle.properties['area'] > 10000 else 'medium'
            })
        
        # Find narrow passages
        for path in analysis['open_paths']:
            if path['width'] < 100:  # Narrow passage threshold
                analysis['narrow_passages'].append(path)
        
        # Find large open areas
        for open_space in open_spaces:
            if open_space.properties['area'] > 20000:  # Large area threshold
                analysis['large_open_areas'].append({
                    'region': open_space,
                    'area': open_space.properties['area']
                })
        
        return analysis
    
    def _generate_scene_map(self, regions: List[SceneRegion], frame_shape: Tuple[int, int, int]) -> np.ndarray:
        """Generate a grid-based scene map"""
        height, width = frame_shape[:2]
        grid_h = height // self.grid_size
        grid_w = width // self.grid_size
        
        scene_map = np.zeros((grid_h, grid_w), dtype=np.uint8)
        
        for region in regions:
            x, y, w, h = region.bbox
            
            # Convert to grid coordinates
            grid_x1 = max(0, x // self.grid_size)
            grid_y1 = max(0, y // self.grid_size)
            grid_x2 = min(grid_w - 1, (x + w) // self.grid_size)
            grid_y2 = min(grid_h - 1, (y + h) // self.grid_size)
            
            # Set grid cells based on region type
            cell_value = self._get_cell_value(region.element_type)
            scene_map[grid_y1:grid_y2+1, grid_x1:grid_x2+1] = cell_value
        
        self.scene_grid = scene_map
        return scene_map
    
    def _get_cell_value(self, element_type: SceneElement) -> int:
        """Get numeric value for grid cell"""
        values = {
            SceneElement.OPEN_SPACE: 0,
            SceneElement.FLOOR: 0,
            SceneElement.WALL: 1,
            SceneElement.OBSTACLE: 2,
            SceneElement.DOOR: 3,
            SceneElement.CEILING: 4,
            SceneElement.UNKNOWN: 5
        }
        return values.get(element_type, 5)
    
    def _analyze_navigation_features(self, regions: List[SceneRegion], frame: np.ndarray) -> Dict[str, any]:
        """Analyze features relevant for navigation"""
        features = {
            'safe_directions': [],
            'hazardous_areas': [],
            'recommended_speed': 1.0,  # 0.0 to 1.0
            'clearance_estimate': 1.0  # meters
        }
        
        # Find safe directions (open spaces in front of robot)
        robot_center_x = frame.shape[1] // 2
        robot_center_y = frame.shape[0] // 2
        
        # Check different directions (front, left, right)
        directions = [
            (0, -1, "forward"),   # Up
            (-1, 0, "left"),      # Left
            (1, 0, "right")       # Right
        ]
        
        for dx, dy, direction_name in directions:
            # Sample points in this direction
            sample_points = []
            for i in range(1, 6):  # Sample 5 points
                x = robot_center_x + dx * i * 50
                y = robot_center_y + dy * i * 50
                if 0 <= x < frame.shape[1] and 0 <= y < frame.shape[0]:
                    sample_points.append((x, y))
            
            # Check if path is clear
            path_clear = True
            min_clearance = float('inf')
            
            for x, y in sample_points:
                # Check what region this point belongs to
                for region in regions:
                    rx, ry, rw, rh = region.bbox
                    if rx <= x <= rx + rw and ry <= y <= ry + rh:
                        if region.element_type in [SceneElement.WALL, SceneElement.OBSTACLE]:
                            path_clear = False
                            break
                        elif region.element_type == SceneElement.OPEN_SPACE:
                            # Calculate clearance
                            clearance = min(x - rx, rx + rw - x, y - ry, ry + rh - y)
                            min_clearance = min(min_clearance, clearance)
            
            if path_clear:
                features['safe_directions'].append({
                    'direction': direction_name,
                    'clearance': min_clearance if min_clearance != float('inf') else 100
                })
        
        # Find hazardous areas (obstacles, narrow passages)
        obstacles = [r for r in regions if r.element_type == SceneElement.OBSTACLE]
        for obstacle in obstacles:
            features['hazardous_areas'].append({
                'type': 'obstacle',
                'bbox': obstacle.bbox,
                'risk_level': 'high' if obstacle.properties['area'] > 10000 else 'medium'
            })
        
        # Adjust recommended speed based on environment
        if features['hazardous_areas']:
            features['recommended_speed'] = 0.3
        elif len(features['safe_directions']) < 2:
            features['recommended_speed'] = 0.6
        else:
            features['recommended_speed'] = 1.0
        
        # Estimate clearance
        if features['safe_directions']:
            min_clearance = min(d['clearance'] for d in features['safe_directions'])
            features['clearance_estimate'] = min_clearance / 100.0  # Convert to meters
        
        return features
    
    def get_status(self) -> dict:
        """Get status information"""
        return {
            'scene_grid_size': self.scene_grid.shape if self.scene_grid is not None else None,
            'grid_cell_size': self.grid_size,
            'frame_dimensions': (self.frame_width, self.frame_height)
        }
    
    def reset(self):
        """Reset scene understanding"""
        self.scene_grid = None
        logger.info("Scene understanding reset") 